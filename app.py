import streamlit as st
import fpl_data
import xp_engine
import optimizer

st.set_page_config(page_title="FPL xP Optimizer", layout="wide")

st.title("🦉 FPL OPTIMIZER 🦉")
st.markdown("🦉 WRITTEN BY 6IXSIDE MIKE 🦉")

# Cache data loading so UI slider updates don't trigger API calls repeatedly
@st.cache_data
def load_and_prep_data():
    raw_data = fpl_data.fetch_data()
    return fpl_data.process_and_filter_data(raw_data)

# Fetch Base Data & Calculate Limits
df_filtered = load_and_prep_data()
dynamic_min_budget = fpl_data.get_min_budget(df_filtered)

# Sidebar Controls
st.sidebar.header("Optimization Constraints")
budget_input = st.sidebar.number_input(
    "Max Budget (£m)", 
    min_value=dynamic_min_budget, 
    max_value=105.0, 
    value=max(100.0, dynamic_min_budget), # Defaults to 100 or min feasible
    step=0.1,
    help=f"Minimum possible budget for a valid active 15-man squad is £{dynamic_min_budget:.1f}m"
)
budget = int(budget_input * 10) # Convert to API integer scale

risk_appetite = st.sidebar.slider(
    "Differential / Risk Strategy", 
    min_value=-1.0, max_value=1.0, value=0.0, step=0.1,
    help="-1.0 (Template/Safe) to 1.0 (Differential/Punts)"
)

if st.sidebar.button("Run Optimizer"):
    with st.spinner("Solving integer linear programming constraints..."):
        
        # 1. xP Engine
        df_xp = xp_engine.calculate_xp(df_filtered, risk_differential_weight=risk_appetite)
        
        # 2. Optimize
        optimal_squad, total_xp = optimizer.optimize_team(df_xp, budget=budget)
        
        # 3. Display Logic
        st.success(f"Projected Expected Points (xP): **{total_xp:.2f}**")
        
        starters = optimal_squad[optimal_squad['is_starter'] == 1]
        bench = optimal_squad[optimal_squad['is_starter'] == 0]
        
        st.subheader("Starting XI")
        
        # Pitch Visualization (Centered Grid Layout)
        positions = ['GK', 'DEF', 'MID', 'FWD']
        for pos in positions:
            players_in_pos = starters[starters['position'] == pos]
            count = len(players_in_pos)
            
            if count > 0:
                # Add dynamic side padding to keep player cards centered naturally
                padding = (5 - count) / 2
                
                if padding > 0:
                    col_ratios = [padding] + [1] * count + [padding]
                    all_cols = st.columns(col_ratios)
                    player_cols = all_cols[1:-1]
                else:
                    player_cols = st.columns(count)
                
                for idx, (_, player) in enumerate(players_in_pos.iterrows()):
                    role = " (C)" if player['is_captain'] else ""
                    with player_cols[idx]:
                        st.info(f"**{player['web_name']}**{role}\n\n{player['team_name']}\n\n£{player['now_cost']/10:.1f}m | xP: {player['custom_xP']:.2f}")

        st.divider()
        st.subheader("Bench")
        bench_cols = st.columns(4)
        for idx, (_, player) in enumerate(bench.iterrows()):
            with bench_cols[idx]:
                st.warning(f"**{player['web_name']}** ({player['position']})\n\n£{player['now_cost']/10:.1f}m | xP: {player['custom_xP']:.2f}")
                
        st.divider()
        st.subheader("Data Engine Breakdown")
        
        # UI/UX Enhancements: Renaming Columns for Table Output
        display_df = optimal_squad.rename(columns={
            'web_name': 'Player',
            'custom_xP': 'XP',
            'layer2_score': 'Stat 1',
            'layer3_score': 'Stat 2',
            'layer4_score': 'Stat 3',
            'layer5_score': 'Stat 4'
        })
        
        # Dropped 'now_cost' from display_cols
        display_cols = ['Player', 'position', 'team_name', 'XP', 'Stat 1', 'Stat 2', 'Stat 3', 'Stat 4']
        
        # Render Table with hidden index and custom RdYlGn (Red/Yellow/Green) Heatmap
        styled_df = display_df[display_cols].style.background_gradient(cmap='RdYlGn', subset=['XP'])
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
        
        # Color Guide / Legend
        st.markdown("""
        **XP Colour Code:**
        * 🟢 **Green** = High Expected Points
        * 🟡 **Yellow** = Medium Expected Points
        * 🔴 **Red** = Low Expected Points
        """)
