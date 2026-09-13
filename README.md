# Vacant & Abandoned Buildings in Chicago: A Housing-Distress Indicator

A small end-to-end data project built for policy analysis,
data analysis & visualization, and data engineering.

## Policy question

Vacant and abandoned buildings are a leading indicator of neighborhood disinvestment,
tied to property tax delinquency, population loss, and reduced access to housing.
The City of Chicago has logged 311 calls reporting these buildings since 2010. This
project asks:

- Where in the city is vacant-building distress concentrated?
- Is it getting better or worse over time, and in which community areas?
- What share of reported buildings are flagged as dangerous, fire-damaged, or
  occupied by non-residents (a proxy for urgency)?

## What's in this repo

| Layer | Tool | File |
|---|---|---|
| **Data engineering** | Python + Socrata Open Data API | `src/etl.py` |
| **Storage** | SQLite | `sql/schema.sql`, `data/processed/chicago_housing.db` |
| **Analysis** | pandas | `src/analysis.py` |
| **Visualization** | matplotlib / seaborn | `visuals/*.png` (generated) |
| **Interactive dashboard** | Streamlit | `dashboard/app.py` |

## Data source

City of Chicago Data Portal, dataset *"311 Service Requests – Vacant and Abandoned
Buildings Reported – Historical"* (resource id `7nii-7srd`), covering 311 calls from
2010 through the dataset's retirement in 2018. Full citation and terms:
https://data.cityofchicago.org/Service-Requests/311-Service-Requests-Vacant-and-Abandoned-Building/7nii-7srd

## How the pieces fit together

1. **`src/etl.py`** hits the Socrata API in paginated batches (`$limit`/`$offset`),
   cleans column names, casts types (dates, booleans, ward/community area as int),
   and writes to SQLite. Falls back to the bundled sample CSV if there's no network
   access, so the rest of the pipeline always has something to run against.
2. **`sql/schema.sql`** defines the `vacant_buildings` table plus two indexes
   (community area, date) since the dashboard filters on both.
3. **`src/analysis.py`** pandas + SQL queries answering the policy questions above:
   reports by community area, reports over time, and the "urgency" flag breakdown.
   Saves each result as a chart in `visuals/`.
4. **`dashboard/app.py`** a Streamlit app with a community-area filter and a date
   range slider, so a policy analyst could explore the data without touching code.

## Running it

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 1. Build the database (uses bundled sample by default)
python src/etl.py --source sample

# To pull the full live dataset instead (needs internet access):
# python src/etl.py --source live

# 2. Run the analysis, generate charts
python src/analysis.py

# 3. Launch the dashboard
streamlit run dashboard/app.py
```

## What I'd do next with more time

- Join against the [Chicago property tax delinquency dataset](https://data.cityofchicago.org)
  to test whether vacant-building density predicts delinquency, not just correlates with it.
- Pull the *current* 311 dataset (`v6vf-nfxy`), which replaced this one in 2018, to
  extend the time series to the present.
- Add population and median income by community area (ACS data) to normalize counts
  per capita rather than raw totals, which currently favor larger community areas.
