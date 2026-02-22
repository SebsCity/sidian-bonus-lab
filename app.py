import streamlit as st
import itertools

def generate_hot_pool_app():
    st.set_page_config(page_title="Sebman Duo Generator", page_icon="🎰")
    
    st.title("🎰 Sebman Duo Generator")
    st.subheader("Strategy: Previous & 3rd Previous Draw (n-1 & n-3)")

    st.write("""
    Enter the 7 numbers (including Bonus) from your draws. 
    You can separate them with **spaces** or **commas**.
    """)

    col1, col2 = st.columns(2)

    with col1:
        # Default example using spaces
        draw_n1 = st.text_input("Draw n-1", "1 8 34 39 46 49 47")
    
    with col2:
        # Default example using spaces
        draw_n3 = st.text_input("Draw n-3", "6 17 18 33 41 43 26")

    if st.button("Generate Hot Pool & Duos"):
        try:
            # Logic to handle both spaces and commas:
            # 1. Replace commas with spaces
            # 2. Split by any whitespace
            set1_list = draw_n1.replace(',', ' ').split()
            set2_list = draw_n3.replace(',', ' ').split()
            
            set1 = set([int(x) for x in set1_list])
            set2 = set([int(x) for x in set2_list])

            if len(set1) != 7 or len(set2) != 7:
                st.warning(f"Check your input: Draw 1 has {len(set1)} unique numbers and Draw 2 has {len(set2)}. Both should have 7.")
                return

            # Calculate unique pool
            hot_pool = sorted(list(set1.union(set2)))
            overlap = set1.intersection(set2)

            # Display Analysis
            st.divider()
            st.success(f"✅ Hot Pool Identified: {len(hot_pool)} Unique Numbers")
            st.write(f"**Your numbers to play from:** `{', '.join(map(str, hot_pool))}`")
            
            if overlap:
                st.info(f"Overlapping numbers (extra hot): `{', '.join(map(str, overlap))}`")
            else:
                st.info("No overlapping numbers between these two draws.")

            # Generate Duos (Pairs)
            all_pairs = list(itertools.combinations(hot_pool, 2))
            
            st.subheader(f"Generated Duos ({len(all_pairs)} total pairs)")
            st.info("Tip: If playing all pairs is too expensive, focus on pairs containing the 'Overlapping' numbers above.")
            
            # Display pairs in a clean grid
            cols = st.columns(4)
            for i, pair in enumerate(all_pairs):
                cols[i % 4].write(f"#{i+1}: **{pair[0]} & {pair[1]}**")

        except ValueError:
            st.error("Please enter valid numbers only. Ensure there are no letters or special characters other than spaces or commas.")

if __name__ == "__main__":
    generate_hot_pool_app()
