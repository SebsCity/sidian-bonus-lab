# app.py
# ------------------------------------------------------------
# STRICT HUMAN-BLIND / UGLY PAIR RANKER
# + ANCHORS
# + ANCHOR COMPANIONS
# ------------------------------------------------------------
# What it does:
# 1) Takes two pasted sets of numbers
# 2) Builds all cross-set pairs (Set A x Set B)
# 3) Ranks them from MOST human-blind / ugly
#    to LEAST human-blind / ugly
# 4) Extracts anchor numbers from the Top N ugliest pairs
# 5) Extracts companion numbers that pair most often with each anchor
# 6) Shows a compact "anchor + companions" shortlist
# ------------------------------------------------------------

import re
from collections import Counter
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Ugly Pair Ranker + Anchor Companions", layout="centered")
st.title("🫥 Ugly Pair Ranker + Anchor Companions")
st.caption("Finds the ugliest pairs, then shows the central anchor numbers and the numbers that most often pair with them.")

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def parse_numbers(text: str) -> list[int]:
    nums = re.findall(r"\d+", text)
    vals = [int(n) for n in nums]
    vals = [n for n in vals if 1 <= n <= 49]
    return vals

def pair_features(a: int, b: int) -> dict:
    x, y = sorted((a, b))
    diff = y - x

    tiny = {1, 2, 3, 4, 5}
    low = set(range(1, 16))
    awkward = {12, 14, 16, 17, 18, 19, 24, 28, 29}
    plain_middle = {12, 14, 16, 17, 18, 19, 20, 24, 25, 26, 27, 28, 29}
    popular = {7, 9, 10, 11, 13, 15, 20, 21, 23, 25, 26, 27, 30, 32, 35, 38, 39, 40, 41, 42, 43, 44, 45, 47, 48, 49}

    return {
        "pair": f"{a}-{b}",
        "a": a,
        "b": b,
        "diff": diff,
        "both_tiny": (a in tiny and b in tiny),
        "both_low": (a in low and b in low),
        "both_awkward": (a in awkward and b in awkward),
        "tiny_plus_awkward": ((a in tiny and b in awkward) or (b in tiny and a in awkward)),
        "both_plain_middle": (a in plain_middle and b in plain_middle),
        "has_backbone": ((20 <= a <= 39) or (20 <= b <= 39)),
        "both_backbone": ((20 <= a <= 39) and (20 <= b <= 39)),
        "both_high": (a >= 40 and b >= 40),
        "consecutive": (diff == 1),
        "near_consecutive": (diff == 2),
        "mirror10": (diff == 10),
        "pop_count": int(a in popular) + int(b in popular),
    }

def human_blind_rank_key(a: int, b: int):
    """
    Lower tuple = uglier / more human-blind.
    """
    f = pair_features(a, b)

    return (
        0 if f["both_tiny"] else 1,
        0 if f["both_awkward"] else 1,
        0 if f["tiny_plus_awkward"] else 1,
        0 if f["both_low"] else 1,
        0 if f["both_plain_middle"] else 1,
        1 if f["has_backbone"] else 0,      # no backbone = uglier
        1 if f["both_high"] else 0,         # double-high = more attractive
        1 if f["consecutive"] else 0,
        1 if f["near_consecutive"] else 0,
        1 if f["mirror10"] else 0,
        f["pop_count"],                     # fewer popular numbers = uglier
        max(a, b),
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
            rows.append(
                {
                    "Set A": a,
                    "Set B": b,
                    "Pair": f"{a}-{b}",
                    "Why": explain_pair(a, b),
                    "SortKey": human_blind_rank_key(a, b),
                }
            )

    df = pd.DataFrame(rows)
    df = df.sort_values(["SortKey", "Pair"], ascending=[True, True]).reset_index(drop=True)
    return df.drop(columns=["SortKey"])

def extract_anchor_numbers(ranked_df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    counter = Counter()
    top_pairs = ranked_df.head(top_n)["Pair"].tolist()

    for pair in top_pairs:
        a, b = map(int, pair.split("-"))
        counter[a] += 1
        counter[b] += 1

    anchor_df = (
        pd.DataFrame(counter.items(), columns=["Number", "Count"])
        .sort_values(["Count", "Number"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return anchor_df

def extract_anchor_companions(ranked_df: pd.DataFrame, top_n_pairs: int = 10, top_n_anchors: int = 3):
    pair_list = ranked_df.head(top_n_pairs)["Pair"].tolist()

    anchor_counter = Counter()
    parsed_pairs = []

    for pair in pair_list:
        a, b = map(int, pair.split("-"))
        parsed_pairs.append((a, b))
        anchor_counter[a] += 1
        anchor_counter[b] += 1

    top_anchors = [num for num, _ in anchor_counter.most_common(top_n_anchors)]

    companion_map = {}
    for anchor in top_anchors:
        comp_counter = Counter()
        for a, b in parsed_pairs:
            if a == anchor:
                comp_counter[b] += 1
            elif b == anchor:
                comp_counter[a] += 1
        companion_map[anchor] = comp_counter.most_common()

    return top_anchors, companion_map

def build_shortlist_from_anchor_companions(top_anchors, companion_map, top_companions_each=3):
    shortlist = []
    for anchor in top_anchors:
        shortlist.append({"Type": "Anchor", "Anchor": anchor, "Number": anchor, "Count": None})
        for num, cnt in companion_map.get(anchor, [])[:top_companions_each]:
            shortlist.append({"Type": "Companion", "Anchor": anchor, "Number": num, "Count": cnt})
    return pd.DataFrame(shortlist)

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
left, right = st.columns(2)

with left:
    set_a_text = st.text_area(
        "Set A",
        value="15\n17\n31\n35\n40\n44\n34",
        height=180,
    )

with right:
    set_b_text = st.text_area(
        "Set B",
        value="5\n12\n23\n26\n47\n49\n39",
        height=180,
    )

show_n = st.slider("Show top / bottom N pairs", 5, 25, 10)
anchor_top_n = st.slider("Use Top N ugliest pairs for anchor extraction", 5, 20, 10)
top_anchor_count = st.slider("How many top anchors to show", 1, 5, 3)
top_companion_count = st.slider("How many companions per anchor", 1, 5, 3)

if st.button("Generate ugly pairs + anchors + companions", type="primary"):
    set_a = parse_numbers(set_a_text)
    set_b = parse_numbers(set_b_text)

    if not set_a or not set_b:
        st.error("Please enter valid numbers in both sets.")
        st.stop()

    ranked = rank_pairs(set_a, set_b)
    anchors = extract_anchor_numbers(ranked, top_n=anchor_top_n)
    top_anchors, companion_map = extract_anchor_companions(
        ranked_df=ranked,
        top_n_pairs=anchor_top_n,
        top_n_anchors=top_anchor_count,
    )
    shortlist_df = build_shortlist_from_anchor_companions(
        top_anchors=top_anchors,
        companion_map=companion_map,
        top_companions_each=top_companion_count,
    )

    st.subheader("Parsed Sets")
    st.write("**Set A:**", set_a)
    st.write("**Set B:**", set_b)

    st.subheader("🫥 Top ugliest / most human-blind pairs")
    st.dataframe(ranked.head(show_n), use_container_width=True)

    st.subheader("👀 Least ugly / most noticeable pairs")
    st.dataframe(ranked.tail(show_n), use_container_width=True)

    st.subheader(f"🎯 Anchor numbers from Top {anchor_top_n} ugliest pairs")
    st.dataframe(anchors, use_container_width=True)

    st.subheader("🔗 Anchor + companion structure")
    for anchor in top_anchors:
        companions = companion_map.get(anchor, [])
        formatted = [f"{num} ({cnt})" for num, cnt in companions[:top_companion_count]]
        st.write(f"**Anchor {anchor}:** {formatted if formatted else 'No companions found'}")

    st.subheader("📌 Shortlist view")
    st.dataframe(shortlist_df, use_container_width=True)

    st.subheader("Quick takeaway")
    st.markdown(f"**Most human-blind pair:** `{ranked.iloc[0]['Pair']}`")
    if top_anchors:
        st.markdown(f"**Primary anchor:** `{top_anchors[0]}`")
        if companion_map.get(top_anchors[0]):
            primary_comps = [str(n) for n, _ in companion_map[top_anchors[0]][:top_companion_count]]
            st.markdown(f"**Best companions for {top_anchors[0]}:** `{', '.join(primary_comps)}`")

    with st.expander("Full pair ranking"):
        st.dataframe(ranked, use_container_width=True)
