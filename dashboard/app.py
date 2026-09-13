"""
Interactive dashboard for the Chicago Vacant & Abandoned Buildings project.

Run with: streamlit run dashboard/app.py
"""
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "chicago_housing.db"

st.set_page_config(page_title="Chicago Vacant Buildings", layout="wide")
st.title("Vacant & Abandoned Buildings in Chicago")
st.caption(
    "311 reports of vacant/abandoned buildings, City of Chicago Data Portal "
    "(dataset 7nii-7srd). Built for the Harris Applied Data Fellowship application."
)


@st.cache_data
def load_data():
    if not DB_PATH.exists():
        st.error(
            "Database not found. Run `python src/etl.py --source sample` from the "
            "project root first."
        )
        st.stop()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql(
        """
        SELECT vb.*, ca.area_name
        FROM vacant_buildings vb
        LEFT JOIN community_areas ca ON vb.community_area = ca.area_number
        """,
        conn,
        parse_dates=["date_received"],
    )
    conn.close()
    return df


df = load_data()

# --- Sidebar filters ---
st.sidebar.header("Filters")

areas = sorted(df["area_name"].dropna().unique())
selected_areas = st.sidebar.multiselect("Community area(s)", areas, default=[])

min_date, max_date = df["date_received"].min(), df["date_received"].max()
date_range = st.sidebar.date_input(
    "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
)

dangerous_only = st.sidebar.checkbox("Dangerous/hazardous only", value=False)

filtered = df.copy()
if selected_areas:
    filtered = filtered[filtered["area_name"].isin(selected_areas)]
if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    filtered = filtered[(filtered["date_received"] >= start) & (filtered["date_received"] <= end)]
if dangerous_only:
    filtered = filtered[filtered["is_dangerous"] == 1]

# --- Top-line metrics ---
col1, col2, col3 = st.columns(3)
col1.metric("Total reports (filtered)", f"{len(filtered):,}")
col2.metric(
    "% flagged dangerous",
    f"{100 * filtered['is_dangerous'].mean():.1f}%" if len(filtered) else "n/a",
)
col3.metric(
    "% occupied by non-residents",
    f"{100 * filtered['people_using_property'].mean():.1f}%" if len(filtered) else "n/a",
)

# --- Reports by community area ---
st.subheader("Reports by Community Area")
by_area = (
    filtered.groupby("area_name")
    .size()
    .sort_values(ascending=False)
    .head(20)
    .rename("report_count")
)
st.bar_chart(by_area)

# --- Reports over time ---
st.subheader("Reports Over Time")
by_month = (
    filtered.set_index("date_received")
    .resample("MS")
    .size()
    .rename("report_count")
)
st.line_chart(by_month)

# --- Map ---
st.subheader("Report Locations")
map_df = filtered.dropna(subset=["latitude", "longitude"])[["latitude", "longitude"]]
if len(map_df):
    st.map(map_df, size=15)
else:
    st.info("No geolocated reports match the current filters.")

# --- Raw data ---
with st.expander("View filtered raw data"):
    st.dataframe(filtered.drop(columns=["latitude", "longitude"], errors="ignore"))
