# app.py
# ============================================================
# Band-Balanced Duo Engine (Rolling-20 Gap Overlay) + Replay Winner
# + Aggressive Duo Engineering (4 / 8 / 12 duos) in ONE unified file
#
# What it does:
# 1) Upload Excel/CSV historical draws
# 2) Uses MAIN 6 numbers (bonus excluded by default; optional include)
# 3) Computes band anchors using Rolling WINDOW gap scoring (Method B)
# 4) Builds:
#    - Standard 4 duos (fixed template)
#    - Aggressive duo pack (8 or 12) using top-2 anchors per band + hub expansion
# 5) Includes:
#    ✅ Sheet fingerprint (MD5)
#    🔁 Replay Winner Anchors toggle (locks 8,17,26,34,42)
#    🏆 Save current anchors as Winner button (saves current computed anchors)
# ============================================================

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# ----------------------------
# PAGE
# ----------------------------
st.set_page_config(page_title="Aggressive Duo Engine", layout="centered")
st.title("🎯 Aggressive Duo Engine")
st.caption("Rolling Window Gap Anchors (B) • Replay Winner • Standard + Aggressive Duo Packs")

# ----------------------------
# BANDS
# ----------------------------
BANDS: Dict[str, Tuple[int, int]] = {
    "1–9": (1, 9),
    "10–19": (10, 19),
    "20–29": (20, 29),
    "30–39": (30, 39),
    "40–49": (40, 49),
}

# Your known successful set (optional replay)
REPLAY_ANCHORS = {
    "1–9": 8,
    "10–19": 17,
    "20–29": 26,
    "30–39": 34,
    "40–49": 42,
}

# ----------------------------
# SETTINGS
# ----------------------------
with st.expander("Settings", expanded=True):
    WINDOW = st.slider("Rolling gap window (draws)", 10, 60, 20, 1)
    EXCLUDE_LATEST = st.toggle("Exclude latest draw numbers when picking anchors", value=True)
    INCLUDE_BONUS = st.toggle("Include bonus in calculations (optional)", value=False)

    st.divider()
    mode = st.radio("Output Mode", ["Standard (4 duos)", "Aggressive (8/12 duos)"], index=0)
    if mode.startswith("Aggressive"):
        DUO_COUNT = st.selectbox("Aggressive Duo Count", [8, 12], index=1)
    else:
        DUO_COUNT = 4

# ----------------------------
# FILE UPLOAD
# ----------------------------
uploaded = st.file_uploader("Upload historical draws (.xlsx/.csv)", type=["xlsx", "xls", "csv"])

def load_file(up) -> pd.DataFrame:
    name = up.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(up)
    if name.endswith(".csv"):
        return pd.read_csv(up)
    raise ValueError("Please upload an Excel (.xlsx/.xls) or CSV (.csv) file.")

def detect_main_cols(df: pd.DataFrame) -> List[str]:
    cols = list(df.columns)
    low = [str(c).strip().lower() for c in cols]

    preferred_sets = [
        ["n1","n2","n3","n4","n5","n6"],
        ["num1","num2","num3","num4","num5","num6"],
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
            "Could not detect 6 main-number columns. "
            "Rename headers to N1..N6 (recommended) or ensure you have 6 numeric columns."
        )
    return numeric_candidates[:6]

def detect_bonus_col(df: pd.DataFrame) -> Optional[str]:
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("bonus", "bb", "bonusball", "bonus_ball", "bonus ball"):
            return c
    for c in df.columns:
        if "bonus" in str(c).strip().lower():
            return c
    return None

def parse_draws(df: pd.DataFrame, main_cols: List[str], bonus_col: Optional[str], include_bonus: bool) -> List[List[int]]:
    draws: List[List[int]] = []
    for _, row in df.iterrows():
        try:
            nums = [int(row[c]) for c in main_cols]
            if include_bonus and bonus_col is not None:
                nums.append(int(row[bonus_col]))
        except Exception:
            continue

        if len(nums) in (6, 7) and all(1 <= n <= 49 for n in nums):
            draws.append(nums)

    if not draws:
        raise ValueError("No valid draws parsed. Check your sheet: 6 main numbers per row.")
    return draws

# ----------------------------
# SCORING: Rolling gap anchors (Method B)
# ----------------------------
def band_candidates(lo: int, hi: int) -> List[int]:
    return list(range(lo, hi + 1))

def rolling_gap_scores(
    draws: List[List[int]],
    lo: int,
    hi: int,
    window: int,
    freq: Counter,
    exclude_recent_draw: Optional[List[int]] = None,
) -> Dict[int, Tuple[int, int, float]]:
    """
    Returns dict: number -> score tuple (gap, freq, -abs(center_dist))
    Higher is better lexicographically.
    gap: draws since last seen in window; if never seen => window+1
    """
    window_draws = draws[-window:] if len(draws) >= window else draws
    last_seen: Dict[int, int] = {}
    for i, d in enumerate(window_draws):
        for n in d:
            if lo <= n <= hi:
                last_seen[n] = i

    last_i = len(window_draws) - 1
    center = (lo + hi) / 2

    scores: Dict[int, Tuple[int, int, float]] = {}
    for n in band_candidates(lo, hi):
        if exclude_recent_draw and n in set(exclude_recent_draw):
            # We'll still score it, but later we can decide to filter out
            pass
        gap = (last_i - last_seen[n]) if n in last_seen else (window + 1)
        scores[n] = (gap, freq.get(n, 0), -abs(n - center))
    return scores

def top_k_anchors_for_band(
    draws: List[List[int]],
    band_lo: int,
    band_hi: int,
    window: int,
    freq: Counter,
    exclude_recent_draw: Optional[List[int]],
    k: int = 2,
) -> List[int]:
    scores = rolling_gap_scores(draws, band_lo, band_hi, window, freq, exclude_recent_draw)
    candidates = list(scores.keys())

    # Apply exclude_latest as a filter if possible (but don't empty the band)
    if exclude_recent_draw:
        ex = set(exclude_recent_draw)
        filtered = [n for n in candidates if n not in ex]
        if filtered:
            candidates = filtered

    # Rank by score tuple descending
    ranked = sorted(candidates, key=lambda n: scores[n], reverse=True)
    return ranked[:k]

def compute_top_anchors(
    draws: List[List[int]],
    window: int,
    freq: Counter,
    exclude_recent_draw: Optional[List[int]],
    k: int = 2,
) -> Dict[str, List[int]]:
    out: Dict[str, List[int]] = {}
    for band_name, (lo, hi) in BANDS.items():
        out[band_name] = top_k_anchors_for_band(draws, lo, hi, window, freq, exclude_recent_draw, k=k)
    return out

# ----------------------------
# DUO BUILDERS
# ----------------------------
def uniq_append(duos: List[Tuple[int, int]], a: int, b: int):
    if a == b:
        return
    pair = tuple(sorted((a, b)))
    if pair not in set(duos):
        duos.append(pair)

def build_standard_4_duos(anchors_best: Dict[str, int]) -> List[Tuple[int, int]]:
    """
    EXACT 4 duos (fixed template):
      1) (20–29) & (1–9)
      2) (20–29) & (30–39)
      3) (10–19) & (30–39)
      4) (20–29) & (40–49)
    """
    a20 = anchors_best["20–29"]
    a1  = anchors_best["1–9"]
    a10 = anchors_best["10–19"]
    a30 = anchors_best["30–39"]
    a40 = anchors_best["40–49"]

    duos: List[Tuple[int, int]] = []
    uniq_append(duos, a20, a1)
    uniq_append(duos, a20, a30)
    uniq_append(duos, a10, a30)
    uniq_append(duos, a20, a40)
    return duos

def build_aggressive_duos(anchors_top2: Dict[str, List[int]], duo_count: int) -> List[Tuple[int, int]]:
    """
    Aggressive duo engineering focused on DUO hits:
    - Primary hub: best 20–29 anchor paired widely
    - Secondary hub: best 30–39 anchor paired widely
    Uses top-2 per band to expand coverage without chaos.
    """
    # best & runner-up per band (fallback to best if only one exists)
    def best(b: str) -> int: return anchors_top2[b][0]
    def second(b: str) -> int: return anchors_top2[b][1] if len(anchors_top2[b]) > 1 else anchors_top2[b][0]

    a1_1, a1_2   = best("1–9"),   second("1–9")
    a10_1, a10_2 = best("10–19"), second("10–19")
    a20_1, a20_2 = best("20–29"), second("20–29")
    a30_1, a30_2 = best("30–39"), second("30–39")
    a40_1, a40_2 = best("40–49"), second("40–49")

    duos: List[Tuple[int, int]] = []

    # Pack A: standard 4 (keeps structure)
    uniq_append(duos, a20_1, a1_1)
    uniq_append(duos, a20_1, a30_1)
    uniq_append(duos, a10_1, a30_1)
    uniq_append(duos, a20_1, a40_1)

    if duo_count <= 4:
        return duos[:duo_count]

    # Pack B: expand primary hub (20–29) with second-best anchors in other bands
    uniq_append(duos, a20_1, a1_2)
    uniq_append(duos, a20_1, a30_2)
    uniq_append(duos, a20_1, a40_2)
    uniq_append(duos, a20_1, a10_2)  # extra link to 10–19

    if duo_count <= 8:
        return duos[:duo_count]

    # Pack C: secondary hub (30–39) for hedge coverage if 20 misses
    uniq_append(duos, a30_1, a1_1)
    uniq_append(duos, a30_1, a10_1)
    uniq_append(duos, a30_1, a40_1)
    uniq_append(duos, a30_1, a20_2)  # cross-link into 20–29 runner-up

    # If anything duplicates removed, fill by sensible extra links (still controlled)
    # (Only if needed to reach duo_count)
    fillers = [
        (a20_2, a1_1),
        (a20_2, a30_1),
        (a20_2, a40_1),
        (a10_2, a30_2),
        (a10_1, a40_1),
        (a1_1, a40_1),
    ]
    for x, y in fillers:
        if len(duos) >= duo_count:
            break
        uniq_append(duos, x, y)

    return duos[:duo_count]

# ----------------------------
# SESSION STATE: WINNER ANCHORS
# ----------------------------
if "winner_anchors" not in st.session_state:
    st.session_state.winner_anchors = None

# ----------------------------
# MAIN
# ----------------------------
if not uploaded:
    st.info("Upload your historical draw file to generate anchors + duos.")
    st.stop()

try:
    df = load_file(uploaded)
    main_cols = detect_main_cols(df)
    bonus_col = detect_bonus_col(df)

    # Fingerprint to prove file unchanged
    try:
        raw = df.to_csv(index=False).encode("utf-8")
        st.caption(f"📌 Sheet fingerprint (MD5): {hashlib.md5(raw).hexdigest()}")
    except Exception:
        st.caption("📌 Sheet fingerprint unavailable.")

    st.caption(f"Detected main columns: {', '.join(map(str, main_cols))}")

    if INCLUDE_BONUS and bonus_col:
        st.caption(f"Bonus column detected: {bonus_col} (included)")
    elif INCLUDE_BONUS and not bonus_col:
        st.warning("Bonus include is ON but no bonus column was detected. Using main 6 only.")
        INCLUDE_BONUS = False

    draws = parse_draws(df, main_cols, bonus_col, INCLUDE_BONUS)
    latest_draw = draws[-1]
    st.write("Latest draw detected:", latest_draw)

    # Frequency map over whatever we included (main 6, or main+bonus)
    freq = Counter()
    for d in draws:
        freq.update(d)

    # Replay + Save controls
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        replay_mode = st.toggle("🔁 Replay Winner", value=False)
    with c2:
        save_winner = st.button("🏆 Save Winner")
    with c3:
        load_default_replay = st.button("↩️ Load 8,17,26,34,42")

    # Allow user to quickly load the known successful set into session state
    if load_default_replay:
        st.session_state.winner_anchors = REPLAY_ANCHORS.copy()
        st.success(f"Loaded default replay anchors: {st.session_state.winner_anchors}")

    exclude = latest_draw if EXCLUDE_LATEST else None

    # Decide anchors
    anchors_best: Optional[Dict[str, int]] = None
    anchors_top2: Optional[Dict[str, List[int]]] = None

    if replay_mode:
        if st.session_state.winner_anchors is None:
            st.warning("No winner anchors saved yet. Turn off Replay, compute anchors, then press Save Winner.")
        else:
            anchors_best = st.session_state.winner_anchors
            # For aggressive mode while replaying, create synthetic top2 lists
            anchors_top2 = {k: [v, v] for k, v in anchors_best.items()}
    else:
        # Compute top-2 per band (needed for aggressive mode)
        anchors_top2 = compute_top_anchors(draws, WINDOW, freq, exclude, k=2)
        anchors_best = {band: anchors_top2[band][0] for band in anchors_top2}

        if save_winner:
            st.session_state.winner_anchors = anchors_best.copy()
            st.success(f"Winner anchors saved: {st.session_state.winner_anchors}")

    if anchors_best is None or anchors_top2 is None:
        st.stop()

    st.subheader("Band anchors in use")
    st.write(anchors_best)

    with st.expander("Top-2 per band (for aggressive mode)", expanded=False):
        st.write(anchors_top2)

    # Build duos according to selected mode
    if mode.startswith("Standard"):
        duos = build_standard_4_duos(anchors_best)
    else:
        duos = build_aggressive_duos(anchors_top2, duo_count=DUO_COUNT)

    st.subheader(f"✅ Duos Output ({len(duos)} duos)")
    for i, (a, b) in enumerate(duos, start=1):
        st.markdown(f"**{i}. {a} & {b}**")

    st.caption(
        "Reminder: This is a coverage/discipline engine. It does not guarantee wins. "
        "Best practice: lock a chosen pack for a 3-draw cycle before changing anything."
    )

except Exception as e:
    st.error(f"Error: {e}")
