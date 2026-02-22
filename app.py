import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Sidian Tri-Tier Lab", layout="wide")

st.title("🎰 Sidian Synthesis Engine")
st.subheader("Tri-Tier Signature Analysis")

@st.cache_data
def analyze_signature_probabilities(file):
    df = pd.read_excel(file)
    draw_data = df.select_dtypes(include=['number']).values
    
    repeat_tally = Counter()
    total_occurrences = Counter()

    # Scan 2,278 draws in windows of 4
    for i in range(len(draw_data) - 4):
        past_3_draws = set(draw_data[i:i+3].flatten())
        next_draw = set(draw_data[i+3])
        
        for num in past_3_draws:
            total_occurrences[num] += 1
            if num in next_draw:
                repeat_tally[num] += 1
                
    # Calculate Repeat Probability (Repeat / Total)
    # Higher = Most Likely to repeat; Lower = Least Likely (Decay)
    return {num: repeat_tally[num] / total_occurrences[num] for num in total_occurrences}

uploaded_file = st.sidebar.file_uploader("Upload 'Full A Lister 1.0'", type=["xlsx", "xls"])

with st.form("tritier_logic_form"):
    st.write("Enter your 21 numbers to categorize them into Signature Tiers.")
    col_a, col_b, col_c = st.columns(3)
    row1 = col_a.text_input("Latest Draw")
    row2 = col_b.text_input("Draw 2")
    row3 = col_c.text_input("Draw 3")
    submit = st.form_submit_button("Generate Tri-Tier Report", type="primary")

if submit and uploaded_file:
    prob_map = analyze_signature_probabilities(uploaded_file)
    current_21 = list(set([int(n) for n in (row1 + " " + row2 + " " + row3).replace(",", " ").split() if n.isdigit()]))
    
    if len(current_21) >= 12:
        # Score and Sort
        scored = sorted([(num, prob_map.get(num, 0.5)) for num in current_21], key=lambda x: x[1], reverse=True)
        
        most_likely = scored[:4]        # Top 4
        least_likely = scored[-4:]      # Bottom 4
        
        # Calculate the middle index for 'Between'
        mid = len(scored) // 2
        between = scored[mid-2:mid+2]   # Middle 4

        # --- DISPLAY RESULTS ---
        st.divider()
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.success("### 🔥 Most Likely")
            st.caption("Highest Repeat Rate")
            for n, p in most_likely:
                st.metric(label=f"Num {n}", value=f"{p:.1%}")

        with c2:
            st.warning("### ⚖️ The Between")
            st.caption("Neutral Equilibrium")
            for n, p in between:
                st.metric(label=f"Num {n}", value=f"{p:.1%}")

        with c3:
            st.error("### 🧊 Least Likely")
            st.caption("Highest Decay Rate")
            for n, p in least_likely:
                st.metric(label=f"Num {n}", value=f"{p:.1%}")
    else:
        st.error("Please enter at least 12 unique numbers across the 3 draws.")

st.sidebar.info("Method: Sidian Tri-Tier Signature Extraction")
