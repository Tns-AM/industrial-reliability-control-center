# Industrial Reliability Control Center

An interactive Streamlit dashboard for exploring industrial maintenance events, reliability KPIs, recurring failure modes, downtime trends, and asset maintenance priorities.

## What it does

- Loads the included synthetic demo data or an uploaded maintenance-event CSV
- Validates required fields, dates, numeric values, and negative downtime
- Calculates failure count, MTBF, MTTR, estimated availability, and a transparent priority index per asset
- Shows monthly downtime trends, failure-mode Pareto, and an asset risk scatter plot
- Filters by asset and date range, then exports the KPI table as CSV

The priority index is a relative ranking based on normalized downtime (65%) and failure count (35%). It is not a failure probability or predictive model.

## Run locally

Requires Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## CSV format

Required columns:

```csv
event_date,asset,area,failure_mode,downtime_hours,repair_hours,production_loss_units
2026-01-10,P-101,Utilities,Seal leak,3.5,2.1,120
```

Dates should use ISO format (`YYYY-MM-DD`). `production_loss_units` is optional; the other columns are required. Each row represents one maintenance event. Keep one consistent unit and reporting convention throughout a file.

## KPI definitions and assumptions

- **MTBF** = estimated observation exposure hours / failure events
- **MTTR** = total downtime hours / failure events
- **Estimated availability** = (exposure hours − downtime hours) / exposure hours × 100

Exposure is approximated as the calendar span of the selected data multiplied by 24 hours per asset. This is a screening estimate; use actual planned operating hours for formal reliability reporting. MTBF and availability depend on the reporting window and event completeness.

## Data handling

The included demo data is synthetic. Uploaded data is processed in the running app session and is not written to a database by this project. Do not upload confidential plant, employer, customer, or personal data to a hosted deployment without appropriate authorization.

## Contributing

Contributions are welcome. Please describe the calculation, include an anonymized sample row, and explain the expected result.

## License

MIT. See [LICENSE](LICENSE).
