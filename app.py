import streamlit as st
import pandas as pd
import numpy as np
import itertools

st.set_page_config(page_title="2–3 Hunter Engine", layout="wide")

st.title("🎯 2–3 Hunter Engine")
st.caption("Prioritized 3-number selection from last 3 draws (AI weighted)")

# ==========================
# FILE UPLOAD (EXCEL)
# ==========================
uploaded_file = st.file_uploader("Upload Lotto History (.xlsx)", type=["xlsx"])

if uploaded_file:

    # Read Excel safely
    df = pd.read_excel(uploaded_file)

    st.success("Excel file loaded successfully.")

    # --------------------------
    # Basic Cleaning
    # --------------------------
    df = df.dropna(how="all")
    df = df.reset_index(drop=True)

    # Assuming:
    # Column 0 = Date
    # Columns 1–6 = Main numbers
    # Column 7 = Bonus (optional)

    if df.shape[1] < 7:
        st.error("File format incorrect. Expecting at least 7 columns.")
        st.stop()

    number_columns = df.columns[1:8]  # 6 mains + bonus
    df = df.sort_values(by=df.columns[0])

    # ==========================
    # EXTRACT LAST 3 DRAWS
    # ==========================
    last3 = df.tail(3)

    pool = []
    for col in number_columns:
        pool.extend(last3[col].values)

    pool = [int(x) for x in pool if pd.notnull(x)]

    st.subheader("📊 Last 3 Draws Pool (21 Numbers)")
    st.write(pool)

    # ==========================
    # AI WEIGHTED SCORING
    # ==========================
    scores = {}

    for number in set(pool):
        scores[number] = 0

    # Frequency weighting
    for number in pool:
        scores[number] += pool.count(number) * 3

    # Recency bonus (latest draw)
    latest_draw = last3.iloc[-1][number_columns].values
    for number in latest_draw:
        scores[number] += 2

    # Overheat penalty (appears in all 3 draws)
    for number in set(pool):
        if pool.count(number) >= 3:
            scores[number] -= 2

    # Sort ranked numbers
    ranked_numbers = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    st.subheader("🧠 Ranked Numbers (AI Weighted)")
    st.write(ranked_numbers)

    # ==========================
    # BUILD 3-NUMBER HUNTER SETS
    # ==========================
    top_numbers = [num for num, score in ranked_numbers[:7]]

    combos = list(itertools.combinations(top_numbers, 3))

    combo_scores = []

    for combo in combos:
        combo_score = sum(scores[n] for n in combo)
        combo_scores.append((combo, combo_score))

    combo_scores = sorted(combo_scores, key=lambda x: x[1], reverse=True)

    st.subheader("🔥 Top Prioritized 3-Number Hunter Sets")

    for combo, score in combo_scores[:5]:
        st.write(f"{combo}  | Score: {score}")

else:
    st.info("Upload your Excel file (.xlsx) to begin.")
