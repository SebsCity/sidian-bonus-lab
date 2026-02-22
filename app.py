import streamlit as st
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Sidian Filter Lab", layout="centered")

st.title("🎰 Sidian Synthesis Engine")
st.subheader("Historical Non-Repeater Analysis")

# --- DATASET PROCESSING ---
@st.cache_data
def analyze_non_repeater_signature(file):
    df = pd.read_excel(file)
    # Ensure we only look at the numeric draw columns
    draw_data = df.select_dtypes(include=['number']).values
    
    non_repeater_tally = Counter()
    total_window_occurrences = Counter()

    # Scan history in windows of 4 (3 draws input -> 1 draw result)
    for i in range(len(draw_data) - 4):
        past_3_draws = set(draw_data[i:i+3].flatten())
        next_draw = set(draw_data[i+3])
        
        for num in past_3_draws:
            total_window_occurrences[num] += 1
            if num not in next_draw:
                # This number was present in the 3-draw window but NOT in the 4th
                non_repeater_tally[num] += 1
                
    # Calculate the 'Non-Repeat Probability' for every number in history
    probabilities = {}
    for num in total_window_occurrences:
        probabilities[num] = non_repeater_tally[num] / total_window_occurrences[num]
        
    return probabilities

uploaded_file = st.sidebar.file_uploader("Upload 'Full A Lister 1.0'", type=["xlsx", "xls"])

with st.form("filter_logic_form"):
    st.write("Input your 21 numbers to find which are historically least likely to repeat.")
    
    def parse_input(text):
        return [int(n.strip()) for n in text.replace(",", " ").split() if n.strip().isdigit()]

    row1 = st.text_input("Latest Draw")
    row2 = st.text_input("Draw 2")
    row3 = st.text_input("Draw 3")
    
    submit = st.form_submit_button("Run Filter Analysis", type="primary")

if submit and uploaded_file:
    with st.spinner("Calculating Historical Decay Rates..."):
        prob_map = analyze_non_repeater_signature(uploaded_file)
    
    current_21 = list(set(parse_input(row1) + parse_input(row2) + parse_input(row3)))
    
    if len(current_21) > 0:
        # Score your 21 numbers based on their historical 'Non-Repeat' probability
        scored_numbers = []
        for num in current_21:
            # If the number isn't in history, we give it a neutral score
            score = prob_map.get(num, 0.5) 
            scored_numbers.append((num, score))
        
        # Sort by HIGHEST probability of NOT repeating
        scored_numbers.sort(key=lambda x: x[1], reverse=True)
        final_4 = scored_numbers[:4]

        # --- RESULTS ---
        st.divider()
        st.error("### 📉 Predicted Non-Repeaters:")
        st.write("Based on 2,278 draws, these numbers from your input are historically most likely to **STAY OUT** of the next draw.")
        
        cols = st.columns(4)
        for i, (val, prob) in enumerate(final_4):
            cols[i].metric(label=f"Rank {i+1}", value=int(val), delta=f"{prob:.1%} Decay", delta_color="inverse")
            
        st.caption("Logic: High Decay Score = Number historically disappears after appearing in a 3-draw window.")
    else:
        st.error("Please enter your draws correctly.")

st.sidebar.info("Method: Decay Visualization & Signature Filtering")
