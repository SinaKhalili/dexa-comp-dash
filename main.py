import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

ESSENTIAL_BF = 2.0

st.set_page_config(page_title="BF% Competition Calculator", layout="wide")
st.title("Body Fat % Competition Calculator")
st.caption("Predict outcomes for a DEXA scan body fat percentage competition")

with st.sidebar:
    st.header("Settings")
    num_people = st.number_input(
        "Number of competitors", min_value=2, max_value=10, value=6
    )
    use_adjusted = st.toggle(
        "Use adjusted scoring (essential BF%)",
        value=True,
        help=(
            "Adjusted scoring measures what fraction of *losable* fat you lost. "
            "Losable fat = current BF% − essential BF%. "
            "This levels the playing field for people starting at different BF%."
        ),
    )

st.header("Competitors")

DEFAULTS = [
    {"name": "Sina", "weight": 187.0, "start_bf": 26.9, "end_bf": 20.1},
    {"name": "Malvin", "weight": 204.0, "start_bf": 17.5, "end_bf": 12.0},
    {"name": "Mason", "weight": 177.0, "start_bf": 21.5, "end_bf": 15.0},
    {"name": "Ricardo", "weight": 175.0, "start_bf": 18.1, "end_bf": 13.0},
    {"name": "Mateo", "weight": 165.0, "start_bf": 17.8, "end_bf": 13.5},
    {"name": "Dayal", "weight": 180.0, "start_bf": 29.8, "end_bf": 20.1},
]

competitors = []
cols_per_row = min(num_people, 3)
rows = (num_people + cols_per_row - 1) // cols_per_row

idx = 0
for row in range(rows):
    cols = st.columns(cols_per_row)
    for col in cols:
        if idx >= num_people:
            break
        d = DEFAULTS[idx] if idx < len(DEFAULTS) else {}
        with col:
            with st.container(border=True):
                name = st.text_input(
                    "Name", value=d.get("name", f"Person {idx + 1}"), key=f"name_{idx}"
                )
                weight = st.number_input(
                    "Starting weight (lbs)",
                    min_value=80.0,
                    max_value=500.0,
                    value=d.get("weight", 180.0),
                    step=1.0,
                    key=f"weight_{idx}",
                )
                start_bf = st.number_input(
                    "Starting BF%",
                    min_value=3.0,
                    max_value=60.0,
                    value=d.get("start_bf", 20.0),
                    step=0.1,
                    format="%.1f",
                    key=f"start_bf_{idx}",
                )

                essential = ESSENTIAL_BF
                min_end = essential + 0.1

                end_bf = st.slider(
                    "Predicted ending BF%",
                    min_value=min_end,
                    max_value=start_bf,
                    value=round(max(d.get("end_bf", start_bf - 3.0), min_end), 1),
                    step=0.1,
                    format="%.1f",
                    key=f"end_bf_{idx}",
                )

                competitors.append(
                    {
                        "name": name,
                        "weight_lbs": weight,
                        "start_bf": start_bf,
                        "end_bf": end_bf,
                        "essential_bf": essential,
                    }
                )
        idx += 1

st.divider()
st.header("Predicted Results")

rows = []
for c in competitors:
    abs_drop = c["start_bf"] - c["end_bf"]
    pct_loss = (abs_drop / c["start_bf"]) * 100  # % reduction of BF%
    losable = c["start_bf"] - c["essential_bf"]
    adjusted = (abs_drop / losable) * 100 if losable > 0 else 0.0

    fat_mass_start = c["weight_lbs"] * c["start_bf"] / 100
    fat_mass_end = (
        c["weight_lbs"] * c["end_bf"] / 100
    )  # approximation (LBM stays ~constant)
    fat_lbs_lost = fat_mass_start - fat_mass_end

    rows.append(
        {
            "Name": c["name"],
            "Start BF%": c["start_bf"],
            "End BF%": c["end_bf"],
            "BF% Drop": round(abs_drop, 1),
            "% Loss (raw)": round(pct_loss, 1),
            "Essential BF%": c["essential_bf"],
            "% Losable Fat Lost": round(adjusted, 1),
            "Est. Fat Lost (lbs)": round(fat_lbs_lost, 1),
        }
    )

df = pd.DataFrame(rows)

score_col = "% Losable Fat Lost" if use_adjusted else "% Loss (raw)"
df = df.sort_values(score_col, ascending=False).reset_index(drop=True)
df.index = df.index + 1
df.index.name = "Rank"

st.dataframe(df, use_container_width=True)

winner = df.iloc[0]
st.success(
    f"**Predicted winner: {winner['Name']}** with a {score_col.lower()} of **{winner[score_col]}%**"
)

st.subheader("Comparison")

chart_df = df[["Name", "Start BF%", "End BF%", "Essential BF%"]].set_index("Name")
st.bar_chart(chart_df)

st.subheader("Winner across essential BF% values")
st.caption(
    "How the adjusted score for each competitor changes as you vary the essential body fat threshold. "
    "Where lines cross, the winner changes."
)

essential_range = np.arange(0.0, 4.01, 0.5)

sensitivity_rows = []
for ebf in essential_range:
    for c in competitors:
        if c["start_bf"] <= ebf:
            continue
        drop = c["start_bf"] - c["end_bf"]
        losable = c["start_bf"] - ebf
        score = (drop / losable) * 100
        sensitivity_rows.append(
            {
                "Essential BF%": ebf,
                "Name": c["name"],
                "Adjusted Score (%)": round(score, 2),
            }
        )

if sensitivity_rows:
    sens_df = pd.DataFrame(sensitivity_rows)
    fig = px.line(
        sens_df,
        x="Essential BF%",
        y="Adjusted Score (%)",
        color="Name",
    )
    comp_list = list(competitors)
    crossings = []
    for i in range(len(comp_list)):
        for j in range(i + 1, len(comp_list)):
            a, b = comp_list[i], comp_list[j]
            drop_a = a["start_bf"] - a["end_bf"]
            drop_b = b["start_bf"] - b["end_bf"]
            denom = drop_b - drop_a
            if abs(denom) < 1e-9:
                continue
            ebf_cross = (drop_b * a["start_bf"] - drop_a * b["start_bf"]) / denom
            if (
                0 <= ebf_cross <= 4
                and a["start_bf"] > ebf_cross
                and b["start_bf"] > ebf_cross
            ):
                score_at = (drop_a / (a["start_bf"] - ebf_cross)) * 100
                crossings.append((ebf_cross, score_at, a["name"], b["name"]))
    for ebf_x, score_y, name_a, name_b in crossings:
        fig.add_vline(x=ebf_x, line_dash="dash", line_color="gray", opacity=0.8)
        fig.add_annotation(
            x=ebf_x,
            y=score_y,
            text=f"{name_a} ↔ {name_b}",
            showarrow=True,
            arrowhead=1,
            ax=0,
            ay=-40,
            font=dict(size=10),
        )
    st.plotly_chart(fig, use_container_width=True)

with st.expander("How scoring works"):
    st.markdown(
        """
**Raw % loss** = `(start − end) / start × 100`

Going from 20% → 15% is a **25%** reduction in your body fat percentage.

---

**Adjusted scoring (essential BF%)** = `(start − end) / (start − essential) × 100`

This measures what fraction of your *losable* fat you actually lost.
Essential body fat is the minimum needed for health (~3%).

**Why it matters:** Someone at 30% BF can lose 5 points much more easily than someone
at 15%. Adjusted scoring accounts for this by measuring progress relative to each
person's realistic floor.

**Example:**
- Person A: 30% → 25%. Raw = 16.7%. Adjusted = (5 / 27) = 18.5%
- Person B: 18% → 14%. Raw = 22.2%. Adjusted = (4 / 15) = 26.7%
"""
    )
