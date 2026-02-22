import streamlit as st
import itertools

def generate_filtered_duos_app():
    st.set_page_config(page_title="Sebman Gap Filter Strategy", page_icon="🎯")
    
    st.title("🎯 Sebman Duo Generator")
    st.subheader("Strategy: '42 Density' with Gap Filter (Max Gap 20)")

    st.write("""
    Enter the 7 numbers (including Bonus) from your $n-1$ and $n-3$ draws. 
    Separate numbers using **spaces** (e.g., `1 12 15 22 34 40 45`).
    """)

    col1, col2 = st.columns(2)

    with col1:
        draw_n1 = st.text_input("Draw n-1", "4 10 14 20 42 49 12")
    
    with col2:
        draw_n3 = st.text_input("Draw n-3", "5 7 14 19 30 40 15")

    if st.button("Generate & Filter Duos"):
        try:
            # Parse inputs: replace commas with spaces, split by whitespace
            set1_list = draw_n1.replace(',', ' ').split()
            set2_list = draw_n3.replace(',', ' ').split()
            
            set1 = set([int(x) for x in set1_list])
            set2 = set([int(x) for x in set2_list])

            # Validation
            if len(set1) != 7 or len(set2) != 7:
                st.warning(f"Check your input! Draw 1 has {len(set1)} unique numbers. Draw 2 has {len(set2)}. Both must have exactly 7.")
                return

            # Generate internal combinations (The 42 Density)
            pairs_n1 = set(itertools.combinations(sorted(list(set1)), 2))
            pairs_n3 = set(itertools.combinations(sorted(list(set2)), 2))
            
            # Combine pairs (deduplicates automatically if the same pair exists in both)
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
            st.divider()
            st.success("✅ Pairs Generated and Filtered Successfully!")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            col_stat1.metric("Base Pairs (Density)", f"{total_base}")
            col_stat2.metric("Pairs Discarded (Gap 21+)", f"{discarded}")
            col_stat3.metric("Final Pairs to Play", f"{total_filtered}")

            st.info(f"**Financial Outlook:** Stake is **R{stake}**. If one pair hits, your profit is **R{profit_on_win}** (ROI: **{roi:.1f}%**).")

            # Display Final Pairs
            st.subheader(f"Your {total_filtered} Playable Duos:")
            
            # Display pairs in a clean 4-column grid
            cols = st.columns(4)
            for i, pair in enumerate(filtered_pairs):
                gap = abs(pair[0] - pair[1])
                # Show the pair and the gap for context
                cols[i % 4].write(f"**{pair[0]} & {pair[1]}** *(Gap: {gap})*")

        except ValueError:
            st.error("Invalid input. Please enter numbers separated by spaces only.")

if __name__ == "__main__":
    generate_filtered_duos_app()
