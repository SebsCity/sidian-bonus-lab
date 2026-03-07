# app.py
# ------------------------------------------------------------
# Human Selection Bias Duo Ranker
# Paste / type two sets, and it ranks all cross-set duos from:
# MOST likely chosen by humans  ->  LEAST likely noticed by humans
#
# You can use:
# - 6 main + optional bonus for Set A
# - 6 main + optional bonus for Set B
#
# Example input:
# 15 19 32 39 42 48 43
# 6 9 20 27 42 43 5
# ------------------------------------------------------------

import re
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Human Bias Duo Ranker", layout="centered")
st.title("🧠 Human Selection Bias Duo Ranker")
st.caption("Ranks cross-set duos from most human-picked to most human-ignored.")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def parse_numbers(text: str) -> list[int]:
    nums = re.findall(r"\d+", text)
    values = [int(n) for n in nums]
    values = [n for n in values if 1 <= n <= 49]
    return values

def number_human_bias_score(n: int) -> float:
    """
    Higher = more likely humans choose it.
    """
    score = 0.0

    # Popular small/familiar numbers
    if n in {7, 9, 11, 13, 15, 21, 23, 26, 27, 32, 39, 42, 43, 44, 45, 47, 48, 49}:
        score += 2.0

    # Multiples of 5 / round-ish numbers feel attractive
    if n % 5 == 0:
        score += 1.3

    # High numbers often feel "strong"
    if 40 <= n <= 49:
        score += 1.8

    # 20s/30s feel balanced / natural
    if 20 <= n <= 39:
        score += 1.0

    # Very tiny numbers are often avoided in pairs unless they form a pattern
    if 1 <= n <= 5:
        score -= 1.5

    # Awkward teen-ish middles
    if n in {12, 14, 16, 17, 18, 19, 24, 28, 29}:
        score -= 0.8

    return score

def duo_bias_score(a: int, b: int) -> tuple[float, list[str]]:
    """
    Higher = more likely humans choose this duo.
    """
    reasons = []
    score = number_human_bias_score(a) + number_human_bias_score(b)

    x, y = sorted((a, b))
    diff = y - x

    # Same number (very noticeable if allowed)
    if a == b:
        score += 4.5
        reasons.append("same-number pair")

    # Consecutive / near-consecutive
    if diff == 1:
        score += 4.0
        reasons.append("consecutive")
    elif diff == 2:
        score += 2.5
        reasons.append("near-consecutive")
    elif diff == 3:
        score += 1.5
        reasons.append("tight spacing")

    # Mirror / visually neat
    if abs(a - b) == 10:
        score += 2.2
        reasons.append("mirror spacing ±10")

    # Both high
    if a >= 40 and b >= 40:
        score += 2.8
        reasons.append("double high numbers")

    # Both low = usually less attractive
    if a <= 15 and b <= 15:
        score -= 2.8
        reasons.append("double low cluster")

    # Small + awkward mid often ignored
    if ({a, b} & {1, 2, 3, 4, 5}) and ({a, b} & {12, 14, 16, 17, 18, 19, 24, 28, 29}):
        score -= 1.5
        reasons.append("awkward small+mid")

    # Both in 20-39 = moderate natural appeal
    if 20 <= a <= 39 and 20 <= b <= 39:
        score += 1.5
        reasons.append("mid-band balance")

    # Both weird/plain middles can be overlooked
    if {a, b}.issubset({12, 14, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29}):
        score -= 1.2
        reasons.append("plain middle pair")

    return score, reasons

def rank_duos(set_a: list[int], set_b: list[int]) -> pd.DataFrame:
    rows = []
    for a in set_a:
        for b in set_b:
            score, reasons = duo_bias_score(a, b)
            rows.append({
                "Set A": a,
                "Set B": b,
                "Duo": f"{a}-{b}",
                "Bias Score": round(score, 2),
                "Human Bias Reasoning": ", ".join(reasons) if reasons else "neutral structure"
            })
    df = pd.DataFrame(rows)
    df = df.sort_values("Bias Score", ascending=False).reset_index(drop=True)
    return df

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
col1, col2 = st.columns(2)

with col1:
    set_a_text = st.text_area(
        "Set A numbers",
        value="15\n19\n32\n39\n42\n48\n43",
        height=180
    )

with col2:
    set_b_text = st.text_area(
        "Set B numbers",
        value="6\n9\n20\n27\n42\n43\n5",
        height=180
    )

show_top = st.slider("Show top / bottom N duos", 5, 25, 10)

if st.button("Rank duos by human bias", type="primary"):
    set_a = parse_numbers(set_a_text)
    set_b = parse_numbers(set_b_text)

    if not set_a or not set_b:
        st.error("Please enter valid numbers for both sets.")
        st.stop()

    st.subheader("Parsed sets")
    st.write("**Set A:**", set_a)
    st.write("**Set B:**", set_b)

    df_ranked = rank_duos(set_a, set_b)

    st.subheader("Most likely chosen by humans")
    st.dataframe(df_ranked.head(show_top), use_container_width=True)

    st.subheader("Least likely noticed by humans")
    st.dataframe(df_ranked.tail(show_top).sort_values("Bias Score"), use_container_width=True)

    most_human = df_ranked.iloc[0]
    least_human = df_ranked.iloc[-1]

    st.subheader("Quick takeaway")
    st.markdown(f"**Most human-picked duo:** `{most_human['Duo']}`")
    st.markdown(f"**Most human-ignored duo:** `{least_human['Duo']}`")
