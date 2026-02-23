import streamlit as st
import itertools

def run_strategy_hub_app():
    st.set_page_config(page_title="Sebman Strategy Hub", page_icon="🎯", layout="centered")
    
    st.title("🎯 Sebman Strategy Hub")
    
    # Create two tabs for the two different strategies
    tab1, tab2 = st.tabs(["⚓ Dynamic Anchor (Daily)", "🔫 Sniper Sets (Triggers)"])
    
    # ==========================================
    # TAB 1: DYNAMIC ANCHOR STRATEGY
    # ==========================================
    with tab1:
        st.subheader("Strategy: 42-Density Filtered by Anchor Gaps")
        st.write("""
        Use this **every day**. It anchors numbers from your **n-1** and **n-3** draws 
        based on your target gap to catch clustered numbers.
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            draw_n1 = st.text_input("Draw n-1 (Required)", "4 10 14 20 42 49 12", key="n1_input")
        with col2:
            draw_n3 = st.text_input("Draw n-3 (Required)", "5 7 14 19 30 40 15", key="n3_input")
            
        st.divider()
        max_gap = st.slider("Maximum Gap Allowed (Your Sweet Spot is 10):", min_value=1, max_value=25, value=10, step=1)
        current_draw_1 = st.text_input("Current Draw (Optional - To check results)", "", key="cur1_input")
        
        if st.button("Generate Anchored Duos", key="btn_anchor"):
            try:
                set1 = set([int(x.strip()) for x in draw_n1.replace(',', ' ').split()])
                set2 = set([int(x.strip()) for x in draw_n3.replace(',', ' ').split()])
                
                if len(set1) != 7 or len(set2) != 7:
                    st.warning("Check your input! Both draws must have exactly 7 unique numbers.")
                else:
                    # Generate base combinations
                    pairs_n1 = set(itertools.combinations(sorted(list(set1)), 2))
                    pairs_n3 = set(itertools.combinations(sorted(list(set2)), 2))
                    base_pairs = pairs_n1.union(pairs_n3)
                    
                    # Apply Gap Filter
                    filtered_pairs = sorted([p for p in base_pairs if 1 <= abs(p[0] - p[1]) <= max_gap])
                    
                    stake = len(filtered_pairs)
                    profit_on_win = 50 - stake
                    roi = (profit_on_win / stake) * 100 if stake > 0 else 0
                    
                    # Display Dashboard
                    st.success("✅ Pairs Anchored and Compressed!")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Base Pairs (Density)", len(base_pairs))
                    c2.metric(f"Discarded (> {max_gap} Gap)", len(base_pairs) - stake)
                    c3.metric("Final Pairs to Play", stake)
                    
                    if stake > 0:
                        st.info(f"**Financial Outlook:** Stake **R{stake}**. Profit on 1 win: **R{profit_on_win}** (ROI: **{roi:.1f}%**).")
                    else:
                        st.error("No valid intervals today! Keep your money in your pocket.")

                    # Result Checker
                    if current_draw_1.strip() and stake > 0:
                        cur_set = set([int(x.strip()) for x in current_draw_1.replace(',', ' ').split()])
                        if len(cur_set) == 7:
                            winning_pairs = [p for p in filtered_pairs if p[0] in cur_set and p[1] in cur_set]
                            st.divider()
                            st.subheader("🏆 Draw Results")
                            if winning_pairs:
                                won = len(winning_pairs) * 50
                                st.balloons()
                                st.success(f"🎉 WINNER! {len(winning_pairs)} pair(s) hit! Revenue: R{won} | Net Profit: R{won - stake}")
                                for wp in winning_pairs:
                                    st.write(f"✅ **{wp[0]} & {wp[1]}** *(Gap: {abs(wp[0]-wp[1])})*")
                            else:
                                st.error("❌ No winning pairs. The strategy absorbed the loss.")
                    
                    # Display Anchored Pairs
                    if stake > 0:
                        st.divider()
                        st.subheader("🔗 Your Playable Duos (Grouped by Anchor)")
                        anchors = sorted(list(set([p[0] for p in filtered_pairs])))
                        for anchor in anchors:
                            anchor_pairs = [p for p in filtered_pairs if p[0] == anchor]
                            pair_strings = [f"**{p[0]} & {p[1]}** *(Gap {abs(p[0]-p[1])})*" for p in anchor_pairs]
                            st.markdown(f"### Anchored to {anchor}")
                            st.write(" • " + " | ".join(pair_strings))
                            st.write("---")
            except ValueError:
                st.error("Invalid input. Use spaces or commas.")

    # ==========================================
    # TAB 2: SNIPER SETS (THE LOW & HIGH TRAPS)
    # ==========================================
    with tab2:
        st.subheader("🔫 The Sniper Traps")
        st.write("""
        **These are mathematically fixed sets.** Enter the previous draw to check if either strategy 
        is "Triggered" for today. Enter the current draw to check if your tickets won.
        """)
        
        # Define the sets
        set_low = [1, 2, 3, 5, 7, 9, 10, 11, 12]
        set_high = [41, 42, 43, 44, 45, 46, 47, 48, 49]
        
        pairs_low = sorted(list(itertools.combinations(set_low, 2)))
        pairs_high = sorted(list(itertools.combinations(set_high, 2)))
        
        col_prev, col_curr = st.columns(2)
        with col_prev:
            prev_draw_input = st.text_input("Previous Draw (To check Triggers)", "14 22 29 34 38 46 17", key="prev2_input")
        with col_curr:
            curr_draw_input = st.text_input("Tonight's Draw (To check Wins)", "", key="cur2_input")

        if st.button("Check Triggers & Results", key="btn_sniper"):
            try:
                prev_set = set([int(x.strip()) for x in prev_draw_input.replace(',', ' ').split()]) if prev_draw_input.strip() else set()
                curr_set = set([int(x.strip()) for x in curr_draw_input.replace(',', ' ').split()]) if curr_draw_input.strip() else set()
                
                # --- CHECK TRIGGERS ---
                if len(prev_set) == 7:
                    st.divider()
                    st.write("### 🚦 Trigger Status for Today")
                    
                    # Low Trap Logic (0 hits)
                    low_hits_prev = len(prev_set.intersection(set(set_low)))
                    if low_hits_prev == 0:
                        st.success(f"✅ **LOW TRAP IS ACTIVE!** (0 low numbers hit yesterday. The Rubber Band effect is primed!)")
                    else:
                        st.error(f"❌ **LOW TRAP INACTIVE.** ({low_hits_prev} low numbers hit yesterday. Do not play this today.)")
                        
                    # High Trap Logic (Exactly 1 hit)
                    high_hits_prev = len(prev_set.intersection(set(set_high)))
                    if high_hits_prev == 1:
                        st.success(f"✅ **HIGH TRAP IS ACTIVE!** (Exactly 1 high number hit yesterday. The Warning Shot was fired!)")
                    else:
                        st.error(f"❌ **HIGH TRAP INACTIVE.** ({high_hits_prev} high numbers hit yesterday. Do not play this today.)")
                elif prev_draw_input.strip():
                    st.warning("Previous draw must have exactly 7 numbers.")

                # --- CHECK WINS ---
                if len(curr_set) == 7:
                    st.divider()
                    st.write("### 🏆 Tonight's Results")
                    
                    # Check Low Trap Wins
                    win_low = [p for p in pairs_low if p[0] in curr_set and p[1] in curr_set]
                    if win_low:
                        st.success(f"🔥 **LOW TRAP WON!** {len(win_low)} pairs hit. (Profit: R{(len(win_low)*50)-36})")
                        for wp in win_low: st.write(f"   ✅ {wp[0]} & {wp[1]}")
                    
                    # Check High Trap Wins
                    win_high = [p for p in pairs_high if p[0] in curr_set and p[1] in curr_set]
                    if win_high:
                        st.success(f"🔥 **HIGH TRAP WON!** {len(win_high)} pairs hit. (Profit: R{(len(win_high)*50)-36})")
                        for wp in win_high: st.write(f"   ✅ {wp[0]} & {wp[1]}")
                        
                    if not win_low and not win_high:
                        st.info("No Sniper Sets hit in tonight's draw.")

            except ValueError:
                st.error("Invalid input. Use spaces or commas.")
        
        # --- DISPLAY THE STATIC SETS ---
        st.divider()
        exp_low = st.expander(f"View the 36 LOW TRAP Pairs (Cost: R36) | {set_low}")
        with exp_low:
            c1, c2, c3, c4 = st.columns(4)
            for i, p in enumerate(pairs_low): c1.write(f"{p[0]} & {p[1]}") if i%4==0 else c2.write(f"{p[0]} & {p[1]}") if i%4==1 else c3.write(f"{p[0]} & {p[1]}") if i%4==2 else c4.write(f"{p[0]} & {p[1]}")

        exp_high = st.expander(f"View the 36 HIGH TRAP Pairs (Cost: R36) | {set_high}")
        with exp_high:
            c1, c2, c3, c4 = st.columns(4)
            for i, p in enumerate(pairs_high): c1.write(f"{p[0]} & {p[1]}") if i%4==0 else c2.write(f"{p[0]} & {p[1]}") if i%4==1 else c3.write(f"{p[0]} & {p[1]}") if i%4==2 else c4.write(f"{p[0]} & {p[1]}")

if __name__ == "__main__":
    run_strategy_hub_app()
