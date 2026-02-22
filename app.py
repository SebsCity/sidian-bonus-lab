import streamlit as st
from collections import Counter

# Mobile-friendly layout
st.set_page_config(page_title="Sidian Bonus Lab", layout="centered")

st.title("🎰 Sidian Synthesis Engine")
st.subheader("Repeater Logic Mode")
st.markdown("Goal: Identify which numbers are likely to **repeat**.")

# --- SECTION: INPUT DRAWS ---
with st.form("sidian_repeater_form"):
    st.write("Input format: 6 main numbers + 1 bonus (7 total per row)")

    def parse_numbers(text):
        clean_text = text.replace(",", " ")
        parts = clean_text.split()
        return [int(p) for p in parts if p.isdigit()]

    def get_input_row(label):
        val = st.text_input(label, placeholder="e.g. 5 12 22 30 31 45 8")
        if val:
            nums = parse_numbers(val)
            if len(nums) == 7: return nums
            else: st.warning(f"Enter 7 numbers for {label}.")
        return []

    d1 = get_input_row("Latest Draw")
    d2 = get_input_row("Draw 2")
    d3 = get_input_row("Draw 3")

    submit = st.form_submit_button("Analyze for Repeaters", type="primary")

# --- SECTION: NEW REPEATER LOGIC ---
if submit:
    all_inputs = d1 + d2 + d3
    
    if len(all_inputs) < 21:
        st.error("Please provide all 3 draws (21 numbers total).")
    else:
        # 1. Count frequencies (Which numbers already repeated?)
        counts = Counter(all_inputs)
        
        # 2. Calculate the mathematical 'Hot Zone' (Average)
        avg_val = int(sum(all_inputs) / len(all_inputs))
        
        # 3. Build the Prediction List
        predictions = []
        
        # STRATEGY A: Prioritize numbers that appeared MORE THAN ONCE in the 21 inputs
        repeaters = [num for num, count in counts.items() if count > 1]
        predictions.extend(repeaters)
        
        # STRATEGY B: Check the 'Hot Zone' neighbors
        # If these neighbors are in your recent 21, they are high-priority
        hot_zone = [avg_val, avg_val - 1, avg_val + 1, avg_val + 5, avg_val - 5]
        
        for candidate in hot_zone:
            if candidate in all_inputs: # This is the 'Conflict Solver' flip
                predictions.append(candidate)
        
        # 4. Clean up: Remove duplicates and limit to 4
        # We use dict.fromkeys to keep the priority order
        final_4 = list(dict.fromkeys(predictions))[:4]
        
        # Fallback: If we still don't have 4 (unlikely with 21 inputs), 
        # just pick the highest numbers from the input
        if len(final_4) < 4:
            additional = sorted(list(set(all_inputs)), reverse=True)
            for num in additional:
                if num not in final_4:
                    final_4.append(num)
                if len(final_4) == 4: break

        # --- DISPLAY RESULTS ---
        st.divider()
        st.balloons()
        st.write("### 🔮 Predicted Repeaters:")
        
        cols = st.columns(4)
        for i, p_num in enumerate(final_4):
            cols[i].metric(label=f"Rank {i+1}", value=p_num)

        st.info("Logic: Priority given to numbers appearing multiple times in inputs or falling in the 'Hot Zone' average.")

st.sidebar.write("Developed for **Sidian Brand**")
st.sidebar.info("Running: **Repeater Preference Mode**")
