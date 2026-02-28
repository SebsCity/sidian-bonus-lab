# ============================================================
# PHASE DETECTOR (Drop-in for your Streamlit)
# Detects 3 phases from bonus-ball direction:
#   1) OSCILLATION  -> frequent reversals, no sustained trend
#   2) EXPANSION    -> sustained same-direction moves, large steps
#   3) COMPRESSION  -> after big expansion, pullback toward center
#
# Works on the last N bonus balls (default 20).
# Outputs:
# - Phase label
# - Key metrics
# - Suggested directional bias for the NEXT move
# ============================================================

import numpy as np
import streamlit as st

def phase_detector(bonus_series, window=20, strong_thresh=10, center=25):
    """
    bonus_series: list[int] in chronological order (oldest -> newest)
    window: how many latest bonuses to analyze
    strong_thresh: |delta| > strong_thresh considered a strong move
    center: mean-centering target (for 1..49, ~25 is natural)
    """
    if len(bonus_series) < 6:
        return {"phase": "INSUFFICIENT_DATA", "reason": "Need at least 6 bonus values."}

    seq = bonus_series[-window:] if len(bonus_series) >= window else bonus_series[:]
    deltas = np.diff(seq)
    mags = np.abs(deltas)
    signs = np.sign(deltas)

    # Remove zeros for direction logic
    nonzero = signs[signs != 0]
    if len(nonzero) < 3:
        return {"phase": "FLAT/NOISY", "reason": "Too many zero changes."}

    # Reversal rate
    rev = 0
    cont = 0
    for i in range(len(nonzero) - 1):
        if nonzero[i] != nonzero[i + 1]:
            rev += 1
        else:
            cont += 1
    reversal_rate = rev / (rev + cont) if (rev + cont) else 0

    # Strong move rate
    strong_mask = mags > strong_thresh
    strong_rate = strong_mask.mean() if len(mags) else 0

    # Same-direction run length near the end (trend strength)
    # Count how many last consecutive signs are the same
    last_sign = signs[-1] if signs[-1] != 0 else (nonzero[-1] if len(nonzero) else 0)
    run_len = 1
    for i in range(len(signs) - 2, -1, -1):
        if signs[i] == 0:
            continue
        if signs[i] == last_sign:
            run_len += 1
        else:
            break

    # Center distance behavior
    # If we are far from center and last moves were in the outward direction, we call it expansion
    # If we are far from center and last move was toward center, we call it compression
    last_bonus = seq[-1]
    dist_from_center = abs(last_bonus - center)

    # Determine whether last move moved away from center or toward center
    prev_bonus = seq[-2]
    prev_dist = abs(prev_bonus - center)
    moved_away = dist_from_center > prev_dist
    moved_toward = dist_from_center < prev_dist

    # ---- Phase classification rules (simple, interpretable) ----
    # OSCILLATION: high reversal rate
    # EXPANSION: low reversal + strong moves + run_len>=2 + moved away from center
    # COMPRESSION: after being far from center, moved toward center (often after expansion)
    phase = "OSCILLATION"

    if reversal_rate >= 0.60:
        phase = "OSCILLATION"
    else:
        # not oscillating, check expansion vs compression
        if run_len >= 2 and strong_rate >= 0.35 and moved_away and dist_from_center >= 10:
            phase = "EXPANSION"
        elif moved_toward and dist_from_center >= 6:
            phase = "COMPRESSION"
        else:
            # neutral / mixed
            phase = "MIXED"

    # ---- Suggest next directional bias (not a prediction) ----
    # Oscillation -> bias reversal
    # Expansion -> bias pullback (toward center)
    # Compression -> bias mild continuation toward center then stabilize
    if phase == "OSCILLATION":
        bias = "REVERSE_LAST_DIRECTION"
    elif phase == "EXPANSION":
        bias = "PULL_BACK_TOWARD_CENTER"
    elif phase == "COMPRESSION":
        bias = "CONTINUE_TOWARD_CENTER (MILD)"
    else:
        bias = "NO_STRONG_BIAS"

    return {
        "phase": phase,
        "reversal_rate": round(reversal_rate, 3),
        "strong_rate": round(float(strong_rate), 3),
        "run_len_same_direction_end": int(run_len),
        "last_bonus": int(last_bonus),
        "last_delta": int(deltas[-1]),
        "dist_from_center": float(dist_from_center),
        "moved_away_from_center": bool(moved_away),
        "moved_toward_center": bool(moved_toward),
        "bias": bias,
        "window_used": len(seq),
        "strong_thresh": strong_thresh,
        "center": center,
    }

# -----------------------------
# Streamlit usage example
# -----------------------------
# Assuming you already have df loaded and a 'Bonus' column
# bonuses = df["Bonus"].dropna().astype(int).tolist()

st.subheader("🧭 Bonus Phase Detector")

window = st.slider("Phase window (bonuses)", 10, 60, 20, 1)
strong_thresh = st.slider("Strong move threshold (|delta| > x)", 5, 20, 10, 1)
center = st.slider("Center target (1–49 midpoint)", 15, 35, 25, 1)

# Detect bonus column automatically
bonus_col = None
for c in df.columns:
    if "bonus" in str(c).strip().lower():
        bonus_col = c
        break

if bonus_col is None:
    st.error("No bonus column found in file.")
    st.stop()

bonuses = df[bonus_col].dropna().astype(int).tolist()
res = phase_detector(bonuses, window=window, strong_thresh=strong_thresh, center=center)

st.write(res)

# Optional: simple next-step candidate zone guidance
if res.get("phase") in ("OSCILLATION", "EXPANSION", "COMPRESSION"):
    last = res["last_bonus"]
    last_delta = res["last_delta"]
    st.markdown("### Next-step guidance (zone)")

    if res["bias"] == "REVERSE_LAST_DIRECTION":
        # reverse last move, use similar magnitude bucket
        mag = abs(last_delta)
        mag = max(6, min(15, mag))  # clamp to a realistic band
        if last_delta > 0:
            lo, hi = max(1, last - mag - 3), max(1, last - mag + 3)
        else:
            lo, hi = min(49, last + mag - 3), min(49, last + mag + 3)
        st.write(f"Bias: reverse. Suggested zone ≈ {lo} to {hi}")

    elif res["bias"] == "PULL_BACK_TOWARD_CENTER":
        # pull toward center by 8-18
        step = 12
        if last > center:
            lo, hi = max(1, last - (step + 6)), max(1, last - (step - 6))
        else:
            lo, hi = min(49, last + (step - 6)), min(49, last + (step + 6))
        st.write(f"Bias: pullback toward center. Suggested zone ≈ {lo} to {hi}")

    elif res["bias"].startswith("CONTINUE_TOWARD_CENTER"):
        # continue mild toward center by 5-12
        step = 8
        if last > center:
            lo, hi = max(1, last - (step + 4)), max(1, last - (step - 4))
        else:
            lo, hi = min(49, last + (step - 4)), min(49, last + (step + 4))
        st.write(f"Bias: mild continuation toward center. Suggested zone ≈ {lo} to {hi}")
