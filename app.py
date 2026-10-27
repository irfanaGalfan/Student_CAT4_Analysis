
import re
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------
# Page configuration
# ---------------------------
st.set_page_config(
    page_title="Student Cognitive Insights",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Student Cognitive Profile Dashboard")
st.caption(
    "CAT4 reasoning analysis | Year-group comparisons | Data quality"
)

# ---------------------------
# Load data
# ---------------------------
uploaded_file = st.sidebar.file_uploader(
    "Upload CAT4 CSV (optional)",
    type=["csv"]
)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
else:
    file_path = Path(__file__).parent / "CAT4_Dashboard_Data.csv"

    if not file_path.exists():
        st.error(
            "CSV not found. Put CAT4_Dashboard_Data.csv "
            "in the same folder as app.py, or upload it in the sidebar."
        )
        st.stop()

    df = pd.read_csv(file_path)

reasoning_cols = [
    "CAT4 V SAS",
    "CAT4 Q SAS",
    "CAT4 NV SAS",
    "CAT4 Spatial SAS"
]

cat4_cols = reasoning_cols + ["CAT4 Overall Mean"]

required_cols = ["Student ID", "Class", "Division"] + cat4_cols
missing_columns = [c for c in required_cols if c not in df.columns]

if missing_columns:
    st.error(f"Required columns are missing: {missing_columns}")
    st.stop()

# Ensure scores are numeric
for col in cat4_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ---------------------------
# Sidebar filters
# ---------------------------
st.sidebar.header("Dashboard Filters")

classes = sorted(
    df["Class"].dropna().unique().tolist(),
    key=lambda x: (
        int(re.search(r"Year\s+(\d+)", str(x)).group(1))
        if re.search(r"Year\s+(\d+)", str(x))
        else 999,
        str(x)
    )
)

selected_classes = st.sidebar.multiselect(
    "Select year groups",
    options=classes,
    default=classes
)

divisions = sorted(df["Division"].dropna().unique().tolist())

selected_divisions = st.sidebar.multiselect(
    "Select divisions",
    options=divisions,
    default=divisions
)

filtered = df[
    df["Class"].isin(selected_classes)
    & df["Division"].isin(selected_divisions)
].copy()

if filtered.empty:
    st.warning("No records match these filters. Select another group.")
    st.stop()

# ---------------------------
# Data quality
# ---------------------------
complete_mask = filtered[cat4_cols].notna().all(axis=1)
complete_records = int(complete_mask.sum())
missing_any = int((~complete_mask).sum())
missing_all = int(filtered[cat4_cols].isna().all(axis=1).sum())
total_records = len(filtered)

overall_mean = filtered.loc[
    complete_mask, "CAT4 Overall Mean"
].mean()

# ---------------------------
# KPI cards
# ---------------------------
st.subheader("Executive Overview")

c1, c2, c3, c4 = st.columns(4)

c1.metric("Student records", f"{total_records:,}")
c2.metric("Complete CAT4 records", f"{complete_records:,}")
c3.metric("Records with missing CAT4", f"{missing_any:,}")
c4.metric(
    "Average CAT4 Overall Mean",
    f"{overall_mean:.1f}" if pd.notna(overall_mean) else "N/A"
)

if total_records:
    st.caption(
        f"{missing_any / total_records * 100:.2f}% of filtered records "
        "have at least one missing CAT4 score."
    )

st.divider()
# ---------------------------
# Data completeness pie chart
# ---------------------------
st.subheader("📌 Data Completeness")

complete_count = int(complete_mask.sum())
incomplete_count = int((~complete_mask).sum())

completeness_df = pd.DataFrame({
    "Data status": ["Complete CAT4 scores", "Missing one or more CAT4 scores"],
    "Number of records": [complete_count, incomplete_count]
})

fig_complete = px.pie(
    completeness_df,
    names="Data status",
    values="Number of records",
    hole=0.45,
    title="CAT4 Data Completeness",
    color_discrete_sequence=["#2E86AB", "#F4A261"]
)

fig_complete.update_traces(
    textinfo="label+percent",
    hovertemplate="%{label}<br>Records: %{value}<br>Share: %{percent}<extra></extra>"
)

st.plotly_chart(fig_complete, use_container_width=True)

# ---------------------------
# Domain averages
# ---------------------------
st.subheader("Cognitive Profile by Reasoning Domain")

st.write(
    "Compare the average Standard Age Scores (SAS) across the four "
    "reasoning domains. This chart uses records with complete CAT4 data."
)

complete_df = filtered.loc[complete_mask].copy()

domain_labels = {
    "CAT4 V SAS": "Verbal",
    "CAT4 Q SAS": "Quantitative",
    "CAT4 NV SAS": "Non-verbal",
    "CAT4 Spatial SAS": "Spatial"
}

if not complete_df.empty:
    domain_means = (
        complete_df[reasoning_cols]
        .mean()
        .rename(index=domain_labels)
        .rename_axis("Reasoning domain")
        .reset_index(name="Average SAS")
    )

    fig_domains = px.bar(
        domain_means,
        x="Reasoning domain",
        y="Average SAS",
        color="Reasoning domain",
        text_auto=".1f",
        title="Average CAT4 SAS by Domain"
    )

    fig_domains.add_hline(
        y=100,
        line_dash="dash",
        annotation_text="SAS reference average: 100"
    )

    fig_domains.update_layout(
        showlegend=False,
        yaxis_title="Average Standard Age Score",
        xaxis_title=""
    )

    st.plotly_chart(fig_domains, use_container_width=True)

    highest = domain_means.loc[
        domain_means["Average SAS"].idxmax()
    ]
    lowest = domain_means.loc[
        domain_means["Average SAS"].idxmin()
    ]

    st.info(
        f"Descriptive finding: {highest['Reasoning domain']} has the "
        f"highest average ({highest['Average SAS']:.1f}), while "
        f"{lowest['Reasoning domain']} has the lowest "
        f"({lowest['Average SAS']:.1f}). Investigate distributions and "
        "academic outcomes before drawing conclusions."
    )
else:
    st.warning("There are no complete CAT4 records for these filters.")

st.divider()

# ---------------------------
# Student distribution by year group
# ---------------------------
st.subheader("🎓 Student Records by Year Group")

year_counts = (
    filtered.groupby("Class")
    .size()
    .reset_index(name="Number of records")
)

fig_years_pie = px.pie(
    year_counts,
    names="Class",
    values="Number of records",
    hole=0.35,
    title="Distribution of Records Across Year Groups",
    color_discrete_sequence=px.colors.qualitative.Set2
)

fig_years_pie.update_traces(
    textinfo="percent",
    hovertemplate="%{label}<br>Records: %{value}<br>Share: %{percent}<extra></extra>"
)

st.plotly_chart(fig_years_pie, use_container_width=True)

# ---------------------------
# Year-group comparison
# ---------------------------
st.subheader("Compare Year Groups")

if not complete_df.empty:
    class_means = (
        complete_df.groupby("Class")[reasoning_cols]
        .mean()
        .reset_index()
        .melt(
            id_vars="Class",
            var_name="Domain",
            value_name="Average SAS"
        )
    )

    class_means["Domain"] = class_means["Domain"].map(domain_labels)

    class_order = [
        c for c in classes if c in complete_df["Class"].unique()
    ]

    fig_years = px.bar(
        class_means,
        x="Class",
        y="Average SAS",
        color="Domain",
        barmode="group",
        category_orders={"Class": class_order},
        title="Average Reasoning Scores by Year Group"
    )

    fig_years.add_hline(
        y=100,
        line_dash="dash",
        annotation_text="SAS reference average: 100"
    )

    fig_years.update_layout(
        xaxis_title="Year group",
        yaxis_title="Average SAS",
        legend_title="Reasoning domain"
    )

    st.plotly_chart(fig_years, use_container_width=True)

st.divider()

# ---------------------------
# Score distribution
# ---------------------------
st.subheader("Explore Score Distributions")

chosen_domain = st.selectbox(
    "Choose a reasoning domain",
    options=reasoning_cols,
    format_func=lambda x: domain_labels[x]
)

distribution_df = complete_df[["Class", chosen_domain]].dropna()

if not distribution_df.empty:
    fig_box = px.box(
        distribution_df,
        x="Class",
        y=chosen_domain,
        points="outliers",
        category_orders={"Class": classes},
        title=f"{domain_labels[chosen_domain]} SAS Distribution by Year Group"
    )

    fig_box.add_hline(
        y=100,
        line_dash="dash",
        annotation_text="SAS reference average: 100"
    )

    fig_box.update_layout(
        xaxis_title="Year group",
        yaxis_title="Standard Age Score"
    )

    st.plotly_chart(fig_box, use_container_width=True)

    st.caption(
        "Box plots show the median, spread and potential outliers. "
        "Outliers are prompts for investigation, not automatic errors."
    )

st.divider()

# ---------------------------
# Data-quality report
# ---------------------------
st.subheader("Data Quality")

quality_df = pd.DataFrame({
    "CAT4 field": cat4_cols,
    "Missing values": [
        int(filtered[col].isna().sum()) for col in cat4_cols
    ],
    "Missing percentage": [
        round(filtered[col].isna().mean() * 100, 2)
        for col in cat4_cols
    ]
})

st.dataframe(quality_df, hide_index=True, use_container_width=True)

st.write(
    f"Records missing all five CAT4 fields: **{missing_all}** "
    f"out of **{total_records}** filtered records."
)

with st.expander("View year-group summary"):
    if not complete_df.empty:
        summary = (
            complete_df.groupby("Class")[reasoning_cols]
            .agg(["count", "mean", "std"])
            .round(2)
        )
        st.dataframe(summary, use_container_width=True)

st.caption(
    "Interpret CAT4 as cognitive reasoning information, not as a direct "
    "measure of academic attainment. Compare with appropriate academic "
    "assessments and school context before recommending interventions."
)


