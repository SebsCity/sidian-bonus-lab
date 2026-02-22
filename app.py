import streamlit as st
import itertools

def generate_filtered_duos_app():
    st.set_page_config(page_title="Sebman Gap Filter Strategy", page_icon="🎯", layout="centered")
    
    st.title("🎯 Sebman Duo Generator & Checker")
    st.subheader("Strategy: '42 Density' with Gap Filter (Max Gap 20)")

    st.write("""
    Enter your numbers (separated by spaces or commas). 
    Fill in **n-1** and **n-3** to generate your pairs. 
    Add the **Current Draw** to see if you won!
    """)

    # Input section
    col1, col2 = st.columns(2)
    with col1:
        draw_n1 = st.text_input("Draw n-1 (Required)", "4 10 14 20 42 49 12")
    with col2:
        draw_n3 = st.text_input("Draw n-3 (Required)", "5 7 14 19 30 40 15")
        
    st.divider()
    current_draw = st.text_input("Current Draw (Optional - To check results)", "")

    if st.button("Generate & Check Duos"):
        try:
            # Parse inputs
            set1 = set([int(x.strip()) for x in draw_n1.replace(',', ' ').split()])
            set2 = set([int(x.strip()) for x in draw_n3.replace(',', ' ').split()])

            # Validation for n-1 and n-3
            if len(set1) != 7 or len(set2) != 7:
                st.warning(f"Check your input! Draw 1 has {len(set1)} unique numbers. Draw 2 has {len(set2)}. Both must have exactly 7.")
                return

            # Generate internal combinations (The 42 Density)
            pairs_n1 = set(itertools.combinations(sorted(list(set1)), 2))
            pairs_n3 = set(itertools.combinations(sorted(list(set2)), 2))
            base_pairs = pairs_n1.union(pairs_n3)
            
            # Apply the Gap Filter (Keep gaps <= 20)
            filtered_pairs = sorted([p for p in base_pairs if abs(p[0] - p[1]) <= 20])
            
            # Calculate financials
            total_base = len(base_pairs)
            total_filtered = len(filtered_pairs)
            discarded = total_base - total_filtered
            stake = total_filtered  # Assuming R1 per pair
            profit_on_win = 50 - stake
            roi = (profit_on_win / stake) * 100 if stake > 0 else 0

            # Display Summary Dashboard
            st.success("✅ Pairs Generated and Filtered Successfully!")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Base Pairs (Density)", f"{total_base}")
            col_stat2.metric("Pairs Discarded (Gap 21+)", f"{discarded}")
            col_stat3.metric("Final Pairs to Play", f"{total_filtered}")

            st.info(f"**Financial Outlook:** Stake is **R{stake}**. If a pair hits, your profit is **R{profit_on_win}** (ROI: **{roi:.1f}%**).")

            # --- RESULT CHECKING LOGIC ---
            if current_draw.strip():
                current_set = set([int(x.strip()) for x in current_draw.replace(',', ' ').split()])
                
                if len(current_set) != 7:
                    st.warning(f"Current draw input has {len(current_set)} numbers. It should be exactly 7 to check properly.")
                else:
                    st.divider()
                    st.subheader("🏆 Draw Results")
                    
                    # Find winning pairs inside the filtered list
                    winning_pairs = [p for p in filtered_pairs if p[0] in current_set and p[1] in current_set]
                    
                    if winning_pairs:
                        total_won = len(winning_pairs) * 50
                        net_profit = total_won - stake
                        st.balloons()
                        st.success(f"🎉 **WINNER!** You hit {len(winning_pairs)} winning pair(s)!")
                        st.write(f"**Total Revenue:** R{total_won} | **Net Profit:** R{net_profit}")
                        
                        st.write("### ⭐️ Your Winning Pairs:")
                        for wp in winning_pairs:
                            st.write(f"✅ **{wp[0]} & {wp[1]}**")
                    else:
                        st.error("❌ No winning pairs in this draw. Better luck next time!")
            
            # --- DISPLAY ALL PLAYABLE PAIRS ---
            st.divider()
            st.subheader(f"Your {total_filtered} Playable Duos:")
            
            cols = st.columns(4)
            for i, pair in enumerate(filtered_pairs):
                gap = abs(pair[0] - pair[1])
                cols[i % 4].write(f"{pair[0]} & {pair[1]} *(Gap: {gap})*")

        except ValueError:
            st.error("Invalid input. Please enter numbers separated by spaces or commas only.")

if __name__ == "__main__":
    generate_filtered_duos_app()
