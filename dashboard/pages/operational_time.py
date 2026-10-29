from datetime import time
import hashlib
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.common import _remember, _restore, chart, download_csv, setup_style
from dashboard.operational import select_population
from intelligent_mdm.operational_time import analyze, observation_windows, read_time_csv, validate_records
from intelligent_mdm.operational_time.report import build_time_report
from intelligent_mdm.operational_time.synthetic import demo_fixture, generate_visits

def change_source():
    _remember("ot_source")
    for key in ["ot_rooms", "ot_dates", "ot_apply_map", "ot_allow_invalid", "ot_employees", "ot_closing"]:
        st.session_state.pop("saved_"+key, None)
        st.session_state.pop(key, None)


setup_style()
st.markdown('<div class="eyebrow">LUMEN / RESOURCE INTELLIGENCE</div>', unsafe_allow_html=True)
st.title("Operational Time Analytics")
st.write("Understand when shared resources are used, where occupancy peaks, and which people overlap.")

with st.sidebar:
    st.caption("OPERATIONAL DATA")
    _restore("ot_source", "Known-result demo")
    source = st.selectbox("Visit dataset", ["Known-result demo", "Multi-day synthetic", "Identity mapping demo",
                                          "Validation challenge", "Uploaded CSV"], key="ot_source",
                          on_change=change_source)
    _restore("ot_seed", 42)
    seed = int(st.number_input("Operational seed", min_value=0, max_value=999999, key="ot_seed",
                               on_change=_remember, args=("ot_seed",)))
    uploaded = st.file_uploader("Upload visits · Employee, Start, End", type=["csv"], key="ot_upload")
    if uploaded is not None:
        st.session_state["ot_upload_bytes"] = uploaded.getvalue()
    _restore("ot_reference", pd.Timestamp("2026-09-30").date())
    assumed = st.date_input("Date for time-only rows without Date", key="ot_reference", on_change=_remember, args=("ot_reference",))

fixture = demo_fixture(aliases=source == "Identity mapping demo")
try:
    if source == "Uploaded CSV":
        if "ot_upload_bytes" not in st.session_state:
            st.info("Upload a UTF-8 CSV with Employee, Start and End; then select the rooms, dates and population.")
            st.stop()
        raw = read_time_csv(st.session_state["ot_upload_bytes"])
        st.caption("Uploaded data stay in this local session. The most recent upload is retained while switching pages.")
    elif source == "Multi-day synthetic":
        raw = generate_visits(2000, seed)
    elif source == "Validation challenge":
        raw = fixture.invalid_records
    else:
        raw = fixture.records
    validation = validate_records(raw, assumed_date=str(assumed))
except (ValueError, TypeError, OverflowError) as exc:
    st.error(str(exc))
    st.stop()

with st.expander("Input validation", expanded=validation.has_errors):
    st.write(f"{len(raw):,} original rows · {len(validation.records):,} valid rows · "
             f"{len(validation.issues):,} validation findings")
    st.dataframe(validation.issues, hide_index=True, width="stretch")
    st.dataframe(raw.head(100), hide_index=True, width="stretch")
    download_csv("Download validation findings", validation.issues, "operational_validation.csv", key="ot_validation_export")
allow_invalid = False
if validation.has_errors:
    st.error("Some input rows cannot be interpreted safely. Fix the input or explicitly exclude quarantined rows below.")
    _restore("ot_allow_invalid", False)
    allow_invalid = st.checkbox("Analyze valid rows only; retain quarantined rows in the evidence export", key="ot_allow_invalid", on_change=_remember, args=("ot_allow_invalid",))
    if not allow_invalid:
        st.stop()
if validation.records.empty:
    st.info("No valid visits remain. Load another dataset to calculate occupancy.")
    st.stop()

records = validation.records
rooms_available = sorted(records.Room.unique().tolist())
employees_available = sorted(records.Employee.unique().tolist())
with st.sidebar:
    st.divider()
    st.caption("ANALYSIS SCOPE")
    _restore("ot_rooms", rooms_available)
    st.session_state["ot_rooms"] = [r for r in st.session_state.ot_rooms if r in rooms_available]
    rooms = st.multiselect("Resources", rooms_available, key="ot_rooms", on_change=_remember, args=("ot_rooms",))
    lower = records.Start.min().date()
    upper = (records.End.max()-pd.Timedelta(1, unit="ns")).date()
    _restore("ot_dates", (lower, upper))
    saved_dates = st.session_state["ot_dates"]
    if len(saved_dates) != 2 or saved_dates[0] < lower or saved_dates[-1] > upper:
        st.session_state["ot_dates"] = (lower, upper)
    dates = st.date_input("Local dates", min_value=lower, max_value=upper, key="ot_dates",
                          on_change=_remember, args=("ot_dates",))
    _restore("ot_population", "All employees")
    employee_mode = st.selectbox("Population", ["All employees", "Selected employees"], key="ot_population", on_change=_remember, args=("ot_population",))
    _restore("ot_employees", [])
    st.session_state["ot_employees"] = [p for p in st.session_state.ot_employees if p in employees_available]
    employees = employees_available if employee_mode == "All employees" else st.multiselect(
        "Observed employee labels", employees_available, key="ot_employees", on_change=_remember, args=("ot_employees",))
    _restore("ot_schedule", True)
    has_schedule = st.checkbox("Use explicit daily availability", key="ot_schedule", on_change=_remember, args=("ot_schedule",))
    _restore("ot_opening", time(8))
    _restore("ot_closing", time(18) if source == "Multi-day synthetic" else time(12))
    opening = st.time_input("Opening", key="ot_opening", disabled=not has_schedule, on_change=_remember, args=("ot_opening",))
    closing = st.time_input("Closing", key="ot_closing", disabled=not has_schedule,
                            on_change=_remember, args=("ot_closing",))
    _restore("ot_capacity_enabled", False)
    configure_capacity = st.checkbox("Configure capacity per selected resource", key="ot_capacity_enabled", on_change=_remember, args=("ot_capacity_enabled",))
    capacities = {}
    if configure_capacity:
        for room in rooms:
            key = "ot_capacity_"+hashlib.sha256(room.encode()).hexdigest()[:12]
            _restore(key, 2)
            capacities[room] = int(st.number_input(f"Capacity · {room}", min_value=1, key=key, on_change=_remember, args=(key,)))
    map_upload = st.file_uploader("Reviewed identity map · Alias, Canonical", type=["csv"], key="ot_identity_upload")
    if map_upload is not None:
        st.session_state["ot_map_bytes"] = map_upload.getvalue()
    _restore("ot_apply_map", False)
    apply_map = st.checkbox("Apply reviewed identity map", key="ot_apply_map", on_change=_remember, args=("ot_apply_map",))

if len(dates) != 2 or not rooms or not employees:
    st.info("Select two dates, at least one resource and at least one employee.")
    st.stop()
if has_schedule and opening >= closing:
    st.error("Closing must be after opening. Daily availability does not infer overnight hours.")
    st.stop()
if (pd.Timestamp(dates[1])-pd.Timestamp(dates[0])).days > 365:
    st.error("Select at most 366 local dates per interactive analysis.")
    st.stop()
selected = select_population(validation, rooms, employees, str(dates[0]), str(dates[1]))
windows = observation_windows(rooms, pd.date_range(dates[0], dates[1]).strftime("%Y-%m-%d").tolist(),
                              opening.strftime("%H:%M:%S"), closing.strftime("%H:%M:%S")) if has_schedule else None
selection = {"dataset": source, "seed": seed if source == "Multi-day synthetic" else None,
             "rooms": rooms, "observed_employees": employees, "dates": [str(dates[0]), str(dates[1])]}
mapping = None
try:
    if apply_map:
        if "ot_map_bytes" in st.session_state:
            mapping = read_time_csv(st.session_state["ot_map_bytes"])
        elif source == "Identity mapping demo":
            mapping = fixture.identity_map
        else:
            raise ValueError("Upload an exact reviewed Alias,Canonical map, or choose the identity mapping demo")
    output = analyze(selected, windows=windows, capacities=capacities, identity_map=mapping,
                     allow_quarantined=allow_invalid, selection=selection)
except (ValueError, TypeError, OverflowError) as exc:
    st.error(str(exc))
    st.stop()

if mapping is not None:
    try:
        before = analyze(selected, windows=windows, capacities=capacities, allow_quarantined=allow_invalid, selection=selection)
        output.tables["identity_comparison"] = pd.DataFrame([
            {"Stage": label, **{key: data.summary[key] for key in
             ["employees", "unique_pairs", "peak_people_in_one_resource", "person_seconds"]}}
            for label, data in [("Observed identities", before), ("Explicit canonical map", output)]])
        output.metadata["identity_comparison_status"] = "Computed from the same selected population and windows"
    except ValueError as exc:
        output.metadata["identity_comparison_status"] = f"Baseline comparison unavailable: {exc}"

summary = output.summary
st.session_state["ot_last_summary"] = summary
scope_label = "All observed employees" if employee_mode == "All employees" else "Selected employee population"
st.caption(f"{scope_label} · {len(selected.records):,} selected valid rows · {summary['employees']:,} people within analysis windows · "
           f"{len(rooms)} resource(s). Time-only rows use {assumed} unless Date is supplied.")
if employee_mode != "All employees":
    st.warning("Occupancy now describes the selected people. It does not represent total resource occupancy.")
cols = st.columns(4)
for col, label, value in zip(cols, ["Usage (h)", "Utilization", "Peak", "Pairs"],
                            [f"{summary['occupied_resource_seconds']/3600:.2f}",
                             f"{summary['utilization']:.1%}" if summary['utilization'] is not None else "Not defined",
                             str(summary['peak_people_in_one_resource']), str(summary['unique_pairs'])]):
    col.metric(label, value)
st.caption("Usage is occupied resource-hours across selected rooms. Peak is the highest count in one resource. "
           "A pair needs one continuous overlap >60 seconds in the same resource and local date.")

occupancy, contacts, quality, export = st.tabs(["Occupancy", "Coincidences", "Quality & provenance", "Export"])
with occupancy:
    st.subheader("Presence timeline")
    visits = output.tables["consolidated_visits"]
    if not visits.empty:
        if len(visits) > 1000:
            st.info("Timeline previews the first 1,000 consolidated visits; calculations and exports use the full selection.")
        timeline = visits.head(1000).copy()
        timeline["Lane"] = timeline.Room+" · "+timeline.Employee
        timeline_figure = px.timeline(timeline, x_start="Start", x_end="End", y="Lane", color="Room",
                                      hover_data=["record_ids", "Seconds"])
        timeline_figure.update_yaxes(autorange="reversed", title=None)
        chart(timeline_figure)
    st.subheader("Concurrent people")
    segments = output.tables["occupancy"]
    figure = go.Figure()
    for room, group in segments.groupby("Room", sort=True):
        x, y, previous = [], [], None
        for row in group.itertuples(index=False):
            if previous is not None and previous != row.Start:
                x.append(None)
                y.append(None)
            x.extend([row.Start, row.End])
            y.extend([row.People, row.People])
            previous = row.End
        figure.add_trace(go.Scatter(x=x, y=y, mode="lines", name=room, line_shape="hv", fill="tozeroy"))
    figure.update_layout(yaxis_title="Unique people", xaxis_title="Local time", yaxis=dict(dtick=1, rangemode="tozero"))
    chart(figure)
    st.subheader("All daily peak intervals")
    st.dataframe(output.tables["peak_intervals"], hide_index=True, width="stretch")
    hourly = output.tables["hourly_occupancy"]
    if not hourly.empty and hourly.Date.nunique() > 1:
        weighted = hourly.groupby(["Date", "Hour"], as_index=False)[["PersonSeconds", "ObservedSeconds"]].sum()
        weighted["Mean people per resource"] = weighted.PersonSeconds/weighted.ObservedSeconds
        heatmap = weighted.pivot(index="Date", columns="Hour", values="Mean people per resource")
        st.subheader("Hourly activity · duration-weighted mean people per resource")
        chart(px.imshow(heatmap, aspect="auto", color_continuous_scale="Teal", labels={"color": "Mean people"}))
    st.subheader("Daily utilization and capacity")
    st.dataframe(output.tables["daily_summary"], hide_index=True, width="stretch")
    st.caption("Idle time and utilization are undefined without availability. Overcapacity is undefined without a configured capacity.")
with contacts:
    st.subheader("Distinct-contact ranking · ties retained")
    ranking = output.tables["ranking"]
    if not ranking.empty:
        chart(px.bar(ranking.head(30), x="DistinctPeople", y="Employee", orientation="h", color="DistinctPeople"))
    st.dataframe(ranking, hide_index=True, width="stretch")
    st.caption("Ranking deduplicates people across all selected rooms/dates and includes zero-contact people. Chart previews the top 30.")
    st.subheader("Qualifying pairs by resource and day")
    st.dataframe(output.tables["pairs"], hide_index=True, width="stretch")
    st.subheader("Temporal evidence")
    st.dataframe(output.tables["coincidence_evidence"], hide_index=True, width="stretch")
    st.subheader("Consolidated stay durations")
    if not visits.empty:
        chart(px.histogram(visits.assign(Minutes=visits.Seconds/60), x="Minutes", nbins=25))
    st.dataframe(output.tables["employee_time"], hide_index=True, width="stretch")
    st.caption("Duration statistics describe consolidated person/resource visits after clipping, before midnight splitting.")
with quality:
    st.subheader("Input decisions and source lineage")
    st.dataframe(output.tables["validation_issues"], hide_index=True, width="stretch")
    st.dataframe(output.tables["clipping_audit"], hide_index=True, width="stretch")
    st.caption("Clipping evidence is per input row; duplicate-row durations must not be summed as unique person-time.")
    st.dataframe(output.tables["identity_audit"], hide_index=True, width="stretch")
    if mapping is not None:
        st.subheader("Before / after identity mapping")
        if "identity_comparison" in output.tables:
            st.dataframe(output.tables["identity_comparison"], hide_index=True, width="stretch")
        else:
            st.warning(output.metadata["identity_comparison_status"])
        st.dataframe(mapping, hide_index=True, width="stretch")
    st.json(output.metadata)
    st.caption("Names are exact labels. Shared names may represent different people; use stable source IDs when available. "
               "Local timestamps do not resolve timezones or daylight-saving transitions.")
with export:
    st.subheader("Reproducible operational evidence")
    st.write("Export the original input, selected rows, identity decisions, availability, computed tables and methods together.")
    download_csv("Download daily metrics", output.tables["daily_summary"], "operational_daily_metrics.csv", key="ot_daily_export")
    download_csv("Download coincidence evidence", output.tables["coincidence_evidence"], "operational_coincidences.csv", key="ot_pairs_export")
    report_key = hashlib.sha256(json.dumps({"metadata": output.metadata,
        "windows": output.tables['observation_windows'].to_csv(index=False)}, sort_keys=True).encode()).hexdigest()
    if st.button("Build operational evidence report", type="primary", key="ot_build_report"):
        st.session_state["ot_report_archive"] = build_time_report(output)
        st.session_state["ot_report_key"] = report_key
    if st.session_state.get("ot_report_key") == report_key:
        st.download_button("Download operational report ZIP", st.session_state.ot_report_archive,
                           "lumen_operational_evidence.zip", "application/zip", key="ot_report_export")
    st.page_link("pages/reports.py", label="Open other Lumen reports", icon=":material/download:")
