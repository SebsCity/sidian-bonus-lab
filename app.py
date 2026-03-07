# app.py
import re
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Strict Human-Blind Pair Ranker", layout="centered")
st.title("🫥 Strict Human-Blind / Ugly Pair Ranker")
st.caption("Ranks cross-set duos from most ignored by humans to least ignored.")

def parse_numbers(text: str) -> list[int]:
    nums = re.findall(r"\d+", text)
    vals = [int(n) for n in nums if 1 <= int(n) <= 49]
    return vals

def pair_features(a: int, b: int):
    x, y = sorted((a, b))
    diff = y - x

    tiny = {1, 2, 3, 4, 5}
    low = set(range(1, 16))
    awkward = {12, 14, 16, 17, 18, 19, 24, 28, 29}
    plain_middle = {12, 14, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29}
    popular = {7, 9, 10, 11, 13, 15, 20, 21, 23, 25, 26, 27, 30, 32, 35, 38, 39, 40, 41, 42, 43, 44, 45, 47, 48, 49}

    both_tiny = (a in tiny and b in tiny)
    both_low = (a in low and b in low)
    both_awkward = (a in awkward and b in awkward)
    tiny_plus_awkward = ((a in tiny and b in awkward) or (b in tiny and a in awkward))
    both_plain_middle = (a in plain_middle and b in plain_middle)
    has_backbone = (20 <= a <= 39) or (20 <= b <= 39)
    both_backbone = (20 <= a <= 39) and (20 <= b <= 39)
    both_high = (a >= 40 and b >= 40)
    consecutive = diff == 1
    near_consecutive = diff == 2
    mirror10 = diff == 10
    pop_count = int(a in popular) + int(b in popular)

    return {
        "pair": f"{a}-{b}",
        "a": a,
        "b": b,
        "both_tiny": both_tiny,
        "both_low": both_low,
        "both_awkward": both_awkward,
        "tiny_plus_awkward": tiny_plus_awkward,
        "both_plain_middle": both_plain_middle,
        "has_backbone": has_backbone,
        "both_backbone": both_backbone,
        "both_high": both_high,
        "consecutive": consecutive,
        "near_consecutive": near_consecutive,
        "mirror10": mirror10,
        "pop_count": pop_count,
    }

def human_blind_rank_key(a: int, b: int):
    f = pair_features(a, b)

    # LOWER tuple = MORE human-blind / uglier
    # This ordering is intentionally hard-coded to force the priority you wanted.
    return (
        0 if f["both_tiny"] else 1,
        0 if f["both_awkward"] else 1,
        0 if f["tiny_plus_awkward"] else 1,
        0 if f["both_low"] else 1,
        0 if f["both_plain_middle"] else 1,
        1 if f["has_backbone"] else 0,      # no backbone should rank uglier
        1 if f["both_high"] else 0,         # double-high is attractive, so push down
        1 if f["consecutive"] else 0,       # consecutive is attractive
        1 if f["near_consecutive"] else 0,  # near-consecutive is attractive
        1 if f["mirror10"] else 0,          # mirror spacing is attractive
        f["pop_count"],                     # fewer popular numbers = uglier
        max(a, b),                          # tie-breakers
        min(a, b),
    )

def explain_pair(a: int, b: int) -> str:
    f = pair_features(a, b)
    reasons = []
    if f["both_tiny"]:
        reasons.append("tiny-number pair")
    if f["both_awkward"]:
        reasons.append("awkward unattractive pair")
    if f["tiny_plus_awkward"]:
        reasons.append("small + awkward mid")
    if f["both_low"]:
        reasons.append("double low cluster")
    if f["both_plain_middle"]:
        reasons.append("plain middle pair")
    if not f["has_backbone"]:
        reasons.append("no 20-39 backbone")
    if not reasons:
        reasons.append("less ugly / more noticeable")
    return ", ".join(reasons)

def rank_pairs(set_a: list[int], set_b: list[int]) -> pd.DataFrame:
    rows = []
    for a in set_a:
        for b in set_b:
            rows.append({
                "Set A": a,
                "Set B": b,
                "Pair": f"{a}-{b}",
                "Why": explain_pair(a, b),
                "SortKey": human_blind_rank_key(a, b),
            })

    df = pd.DataFrame(rows)
    df = df.sort_values("SortKey", ascending=True).reset_index(drop=True)
    return df.drop(columns=["SortKey"])

left, right = st.columns(2)

with left:
    set_a_text = st.text_area(
        "Set A",
        value="5\n12\n23\n26\n47\n49\n39",
        height=180
    )

with right:
    set_b_text = st.text_area(
        "Set B",
        value="3\n16\n20\n21\n26\n38\n2",
        height=180
    )

top_n = st.slider("How many pairs to show", 5, 25, 10)

if st.button("Generate strict human-blind ranking", type="primary"):
    set_a = parse_numbers(set_a_text)
    set_b = parse_numbers(set_b_text)

    if not set_a or not set_b:
        st.error("Please enter valid numbers in both sets.")
        st.stop()

    ranked = rank_pairs(set_a, set_b)

    st.subheader("🫥 Most human-blind / ugliest pairs")
    st.dataframe(ranked.head(top_n), use_container_width=True)

    st.subheader("👀 Least human-blind / most noticeable pairs")
    st.dataframe(ranked.tail(top_n), use_container_width=True)

    st.markdown(f"**Most human-blind pair:** `{ranked.iloc[0]['Pair']}`")
    st.markdown(f"**Second:** `{ranked.iloc[1]['Pair']}`")
    st.markdown(f"**Third:** `{ranked.iloc[2]['Pair']}`")

    with st.expander("Full ranking"):
        st.dataframe(ranked, use_container_width=True)
