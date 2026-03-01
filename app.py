# app.py
# ============================================================
# Lunchtime Repeat Engine + 4-Duo Generator (Integrated)
# - Upload Excel/CSV with historical draws (Date + N1..N6 + Bonus optional)
# - Infers Lunchtime as FIRST row per date (or every 2nd row if no date column)
# - Computes best REPEAT candidate from yesterday’s Lunchtime draw (historical conditional repeat rate)
# - Computes 5 band anchors using Rolling WINDOW gap (Method B) from Lunchtime-only history
# - Generates 4 locked duos (template) and injects repeat candidate into the duo set:
#     - If repeat candidate already appears in the 4 duos -> keep as-is
#     - Else replace the LOW-band anchor duo (a20 & a1) with (a20 & repeat_candidate)
#       (keeps the hub stable while forcing the repeat candidate into the pack)
#
# Dependencies: streamlit, pandas, numpy, openpyxl
# ============================================================

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter
from typing import List, Optional, Tuple, Dict

st.set_page_config(page_title="Repeat + Duo Engine", layout="centered")
st.title("🔁🎯 Repeat + Duo Engine (Lunchtime Only)")
st.caption("Repeat engineering + Rolling-gap anchors + 4 locked duos (integrated). No guarantees.")

# -----------------------------
# File loading
# -----------------------------
def load_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    raise ValueError("Upload .xlsx/.xls or .csv")

def detect_date_col(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        if "date" in str(c).strip().lower():
            return c
    return None

def detect_main_cols(df: pd.DataFrame) -> List[str]:
    cols = list(df.columns)
    low = [str(c).strip().lower() for c in cols]

    preferred_sets = [
        ["n1", "n2", "n3", "n4", "n5", "n6"],
        ["num1", "num2", "num3", "num4", "num5", "num6"],
    ]
    for pref in preferred_sets:
        if all(p in low for p in pref):
            return [cols[low.index(p)] for p in pref]

    numeric_candidates = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() >= 0.80:
            numeric_candidates.append(c)

    if len(numeric_candidates) < 6:
        raise ValueError(
            "Could not detect 6 main-number columns. Rename headers to N1..N6 (recommended) "
            "or ensure 6 numeric columns exist."
        )
    return numeric_candidates[:6]

def to_draw_list(df: pd.DataFrame, main_cols: List[str]) -> List[List[int]]:
    draws = []
    for _, row in df.iterrows():
        nums = pd.to_numeric(row[main_cols], errors="coerce").dropna().astype(int).tolist()
        if len(nums) == 6 and all(1 <= n <= 49 for n in nums):
            draws.append(nums)
    if not draws:
        raise ValueError("No valid 6-number draws found after parsing.")
    return draws

# -----------------------------
# Lunchtime-only extraction
# -----------------------------
def lunchtime_only(df: pd.DataFrame, date_col: Optional[str]) -> pd.DataFrame:
    dfx = df.copy()

    if date_col is None:
        # No date column: assume two draws per day in file order
        return dfx.iloc[::2].reset_index(drop=True)

    dfx[date_col] = pd.to_datetime(dfx[date_col], errors="coerce")
    dfx = dfx.dropna(subset=[date_col]).copy()
    dfx["_row_order"] = np.arange(len(dfx))
    dfx = dfx.sort_values([date_col, "_row_order"], ascending=[True, True])

    lunch = dfx.groupby(date_col, as_index=False).head(1).copy()
    lunch = lunch.drop(columns=["_row_order"])
    return lunch.reset_index(drop=True)

# -----------------------------
# Repeat stats
# -----------------------------
def compute_repeat_stats(lunch_draws: List[List[int]]) -> Dict:
    if len(lunch_draws) < 3:
        raise ValueError("Need at least 3 Lunchtime draws to analyze repeats.")

    repeat_counts = []
    appeared_as_prev = Counter()
    repeated_next = Counter()
    last_repeat_idx = {}

    for i in range(len(lunch_draws) - 1):
        prev_set = set(lunch_draws[i])
        next_set = set(lunch_draws[i + 1])
        inter = prev_set.intersection(next_set)

        repeat_counts.append(len(inter))

        for n in prev_set:
            appeared_as_prev[n] += 1
        for n in inter:
            repeated_next[n] += 1
            last_repeat_idx[n] = i

    return {
        "repeat_counts": repeat_counts,
        "repeat_dist": Counter(repeat_counts),
        "appeared_as_prev": appeared_as_prev,
        "repeated_next": repeated_next,
        "last_repeat_idx": last_repeat_idx,
        "num_transitions": len(repeat_counts),
    }

def band_boost(n: int) -> float:
    if 20 <= n <= 39:
        return 0.20
    if 10 <= n <= 19 or 40 <= n <= 49:
        return 0.08
    return 0.00

def rank_yesterday_repeats(
    yesterday: List[int],
    stats: Dict,
    current_transition_index: int,
    min_support: int = 25,
) -> pd.DataFrame:
    appeared = stats["appeared_as_prev"]
    repeated = stats["repeated_next"]
    last_rep = stats["last_repeat_idx"]

    rows = []
    for n in sorted(yesterday):
        a = appeared.get(n, 0)
        r = repeated.get(n, 0)
        p = (r / a) if a > 0 else 0.0

        gap = (current_transition_index - last_rep[n]) if n in last_rep else (current_transition_index + 1)
        recency_score = np.log1p(gap) / 5.0

        support_factor = min(1.0, a / float(min_support))

        score = 0.0
        score += 3.0 * p * support_factor
        score += 0.6 * recency_score
        score += band_boost(n)

        why = [f"P(repeat|present)={p:.3f} (support={a})", f"gap={gap}"]
        if band_boost(n) > 0:
            why.append("band boost")

        rows.append({
            "Number": n,
            "Score": score,
            "Why": "; ".join(why),
            "Support(prev appearances)": a,
            "Repeat hits": r,
        })

    return pd.DataFrame(rows).sort_values("Score", ascending=False).reset_index(drop=True)

# -----------------------------
# Rolling-gap anchors (Method B) from Lunchtime-only history
# -----------------------------
BANDS: Dict[str, Tuple[int, int]] = {
    "1–9": (1, 9),
    "10–19": (10, 19),
    "20–29": (20, 29),
    "30–39": (30, 39),
    "40–49": (40, 49),
}

def rolling_gap_anchor(
    draws: List[List[int]],
    band_lo: int,
    band_hi: int,
    window: int,
    freq: Counter,
    exclude_recent_draw: Optional[List[int]] = None,
) -> int:
    window_draws = draws[-window:] if len(draws) >= window else draws
    last_seen: Dict[int, int] = {}

    for i, d in enumerate(window_draws):
        for n in d:
            if band_lo <= n <= band_hi:
                last_seen[n] = i

    candidates = list(range(band_lo, band_hi + 1))

    if exclude_recent_draw:
        ex = set(exclude_recent_draw)
        filtered = [n for n in candidates if n not in ex]
        if filtered:
            candidates = filtered

    last_i = len(window_draws) - 1
    center = (band_lo + band_hi) / 2

    def score(n: int):
        gap = (last_i - last_seen[n]) if n in last_seen else (window + 1)
        return (gap, freq.get(n, 0), -abs(n - center))

    return max(candidates, key=score)

def compute_band_anchors(
    lunch_draws: List[List[int]],
    window: int,
    exclude_latest: bool,
) -> Dict[str, int]:
    freq = Counter()
    for d in lunch_draws:
        freq.update(d)

    latest = lunch_draws[-1]
    exclude = latest if exclude_latest else None

    anchors = {}
    for band, (lo, hi) in BANDS.items():
        anchors[band] = rolling_gap_anchor(lunch_draws, lo, hi, window, freq, exclude_recent_draw=exclude)
    return anchors

# -----------------------------
# 4 duos + repeat injection
# -----------------------------
def uniq_duos(pairs: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out = []
    seen = set()
    for a, b in pairs:
        p = tuple(sorted((a, b)))
        if p[0] == p[1]:
            continue
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def build_4_duos(anchors: Dict[str, int]) -> List[Tuple[int, int]]:
    a20 = anchors["20–29"]
    a1  = anchors["1–9"]
    a10 = anchors["10–19"]
    a30 = anchors["30–39"]
    a40 = anchors["40–49"]

    duos = [
        (a20, a1),
        (a20, a30),
        (a10, a30),
        (a20, a40),
    ]
    return uniq_duos(duos)

def inject_repeat_into_duos(duos: List[Tuple[int, int]], anchors: Dict[str, int], repeat_num: int) -> Tuple[List[Tuple[int,int]], str]:
    """
    If repeat_num already in any duo => no change.
    Else replace duo (a20, a1) with (a20, repeat_num).
    """
    flat = set([x for p in duos for x in p])
    a20 = anchors["20–29"]
    a1  = anchors["1–9"]

    if repeat_num in flat:
        return duos, "Repeat candidate already covered in duos (no change)."

    # Replace the low-band pair
    new_duos = []
    replaced = False
    for a, b in duos:
        if not replaced and set((a, b)) == set((a20, a1)):
            new_duos.append(tuple(sorted((a20, repeat_num))))
            replaced = True
        else:
            new_duos.append(tuple(sorted((a, b))))

    new_duos = uniq_duos(new_duos)
    return new_duos, f"Injected repeat candidate by replacing ({a20},{a1}) with ({a20},{repeat_num})."

# -----------------------------
# UI
# -----------------------------
uploaded = st.file_uploader("Upload your historical sheet", type=["xlsx", "xls", "csv"])
if not uploaded:
    st.info("Upload a file to start.")
    st.stop()

try:
    df = load_file(uploaded)

    date_col = detect_date_col(df)
    main_cols = detect_main_cols(df)

    st.write("Columns detected:", df.columns.tolist())
    st.success(f"Main columns: {main_cols}")
    st.info(f"Lunchtime inference: {'First row per date' if date_col else 'Every 2nd row (0,2,4,...)'}")

    lunch_df = lunchtime_only(df, date_col)
    lunch_draws = to_draw_list(lunch_df, main_cols)

    st.write(f"Lunchtime draws detected: {len(lunch_draws)}")

    # Settings
    with st.expander("Engine Settings", expanded=True):
        window = st.slider("Rolling gap window (lunchtime draws)", 10, 60, 20, 1)
        exclude_latest = st.toggle("Exclude latest Lunchtime numbers when selecting anchors", value=True)
        min_support = st.slider("Min support before full confidence (repeat engine)", 5, 120, 25, 5)

    # Repeat engine
    st.subheader("1) Repeat Engine Output")
    stats = compute_repeat_stats(lunch_draws)
    yesterday = lunch_draws[-1]
    st.write("Most recent Lunchtime draw (yesterday-set):", yesterday)

    ranked = rank_yesterday_repeats(
        yesterday=yesterday,
        stats=stats,
        current_transition_index=stats["num_transitions"],
        min_support=min_support,
    )

    st.dataframe(ranked, use_container_width=True)

    best_repeat = int(ranked.iloc[0]["Number"])
    backup_repeat = int(ranked.iloc[1]["Number"]) if len(ranked) > 1 else best_repeat

    st.markdown(f"**Best repeat candidate:** `{best_repeat}`")
    st.markdown(f"**Backup repeat candidate:** `{backup_repeat}`")

    # Duo engine
    st.subheader("2) Duo Engine Output (Rolling-gap anchors)")
    anchors = compute_band_anchors(lunch_draws, window=window, exclude_latest=exclude_latest)
    st.write("Band anchors:", anchors)

    base_duos = build_4_duos(anchors)
    st.markdown("### Base 4 duos")
    for i, (a, b) in enumerate(base_duos, start=1):
        st.markdown(f"**{i}. {a} & {b}**")

    # Inject repeat
    st.subheader("3) Integrated Output (Repeat injected)")
    integrated_duos, note = inject_repeat_into_duos(base_duos, anchors, best_repeat)
    st.info(note)

    for i, (a, b) in enumerate(integrated_duos, start=1):
        st.markdown(f"**{i}. {a} & {b}**")

    st.caption(
        "Reminder: This combines two independent ideas: repeat-likelihood (from lunchtime history) "
        "and band-balanced anchor duos (rolling-gap). It does not guarantee wins."
    )

except Exception as e:
    st.error(f"Error: {e}")
