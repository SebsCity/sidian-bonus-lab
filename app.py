import streamlit as st

# Mobile-friendly layout
st.set_page_config(page_title="Sidian Bonus Lab", layout="centered")

st.title("🎰 Sidian Synthesis Engine")
st.markdown("### Internal Pattern Analysis (Input-Only)")

# --- SECTION: INPUT DRAWS ---
# We use a form to make it fast on Android
with st.form("sidian_internal_form"):
    st.subheader("Input 3 Previous Draws")
    st.caption("Enter 6 main numbers + 1 bonus (7 total per row)")

    def get_input_row(label):
        val = st.text_input(label, placeholder="e.g. 1, 10, 15, 22, 30, 45, 7")
        if val:
            try:
                nums = [int(n.strip()) for n in val.split(',')]
                if len(nums) == 7:
                    return nums
                else:
                    st.warning(f"Row needs 7 numbers. You have {len(nums)}.")
            except:
                st.error("Please use numbers and commas only.")
        return []

    d1 = get_input_row("Latest Draw")
    d2 = get_input_row("Draw 2")
    d3 = get_input_row("Draw 3")
    
    submit = st.form_submit_button("Generate Prediction", type="primary")

# --- SECTION: LOGIC (No Uploaded Data) ---
if submit:
    all_inputs = d1 + d2 + d3
    
    if len(all_inputs) < 21:
        st.error("Please provide all 21 numbers to calculate the pattern.")
    else:
        # 1. Calculate Average (The 'Balance' Number)
        avg_val = sum(all_inputs) / len(all_inputs)
        
        # 2. Identify the Range
        min_val = min(all_inputs)
        max_val = max(all_inputs)
        
        # 3. Pattern Generation (Mathematical Offsets)
        # We look for numbers that fill the gaps between your inputs
        sorted_inputs = sorted(list(set(all_inputs)))
        
        predictions = []
        # Logic: Pick numbers near the average that weren't in the input
        potential_target = int(avg_val)
        
        # Generate 4 distinct numbers based on proximity to the 'Sidian Center'
        offsets = [-2, 2, -5, 5] 
        for offset in offsets:
            candidate = potential_target + offset
            # Ensure candidate is within standard lotto range and not in the recent 21
            if 1 <= candidate <= 52 and candidate not in all_inputs:
                predictions.append(candidate)
            else:
                # Fallback if the offset hits a recent number
                predictions.append(candidate + 1 if candidate + 1 not in all_inputs else candidate + 3)

        # Ensure we only have 4 unique numbers
        final_4 = list(set(predictions))[:4]

        # Display Results
        st.divider()
        st.balloons()
        st.write("### 🔮 Predicted Next 4 (Internal Logic):")
        cols = st.columns(4)
        for i, p_num in enumerate(final_4):
            cols[i].metric(label=f"Position {i+1}", value=p_num)
        
        st.caption("Logic: Calculated via Mean Center and Exclusion Gaps from your 21 inputs.")

st.sidebar.write("Developed for **Sidian Brand**")
st.sidebar.info("Currently running on **Internal Synthesis mode** (Ignoring Datasheet).")
