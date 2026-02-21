import streamlit as st
import pandas as pd
from collections import Counter

# Optimized for mobile viewing
st.set_page_config(page_title="Sidian Bonus Lab", layout="centered")

st.title("🎰 Sidian Synthesis Engine")
st.caption("Version 1.0 - Predictive Analysis")

# --- DATA CACHING (Stops the slowness) ---
@st.cache_data
def load_and_process(file):
    # Reads Excel and prepares frequency map once per upload
    df = pd.read_excel(file)
    # Extract all numbers from all columns
    all_vals = df.select_dtypes(include=['number']).values.flatten()
    clean_vals = [int(n) for n in all_vals if pd.notnull(n)]
    return Counter(clean_vals)

# --- SIDEBAR UPLOAD ---
st.sidebar.header("Data Source")
uploaded_file = st.sidebar.file_uploader("Upload 'Full A Lister 1.0'", type=["xlsx", "xls"])

if uploaded_file:
    with st.spinner("Analyzing 2,278 draws..."):
        freq_map = load_and_process(uploaded_file)
    st.sidebar.success("Analysis Complete!")

    # --- INPUT FORM (Stops lag while typing) ---
    with st.form("main_logic_form"):
        st.subheader("Input Previous 3 Draws")
        st.info("Enter 6 numbers + bonus, separated by commas")
        
        row1 = st.text_input("Latest Draw (Draw 1)", placeholder="e.g. 1, 15, 22, 30, 41, 49, 8")
        row2 = st.text_input("Draw 2", placeholder="e.g. 4, 10, 19, 25, 33, 40, 2")
        row3 = st.text_input("Draw 3", placeholder="e.g. 7, 12, 18, 28, 35, 42, 11")
        
        submit = st.form_submit_button("GENERATE PREDICTION")

    if submit:
        try:
            # Parse all 21 numbers
            all_inputs = []
            for r in [row1, row2, row3]:
                nums = [int(n.strip()) for n in r.split(',')]
                if len(nums) != 7:
                    st.error(f"Row error: Expected 7 numbers, found {len(nums)}")
                    st.stop()
                all_inputs.extend(nums)

            # Sidian Prediction Logic:
            # Find the most frequent numbers in history that are NOT in the last 21 numbers.
            recent_set = set(all_inputs)
            sorted_history = sorted(freq_map.items(), key=lambda x: x[1], reverse=True)
            
            final_4 = []
            for num, count in sorted_history:
                if num not in recent_set:
                    final_4.append(num)
                if len(final_4) == 4:
                    break
            
            # Result Display
            st.divider()
            st.success("### 🔮 Predicted Next 4 Numbers")
            res_cols = st.columns(4)
            for i, val in enumerate(final_4):
                res_cols[i].metric(label=f"Rank {i+1}", value=val)
                
        except Exception as e:
            st.error("Format Error: Ensure you use commas between numbers.")

else:
    st.warning("Please upload your Excel file in the sidebar to start the engine.")
