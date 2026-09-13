"""
Analysis for the Chicago Vacant & Abandoned Buildings project.

Reads from the SQLite database built by etl.py, answers the policy questions
in the README with pandas + SQL, and saves charts to visuals/.
"""
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "chicago_housing.db"
VISUALS_DIR = ROOT / "visuals"

sns.set_theme(style="whitegrid")


def get_connection() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found. Run `python src/etl.py --source sample` first."
        )
    return sqlite3.connect(DB_PATH)


def reports_by_community_area(conn) -> pd.DataFrame:
    query = """
        SELECT
            ca.area_name,
            COUNT(*) AS report_count,
            SUM(COALESCE(vb.is_dangerous, 0)) AS dangerous_count,
            ROUND(100.0 * SUM(COALESCE(vb.is_dangerous, 0)) / COUNT(*), 1) AS pct_dangerous
        FROM vacant_buildings vb
        LEFT JOIN community_areas ca ON vb.community_area = ca.area_number
        WHERE vb.community_area IS NOT NULL
        GROUP BY ca.area_name
        ORDER BY report_count DESC
    """
    return pd.read_sql(query, conn)


def reports_over_time(conn) -> pd.DataFrame:
    query = """
        SELECT
            strftime('%Y-%m', date_received) AS month,
            COUNT(*) AS report_count
        FROM vacant_buildings
        GROUP BY month
        ORDER BY month
    """
    return pd.read_sql(query, conn)


def urgency_breakdown(conn) -> pd.DataFrame:
    query = """
        SELECT
            open_or_boarded,
            COUNT(*) AS n,
            SUM(COALESCE(is_dangerous, 0)) AS dangerous,
            SUM(COALESCE(vacant_due_to_fire, 0)) AS fire_related,
            SUM(COALESCE(people_using_property, 0)) AS occupied_by_others
        FROM vacant_buildings
        WHERE open_or_boarded IS NOT NULL AND open_or_boarded != ''
        GROUP BY open_or_boarded
        ORDER BY n DESC
    """
    return pd.read_sql(query, conn)


def plot_top_community_areas(df: pd.DataFrame):
    top15 = df.head(15)
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=top15, y="area_name", x="report_count", color="#4C72B0", ax=ax)
    ax.set_title("Vacant/Abandoned Building Reports by Community Area (Top 15)")
    ax.set_xlabel("Number of 311 Reports")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(VISUALS_DIR / "top_community_areas.png", dpi=150)
    plt.close(fig)


def plot_pct_dangerous(df: pd.DataFrame):
    top15 = df.head(15).sort_values("pct_dangerous", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 6))
    sns.barplot(data=top15, y="area_name", x="pct_dangerous", color="#C44E52", ax=ax)
    ax.set_title("Share of Reported Buildings Flagged Dangerous/Hazardous\n(Top 15 Community Areas by Report Volume)")
    ax.set_xlabel("% Flagged Dangerous")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(VISUALS_DIR / "pct_dangerous_by_area.png", dpi=150)
    plt.close(fig)


def plot_reports_over_time(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df["month"], df["report_count"], marker="o", markersize=3, color="#4C72B0")
    ax.set_title("Vacant/Abandoned Building Reports Over Time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Number of Reports")
    ax.tick_params(axis="x", rotation=90)
    # thin out x tick labels so they stay readable
    for i, label in enumerate(ax.xaxis.get_ticklabels()):
        if i % 3 != 0:
            label.set_visible(False)
    fig.tight_layout()
    fig.savefig(VISUALS_DIR / "reports_over_time.png", dpi=150)
    plt.close(fig)


def plot_urgency_breakdown(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.barplot(data=df, x="open_or_boarded", y="n", color="#55A868", ax=ax)
    ax.set_title("Reports by Building Status (Open vs Boarded)")
    ax.set_xlabel("")
    ax.set_ylabel("Number of Reports")
    fig.tight_layout()
    fig.savefig(VISUALS_DIR / "urgency_breakdown.png", dpi=150)
    plt.close(fig)


def main():
    VISUALS_DIR.mkdir(parents=True, exist_ok=True)
    conn = get_connection()

    print("\n=== Reports by community area (top 10) ===")
    by_area = reports_by_community_area(conn)
    print(by_area.head(10).to_string(index=False))
    plot_top_community_areas(by_area)
    plot_pct_dangerous(by_area)

    print("\n=== Reports over time ===")
    over_time = reports_over_time(conn)
    print(over_time.to_string(index=False))
    plot_reports_over_time(over_time)

    print("\n=== Urgency breakdown ===")
    urgency = urgency_breakdown(conn)
    print(urgency.to_string(index=False))
    plot_urgency_breakdown(urgency)

    pct_null_dangerous = 100 * conn.execute(
        "SELECT AVG(CASE WHEN is_dangerous IS NULL THEN 1.0 ELSE 0 END) FROM vacant_buildings"
    ).fetchone()[0]
    print(
        f"\nData quality note: {pct_null_dangerous:.0f}% of reports have no "
        "'dangerous/hazardous' flag recorded (311 operators rarely fill this field in) "
        "-- pct_dangerous above is a floor, not a true rate."
    )

    conn.close()
    print(f"\nCharts saved to {VISUALS_DIR}/")


if __name__ == "__main__":
    main()
