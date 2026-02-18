import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="BF% Calculator", layout="wide")

path = os.path.join(os.path.dirname(__file__), "..", "style.css")
with open(path) as css:
    st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)
st.title("BF% Calculator")
st.caption("Calculate your ending body fat percentage from fat lost and muscle gained")

col1, col2 = st.columns(2)

with col1:
    weight = st.number_input(
        "Starting weight (lbs)", min_value=80.0, max_value=500.0, value=187.0, step=1.0
    )
    start_bf = st.number_input(
        "Starting BF%",
        min_value=1.0,
        max_value=60.0,
        value=26.9,
        step=0.1,
        format="%.1f",
    )

fat_mass_start = weight * start_bf / 100
lean_mass_start = weight - fat_mass_start

with col2:
    fat_lost = st.number_input(
        "Fat lost (lbs)", min_value=0.0, max_value=fat_mass_start, value=14.5, step=0.5
    )
    muscle_gained = st.number_input(
        "Muscle gained (lbs)", min_value=0.0, max_value=100.0, value=5.0, step=0.5
    )
    tdee = st.number_input(
        "Maintenance calories (TDEE)",
        min_value=1000,
        max_value=6000,
        value=2200,
        step=50,
    )

fat_mass_end = fat_mass_start - fat_lost
lean_mass_end = lean_mass_start + muscle_gained
end_weight = fat_mass_end + lean_mass_end
end_bf = fat_mass_end / end_weight * 100
bf_drop = start_bf - end_bf

st.divider()

c1, c2, c3 = st.columns(3)
c1.metric("Ending BF%", f"{end_bf:.1f}%", f"{bf_drop:.1f}pp drop")
c2.metric("Ending weight", f"{end_weight:.1f} lbs", f"{end_weight - weight:+.1f} lbs")
c3.metric(
    "Weight change",
    f"-{fat_lost:.1f}f / +{muscle_gained:.1f}m",
    f"{-fat_lost + muscle_gained:+.1f} lbs net",
)

CAL_PER_LB_FAT = 3500
CAL_PER_LB_MUSCLE = 2500  # approx surplus needed to build 1 lb muscle
WEEKS = 4 * 4  # 4 months ≈ 16 weeks
DAYS = WEEKS * 7

fat_per_week = fat_lost / WEEKS
muscle_per_week = muscle_gained / WEEKS

daily_fat_deficit = (fat_lost * CAL_PER_LB_FAT) / DAYS
daily_muscle_surplus = (muscle_gained * CAL_PER_LB_MUSCLE) / DAYS
daily_target = tdee - daily_fat_deficit + daily_muscle_surplus

st.divider()

st.subheader("Weekly targets (over 4 months)")
w1, w2 = st.columns(2)
w1.metric(
    "Fat loss per week",
    f"{fat_per_week:.2f} lbs/wk",
    f"{fat_per_week * CAL_PER_LB_FAT:.0f} cal deficit/wk",
)
w2.metric("Muscle gain per week", f"{muscle_per_week:.2f} lbs/wk")

st.subheader("Daily calories")
d1, d2, d3 = st.columns(3)
d1.metric("TDEE (maintenance)", f"{tdee:,} cal")
d2.metric(
    "Daily target",
    f"{daily_target:,.0f} cal",
    f"{daily_target - tdee:+,.0f} from maintenance",
)
d3.metric(
    "Net daily deficit",
    f"{daily_fat_deficit - daily_muscle_surplus:,.0f} cal",
    f"= {daily_fat_deficit:,.0f} fat loss − {daily_muscle_surplus:,.0f} muscle build",
)

st.divider()

st.subheader("Check-in calendar")
start_date = st.date_input("Competition start date", value=date.today())
checkin_interval = st.selectbox(
    "Check-in every", ["1 week", "2 weeks", "4 weeks"], index=1
)
interval_weeks = int(checkin_interval.split()[0])

checkins = []
for wk in range(0, WEEKS + 1, interval_weeks):
    frac = wk / WEEKS
    fat_at = fat_mass_start - fat_lost * frac
    lean_at = lean_mass_start + muscle_gained * frac
    wt_at = fat_at + lean_at
    bf_at = fat_at / wt_at * 100
    checkins.append(
        {
            "Date": start_date + timedelta(weeks=wk),
            "Week": wk,
            "Weight (lbs)": round(wt_at, 1),
            "Fat mass (lbs)": round(fat_at, 1),
            "Lean mass (lbs)": round(lean_at, 1),
            "BF%": round(bf_at, 1),
        }
    )

checkin_df = pd.DataFrame(checkins)
st.dataframe(checkin_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("BF% landscape: fat loss vs muscle gain")
st.caption("Contour lines show ending BF%. The marker shows your current inputs.")

fat_range = np.linspace(0, min(fat_mass_start, 40), 80)
muscle_range = np.linspace(0, 20, 60)
fat_grid, muscle_grid = np.meshgrid(fat_range, muscle_range)

bf_grid = (fat_mass_start - fat_grid) / (weight - fat_grid + muscle_grid) * 100

fig = go.Figure()
fig.add_trace(
    go.Contour(
        x=fat_range,
        y=muscle_range,
        z=bf_grid,
        colorscale="Tealgrn_r",
        contours=dict(showlabels=True, labelfont=dict(size=11, color="white"), size=1),
        colorbar=dict(title="Ending BF%"),
        hovertemplate="Fat lost: %{x:.1f} lbs<br>Muscle gained: %{y:.1f} lbs<br>BF%%: %{z:.1f}%<extra></extra>",
    )
)
fig.add_trace(
    go.Scatter(
        x=[0, fat_lost],
        y=[0, muscle_gained],
        mode="lines+markers+text",
        line=dict(color="white", width=2, dash="dot"),
        marker=dict(size=10, color="white", line=dict(width=2, color="#111")),
        text=[f"{start_bf:.1f}%", f"{end_bf:.1f}%"],
        textposition=["bottom right", "top right"],
        textfont=dict(color="white", size=13),
        showlegend=False,
        hoverinfo="skip",
    )
)
fig.update_layout(
    xaxis_title="Fat lost (lbs)",
    yaxis_title="Muscle gained (lbs)",
    height=500,
    margin=dict(t=20, b=40),
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

st.subheader("Breakdown")
col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Before**")
    st.markdown(f"- Weight: **{weight:.1f}** lbs")
    st.markdown(f"- Fat mass: **{fat_mass_start:.1f}** lbs")
    st.markdown(f"- Lean mass: **{lean_mass_start:.1f}** lbs")
    st.markdown(f"- BF%: **{start_bf:.1f}%**")
with col_b:
    st.markdown("**After**")
    st.markdown(f"- Weight: **{end_weight:.1f}** lbs")
    st.markdown(f"- Fat mass: **{fat_mass_end:.1f}** lbs")
    st.markdown(f"- Lean mass: **{lean_mass_end:.1f}** lbs")
    st.markdown(f"- BF%: **{end_bf:.1f}%**")
