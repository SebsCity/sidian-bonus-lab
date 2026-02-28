import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Bonus Generator", layout="centered")
st.title("🎯 Bonus Generator (Directional + Phase)")
st.caption("Upload your historical sheet and generate ranked possible next bonus balls.")

# ----------------------------
# Load file
# ----------------------------
def load_file(uploaded) -> pd.DataFrame:
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded)
    if name.endswith(".csv"):
        return pd.read_csv(uploaded)
    raise ValueError("Upload .xlsx/.xls or .csv")

def detect_bonus_col(df: pd.DataFrame) -> str:
    for c in df.columns:
        if "bonus" in str(c).strip().lower():
            return c
    raise ValueError("No bonus column found. Ensure a header contains the word 'bonus'.")

def safe_bonus_list(series: pd.Series) -> list[int]:
    s = pd.to_numeric(series, errors="coerce").dropna()
    s = s[(s >= 1) & (s <= 49)]
    return s.astype(int).tolist()

# ----------------------------
# Phase detector (simple + interpretable)
# ----------------------------
def phase_detector(bonuses: list[int], window=20, strong_thresh=10, center=25) -> dict:
    if len(bonuses) < 8:
        return {"phase": "INSUFFICIENT_DATA", "bias": "NONE"}

    seq = bonuses[-window:] if len(bonuses) >= window else bonuses[:]
    deltas = np.diff(seq)
    mags = np.abs(deltas)
    signs = np.sign(deltas)
    nz = signs[signs != 0]

    if len(nz) < 3:
        return {"phase": "FLAT/NOISY", "bias": "NONE"}

    # reversal rate
    rev = 0
    cont = 0
    for i in range(len(nz) - 1):
        if nz[i] != nz[i + 1]:
            rev += 1
        else:
            cont += 1
    reversal_rate = rev / (rev + cont) if (rev + cont) else 0

    # strong move rate
    strong_rate = float((mags > strong_thresh).mean()) if len(mags) else 0.0

    last = seq[-1]
    prev = seq[-2]
    dist = abs(last - center)
    prev_dist = abs(prev - center)
    moved_away = dist > prev_dist
    moved_toward = dist < prev_dist

    # run length at end (same direction)
    last_sign = nz[-1]
    run_len = 1
    for i in range(len(signs) - 2, -1, -1):
        if signs[i] == 0:
            continue
        if signs[i] == last_sign:
            run_len += 1
        else:
            break

    if reversal_rate >= 0.60:
        phase = "OSCILLATION"
        bias = "REVERSE"
    else:
        if run_len >= 2 and strong_rate >= 0.35 and moved_away and dist >= 10:
            phase = "EXPANSION"
            bias = "PULL_TO_CENTER"
        elif moved_toward and dist >= 6:
            phase = "COMPRESSION"
            bias = "MILD_TO_CENTER"
        else:
            phase = "MIXED"
            bias = "NONE"

    return {
        "phase": phase,
        "bias": bias,
        "window_used": len(seq),
        "last_bonus": int(last),
        "last_delta": int(deltas[-1]) if len(deltas) else 0,
        "reversal_rate": round(float(reversal_rate), 3),
        "strong_rate": round(float(strong_rate), 3),
        "run_len_end": int(run_len),
        "center": int(center),
        "strong_thresh": int(strong_thresh),
    }

# ----------------------------
# Candidate generator (ranked)
# ----------------------------
def generate_candidates(
    bonuses: list[int],
    window=20,
    strong_thresh=10,
    center=25,
    top_n=10,
    exclude_recent_k=0,
) -> tuple[list[tuple[int, float, str]], dict]:
    """
    Returns list of (number, score, explanation) sorted desc, plus phase dict.
    Scoring combines:
      - directional bias (phase-based)
      - step-size likelihood from recent deltas
      - digit preference from recent last digits
      - mild mean-reversion toward center
    """
    seq = bonuses[-window:] if len(bonuses) >= window else bonuses[:]
    last = seq[-1]
    deltas = np.diff(seq)
    abs_deltas = np.abs(deltas) if len(deltas) else np.array([1])

    # phase
    phase = phase_detector(bonuses, window=window, strong_thresh=strong_thresh, center=center)
    bias = phase["bias"]
    last_delta = phase.get("last_delta", 0)

    # step size histogram (recent)
    # clamp steps to 1..25
    steps = np.clip(abs_deltas.astype(int), 1, 25)
    step_counts = np.bincount(steps, minlength=26)
    step_probs = step_counts / step_counts.sum() if step_counts.sum() else np.ones(26) / 26

    # digit preference histogram (last digit)
    digits = [b % 10 for b in seq]
    dig_counts = np.bincount(digits, minlength=10)
    dig_probs = dig_counts / dig_counts.sum() if dig_counts.sum() else np.ones(10) / 10

    # recent exclusions (optional)
    recent_set = set(seq[-exclude_recent_k:]) if exclude_recent_k > 0 else set()

    candidates = []
    for x in range(1, 50):
        if x in recent_set:
            continue

        score = 0.0
        reasons = []

        # --- Directional bias ---
        delta = x - last
        ad = abs(delta)
        dir_sign = np.sign(delta)

        if bias == "REVERSE":
            # reverse last direction if last_delta != 0
            if last_delta != 0 and dir_sign == -np.sign(last_delta):
                score += 2.5
                reasons.append("matches reversal bias")
            elif last_delta == 0:
                score += 0.5
        elif bias == "PULL_TO_CENTER":
            # reward moving toward center
            moved_toward = abs(x - center) < abs(last - center)
            if moved_toward:
                score += 2.0
                reasons.append("pulls toward center")
        elif bias == "MILD_TO_CENTER":
            moved_toward = abs(x - center) < abs(last - center)
            if moved_toward:
                score += 1.2
                reasons.append("mild toward center")

        # --- Step size likelihood ---
        ad = int(np.clip(ad, 1, 25))
        score += 1.6 * float(step_probs[ad])
        reasons.append(f"step|Δ|={ad} favored")

        # --- Digit preference ---
        score += 0.9 * float(dig_probs[x % 10])
        reasons.append(f"last-digit {x%10} seen often")

        # --- Soft center preference (keep it realistic) ---
        # prefer mid-zone a bit, but not too strong
        score += 0.4 * (1.0 - (abs(x - center) / 24.0))

        candidates.append((x, score, "; ".join(reasons)))

    candidates.sort(key=lambda t: t[1], reverse=True)
    return candidates[:top_n], phase

# ----------------------------
# UI
# ----------------------------
uploaded = st.file_uploader("Upload Excel/CSV", type=["xlsx", "xls", "csv"])

if not uploaded:
    st.info("Upload your file to generate bonus candidates.")
    st.stop()

try:
    df = load_file(uploaded)
    bonus_col = detect_bonus_col(df)
    bonuses = safe_bonus_list(df[bonus_col])

    st.success(f"Bonus column detected: {bonus_col}")
    st.write(f"Total bonus records: {len(bonuses)}")

    with st.expander("Settings", expanded=True):
        window = st.slider("Lookback window (bonuses)", 10, 60, 20, 1)
        strong_thresh = st.slider("Strong move threshold (|delta| > x)", 5, 20, 10, 1)
        center = st.slider("Center target (1–49 midpoint)", 15, 35, 25, 1)
        top_n = st.selectbox("How many candidates to show", [5, 10, 15], index=1)
        exclude_recent_k = st.selectbox("Exclude last K bonuses (optional)", [0, 1, 2, 3, 5], index=0)

    if len(bonuses) < 8:
        st.warning("Not enough bonus history in the file.")
        st.stop()

    # show last bonuses
    st.subheader("Recent bonuses")
    st.write(bonuses[-min(window, len(bonuses)) :])

    ranked, phase = generate_candidates(
        bonuses,
        window=window,
        strong_thresh=strong_thresh,
        center=center,
        top_n=top_n,
        exclude_recent_k=exclude_recent_k,
    )

    st.subheader("Phase read")
    st.json(phase)

    st.subheader(f"🎯 Ranked possible next bonus candidates (Top {top_n})")
    out_df = pd.DataFrame(ranked, columns=["Candidate", "Score", "Why it ranks high"])
    st.dataframe(out_df, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
