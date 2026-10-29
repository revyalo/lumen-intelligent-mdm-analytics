import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.common import chart, context, download_csv, page_title
from intelligent_mdm.cleaning import impute
from intelligent_mdm.data_quality import DEFAULT_WEIGHTS, assess, compare_sources

bundle, _, name = context()
raw = st.session_state._raw
clean = st.session_state._clean
audit = st.session_state._audit
page_title("Data Quality", "Which fields and sources need stewardship, and what does normalization actually improve?")
with st.expander("Configure dimension weights"):
    columns = st.columns(3)
    weights = {key: columns[i % 3].number_input(key.replace("_", " ").title(), min_value=0., max_value=1.,
                                              value=value, step=.05, key="w_"+key)
               for i, (key, value) in enumerate(DEFAULT_WEIGHTS.items())}
    st.caption("Applicable weights are renormalized. A dimension without tests is excluded.")
kwargs = dict(name=name, tables=bundle.tables, as_of=bundle.metadata["as_of"], weights=weights)
before, after = assess(raw, **kwargs), assess(clean, **kwargs)
c1, c2, c3 = st.columns(3)
c1.metric("Original score", f"{before['score']:.1f}" if before["score"] is not None else "N/A")
c2.metric("Normalized score", f"{after['score']:.1f}" if after["score"] is not None else "N/A")
c3.metric("Audited cell changes", f"{len(audit):,}")
comparison = pd.DataFrame({"dimension": list(DEFAULT_WEIGHTS), "Original": list(before["dimensions"].values()),
                           "Normalized": list(after["dimensions"].values())})
chart(px.bar(comparison.melt(id_vars="dimension", var_name="version", value_name="score"),
             x="dimension", y="score", color="version", barmode="group", range_y=[0, 100]))
st.caption("Invalid emails are quarantined as missing. Completeness may decrease; no identifiers or contradictory values are silently repaired.")
tabs = st.tabs(["Field rules", "Source comparison", "Transformation audit", "Explicit imputation"])
with tabs[0]:
    st.dataframe(before["rules"], width="stretch", hide_index=True)
    st.dataframe(before["missing"].sort_values("missing_pct", ascending=False), width="stretch", hide_index=True)
with tabs[1]:
    st.dataframe(compare_sources(raw, **kwargs), width="stretch", hide_index=True)
with tabs[2]:
    st.dataframe(audit.head(2000), width="stretch", hide_index=True)
    download_csv("Export full cleaning audit", audit, "cleaning_audit.csv")
    download_csv("Export normalized snapshot", clean, "normalized.csv")
    download_csv("Export original observations", raw, "original.csv")
with tabs[3]:
    st.caption("Opt-in demonstration on the normalized snapshot. Results do not overwrite the input or current analysis selection.")
    eligible = [c for c in clean if not c.endswith("_id") and c not in {"record_id", "email", "phone", "sku"}
                and clean[c].isna().any() and not pd.api.types.is_datetime64_any_dtype(clean[c])]
    if eligible:
        field = st.selectbox("Field to impute", eligible)
        strategy = st.selectbox("Strategy", ["median", "mode"] if pd.api.types.is_numeric_dtype(clean[field]) else ["mode"])
        reason = st.text_input("Rationale", placeholder="Explain why this assumption is defensible for this field")
        if st.button("Generate audited imputation"):
            try:
                result, log = impute(clean, field, strategy, reason)
                st.dataframe(log, hide_index=True, width="stretch")
                download_csv("Export imputed snapshot", result, "imputed.csv")
                download_csv("Export imputation audit", log, "imputation_audit.csv")
            except ValueError as exc:
                st.error(str(exc))
    else:
        st.info("No eligible fields with missing values.")
