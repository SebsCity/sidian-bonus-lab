import streamlit as st
import itertools

def run_strategy_hub_app():
    st.set_page_config(page_title="Sebman Strategy Hub", page_icon="🎯", layout="centered")
    
    st.title("🎯 Sebman Strategy Hub")
    
    # Create two tabs
    tab1, tab2 = st.tabs(["⚓ Daily Anchor (Duos)", "🔥 Trio Triggers (R500 Payouts)"])
    
    # ==========================================
    # TAB 1: DYNAMIC ANCHOR STRATEGY (DUOS)
    # ==========================================
    with tab1:
        st.subheader("Strategy: 42-Density Filtered by Anchor Gaps")
        st.write("Use this **every day**. It anchors numbers from your **n-1** and **n-3** draws based on your target gap to catch clustered numbers for Duo wins (R50).")
        
        col1, col2 = st.columns(2)
        with col1:
            draw_n1 = st.text_input("Draw n-1 (Required)", "4 10 14 20 42 49 12", key="n1_input")
        with col2:
            draw_n3 = st.text_input("Draw n-3 (Required)", "5 7 14 19 30 40 15", key="n3_input")
            
        st.divider()
        max_gap = st.slider("Maximum Gap Allowed (Your Sweet Spot is 10):", min_value=1, max_value=25, value=10, step=1)
        
        if st.button("Generate Anchored Duos", key="btn_anchor"):
            try:
                set1 = set([int(x.strip()) for x in draw_n1.replace(',', ' ').split()])
                set2 = set([int(x.strip()) for x in draw_n3.replace(',', ' ').split()])
                
                if len(set1) != 7 or len(set2) != 7:
                    st.warning("Check your input! Both draws must have exactly 7 unique numbers.")
                else:
                    base_pairs = set(itertools.combinations(sorted(list(set1)), 2)).union(set(itertools.combinations(sorted(list(set2)), 2)))
                    filtered_pairs = sorted([p for p in base_pairs if 1 <= abs(p[0] - p[1]) <= max_gap])
                    
                    stake = len(filtered_pairs)
                    if stake > 0:
                        st.success(f"✅ Generated {stake} Playable Duos (Cost: R{stake})")
                        anchors = sorted(list(set([p[0] for p in filtered_pairs])))
                        for anchor in anchors:
                            anchor_pairs = [p for p in filtered_pairs if p[0] == anchor]
                            pair_strings = [f"**{p[0]} & {p[1]}** *(Gap {abs(p[0]-p[1])})*" for p in anchor_pairs]
                            st.markdown(f"### Anchored to {anchor}")
                            st.write(" • " + " | ".join(pair_strings))
                            st.write("---")
                    else:
                        st.error("No valid intervals today! Keep your money in your pocket.")
            except ValueError:
                st.error("Invalid input. Use spaces or commas.")

    # ==========================================
    # TAB 2: TRIO TRIGGERS (SNIPER & SNOWBALL)
    # ==========================================
    with tab2:
        st.subheader("🔥 The R500 Trio Triggers")
        st.write("""
        Paste the results of **last night's draw**. The system will scan the board and alert you 
        if either of your two mathematically explosive Trio strategies are primed to hit tonight.
        """)
        
        # Define the Elite Sets
        elite_40s = [40, 41, 42, 43, 44, 49]
        elite_20s = [20, 21, 22, 23, 24, 26]
        
        # Generate Combinations
        trios_40s = sorted(list(itertools.combinations(elite_40s, 3)))
        trios_20s = sorted(list(itertools.combinations(elite_20s, 3)))
        
        latest_draw_input = st.text_input("Enter Last Night's Draw (7 numbers):", "14 22 29 34 38 46 17", key="latest_draw_input")

        if st.button("Scan for Triggers", key="btn_scan"):
            try:
                latest_set = set([int(x.strip()) for x in latest_draw_input.replace(',', ' ').split()])
                
                if len(latest_set) == 7:
                    st.divider()
                    st.write("### 🚦 Dashboard Analysis")
                    
                    # Analyze Hits
                    hits_40s = len(latest_set.intersection(set(elite_40s)))
                    hits_20s = len(latest_set.intersection(set(elite_20s)))
                    
                    # Status Trackers
                    play_40s = (hits_40s == 1)
                    play_20s = (hits_20s >= 2)
                    
                    # --- 1. EVALUATE HIGH 40s (SNIPER TRAP) ---
                    if play_40s:
                        st.success(f"🟢 **HIGH 40s SNIPER TRAP ACTIVATED!**")
                        st.write(f"*(Exactly 1 Elite 40s number dropped yesterday. The Warning Shot was fired. They are primed to cluster tonight!)*")
                    else:
                        st.error(f"🔴 **HIGH 40s INACTIVE** ({hits_40s} hits yesterday. Requires exactly 1.)")
                        
                    # --- 2. EVALUATE 20s (SNOWBALL EFFECT) ---
                    if play_20s:
                        st.success(f"🟢 **20s SNOWBALL EFFECT ACTIVATED!**")
                        st.write(f"*(Multiple Elite 20s dropped yesterday ({hits_20s} hits). They are running violently hot. Ride the momentum!)*")
                    else:
                        st.error(f"🔴 **20s INACTIVE** ({hits_20s} hits yesterday. Requires 2 or more.)")

                    # --- THE "WALK AWAY" CHECK ---
                    if not play_40s and not play_20s:
                        st.warning("🛑 **NO TRIGGERS MET.** Do not play the Trios today. Keep your R20 in your pocket.")

                    # --- DISPLAY PLAYABLE TICKETS ---
                    if play_40s or play_20s:
                        st.divider()
                        st.subheader("🎟️ Your Action Plan for Tonight")
                        
                        if play_40s:
                            st.write("### Play these 20 High-40s Trios (Cost: R20 | Win: R500+)")
                            c1, c2, c3, c4 = st.columns(4)
                            for i, t in enumerate(trios_40s): 
                                [c1, c2, c3, c4][i % 4].write(f"**{t[0]} - {t[1]} - {t[2]}**")
                                
                        if play_20s:
                            st.write("### Play these 20 Elite-20s Trios (Cost: R20 | Win: R500+)")
                            c1, c2, c3, c4 = st.columns(4)
                            for i, t in enumerate(trios_20s): 
                                [c1, c2, c3, c4][i % 4].write(f"**{t[0]} - {t[1]} - {t[2]}**")

                else:
                    st.warning("Please enter exactly 7 numbers.")

            except ValueError:
                st.error("Invalid input. Please use spaces or commas to separate your numbers.")

if __name__ == "__main__":
    run_strategy_hub_app()
