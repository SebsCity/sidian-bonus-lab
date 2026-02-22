import streamlit as st
import re

# Mobile-friendly layout
st.set_page_config(page_title="Sidian Bonus Lab", layout="centered")

st.title("🎰 Sidian Synthesis Engine")
st.markdown("### Internal Pattern Analysis (Input-Only)")

# --- SECTION: INPUT DRAWS ---
with st.form("sidian_internal_form"):
    st.subheader("Input 3 Previous Draws")
    st.caption("Enter 6 main numbers + 1 bonus (7 total per row)")
    st.caption("You can separate numbers with spaces OR commas")

    def parse_numbers(text):
        # Replace commas with spaces, then split
        clean_text = text.replace(",", " ")
        parts = clean_text.split()
        
        numbers = []
        for p in parts:
            if p.isdigit():
                numbers.append(int(p))
            else:
                raise ValueError("Invalid character detected.")
        return numbers

    def get_input_row(label):
        val = st.text_input(label, placeholder="e.g. 1 10 15 22 30 45 7")
        if val:
            try:
                nums = parse_numbers(val)
                if len(nums) == 7:
                    return nums
                else:
                    st.warning(f"{label} needs exactly 7 numbers. You entered {len(nums)}.")
            except:
                st.error("Use numbers separated by spaces or commas only.")
        return []

    d1 = get_input_row("Latest Draw")
    d2 = get_input_row("Draw 2")
    d3 = get_input_row("Draw 3")

    submit = st.form_submit_button("Generate Prediction", type="primary")

# --- SECTION: LOGIC ---
if submit:
    all_inputs = d1 + d2 + d3
    
    if len(all_inputs) < 21:
        st.error("Please provide all 21 numbers to calculate the pattern.")
    else:
        avg_val = sum(all_inputs) / len(all_inputs)
        min_val = min(all_inputs)
        max_val = max(all_inputs)

        sorted_inputs = sorted(list(set(all_inputs)))
        predictions = []
        potential_target = int(avg_val)

        offsets = [-2, 2, -5, 5]

        for offset in offsets:
            candidate = potential_target + offset
            
            if 1 <= candidate <= 52 and candidate not in all_inputs:
                predictions.append(candidate)
            else:
                fallback = candidate + 1
                while fallback in all_inputs and fallback <= 52:
                    fallback += 1
                if 1 <= fallback <= 52:
                    predictions.append(fallback)

        final_4 = list(dict.fromkeys(predictions))[:4]

        st.divider()
        st.balloons()
        st.write("### 🔮 Predicted Next 4 (Internal Logic):")

        cols = st.columns(4)
        for i, p_num in enumerate(final_4):
            cols[i].metric(label=f"Position {i+1}", value=p_num)

        st.caption("Logic: Calculated via Mean Center and Exclusion Gaps from your 21 inputs.")

st.sidebar.write("Developed for **Sidian Brand**")
st.sidebar.info("Currently running on **Internal Synthesis mode** (Ignoring Datasheet).")
