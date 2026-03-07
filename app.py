# app.py
# ------------------------------------------------------------
# STRICT HUMAN-BLIND / UGLY PAIR RANKER
# ------------------------------------------------------------
# Purpose:
# Rank all cross-set duos from MOST human-blind / ugly
# to LEAST human-blind / ugly.
#
# This version is intentionally strict.
# It strongly favors pairs that human eyes usually avoid:
# - double low numbers
# - tiny numbers (1-10)
# - awkward/plain middle numbers
# - no 20-39 backbone
# - no high-number appeal
# - ugly spacing
#
# Input:
# Paste Set A and Set B numbers (main + optional bonus if you want)
#
# Output:
# - Most human-blind pairs
# - Least human-blind pairs
# - Full ranked table
# ------------------------------------------------------------

import re
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Strict Human-Blind Pair Ranker", layout="centered")
st.title("🫥 Strict Human-Blind / Ugly Pair Ranker")
st.caption("Ranks cross-set duos from most ignored by humans to least ignored.")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def parse_numbers(text: str) -> list[int]:
    nums = re.findall(r"\d+", text)
    values = [int(n) for n in nums]
    values = [n for n in values if 1 <= n <= 49]
    return values

def ugly_pair_score(a: int, b: int) -> tuple[float, list[str]]:
    """
    Higher score = more human-blind / uglier / less likely chosen by people.
    """
    x, y = sorted((a, b))
    diff = y - x
    reasons = []
    score = 0.0

    # --------------------------------------------------------
    # Strong HUMAN-BLIND boosts
    # --------------------------------------------------------

    # Double low cluster
    if x <= 15 and y <= 15:
        score += 7.0
        reasons.append("double low cluster")

    # Tiny-number pair
    if x <= 10 and y <= 10:
        score += 6.0
        reasons.append("tiny-number pair")

    # Awkward unattractive numbers
    awkward = {2, 3, 4, 5, 12, 14, 16, 17, 18, 19, 24, 28, 29}
    if a in awkward and b in awkward:
        score += 4.5
        reasons.append("awkward unattractive pair")

    # Small + awkward-mid combination
    tiny = {1, 2, 3, 4, 5}
    awkward_mid = {12, 14, 16, 17, 18, 19, 24, 28, 29}
    if ({a, b} & tiny) and ({a, b} & awkward_mid):
        score += 3.5
        reasons.append("small + awkward mid")

    # No 20-39 backbone and no high-number glamour
    if not (20 <= a <= 39 or 20 <= b <= 39) and not (a >= 40 or b >= 40):
        score += 3.0
        reasons.append("no backbone / no high appeal")

    # Plain middle pair often skipped
    plain_middle = {12, 14, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29}
    if a in plain_middle and b in plain_middle:
        score += 3.0
        reasons.append("plain middle pair")

    # Ugly spacing: not consecutive, not mirror, not neat
    if diff in {4, 6, 7, 8, 9, 11, 13, 14, 17}:
        score += 1.5
        reasons.append("ugly spacing")

    # One low + one plain mid
    if ((1 <= a <= 15 and b in plain_middle) or (1 <= b <= 15 and a in plain_middle)):
        score += 2.0
        reasons.append("low + plain mid")

    # --------------------------------------------------------
    # Human-attractive penalties
    # These REDUCE human-blindness score
    # --------------------------------------------------------

    # Same-number pair looks too obvious
    if a == b:
        score -= 8.0
        reasons.append("same-number obvious")

    # Consecutive / near consecutive are attractive
    if diff == 1:
        score -= 5.0
        reasons.append("consecutive")
    elif diff == 2:
        score -= 3.0
        reasons.append("near-consecutive")
    elif diff == 3:
        score -= 1.5
        reasons.append("tight spacing")

    # Mirror spacing feels neat
    if diff == 10:
        score -= 2.5
        reasons.append("mirror ±10")

    # Double high numbers look strong / attractive
    if a >= 40 and b >= 40:
        score -= 4.0
        reasons.append("double high")

    # Both in 20-39 gives backbone / natural feel
    if 20 <= a <= 39 and 20 <= b <= 39:
        score -= 2.5
        reasons.append("20-39 backbone")

    # Popular-looking numbers people like
    popular = {7, 9, 10, 11, 13, 15, 20, 21, 23, 25, 26, 27, 30, 32, 35, 38, 39, 40, 41, 42, 43, 44, 45, 47, 48, 49}
    pop_count = sum(1 for n in (a, b) if n in popular)
    if pop_count:
        score -= 1.5 * pop_count
        reasons.append("popular-looking number(s)")

    return round(score, 2), reasons

def rank_pairs(set_a: list[int], set_b: list[int]) -> pd.DataFrame:
    rows = []
    for a in set_a:
        for b in set_b:
            score, reasons = ugly_pair_score(a, b)
            rows.append({
                "Set A": a,
                "Set B": b,
                "Pair": f"{a}-{b}",
                "Ugly Score": score,
                "Why": ", ".join(reasons) if reasons else "neutral"
            })

    df = pd.DataFrame(rows)
    df = df.sort_values(["Ugly Score", "Pair"], ascending=[False, True]).reset_index(drop=True)
    return df

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
left, right = st.columns(2)

with left:
    set_a_text = st.text_area(
        "Set A",
        value="15\n19\n32\n39\n42\n48\n43",
        height=180
    )

with right:
    set_b_text = st.text_area(
        "Set B",
        value="6\n9\n20\n27\n42\n43\n5",
        height=180
    )

top_n = st.slider("How many pairs to show", 5, 25, 10)

if st.button("Generate strict human-blind ranking", type="primary"):
    set_a = parse_numbers(set_a_text)
    set_b = parse_numbers(set_b_text)

    if not set_a or not set_b:
        st.error("Please enter valid numbers in both sets.")
        st.stop()

    st.subheader("Parsed Sets")
    st.write("**Set A:**", set_a)
    st.write("**Set B:**", set_b)

    ranked = rank_pairs(set_a, set_b)

    st.subheader("🫥 Most human-blind / ugliest pairs")
    st.dataframe(ranked.head(top_n), use_container_width=True)

    st.subheader("👀 Least human-blind / most noticeable pairs")
    st.dataframe(ranked.tail(top_n).sort_values("Ugly Score"), use_container_width=True)

    st.subheader("Quick answer")
    st.markdown(f"**Most human-blind pair:** `{ranked.iloc[0]['Pair']}`")
    st.markdown(f"**Least human-blind pair:** `{ranked.iloc[-1]['Pair']}`")

    with st.expander("Full ranking"):
        st.dataframe(ranked, use_container_width=True)
