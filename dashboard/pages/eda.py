import numpy as np
import plotly.express as px
import streamlit as st

from dashboard.common import chart, context, download_csv, page_title
from intelligent_mdm.eda import distribution, frequency, missing_by_source, missing_patterns, numeric_data, outliers, profile, static_distribution

bundle, df, name = context()
page_title("Exploratory Analysis", "How are values distributed, related and missing in the selected table?")
if not len(df.columns):
    st.info("Select a table with columns.")
    st.stop()
p = profile(df)
c1, c2, c3 = st.columns(3)
c1.metric("Observations", f"{p['records']:,}")
c2.metric("Variables", p["variables"])
c3.metric("Missing cells", f"{df.isna().to_numpy().mean()*100:.1f}%" if len(df) else "N/A")
tabs = st.tabs(["Distributions", "Statistics & relationships", "Missingness", "Outliers"])
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    measurements = list(numeric_data(df))
    categorical = [c for c in df if c not in measurements and not c.endswith("_id")
                   and not str(df[c].dtype).startswith("datetime") and df[c].nunique() <= 20]
    dates = df.select_dtypes(include="datetime").columns.tolist()
    preferred = list(dict.fromkeys(measurements + categorical + dates + df.columns.tolist()))
    field = c1.selectbox("Variable", preferred)
    kind = c2.selectbox("Numeric distribution", ["histogram", "box"])
    groups = ["None"] + [c for c in df.select_dtypes(include=["object", "string"]) if df[c].nunique() <= 12]
    group = c3.selectbox("Compare by category", groups)
    if field.endswith("_id") and len(df) and df[field].nunique() / len(df) > .9:
        st.info("This identifier is almost unique per row. Inspect its cardinality in Statistics, or select a measurement for distribution analysis.")
    else:
        chart(distribution(df, field, kind, None if group == "None" else group))
    st.caption("Frequency tables show the 30 most frequent values; dates are grouped by month.")
    st.dataframe(frequency(df, field), hide_index=True, width="stretch")
    if field in numeric_data(df):
        png_key = (name, field, len(df), bundle.metadata["seed"], st.session_state.clean_preview)
        if st.button("Prepare Matplotlib PNG"):
            st.session_state["eda_png"] = static_distribution(df[field])
            st.session_state["eda_png_key"] = png_key
        if "eda_png" in st.session_state and st.session_state.get("eda_png_key") == png_key:
            st.download_button("Download static figure", st.session_state.eda_png, "distribution.png", "image/png")
with tabs[1]:
    st.dataframe(p["numeric"], width="stretch", hide_index=True)
    download_csv("Export descriptive statistics", p["numeric"], "statistics.csv")
    nums = list(numeric_data(df))
    if len(nums) >= 2:
        chart(px.imshow(p["correlation"], zmin=-1, zmax=1, color_continuous_scale="RdBu_r", aspect="auto"))
        a, b = st.columns(2)
        x = a.selectbox("Scatter X", nums)
        y = b.selectbox("Scatter Y", nums, index=1)
        data = df.replace([np.inf, -np.inf], np.nan)
        data = data.sample(min(5000, len(data)), random_state=42)
        chart(px.scatter(data, x=x, y=y, opacity=.55))
        st.caption("Scatter preview uses a seeded sample of at most 5,000 rows. Correlations use all finite paired observations and do not establish causality.")
with tabs[2]:
    missing = p["schema"].reset_index(names="field")
    chart(px.bar(missing, x="field", y="missing_pct", color_discrete_sequence=["#48D6BA"]))
    st.dataframe(missing_patterns(df), width="stretch", hide_index=True)
    st.dataframe(missing_by_source(df), width="stretch")
with tabs[3]:
    nums = list(numeric_data(df))
    if nums:
        field2 = st.selectbox("Measurement", nums)
        flags = outliers(df[field2])
        st.write(f"IQR flags: {int(flags.iqr.sum()):,} · |z|>3 flags: {int(flags.z_flag.sum()):,} · Eligible: {int(flags.eligible.sum()):,}")
        st.dataframe(df.join(flags.add_prefix("diagnostic_"))[flags.iqr | flags.z_flag].head(1000), width="stretch")
        download_csv("Export outlier diagnostics", df.join(flags.add_prefix("diagnostic_")), "outliers.csv")
        st.info("Flags are investigation candidates. Heavy tails weaken z-scores; a legitimate bulk order can be extreme. No rows are removed.")
    else:
        st.info("This table has no numeric measurements.")
