import streamlit as st
import itertools

def generate_filtered_duos_app():
    st.set_page_config(page_title="Sebman Density Strategy", page_icon="🎯", layout="centered")
    
    st.title("🎯 Sebman 42-Density Generator")
    st.subheader("Strategy: Internal Combinations + Max Gap Filter")

    st.write("""
    This app isolates the 42 internal combinations from your **n-1** and **n-3** draws.
    It then applies your exact scenario: bounding the numbers by a maximum gap. 
    *(e.g., With a Gap of 20, the number 1 will only pair with numbers up to 21).*
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
        "Maximum Gap Allowed between pairs (Your default is 20):", 
        min_value=5, max_value=48, value=20, step=1
    )
    
    current_draw = st.text_input("Current Draw (Optional - Enter 7 numbers to check if you won)", "")

    if st.button("Generate & Check Duos"):
        try:
            # Parse inputs (handles spaces and commas automatically)
            set1 = set([int(x.strip()) for x in draw_n1.replace(',', ' ').split()])
            set2 = set([int(x.strip()) for x in draw_n3.replace(',', ' ').split()])

            # Validation
            if len(set1) != 7 or len(set2) != 7:
                st.warning(f"Check your input! Draw 1 has {len(set1)} numbers. Draw 2 has {len(set2)}. Both must have exactly 7.")
                return

            # Generate internal combinations (The 42 Density Base)
            pairs_n1 = set(itertools.combinations(sorted(list(set1)), 2))
            pairs_n3 = set(itertools.combinations(sorted(list(set2)), 2))
            
            # Combine pairs (automatically removes duplicates if the same pair exists in both)
            base_pairs = pairs_n1.union(pairs_n3)
            
            # Apply the User's Gap Filter
            filtered_pairs = sorted([p for p in base_pairs if abs(p[0] - p[1]) <= max_gap])
            
            # Calculate financials
            total_base = len(base_pairs)
            total_filtered = len(filtered_pairs)
            discarded = total_base - total_filtered
            stake = total_filtered  # Assuming R1 per pair
            profit_on_win = 50 - stake
            roi = (profit_on_win / stake) * 100 if stake > 0 else 0

            # --- DISPLAY SUMMARY DASHBOARD ---
            st.divider()
            st.success("✅ Pairs Compressed Successfully!")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Base Pairs (Density)", f"{total_base}")
            col_stat2.metric(f"Pairs Discarded (Gap > {max_gap})", f"{discarded}")
            col_stat3.metric("Final Pairs to Play", f"{total_filtered}")

            st.info(f"**Financial Outlook:** Your Stake is **R{stake}**. If just one pair hits, your profit is **R{profit_on_win}** (ROI: **{roi:.1f}%**).")

            # --- RESULT CHECKING LOGIC ---
            if current_draw.strip():
                current_set = set([int(x.strip()) for x in current_draw.replace(',', ' ').split()])
                
                if len(current_set) != 7:
                    st.warning(f"Current draw input has {len(current_set)} numbers. It should be exactly 7 to check properly.")
                else:
                    st.divider()
                    st.subheader("🏆 Draw Results")
                    
                    # Check which filtered pairs actually won
                    winning_pairs = [p for p in filtered_pairs if p[0] in current_set and p[1] in current_set]
                    
                    if winning_pairs:
                        total_won = len(winning_pairs) * 50
                        net_profit = total_won - stake
                        st.balloons()
                        st.success(f"🎉 **WINNER!** You hit {len(winning_pairs)} winning pair(s) out of your {total_filtered} played!")
                        st.write(f"**Total Revenue:** R{total_won} | **Net Profit for this draw:** R{net_profit}")
                        
                        st.write("### ⭐️ Your Winning Pairs:")
                        for wp in winning_pairs:
                            st.write(f"✅ **{wp[0]} & {wp[1]}** *(Gap: {abs(wp[0] - wp[1])})*")
                    else:
                        st.error("❌ No winning pairs in this draw. The strategy absorbed the loss to protect your bankroll!")
            
            # --- DISPLAY ALL PLAYABLE PAIRS ---
            st.divider()
            st.subheader(f"Your {total_filtered} Playable Duos:")
            
            # Display pairs in a clean 4-column grid
            cols = st.columns(4)
            for i, pair in enumerate(filtered_pairs):
                gap = abs(pair[0] - pair[1])
                cols[i % 4].write(f"**{pair[0]} & {pair[1]}** *(Gap: {gap})*")

        except ValueError:
            st.error("Invalid input. Please enter numbers separated by spaces or commas only.")

if __name__ == "__main__":
    generate_filtered_duos_app()
