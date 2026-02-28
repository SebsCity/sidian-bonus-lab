# app.py
# ------------------------------------------------------------
# Band-Balanced + Gap-Pressure (Rolling Window) Duo Generator
# Methods used to generate the locked 4 duos:
# 1) Optional: filter to Lunchtime draws if a suitable column exists
# 2) Rolling gap overlay (default last 20 draws): pick 1 "re-entry" anchor per band
#    Bands: 1–9, 10–19, 20–29, 30–39, 40–49
#    Re-entry anchor = number in band with the longest absence in the rolling window
#    (tie-break by historical frequency, then spread)
# 3) Build EXACT 4 duos (band-balanced):
#    - (20–29 anchor) & (1–9 anchor)
#    - (20–29 anchor) & (30–39 anchor)
#    - (10–19 anchor) & (30–39 anchor)
#    - (20–29 anchor) & (40–49 anchor)
# ------------------------------------------------------------

from __future__ import annotations

import streamlit as st
import pandas as pd
from typing import List, Tuple, Dict, Optional
from collections import Counter

st.set_page_config(page_title="Band-Balanced Duo Engine", layout="centered")
st.title("🎯 Band-Balanced Duo Engine (Gap Overlay)")

# -----------------------------
# Helpers: file load
# -----------------------------
def load_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    raise ValueError("Upload .xlsx, .xls, or .csv")

# -----------------------------
# Helpers: detect draw columns
# -----------------------------
def detect_main_cols(df: pd.DataFrame) -> List[str]:
    """
    Detect 6 main number columns.
    Prefers N1..N6 or Num1..Num6 else first 6 mostly-numeric columns.
    """
    cols = list(df.columns)
    low = [str(c).strip().lower() for c in cols]

    preferred = [
        ["n1","n2","n3","n4","n5","n6"],
        ["num1","num2","num3","num4","num5","num6"],
    ]
    for pref in preferred:
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
            "Rename headers to N1..N6 (recommended) or ensure first 6 columns are numeric."
        )
    return numeric_candidates[:6]

def detect_lunchtime_col(df: pd.DataFrame) -> Optional[str]:
    """
    Try to find a column that indicates draw session/type/time, e.g. 'Lunchtime'/'Teatime'.
    We'll look for common names.
    """
    candidates = ["drawtype", "draw_type", "session", "time", "draw time", "draw_time", "game", "type"]
    low_map = {str(c).strip().lower(): c for c in df.columns}
    for k in candidates:
        if k in low_map:
            return low_map[k]
    # also try any column containing these tokens
    for c in df.columns:
        cl = str(c).strip().lower()
        if any(tok in cl for tok in ["lunch", "tea", "session", "drawtype", "draw type", "draw_time", "draw time"]):
            return c
    return None

def parse_draws(df: pd.DataFrame, main_cols: List[str]) -> List[List[int]]:
    draws: List[List[int]] = []
    for _, row in df.iterrows():
        try:
            nums = [int(row[c]) for c in main_cols]
        except Exception:
            continue
        # basic sanity
        if len(nums) == 6 and all(1 <= n <= 49 for n in nums):
            draws.append(nums)
    if not draws:
        raise ValueError("No valid draws parsed. Check your file rows and number ranges.")
    return draws

# -----------------------------
# Band + scoring
# -----------------------------
BANDS: Dict[str, Tuple[int, int]] = {
    "1–9": (1, 9),
    "10–19": (10, 19),
    "20–29": (20, 29),
    "30–39": (30, 39),
    "40–49": (40, 49),
}

def band_of(n: int) -> Optional[str]:
    for name, (lo, hi) in BANDS.items():
        if lo <= n <= hi:
            return name
    return None

def historical_freq(draws: List[List[int]]) -> Counter:
    cnt = Counter()
    for d in draws:
        cnt.update(d)
    return cnt

def rolling_gap_anchor(
    draws: List[List[int]],
    band_lo: int,
    band_hi: int,
    window: int,
    freq: Counter,
    exclude_recent_draw: Optional[List[int]] = None,
) -> int:
    """
    Pick band anchor using rolling gap within last `window` draws:
      gap(n) = number of draws since last occurrence inside window; if not seen in window -> gap = window+1
    Choose max gap; tie-break by higher historical freq; then by larger spread to band center (optional).
    """
    window_draws = draws[-window:] if len(draws) >= window else draws[:]
    seen_last_index: Dict[int, int] = {}
    # index 0..len(window_draws)-1
    for i, d in enumerate(window_draws):
        for n in d:
            if band_lo <= n <= band_hi:
                seen_last_index[n] = i

    candidates = list(range(band_lo, band_hi + 1))
    if exclude_recent_draw:
        exclude_set = set(exclude_recent_draw)
        candidates = [n for n in candidates if n not in exclude_set] or candidates

    last_i = len(window_draws) - 1

    def score(n: int):
        if n in seen_last_index:
            gap = last_i - seen_last_index[n]
        else:
            gap = window + 1
        # tie-breakers: freq, then distance from band center
        center = (band_lo + band_hi) / 2
        return (gap, freq.get(n, 0), abs(n - center))

    return max(candidates, key=score)

def build_four_duos(anchors: Dict[str, int]) -> List[Tuple[int, int]]:
    """
    EXACT 4 duos as per method:
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
    # ensure uniqueness while preserving order
    out, seen = [], set()
    for d in duos:
        if d[0] == d[1]:
            continue
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out

# -----------------------------
# UI
# -----------------------------
uploaded = st.file_uploader("Upload historical draws (.xlsx / .csv)", type=["xlsx", "xls", "csv"])

with st.expander("Settings", expanded=True):
    window = st.slider("Rolling gap window (draws)", 10, 60, 20, 1)
    exclude_last_draw = st.toggle("Exclude numbers from the latest draw when picking anchors", value=True)
    prefer_lunchtime = st.toggle("Filter to Lunchtime (if column exists)", value=True)

if not uploaded:
    st.info("Upload your file to generate the 4 duos.")
    st.stop()

try:
    df = load_file(uploaded)
    main_cols = detect_main_cols(df)
    st.caption(f"Detected main columns: {', '.join(map(str, main_cols))}")

    # Optional Lunchtime filtering
    lunch_col = detect_lunchtime_col(df)
    df_use = df.copy()

    if prefer_lunchtime and lunch_col:
        # Keep rows where lunch_col contains 'lunch'
        s = df_use[lunch_col].astype(str).str.lower()
        df_lunch = df_use[s.str.contains("lunch", na=False)]
        if len(df_lunch) >= 30:  # only apply if we still have enough history
            df_use = df_lunch
            st.caption(f"Filtered to Lunchtime using column: {lunch_col}")
        else:
            st.caption(f"Lunchtime filter found column '{lunch_col}', but not enough rows after filtering; using full dataset.")

    draws = parse_draws(df_use, main_cols)
    freq = historical_freq(draws)

    latest = draws[-1]
    st.write("Latest draw detected:", latest)

    exclude = latest if exclude_last_draw else None

    # Build band anchors via rolling gap overlay
    anchors: Dict[str, int] = {}
    for band_name, (lo, hi) in BANDS.items():
        anchors[band_name] = rolling_gap_anchor(
            draws=draws,
            band_lo=lo,
            band_hi=hi,
            window=window,
            freq=freq,
            exclude_recent_draw=exclude,
        )

    st.subheader("Band anchors (gap overlay)")
    st.write(anchors)

    # Build EXACT 4 duos from the method
    duos = build_four_duos(anchors)

    st.subheader("✅ Locked 4 Duos (Band-balanced + Gap overlay)")
    for i, (a, b) in enumerate(duos, start=1):
        st.markdown(f"**{i}. {a} & {b}**")

    st.caption(
        "Method: rolling-gap anchors per band (window), then fixed 4-duo template "
        "(20–29 paired with 1–9, 30–39, 40–49; plus 10–19 with 30–39)."
    )

except Exception as e:
    st.error(str(e))
