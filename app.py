# app.py
# ============================================================
# Layered Echo Pack + Replay Mode (Backtest any historical point)
# - Upload Excel/CSV
# - Works on ALL draws (Lunch + Teatime) in file order (sorted by Date if present)
# - Replay Mode lets you choose a historical "current index" i (treated as n-1),
#   then the app generates a NEXT-draw pack as if draw i is the latest known draw.
# ============================================================

from __future__ import annotations
import streamlit as st
import pandas as pd
import numpy as np
from collections import Counter
from typing import List, Optional, Dict, Tuple

st.set_page_config(page_title="Layered Echo Pack + Replay", layout="centered")
st.title("🧠 Layered Echo Pack (Stack2 → n-1 & n-4) + Replay")
st.caption("Replay any historical point to see what the engine would recommend next.")

# -----------------------------
# Load + detect columns
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
    pref = ["n1","n2","n3","n4","n5","n6"]
    if all(p in low for p in pref):
        return [cols[low.index(p)] for p in pref]

    numeric = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() > 0.80:
            numeric.append(c)
    if len(numeric) < 6:
        raise ValueError("Could not detect N1..N6. Rename to N1..N6 or ensure 6 numeric columns exist.")
    return numeric[:6]

def sorted_all_draws(df: pd.DataFrame, date_col: Optional[str]) -> pd.DataFrame:
    dff = df.copy()
    if date_col:
        dff[date_col] = pd.to_datetime(dff[date_col], errors="coerce")
        dff = dff.dropna(subset=[date_col]).copy()
        dff["_row"] = np.arange(len(dff))
        dff = dff.sort_values([date_col, "_row"])
    else:
        dff["_row"] = np.arange(len(dff))
        dff = dff.sort_values(["_row"])
    return dff

def to_draw_list(df: pd.DataFrame, main_cols: List[str]) -> List[List[int]]:
    draws = []
    for _, row in df.iterrows():
        nums = pd.to_numeric(row[main_cols], errors="coerce").dropna().astype(int).tolist()
        if len(nums) == 6 and all(1 <= n <= 49 for n in nums):
            draws.append(nums)
    if len(draws) < 6:
        raise ValueError("Need at least 6 valid draws for n-4 logic.")
    return draws

# -----------------------------
# 20–39 anchors (rolling-gap)
# -----------------------------
BANDS: Dict[str, Tuple[int,int]] = {"20–29": (20, 29), "30–39": (30, 39)}
BAND_20_39 = set(range(20, 40))
BAND_OUTSIDE = set(range(1, 50)) - BAND_20_39

def rolling_gap_anchor(draws: List[List[int]], lo: int, hi: int, window: int, exclude_recent: Optional[List[int]] = None) -> int:
    recent = draws[-window:] if len(draws) >= window else draws
    last_seen = {}
    for i, d in enumerate(recent):
        for n in d:
            if lo <= n <= hi:
                last_seen[n] = i

    candidates = list(range(lo, hi + 1))
    if exclude_recent:
        ex = set(exclude_recent)
        filtered = [n for n in candidates if n not in ex]
        if filtered:
            candidates = filtered

    last_i = len(recent) - 1
    center = (lo + hi) / 2

    def score(n: int):
        gap = (last_i - last_seen[n]) if n in last_seen else (window + 1)
        return (gap, -abs(n - center))

    return max(candidates, key=score)

def compute_20_39_anchors(draws: List[List[int]], window: int, exclude_latest: bool = True) -> List[int]:
    latest = draws[-1]
    ex = latest if exclude_latest else None
    a20 = rolling_gap_anchor(draws, *BANDS["20–29"], window=window, exclude_recent=ex)
    a30 = rolling_gap_anchor(draws, *BANDS["30–39"], window=window, exclude_recent=ex)
    return [a20, a30]

# -----------------------------
# Stack2 trigger + Pack builder
# -----------------------------
def stack2_triggers(draws: List[List[int]]) -> bool:
    # Trigger computed from latest-known history:
    # n-1 shares 0 with n-2 and 0 with n-3
    n1 = set(draws[-1])
    n2 = set(draws[-2])
    n3 = set(draws[-3])
    return len(n1 & n2) == 0 and len(n1 & n3) == 0

def pick_echo_candidates(draws: List[List[int]]) -> Dict[str, List[int]]:
    n1 = set(draws[-1])
    n4 = set(draws[-4])
    return {
        "n1_out": sorted(list(n1 & BAND_OUTSIDE)),
        "n4_out": sorted(list(n4 & BAND_OUTSIDE)),
        "n1_in":  sorted(list(n1 & BAND_20_39)),
        "n4_in":  sorted(list(n4 & BAND_20_39)),
    }

def build_next_pack(draws: List[List[int]], window: int, exclude_latest_anchors: bool) -> Dict:
    anchors = compute_20_39_anchors(draws, window=window, exclude_latest=exclude_latest_anchors)
    trig = stack2_triggers(draws)
    echoes = pick_echo_candidates(draws)

    pack: List[int] = []
    notes: List[str] = []

    if trig:
        notes.append("✅ Stack2 TRIGGERED (n−1 shares 0 with n−2 and n−3). Bias echoes OUTSIDE 20–39.")

        # 1 from n-1 (prefer outside)
        if echoes["n1_out"]:
            pick = echoes["n1_out"][0]
            pack.append(pick); notes.append(f"Picked n−1 OUTSIDE 20–39: {pick}")
        elif echoes["n1_in"]:
            pick = echoes["n1_in"][0]
            pack.append(pick); notes.append(f"Fallback n−1 INSIDE 20–39: {pick}")

        # 1 from n-4 (prefer outside)
        if echoes["n4_out"]:
            pick = echoes["n4_out"][-1]
            if pick not in pack:
                pack.append(pick)
            notes.append(f"Picked n−4 OUTSIDE 20–39: {pick}")
        elif echoes["n4_in"]:
            pick = echoes["n4_in"][-1]
            if pick not in pack:
                pack.append(pick)
            notes.append(f"Fallback n−4 INSIDE 20–39: {pick}")
    else:
        notes.append("❌ Stack2 not triggered. Using anchors + neutral fill.")

    # Add anchors
    for a in anchors:
        if a not in pack:
            pack.append(a)
    notes.append(f"Added 20–39 anchors: {anchors}")

    # Fill remaining slots with high-gap OUTSIDE 20–39
    last_seen = {}
    for i, d in enumerate(draws):
        for n in d:
            last_seen[n] = i
    cur_i = len(draws) - 1

    outside_candidates = [n for n in range(1, 50) if (n in BAND_OUTSIDE) and (n not in pack)]

    def gap_score(n: int):
        gap = (cur_i - last_seen[n]) if n in last_seen else (cur_i + 1)
        return (gap, -abs(n - 25))

    outside_candidates.sort(key=lambda n: gap_score(n), reverse=True)

    while len(pack) < 6 and outside_candidates:
        pack.append(outside_candidates.pop(0))

    pack = sorted(pack)
    return {"stack2_triggered": trig, "pack": pack, "anchors_20_39": anchors, "echo_candidates": echoes, "notes": notes}

# ============================================================
# UI
# ============================================================
uploaded = st.file_uploader("Upload your historical sheet", type=["xlsx", "xls", "csv"])
if not uploaded:
    st.info("Upload a file to start.")
    st.stop()

try:
    df = load_file(uploaded)
    date_col = detect_date_col(df)
    main_cols = detect_main_cols(df)
    dff = sorted_all_draws(df, date_col)
    all_draws = to_draw_list(dff, main_cols)

    st.success(f"Parsed valid draws: {len(all_draws)}")
    st.write("Detected main columns:", main_cols)

    with st.expander("Settings", expanded=True):
        window = st.slider("Rolling window for 20–39 anchors", 10, 60, 20, 1)
        exclude_latest_anchors = st.toggle("Exclude latest draw numbers from anchor selection", value=True)

        replay = st.toggle("Replay mode (backtest any historical point)", value=True)
        # We need at least 4 history draws behind the "current" draw to compute n-4,
        # and we need a "next" draw to compare if you want to score it.
        max_i = len(all_draws) - 2  # leave 1 draw ahead for evaluation
        min_i = 4                  # ensures n-4 exists for the slice
        i = st.slider("Choose current draw index (treated as n−1)", min_i, max_i, max_i)

        show_eval = st.toggle("Show evaluation vs the actual next draw (n)", value=True)

    # Slice history as if draw i is the latest known draw
    history = all_draws[: i + 1]           # up to and including i (n-1)
    actual_next = all_draws[i + 1]         # draw i+1 (n)

    st.subheader("Context (Replay State)")
    st.write(f"Current index (n−1): {i}   |   Next index (n): {i+1}")
    st.write("n−1:", history[-1])
    st.write("n−2:", history[-2])
    st.write("n−3:", history[-3])
    st.write("n−4:", history[-4])

    result = build_next_pack(history, window=window, exclude_latest_anchors=exclude_latest_anchors)

    st.subheader("Engine Output")
    st.write("Stack2 Triggered:", "✅ YES" if result["stack2_triggered"] else "❌ NO")
    st.markdown("### Recommended NEXT pack")
    st.markdown("**" + "  •  ".join(map(str, result["pack"])) + "**")

    with st.expander("Notes / reasoning", expanded=False):
        for n in result["notes"]:
            st.write("•", n)

    with st.expander("Echo candidates (debug)", expanded=False):
        st.json(result["echo_candidates"])

    # Optional evaluation
    if show_eval:
        st.subheader("Evaluation vs Actual Next Draw")
        st.write("Actual next draw (n):", actual_next)

        pred_set = set(result["pack"])
        actual_set = set(actual_next)

        matches = sorted(list(pred_set & actual_set))
        st.write(f"Matches ({len(matches)}):", matches)

        # Also show if the layered echo events occurred in reality
        n1 = set(history[-1])
        n4 = set(history[-4])
        rep_n1 = sorted(list(actual_set & n1))
        rep_n4 = sorted(list(actual_set & n4))

        st.write("Actual repeats from n−1:", rep_n1 if rep_n1 else "None")
        st.write("Actual repeats from n−4:", rep_n4 if rep_n4 else "None")

except Exception as e:
    st.error(f"Error: {e}")
