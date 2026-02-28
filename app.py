# app.py
# ============================================================
# Sidian Bonus Lab — Phase Detector (Robust, Cloud-safe)
# - Upload Excel/CSV
# - Auto-detects main number columns (N1..N6 or first 6 numeric)
# - Auto-detects BONUS column (any column containing "bonus")
# - Computes phase: OSCILLATION / EXPANSION / COMPRESSION / MIXED
# - Shows last 20 bonuses on 1–49 grid + arrows labeled 1-2, 2-3, ...
# ============================================================

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ----------------------------
# PAGE
# ----------------------------
st.set_page_config(page_title="Sidian Bonus Lab — Phase Detector", layout="centered")
st.title("🧭 Sidian Bonus Lab — Phase Detector")
st.caption("Directional technique on Bonus Balls: phases + arrow grid")

# ----------------------------
# HELPERS
# ----------------------------
def load_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    raise ValueError("Upload an .xlsx, .xls or .csv file.")

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
            "Could not detect 6 main-number columns. "
            "Rename headers to N1..N6 (recommended) or ensure you have 6 numeric columns."
        )
    return numeric_candidates[:6]

def detect_bonus_col(df: pd.DataFrame) -> str:
    # Any column that contains "bonus" (case/spacing safe)
    for c in df.columns:
        if "bonus" in str(c).strip().lower():
            return c
    raise ValueError("No bonus column found. Ensure your file has a column containing 'bonus' in the header.")

def safe_int_list(series: pd.Series) -> List[int]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    # keep in range 1..49
    s = s[(s >= 1) & (s <= 49)]
    return s.astype(int).tolist()

def sheet_fingerprint(df: pd.DataFrame) -> str:
    raw = df.to_csv(index=False).encode("utf-8")
    return hashlib.md5(raw).hexdigest()

# ----------------------------
# PHASE DETECTOR
# ----------------------------
def phase_detector(bonus_series: List[int], window: int = 20, strong_thresh: int = 10, center: int = 25) -> Dict:
    """
    bonus_series: chronological list oldest->newest
    window: number of latest bonuses to analyze
    strong_thresh: |delta| > strong_thresh => "strong move"
    center: mean center target (for 1..49, ~25)
    """
    if len(bonus_series) < 6:
        return {"phase": "INSUFFICIENT_DATA", "reason": "Need at least 6 bonus values."}

    seq = bonus_series[-window:] if len(bonus_series) >= window else bonus_series[:]
    deltas = np.diff(seq)
    mags = np.abs(deltas)
    signs = np.sign(deltas)

    # direction list without zeros
    nonzero = signs[signs != 0]
    if len(nonzero) < 3:
        return {"phase": "FLAT/NOISY", "reason": "Too many zero changes."}

    # reversal rate
    rev = 0
    cont = 0
    for i in range(len(nonzero) - 1):
        if nonzero[i] != nonzero[i + 1]:
            rev += 1
        else:
            cont += 1
    reversal_rate = rev / (rev + cont) if (rev + cont) else 0

    # strong move rate
    strong_rate = float((mags > strong_thresh).mean()) if len(mags) else 0.0

    # end run length (same-direction streak at the end)
    last_sign = nonzero[-1]
    run_len = 1
    for i in range(len(signs) - 2, -1, -1):
        if signs[i] == 0:
            continue
        if signs[i] == last_sign:
            run_len += 1
        else:
            break

    last_bonus = int(seq[-1])
    prev_bonus = int(seq[-2])
    dist = abs(last_bonus - center)
    prev_dist = abs(prev_bonus - center)
    moved_away = dist > prev_dist
    moved_toward = dist < prev_dist

    # Phase rules (interpretable)
    if reversal_rate >= 0.60:
        phase = "OSCILLATION"
        bias = "REVERSE_LAST_DIRECTION"
    else:
        if run_len >= 2 and strong_rate >= 0.35 and moved_away and dist >= 10:
            phase = "EXPANSION"
            bias = "PULL_BACK_TOWARD_CENTER"
        elif moved_toward and dist >= 6:
            phase = "COMPRESSION"
            bias = "CONTINUE_TOWARD_CENTER (MILD)"
        else:
            phase = "MIXED"
            bias = "NO_STRONG_BIAS"

    return {
        "phase": phase,
        "bias": bias,
        "window_used": len(seq),
        "last_bonus": last_bonus,
        "prev_bonus": prev_bonus,
        "last_delta": int(deltas[-1]) if len(deltas) else 0,
        "reversal_rate": round(float(reversal_rate), 3),
        "strong_rate": round(float(strong_rate), 3),
        "run_len_same_direction_end": int(run_len),
        "dist_from_center": float(dist),
        "moved_away_from_center": bool(moved_away),
        "moved_toward_center": bool(moved_toward),
        "strong_thresh": int(strong_thresh),
        "center": int(center),
    }

def bias_zone(res: Dict) -> Optional[Tuple[int, int]]:
    if "last_bonus" not in res or "last_delta" not in res:
        return None
    last = res["last_bonus"]
    last_delta = res["last_delta"]
    center = res.get("center", 25)

    if res.get("bias") == "REVERSE_LAST_DIRECTION":
        mag = abs(last_delta)
        mag = max(6, min(15, mag))  # clamp realistic
        if last_delta > 0:
            lo, hi = max(1, last - mag - 3), max(1, last - mag + 3)
        else:
            lo, hi = min(49, last + mag - 3), min(49, last + mag + 3)
        return (min(lo, hi), max(lo, hi))

    if res.get("bias") == "PULL_BACK_TOWARD_CENTER":
        step = 12
        if last > center:
            lo, hi = max(1, last - (step + 6)), max(1, last - (step - 6))
        else:
            lo, hi = min(49, last + (step - 6)), min(49, last + (step + 6))
        return (min(lo, hi), max(lo, hi))

    if str(res.get("bias", "")).startswith("CONTINUE_TOWARD_CENTER"):
        step = 8
        if last > center:
            lo, hi = max(1, last - (step + 4)), max(1, last - (step - 4))
        else:
            lo, hi = min(49, last + (step - 4)), min(49, last + (step + 4))
        return (min(lo, hi), max(lo, hi))

    return None

# ----------------------------
# GRID + ARROWS PLOT
# ----------------------------
DIGIT_COLORS = {
    2: "#d62728",  # red
    1: "#1f77b4",  # blue
    3: "#2ca02c",  # green
    5: "#bcbd22",  # yellow-ish
    6: "#ff7f0e",  # orange
    8: "#9467bd",  # purple
    9: "#8c564b",  # brown
}
NEUTRAL = "#7f7f7f"

def plot_bonus_grid_with_arrows(bonus_series: List[int], window: int = 20) -> plt.Figure:
    seq = bonus_series[-window:] if len(bonus_series) >= window else bonus_series[:]

    cols = 10
    def pos(n: int):
        idx = n - 1
        r = idx // cols
        c = idx % cols
        return c, -r

    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_aspect("equal")
    ax.axis("off")

    # grid
    for n in range(1, 50):
        x, y = pos(n)
        rect = plt.Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, linewidth=0.8)
        ax.add_patch(rect)
        ax.text(x, y, str(n), ha="center", va="center", fontsize=8)

    # points
    points = []
    for i, b in enumerate(seq, start=1):
        x, y = pos(int(b))
        color = DIGIT_COLORS.get(int(b) % 10, NEUTRAL)
        ax.scatter([x], [y], s=220, c=color, edgecolors="black", linewidths=0.6, zorder=3)
        ax.text(x, y + 0.25, f"{i}", ha="center", va="bottom", fontsize=7, zorder=4)
        points.append((x, y))

    # arrows + labels
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        if (x1, y1) == (x2, y2):
            continue
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", lw=1.2, shrinkA=12, shrinkB=12),
            zorder=2,
        )
        mid_x = (x1 + x2) / 2
        mid_y = (y1 + y2) / 2
        ax.text(mid_x, mid_y, f"{i+1}-{i+2}", fontsize=7, ha="center", va="center")

    ax.set_title(
        f"Bonus Direction Grid (Last {len(seq)} bonuses)\n"
        f"Arrows labeled by transition (1-2, 2-3, ...)",
        fontsize=12,
    )
    return fig

# ----------------------------
# UI
# ----------------------------
uploaded = st.file_uploader("Upload your updated historical sheet", type=["xlsx", "xls", "csv"])

if not uploaded:
    st.info("Upload a file to begin.")
    st.stop()

try:
    df = load_file(uploaded)

    st.caption(f"📌 Sheet fingerprint (MD5): {sheet_fingerprint(df)}")
    st.write("Columns detected:", df.columns.tolist())

    main_cols = detect_main_cols(df)
    bonus_col = detect_bonus_col(df)

    st.success(f"Main columns: {main_cols}")
    st.success(f"Bonus column: {bonus_col}")

    bonuses = safe_int_list(df[bonus_col])

    # Phase settings
    st.subheader("Phase Settings")
    w = st.slider("Phase window (bonuses)", 10, 60, 20, 1)
    strong_thresh = st.slider("Strong move threshold (|delta| > x)", 5, 20, 10, 1)
    center = st.slider("Center target (1–49 midpoint)", 15, 35, 25, 1)

    # Compute phase
    res = phase_detector(bonuses, window=w, strong_thresh=strong_thresh, center=center)
    st.subheader("Phase Output")
    st.json(res)

    zone = bias_zone(res)
    if zone:
        st.info(f"Directional bias zone suggestion: **{zone[0]} to {zone[1]}**")

    # Plot grid
    st.subheader("1–49 Grid with Arrows (Draw-by-draw)")
    fig = plot_bonus_grid_with_arrows(bonuses, window=w)
    st.pyplot(fig)

except Exception as e:
    st.error(f"Error: {e}")
