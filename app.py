import streamlit as st
import itertools

def generate_hot_pool_app():
    st.title("🎰 Sebman Duo Generator")
    st.subheader("Strategy: Previous & 3rd Previous Draw (n-1 & n-3)")

    st.write("""
    Enter the 7 numbers (including Bonus) from your two chosen draws to identify 
    the 'Hot Pool' and generate potential winning pairs.
    """)

    col1, col2 = st.columns(2)

    with col1:
        draw_n1 = st.text_input("Draw n-1 (7 numbers, comma separated)", "1, 8, 34, 39, 46, 49, 47")
    
    with col2:
        draw_n3 = st.text_input("Draw n-3 (7 numbers, comma separated)", "6, 17, 18, 33, 41, 43, 26")

    if st.button("Generate Hot Pool & Duos"):
        try:
            # Clean and parse input
            set1 = set([int(x.strip()) for x in draw_n1.split(",")])
            set2 = set([int(x.strip()) for x in draw_n3.split(",")])

            if len(set1) != 7 or len(set2) != 7:
                st.warning("Please ensure both sets have exactly 7 numbers.")
                return

            # Calculate unique pool
            hot_pool = sorted(list(set1.union(set2)))
            overlap = set1.intersection(set2)

            # Display Analysis
            st.divider()
            st.success(f"✅ Hot Pool Identified: {len(hot_pool)} Unique Numbers")
            st.write(f"**The Hot Pool:** `{hot_pool}`")
            
            if overlap:
                st.info(f"Numbers appearing in both draws: `{list(overlap)}`")
            else:
                st.info("No overlapping numbers found.")

            # Generate Duos (Pairs)
            all_pairs = list(itertools.combinations(hot_pool, 2))
            
            st.subheader(f"Generated Duos ({len(all_pairs)} total pairs)")
            
            # Display pairs in a clean grid
            cols = st.columns(4)
            for i, pair in enumerate(all_pairs):
                cols[i % 4].write(f"Pair {i+1}: **{pair[0]} - {pair[1]}**")

        except ValueError:
            st.error("Please enter valid numbers separated by commas (e.g., 1, 2, 3, 4, 5, 6, 7)")

if __name__ == "__main__":
    generate_hot_pool_app()
