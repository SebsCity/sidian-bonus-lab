# app.py
import streamlit as st
import pandas as pd
import numpy as np
import itertools

st.set_page_config(page_title="n-1 & n-4 Triple Engine", layout="centered")
st.title("🎯 n−1 & n−4 Triple Engine")
st.caption("Uploads your sheet → extracts latest n−1 and n−4 → ranks triples (strong ↔ weak).")

# -----------------------
# Helpers
# -----------------------
def detect_main_cols(df: pd.DataFrame):
    cols = list(df.columns)
    low = [str(c).strip().lower() for c in cols]
    pref = ["n1","n2","n3","n4","n5","n6"]
    if all(p in low for p in pref):
        return [cols[low.index(p)] for p in pref]
    # fallback: take first 6 mostly-numeric columns
    numeric = []
    for c in cols:
        s = pd.to_numeric(df[c], errors="coerce")
        if s.notna().mean() > 0.8:
            numeric.append(c)
    if len(numeric) < 6:
        raise ValueError("Could not find 6 main number columns. Ensure N1..N6 exist.")
    return numeric[:6]

def detect_date_col(df: pd.DataFrame):
    for c in df.columns:
        if "date" in str(c).strip().lower():
            return c
    return None

def sort_df(df: pd.DataFrame, date_col: str | None):
    dff = df.copy()
    if date_col:
        dff[date_col] = pd.to_datetime(dff[date_col], errors="coerce")
        dff = dff.dropna(subset=[date_col]).copy()
        dff["_row"] = np.arange(len(dff))
        dff = dff.sort_values([date_col, "_row"])
    else:
        dff["_row"] = np.arange(len(dff))
        dff = dff.sort_values(["_row"])
    return dff

def extract_draws(dff: pd.DataFrame, main_cols):
    draws = []
    for _, r in dff.iterrows():
        nums = pd.to_numeric(r[main_cols], errors="coerce").dropna().astype(int).tolist()
        if len(nums) == 6 and all(1 <= n <= 49 for n in nums):
            draws.append(nums)
    if len(draws) < 4:
        raise ValueError("Need at least 4 valid draws to compute n−4.")
    return draws

# Scoring (same logic as we used)
BAND_20_39 = set(range(20, 40))
LOW = set(range(1, 16))
MID = set(range(16, 30))
HIGH = set(range(30, 50))

def triple_score(triple, intersection):
    score = 0

    # intersection anchor is strongest
    score += sum(4 for n in triple if n in intersection)

    # prefer having at least one 20–39 backbone
    score += 2 if any(n in BAND_20_39 for n in triple) else 0

    # band dispersion reward (low/mid/high)
    bands = set()
    for n in triple:
        if n in LOW: bands.add("low")
        elif n in MID: bands.add("mid")
        else: bands.add("high")
    score += len(bands)

    # penalty for all low cluster
    if all(n in LOW for n in triple):
        score -= 3

    return score

# -----------------------
# UI
# -----------------------
uploaded = st.file_uploader("Upload your Excel/CSV file", type=["xlsx", "xls", "csv"])
if not uploaded:
    st.info("Upload a file to start.")
    st.stop()

try:
    if uploaded.name.lower().endswith(("xlsx","xls")):
        df = pd.read_excel(uploaded)
    else:
        df = pd.read_csv(uploaded)

    date_col = detect_date_col(df)
    main_cols = detect_main_cols(df)
    dff = sort_df(df, date_col)
    draws = extract_draws(dff, main_cols)

    # n-1 and n-4
    n1 = draws[-1]
    n4 = draws[-4]
    s1 = set(n1)
    s4 = set(n4)
    inter = s1 & s4
    pool = sorted(list(s1 | s4))

    st.subheader("Latest n−1 and n−4")
    st.write("**n−1 (latest):**", n1)
    st.write("**n−4:**", n4)
    st.write("**Intersection:**", sorted(list(inter)) if inter else "None")
    st.write("**Pool (n−1 ∪ n−4):**", pool)

    with st.expander("Ranking settings", expanded=True):
        top_k = st.slider("Show Top K strongest triples", 3, 30, 10)
        bottom_k = st.slider("Show Bottom K weakest triples", 3, 30, 10)

    # generate triples
    triples = list(itertools.combinations(pool, 3))
    ranked = []
    for t in triples:
        ranked.append((t, triple_score(t, inter)))
    ranked.sort(key=lambda x: x[1], reverse=True)

    top = ranked[:top_k]
    bottom = ranked[-bottom_k:][::-1]  # weakest first

    st.subheader("✅ Strongest triples")
    for t, sc in top:
        st.write(f"{t}  —  score {sc}")

    st.subheader("🔻 Weakest triples (least-likely)")
    for t, sc in bottom:
        st.write(f"{t}  —  score {sc}")

    # quick “impossible” pick = weakest
    st.subheader("🎯 Most least-likely triplet")
    st.markdown(f"### {bottom[0][0]}")

except Exception as e:
    st.error(f"Error: {e}")
