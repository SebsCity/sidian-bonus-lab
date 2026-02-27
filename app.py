import streamlit as st
import pandas as pd

st.set_page_config(page_title="Duo Compression", layout="centered")

st.title("🎯 Lotto Duo Compression")

uploaded = st.file_uploader("Upload Excel or CSV", type=["xlsx", "xls", "csv"])

if uploaded:

    if uploaded.name.endswith(("xlsx", "xls")):
        df = pd.read_excel(uploaded)
    else:
        df = pd.read_csv(uploaded)

    # assume first 6 numeric columns are main numbers
    numeric_cols = []
    for col in df.columns:
        if pd.to_numeric(df[col], errors="coerce").notna().mean() > 0.8:
            numeric_cols.append(col)

    main_cols = numeric_cols[:6]

    draws = df[main_cols].dropna().astype(int).values.tolist()
    latest = draws[-1]

    st.write("Latest draw:", latest)

    # -5 transformation
    candidates = sorted(set(
        n - 5 for n in latest
        if 1 <= n - 5 <= 49
    ))

    st.write("Candidate set (-5):", candidates)

    # simple compression: top 4 pairs
    pairs = []
    for i in range(len(candidates)):
        for j in range(i+1, len(candidates)):
            pairs.append((candidates[i], candidates[j]))

    st.subheader("Compressed Duos (Top 4)")
    for p in pairs[:4]:
        st.write(f"{p[0]} & {p[1]}")
