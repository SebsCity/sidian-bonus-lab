import streamlit as st
import itertools

def generate_anchored_duos_app():
    st.set_page_config(page_title="Sebman Anchor Strategy", page_icon="⚓", layout="centered")
    
    st.title("⚓ Sebman Anchor Generator")
    st.subheader("Strategy: 42-Density Filtered by Anchor Gaps")

    st.write("""
    This app isolates the internal combinations from your **n-1** and **n-3** draws.
    It selects numbers and anchors them to any other number in the pool that falls 
    strictly within your chosen gap interval.
    """)

    # --- INPUT SECTION ---
    col1, col2 = st.columns(2)
    with col1:
        draw_n1 = st.text_input("Draw n-1 (Required)", "4 10 14 20 42 49 12")
    with col2:
        draw_n3 = st.text_input("Draw n-3 (Required)", "5 7 14 19 30 40 15")
        
    st.divider()
    
    # --- DYNAMIC GAP SLIDER ---
    st.write("### ⚙️ Strategy Settings")
    max_gap = st.slider(
        "Maximum Gap Allowed (Your Goldilocks Zone is 10):", 
        min_value=1, max_value=25, value=10, step=1
    )
    
    current_draw = st.text_input("Current Draw (Optional - Enter 7 numbers to check if you won)", "")

    if st.button("Generate & Check Duos"):
        try:
            # Parse inputs (handles spaces and commas)
            set1 = set([int(x.strip()) for x in draw_n1.replace(',', ' ').split()])
            set2 = set([int(x.strip()) for x in draw_n3.replace(',', ' ').split()])

            # Validation
            if len(set1) != 7 or len(set2) != 7:
                st.warning(f"Check your input! Draw 1 has {len(set1)} numbers. Draw 2 has {len(set2)}. Both must have exactly 7.")
                return

            # Generate internal combinations (The 42 Density Base)
            pairs_n1 = set(itertools.combinations(sorted(list(set1)), 2))
            pairs_n3 = set(itertools.combinations(sorted(list(set2)), 2))
            
            # Combine pairs (automatically removes duplicates)
            base_pairs = pairs_n1.union(pairs_n3)
            
            # Apply the Anchor/Gap Filter
            filtered_pairs = sorted([p for p in base_pairs if 1 <= abs(p[0] - p[1]) <= max_gap])
            
            # Calculate financials
            total_base = len(base_pairs)
            total_filtered = len(filtered_pairs)
            discarded = total_base - total_filtered
            stake = total_filtered  # Assuming R1 per pair
            profit_on_win = 50 - stake
            roi = (profit_on_win / stake) * 100 if stake > 0 else 0

            # --- DISPLAY SUMMARY DASHBOARD ---
            st.divider()
            st.success("✅ Pairs Anchored and Compressed Successfully!")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Base Pairs (Density)", f"{total_base}")
            col_stat2.metric(f"Pairs Discarded (> {max_gap} Gap)", f"{discarded}")
            col_stat3.metric("Final Pairs to Play", f"{total_filtered}")

            if stake > 0:
                st.info(f"**Financial Outlook:** Your Stake is **R{stake}**. If one pair hits, your profit is **R{profit_on_win}** (ROI: **{roi:.1f}%**).")
            else:
                st.error("No numbers in this pool fall within your target gap. Keep your money in your pocket today!")

            # --- RESULT CHECKING LOGIC ---
            if current_draw.strip() and stake > 0:
                current_set = set([int(x.strip()) for x in current_draw.replace(',', ' ').split()])
                
                if len(current_set) != 7:
                    st.warning("Current draw input must have exactly 7 numbers to check properly.")
                else:
                    st.divider()
                    st.subheader("🏆 Draw Results")
                    
                    winning_pairs = [p for p in filtered_pairs if p[0] in current_set and p[1] in current_set]
                    
                    if winning_pairs:
                        total_won = len(winning_pairs) * 50
                        net_profit = total_won - stake
                        st.balloons()
                        st.success(f"🎉 **WINNER!** You hit {len(winning_pairs)} winning pair(s)!")
                        st.write(f"**Total Revenue:** R{total_won} | **Net Profit for this draw:** R{net_profit}")
                        
                        for wp in winning_pairs:
                            st.write(f"✅ **{wp[0]} & {wp[1]}** *(Gap: {abs(wp[0] - wp[1])})*")
                    else:
                        st.error("❌ No winning pairs in this draw. The strategy absorbed the loss to protect your bankroll.")
            
            # --- DISPLAY ANCHORED PAIRS ---
            if stake > 0:
                st.divider()
                st.subheader("🔗 Your Playable Duos (Grouped by Anchor Number)")
                
                # Logic to group pairs by their first number (the anchor)
                anchors = sorted(list(set([p[0] for p in filtered_pairs])))
                
                for anchor in anchors:
                    # Find all pairs that start with this anchor
                    anchor_pairs = [p for p in filtered_pairs if p[0] == anchor]
                    
                    # Create a clean display string for these pairs
                    pair_strings = [f"**{p[0]} & {p[1]}** *(Gap {abs(p[0]-p[1])})*" for p in anchor_pairs]
                    
                    with st.container():
                        st.markdown(f"### Anchored to {anchor}")
                        st.write(" • " + " | ".join(pair_strings))
                        st.write("---") # Visual separator

        except ValueError:
            st.error("Invalid input. Please enter numbers separated by spaces or commas only.")

if __name__ == "__main__":
    generate_anchored_duos_app()
