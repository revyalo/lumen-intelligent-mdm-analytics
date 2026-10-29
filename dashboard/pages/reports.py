import json

import streamlit as st

from dashboard.common import ROOT, context, download_csv, page_title
from intelligent_mdm.data_quality import assess
from intelligent_mdm.eda import profile
from intelligent_mdm.matching import fingerprint

bundle, df, name = context()
page_title("Reports", "What can be exported, reproduced and explained from this analysis?")
st.write("Export the current analysis table and its computed descriptive and quality results. "
         "The full evidence report also includes business metrics, methods and limitations.")
c1, c2 = st.columns(2)
with c1:
    st.subheader("Current table")
    download_csv("Download selected data", df, "selected_data.csv")
    download_csv("Download statistics", profile(df)["numeric"], "statistics.csv")
    if name == "Uploaded CSV" and "upload_original" in st.session_state:
        st.download_button("Download original uploaded bytes", st.session_state.upload_original, "original_upload.csv", "text/csv")
with c2:
    st.subheader("Reproduction manifest")
    manifest = {**bundle.metadata, "analysis_table": name, "normalized": st.session_state.clean_preview,
                "department": st.session_state.get("source", "All sources"),
                "quality_score": assess(df, name=name, tables=bundle.tables)["score"]}
    st.json(manifest)
    st.download_button("Download manifest", json.dumps(manifest, indent=2), "manifest.json", "application/json")
raw = st.session_state._raw
report_key = (bundle.metadata["size"], bundle.metadata["seed"], name,
              fingerprint(raw) if "record_id" in raw else hash(raw.to_csv(index=False)))
if st.button("Build evidence report", type="primary"):
    from intelligent_mdm.reporting import build_report
    with st.spinner("Calculating and packaging evidence…"):
        st.session_state["report_archive"] = build_report(bundle, raw, name)
        st.session_state["report_key"] = report_key
if "report_archive" in st.session_state and st.session_state.get("report_key") == report_key:
    st.download_button("Download evidence report ZIP", st.session_state.report_archive, "lumen_evidence_report.zip", "application/zip")
folder = ROOT / "docs" / "experiments"
if (folder / "summary.json").exists():
    st.subheader("Executed experiment record")
    st.json(json.loads((folder / "summary.json").read_text()))
    st.caption("These saved experiments have their own dataset size/seed provenance; they do not change when sidebar filters change.")


st.subheader("Operational evidence")
st.page_link("pages/operational_time.py", label="Open Operational Time Analytics", icon=":material/schedule:")
st.caption("Temporal reports use their own resource, population and observation-window scope.")
