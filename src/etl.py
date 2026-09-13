"""
ETL for the Chicago Vacant & Abandoned Buildings project.

Data engineering piece of the pipeline: pulls source data (either the live
Socrata API or the bundled offline sample), cleans/casts it, and loads it
into a SQLite database defined by sql/schema.sql.

Usage:
    python src/etl.py --source sample   # uses data/raw/sample_vacant_abandoned_buildings.csv
    python src/etl.py --source live     # pulls the full dataset from data.cityofchicago.org
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "processed" / "chicago_housing.db"
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SAMPLE_CSV = ROOT / "data" / "raw" / "sample_vacant_abandoned_buildings.csv"
COMMUNITY_AREAS_CSV = ROOT / "data" / "raw" / "community_areas.csv"

SOCRATA_ENDPOINT = "https://data.cityofchicago.org/resource/7nii-7srd.json"
PAGE_SIZE = 5000


def fetch_live() -> pd.DataFrame:
    """Pull the full dataset from the Socrata API in pages.

    Requires outbound network access to data.cityofchicago.org, which the
    sandbox this project was drafted in does not have. This function is
    written to run correctly in a normal dev environment with internet
    access; use --source sample to develop/demo without it.
    """
    import requests  # imported here so `--source sample` never needs it installed

    frames = []
    offset = 0
    while True:
        params = {"$limit": PAGE_SIZE, "$offset": offset, "$order": "date_service_request_was_received"}
        resp = requests.get(SOCRATA_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        page = resp.json()
        if not page:
            break
        frames.append(pd.DataFrame(page))
        offset += PAGE_SIZE
        print(f"  fetched {offset} rows...")
    return pd.concat(frames, ignore_index=True)


def load_sample() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_CSV)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names/types regardless of whether the data came from
    the Socrata JSON API (snake_case) or the bundled sample CSV (human-readable
    headers), so downstream code only deals with one schema."""

    rename_map = {
        # sample CSV headers -> canonical names
        "SERVICE REQUEST NUMBER": "service_request_number",
        "DATE SERVICE REQUEST WAS RECEIVED": "date_received",
        "LOCATION ON LOT": "location_on_lot",
        "IS BUILDING DANGEROUS OR HAZARDOUS": "is_dangerous",
        "IS BUILDING OPEN OR BOARDED": "open_or_boarded",
        "ENTRY POINT": "entry_point",
        "IS BUILDING VACANT OR OCCUPIED": "vacant_or_occupied",
        "IS BUILDING VACANT DUE TO FIRE": "vacant_due_to_fire",
        "PEOPLE USING PROPERTY": "people_using_property",
        "ADDRESS STREET NUMBER": "street_number",
        "ADDRESS STREET DIRECTION": "street_direction",
        "ADDRESS STREET NAME": "street_name",
        "ADDRESS STREET SUFFIX": "street_suffix",
        "ZIP CODE": "zip_code",
        "Ward": "ward",
        "Police District": "police_district",
        "Community Area": "community_area",
        "LATITUDE": "latitude",
        "LONGITUDE": "longitude",
        # Socrata JSON API headers -> canonical names
        "sr_number": "service_request_number",
        "date_service_request_was_received": "date_received",
        "if_the_building_is_open_where_is_the_entry_point": "entry_point",
        "is_the_building_dangerous_or_hazardous": "is_dangerous",
        "is_building_open_or_boarded": "open_or_boarded",
        "is_the_building_currently_vacant_or_occupied": "vacant_or_occupied",
        "is_the_building_vacant_due_to_fire": "vacant_due_to_fire",
        "any_people_using_property_homeless_childen_gangs": "people_using_property",
        "address_street_number": "street_number",
        "address_street_direction": "street_direction",
        "address_street_name": "street_name",
        "address_street_suffix": "street_suffix",
        "zip_code": "zip_code",
        "ward": "ward",
        "police_district": "police_district",
        "community_area": "community_area",
        "latitude": "latitude",
        "longitude": "longitude",
    }
    df = df.rename(columns=rename_map)

    keep_cols = [c for c in SCHEMA_COLUMNS if c in df.columns]
    df = df[keep_cols].copy()

    df["date_received"] = pd.to_datetime(df["date_received"], errors="coerce")

    for bool_col in ("is_dangerous", "vacant_due_to_fire", "people_using_property"):
        if bool_col in df.columns:
            df[bool_col] = (
                df[bool_col].astype(str).str.lower().map({"true": 1, "false": 0})
            )

    for int_col in ("ward", "police_district", "community_area"):
        if int_col in df.columns:
            df[int_col] = pd.to_numeric(df[int_col], errors="coerce").astype("Int64")

    df = df.dropna(subset=["service_request_number", "date_received"])
    df = df.drop_duplicates(subset=["service_request_number"])
    return df


SCHEMA_COLUMNS = [
    "service_request_number", "date_received", "location_on_lot", "is_dangerous",
    "open_or_boarded", "entry_point", "vacant_or_occupied", "vacant_due_to_fire",
    "people_using_property", "street_number", "street_direction", "street_name",
    "street_suffix", "zip_code", "ward", "police_district", "community_area",
    "latitude", "longitude",
]


def build_database(df: pd.DataFrame) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())

    df.to_sql("vacant_buildings", conn, if_exists="append", index=False)

    areas = pd.read_csv(COMMUNITY_AREAS_CSV)
    areas.to_sql("community_areas", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()
    print(f"Loaded {len(df)} rows into {DB_PATH}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["sample", "live"], default="sample")
    args = parser.parse_args()

    print(f"Extracting ({args.source})...")
    raw = fetch_live() if args.source == "live" else load_sample()

    print("Transforming...")
    clean_df = clean(raw)

    print("Loading...")
    build_database(clean_df)


if __name__ == "__main__":
    main()
