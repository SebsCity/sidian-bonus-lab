import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Bonus Directional Backtest", layout="centered")
st.title("🎯 Bonus Directional Backtest (Shock → Exhaustion → Reversal)")

# -----------------------------
# Upload
# -----------------------------
uploaded = st.file_uploader("Upload your Excel/CSV sheet", type=["xlsx", "xls", "csv"])
if not uploaded:
    st.info("Upload your sheet to run the backtest.")
    st.stop()

# -----------------------------
# Load file
# -----------------------------
name = uploaded.name.lower()
if name.endswith(("xlsx", "xls")):
    df = pd.read_excel(uploaded)
else:
    df = pd.read_csv(uploaded)

# -----------------------------
# Detect Bonus column
# -----------------------------
def detect_bonus_col(df: pd.DataFrame):
    # strict matches
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("bonus", "bb", "bonusball", "bonus_ball", "bonus ball"):
            return c
    # soft match
    for c in df.columns:
        if "bonus" in str(c).strip().lower():
            return c
    return None

bonus_col = detect_bonus_col(df)
if not bonus_col:
    st.error("Could not find a Bonus column. Rename it to 'Bonus' (recommended).")
    st.stop()

# -----------------------------
# Optional Date sort (if present)
# -----------------------------
def detect_date_col(df: pd.DataFrame):
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("date", "draw_date", "drawdate"):
            return c
    for c in df.columns:
        if "date" in str(c).strip().lower():
            return c
    return None

date_col = detect_date_col(df)
if date_col:
    # try parse
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.sort_values(date_col).reset_index(drop=True)
    except Exception:
        pass

# -----------------------------
# Extract bonus series
# -----------------------------
bonus = pd.to_numeric(df[bonus_col], errors="coerce").dropna().astype(int).tolist()
bonus = [b for b in bonus if 1 <= b <= 49]

if len(bonus) < 25:
    st.error("Not enough bonus history found (need at least ~25 values).")
    st.stop()

# -----------------------------
# Controls
# -----------------------------
with st.expander("Model Settings", expanded=True):
    strong_threshold = st.slider("Strong move threshold (|Δ| >)", 6, 25, 10, 1)
    weak_threshold = st.slider("Weak move threshold (|Δ| ≤)", 1, 12, 6, 1)
    alpha = st.slider("Bounce strength α (fraction of strong move)", 0.20, 0.90, 0.50, 0.05)
    zone_half_width = st.slider("Zone half-width (±)", 1, 6, 2, 1)

    st.caption("Trigger = Strong move, then Weak continuation in same direction. Prediction fires AFTER the weak continuation, for the NEXT bonus.")

# -----------------------------
# Helpers
# -----------------------------
def sgn(x: int) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)

def clamp(n: int, lo: int = 1, hi: int = 49) -> int:
    return max(lo, min(hi, n))

def make_zone(center: int, half: int) -> list:
    z = list(range(center - half, center + half + 1))
    z = [n for n in z if 1 <= n <= 49]
    return z

# -----------------------------
# Backtest
# -----------------------------
# We need deltas between consecutive bonuses:
# delta[i] = bonus[i] - bonus[i-1]  for i >= 1
deltas = [bonus[i] - bonus[i - 1] for i in range(1, len(bonus))]

signals = []
hits = 0
total = 0

# Pattern uses two deltas:
# strong_delta at i (between bonus[i] and bonus[i-1])
# weak_delta at i+1 (between bonus[i+1] and bonus[i])
# Prediction is for bonus[i+2] (next after weak continuation)
#
# Index mapping:
# bonus index: 0..N-1
# delta index: 0..N-2 corresponds to movement to bonus[k+1]
#
# We evaluate k such that:
# strong_delta = deltas[k] (move to bonus[k+1])
# weak_delta   = deltas[k+1] (move to bonus[k+2])
# prediction targets bonus[k+3]
for k in range(len(deltas) - 2):
    strong_delta = deltas[k]
    weak_delta = deltas[k + 1]

    # Conditions:
    # Strong move happened
    if abs(strong_delta) <= strong_threshold:
        continue
    # Weak continuation happened (same direction, but weak)
    if abs(weak_delta) > weak_threshold:
        continue
    if sgn(weak_delta) != sgn(strong_delta):  # must continue same direction
        continue

    # We fire prediction at time of bonus[k+2] (current)
    current_bonus = bonus[k + 2]
    next_actual = bonus[k + 3]

    # Reversal projection:
    bounce = int(round(alpha * abs(strong_delta)))
    bounce = max(1, bounce)  # ensure at least 1 step
    projected = current_bonus + (-sgn(strong_delta) * bounce)
    projected = clamp(projected)

    zone = make_zone(projected, zone_half_width)

    hit = next_actual in zone
    total += 1
    hits += int(hit)

    signals.append({
        "Index": k,
        "Bonus(k)": bonus[k],
        "Bonus(k+1)": bonus[k+1],
        "Bonus(k+2) [current]": current_bonus,
        "Strong Δ": strong_delta,
        "Weak Δ": weak_delta,
        "Projected": projected,
        "Zone": ", ".join(map(str, zone)),
        "Actual next (k+3)": next_actual,
        "Hit": "✅" if hit else "—",
    })

# -----------------------------
# Results
# -----------------------------
zone_size = 2 * zone_half_width + 1
baseline = zone_size / 49

st.subheader("📊 Backtest Results")
if total == 0:
    st.warning("No triggers found with current thresholds. Try lowering Strong threshold or increasing Weak threshold.")
else:
    hit_rate = hits / total
    st.write(f"Triggers found: **{total}**")
    st.write(f"Hits (actual next bonus inside zone): **{hits}**")
    st.write(f"Hit rate: **{hit_rate:.2%}**")
    st.write(f"Random baseline for a {zone_size}-number zone: **{baseline:.2%}**")

    lift = (hit_rate / baseline) if baseline > 0 else 0
    st.write(f"Lift vs random: **{lift:.2f}×**")

st.divider()

st.subheader("🧾 Latest Trigger Signals (most recent first)")
if signals:
    sig_df = pd.DataFrame(signals).iloc[::-1].reset_index(drop=True)
    st.dataframe(sig_df.head(25), use_container_width=True)
else:
    st.info("No signals to display for current settings.")

# -----------------------------
# Live next prediction (from the last available pattern)
# -----------------------------
st.subheader("🔮 Next Bonus Zone (if last two moves match the pattern)")
# Check the last two deltas:
last_strong = deltas[-2]  # second last move
last_weak = deltas[-1]    # last move
current_bonus = bonus[-1]

st.write(f"Last moves: strong candidate Δ={last_strong}, last Δ={last_weak}, current bonus={current_bonus}")

fires = (
    abs(last_strong) > strong_threshold and
    abs(last_weak) <= weak_threshold and
    sgn(last_weak) == sgn(last_strong) and
    sgn(last_strong) != 0
)

if not fires:
    st.warning("Pattern NOT active right now (no prediction fired).")
else:
    bounce = int(round(alpha * abs(last_strong)))
    bounce = max(1, bounce)
    projected = clamp(current_bonus + (-sgn(last_strong) * bounce))
    zone = make_zone(projected, zone_half_width)
    st.success(f"Pattern ACTIVE ✅  Projected={projected}  Zone={zone}")
