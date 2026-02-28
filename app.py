# app.py
# ============================================================
# Band-Balanced Duo Engine (Rolling-20 Gap Overlay) + Replay Winner
# - Upload Excel/CSV historical draws
# - Uses MAIN 6 numbers only (bonus excluded by default)
# - Builds 5 band anchors using "last 20 draws" gap logic (Method B)
# - Generates EXACT 4 duos using fixed band-balanced template
# - Includes:
#   ✅ Sheet fingerprint (prove file didn't change)
#   🔁 Replay Winner Anchors toggle
#   🏆 Save current anchors as Winner button
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
st.set_page_config(page_title="Band-Balanced Duo Engine", layout="centered")
st.title("🎯 Band-Balanced Duo Engine")
st.caption("Rolling-20 Gap Anchors (B) + Replay Winner + Fixed 4-Duo Template")

# ----------------------------
# SETTINGS
# ----------------------------
with st.expander("Settings", expanded=True):
    WINDOW = st.slider("Rolling gap window (draws)", 10, 60, 20, 1)
    EXCLUDE_LATEST = st.toggle("Exclude latest draw numbers when picking anchors", value=True)
    INCLUDE_BONUS = st.toggle("Include bonus in calculations (optional)", value=False)

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
    """
    Detect the 6 main-number columns.
    Preferred headers: N1..N6 or Num1..Num6
    Fallback: first 6 columns that are mostly numeric.
    """
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
            "Could not detect 6 main-number columns. "
            "Rename your headers to N1..N6 (recommended) or ensure you have 6 numeric columns."
        )
    return numeric_candidates[:6]

def detect_bonus_col(df: pd.DataFrame) -> Optional[str]:
    """
    Optional: try to find a bonus column.
    Common names: Bonus, BB, bonus_ball
    """
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("bonus", "bb", "bonusball", "bonus_ball", "bonus ball"):
            return c
    # fallback: any column containing 'bonus'
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

        # Basic sanity: keep only values in 1..49
        if all(1 <= n <= 49 for n in nums) and len(nums) in (6, 7):
            draws.append(nums)

    if not draws:
        raise ValueError("No valid draws parsed. Check your file format and numeric columns.")
    return draws

def rolling_gap_anchor(
    draws: List[List[int]],
    band_lo: int,
    band_hi: int,
    window: int,
    freq: Counter,
    exclude_recent_draw: Optional[List[int]] = None,
) -> int:
    """
    Method B: Rolling window = last `window` draws.
    For each number in band, gap = draws since last seen in window; if never seen => window+1.
    Pick max gap; tie-break by overall frequency; then by closeness to band center.
    """
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

def build_four_duos(anchors: Dict[str, int]) -> List[Tuple[int, int]]:
    """
    EXACT 4 duos (fixed template):
      1) (20–29) & (1–9)
      2) (20–29) & (30–39)
      3) (10–19) & (30–39)
      4) (20–29) & (40–49)
    """
    a20 = anchors["20–29"]
    a1  = anchors["1–9"]
    a10 = anchors["10–19"]
    a30 = anchors["30–39"]
    a40 = anchors["40–49"]

    duos = [
        tuple(sorted((a20, a1))),
        tuple(sorted((a20, a30))),
        tuple(sorted((a10, a30))),
        tuple(sorted((a20, a40))),
    ]

    # unique, ordered
    out: List[Tuple[int, int]] = []
    seen = set()
    for d in duos:
        if d[0] != d[1] and d not in seen:
            seen.add(d)
            out.append(d)
    return out

# ----------------------------
# SESSION STATE: WINNER ANCHORS
# ----------------------------
if "winner_anchors" not in st.session_state:
    st.session_state.winner_anchors = None

# ----------------------------
# MAIN RUN
# ----------------------------
if not uploaded:
    st.info("Upload your historical draw file to generate anchors + 4 duos.")
    st.stop()

try:
    df = load_file(uploaded)
    main_cols = detect_main_cols(df)
    bonus_col = detect_bonus_col(df)

    # Use full df (no lunchtime filter unless you add one)
    df_use = df.copy()

    # Fingerprint to prove file unchanged
    try:
        raw = df_use.to_csv(index=False).encode("utf-8")
        st.caption(f"📌 Sheet fingerprint (MD5): {hashlib.md5(raw).hexdigest()}")
    except Exception:
        st.caption("📌 Sheet fingerprint unavailable (could not serialize).")

    st.caption(f"Detected main columns: {', '.join(map(str, main_cols))}")
    if INCLUDE_BONUS and bonus_col:
        st.caption(f"Bonus column detected: {bonus_col} (included in calculations)")
    elif INCLUDE_BONUS and not bonus_col:
        st.warning("Bonus include is ON but no bonus column was detected. Using main 6 only.")
        INCLUDE_BONUS = False

    draws = parse_draws(df_use, main_cols, bonus_col, INCLUDE_BONUS)

    latest_draw = draws[-1]
    # If bonus included, latest_draw may have 7 values; exclude_latest should exclude all of them
    st.write("Latest draw detected:", latest_draw)

    # Frequency map (over all numbers included)
    freq = Counter()
    for d in draws:
        freq.update(d)

    # Replay + Save controls
    col1, col2 = st.columns(2)
    with col1:
        replay_mode = st.toggle(
            "🔁 Replay Winner Anchors",
            value=False,
            help="ON = use saved winner anchors exactly. OFF = compute anchors from rolling window."
        )
    with col2:
        save_winner = st.button(
            "🏆 Save current anchors as Winner",
            help="Saves the currently computed anchors so you can replay them later."
        )

    # Compute anchors
    exclude = latest_draw if EXCLUDE_LATEST else None

    anchors: Optional[Dict[str, int]] = None

    if replay_mode:
        if st.session_state.winner_anchors is None:
            st.warning("No winner anchors saved yet. Turn off Replay, compute anchors, then press Save.")
        else:
            anchors = st.session_state.winner_anchors
    else:
        anchors = {}
        for band_name, (lo, hi) in BANDS.items():
            anchors[band_name] = rolling_gap_anchor(
                draws=draws,
                band_lo=lo,
                band_hi=hi,
                window=WINDOW,
                freq=freq,
                exclude_recent_draw=exclude,
            )
        if save_winner:
            st.session_state.winner_anchors = anchors.copy()
            st.success(f"Winner anchors saved: {st.session_state.winner_anchors}")

    if anchors:
        st.subheader("Band anchors in use")
        st.write(anchors)

        duos = build_four_duos(anchors)
        st.subheader("✅ Locked 4 Duos")
        for i, (a, b) in enumerate(duos, start=1):
            st.markdown(f"**{i}. {a} & {b}**")

        st.caption(
            "Algorithm: Rolling-window gap anchors per band (window size above), "
            "optional exclusion of latest draw, then fixed 4-duo template."
        )

except Exception as e:
    st.error(f"Error: {e}")
