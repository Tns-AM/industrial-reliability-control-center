from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

REQUIRED = ["event_date", "asset", "area", "failure_mode", "downtime_hours", "repair_hours"]


def demo_data() -> pd.DataFrame:
    rng = np.random.default_rng(2026)
    assets = ["P-101", "P-205", "M-110", "CV-302", "F-410", "CR-501", "CH-610", "PK-701"]
    areas = {"P-101": "Utilities", "P-205": "Utilities", "M-110": "Workshop", "CV-302": "Conveying", "F-410": "Filtration", "CR-501": "Crushing", "CH-610": "Process", "PK-701": "Packaging"}
    modes = ["Bearing wear", "Seal leak", "Electrical fault", "Blockage", "Misalignment", "Sensor fault"]
    rows = []
    start = pd.Timestamp("2024-01-01")
    for i in range(260):
        asset = str(rng.choice(assets))
        downtime = round(float(rng.gamma(1.8, 2.1)), 2)
        rows.append({
            "event_date": start + pd.Timedelta(days=int(rng.integers(0, 900))),
            "asset": asset, "area": areas[asset],
            "failure_mode": str(rng.choice(modes, p=[.24, .18, .17, .15, .14, .12])),
            "downtime_hours": downtime,
            "repair_hours": round(min(downtime, float(rng.gamma(1.5, 1.2))), 2),
            "production_loss_units": int(rng.integers(0, 500)),
        })
    return pd.DataFrame(rows)


def validate_events(data: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    frame = data.copy()
    frame.columns = [str(c).strip() for c in frame.columns]
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    if "production_loss_units" not in frame.columns:
        frame["production_loss_units"] = 0
    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce")
    for col in ["downtime_hours", "repair_hours", "production_loss_units"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    text_ok = frame[["asset", "area", "failure_mode"]].notna().all(axis=1)
    numeric_ok = frame[["downtime_hours", "repair_hours", "production_loss_units"]].notna().all(axis=1)
    nonnegative = (frame[["downtime_hours", "repair_hours", "production_loss_units"]] >= 0).all(axis=1)
    valid = frame["event_date"].notna() & text_ok & numeric_ok & nonnegative
    cleaned = frame.loc[valid].copy()
    cleaned["asset"] = cleaned["asset"].astype(str).str.strip()
    cleaned["area"] = cleaned["area"].astype(str).str.strip()
    cleaned["failure_mode"] = cleaned["failure_mode"].astype(str).str.strip()
    cleaned = cleaned[(cleaned["asset"] != "") & (cleaned["failure_mode"] != "") & (cleaned["area"] != "")]
    return cleaned, len(frame) - len(cleaned)


def make_asset_kpis(events: pd.DataFrame) -> pd.DataFrame:
    start, end = events["event_date"].min().normalize(), events["event_date"].max().normalize()
    exposure = max(1, (end - start).days + 1) * 24
    kpis = events.groupby(["asset", "area"], as_index=False).agg(
        failure_events=("event_date", "size"),
        downtime_hours=("downtime_hours", "sum"),
        repair_hours=("repair_hours", "sum"),
        production_loss_units=("production_loss_units", "sum"),
    )
    kpis["mtbf_hours"] = exposure / kpis["failure_events"]
    kpis["mttr_hours"] = kpis["downtime_hours"] / kpis["failure_events"]
    kpis["estimated_availability_pct"] = ((exposure - kpis["downtime_hours"]).clip(lower=0) / exposure * 100)
    def scale(series):
        span = series.max() - series.min()
        return (series - series.min()) / span if span else pd.Series(0.0, index=series.index)
    kpis["priority_score"] = (0.65 * scale(kpis["downtime_hours"]) + 0.35 * scale(kpis["failure_events"])) * 100
    return kpis.sort_values("priority_score", ascending=False).round(2)


st.set_page_config(page_title="Industrial Reliability Control Center", page_icon="⚙️", layout="wide")
st.title("Industrial Reliability Control Center")
st.caption("Maintenance event analytics for reliability reviews and work prioritization. Demo records are synthetic.")

with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader("Upload maintenance events (CSV)", type=["csv"])
    st.caption("Required: event_date, asset, area, failure_mode, downtime_hours, repair_hours")

try:
    raw = pd.read_csv(uploaded) if uploaded else demo_data()
    events, dropped = validate_events(raw)
except Exception as exc:
    st.error(f"Could not load data: {exc}")
    st.stop()
if events.empty:
    st.error("No valid maintenance events remain after validation.")
    st.stop()

with st.sidebar:
    date_range = st.date_input("Event date range", value=(events.event_date.min().date(), events.event_date.max().date()), min_value=events.event_date.min().date(), max_value=events.event_date.max().date())
    asset_options = sorted(events["asset"].unique().tolist())
    selected_assets = st.multiselect("Assets", asset_options, default=asset_options)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date = end_date = date_range
filtered = events[
    events["event_date"].dt.date.between(start_date, end_date)
    & events["asset"].isin(selected_assets)
].copy()
if filtered.empty:
    st.warning("No events match these filters. Adjust the date range or asset selection.")
    st.stop()

asset_kpis = make_asset_kpis(filtered)
total_failures = len(filtered)
total_downtime = filtered["downtime_hours"].sum()
mttr = total_downtime / total_failures
exposure_hours = max(1, (end_date - start_date).days + 1) * 24 * filtered["asset"].nunique()
availability = max(0.0, (exposure_hours - total_downtime) / exposure_hours * 100)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Failure events", f"{total_failures:,}")
c2.metric("Downtime", f"{total_downtime:,.1f} h")
c3.metric("MTTR", f"{mttr:.2f} h/event")
c4.metric("Estimated availability", f"{availability:.2f}%")
c5.metric("Assets in view", f"{filtered['asset'].nunique()}")

st.divider()
left, right = st.columns(2)
with left:
    monthly = filtered.assign(month=filtered["event_date"].dt.to_period("M").dt.to_timestamp()).groupby("month", as_index=False)["downtime_hours"].sum()
    st.subheader("Monthly downtime")
    st.plotly_chart(px.line(monthly, x="month", y="downtime_hours", markers=True, labels={"month": "Month", "downtime_hours": "Downtime (hours)"}), use_container_width=True)
with right:
    pareto = filtered.groupby("failure_mode", as_index=False).agg(events=("asset", "size"), downtime_hours=("downtime_hours", "sum")).sort_values("downtime_hours", ascending=False)
    st.subheader("Failure-mode Pareto")
    st.plotly_chart(px.bar(pareto, x="downtime_hours", y="failure_mode", orientation="h", color="events", labels={"downtime_hours": "Downtime (hours)", "failure_mode": "Failure mode"}).update_layout(yaxis={"categoryorder": "total ascending"}), use_container_width=True)

st.subheader("Asset priority matrix")
st.plotly_chart(px.scatter(asset_kpis, x="failure_events", y="downtime_hours", size="production_loss_units", color="priority_score", hover_name="asset", hover_data=["area", "mtbf_hours", "mttr_hours"], labels={"failure_events": "Failure events", "downtime_hours": "Downtime (hours)", "priority_score": "Relative priority"}), use_container_width=True)

st.subheader("Asset reliability table")
show_cols = ["asset", "area", "failure_events", "downtime_hours", "mtbf_hours", "mttr_hours", "estimated_availability_pct", "production_loss_units", "priority_score"]
st.dataframe(asset_kpis[show_cols], hide_index=True, use_container_width=True)
st.download_button("Download filtered KPI table", asset_kpis[show_cols].to_csv(index=False), file_name="asset_reliability_kpis.csv", mime="text/csv")
with st.expander("Data quality and metric assumptions"):
    st.write(f"Rows loaded: {len(raw):,}. Invalid rows excluded: {dropped:,}.")
    st.write("Availability and MTBF use a calendar-time exposure estimate for each selected asset. Replace it with actual operating hours for formal reporting. Priority score is a transparent relative ranking (65% downtime, 35% event count), not a probability or predictive model.")
