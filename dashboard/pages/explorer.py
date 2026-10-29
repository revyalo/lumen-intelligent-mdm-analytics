import numpy as np
import pandas as pd
import streamlit as st

from dashboard.common import context, download_csv, page_title
from intelligent_mdm.eda import profile

bundle, df, name = context()
page_title("Data Explorer", "What does this dataset contain, and which records need a closer look?")
search = st.text_input("Search all fields", placeholder="Name, SKU, region, identifier…")
filtered = df.copy()
if search:
    mask = filtered.astype(str).apply(lambda s: s.str.contains(search, case=False, regex=False)).any(axis=1)
    filtered = filtered[mask]
category = st.selectbox("Filter a categorical field", ["None"] + df.select_dtypes(include=["object", "string"]).columns.tolist())
if category != "None":
    options = sorted(df[category].dropna().astype(str).unique().tolist())
    chosen = st.multiselect("Values", options, default=[])
    if chosen:
        filtered = filtered[filtered[category].astype(str).isin(chosen)]
numbers = df.select_dtypes(include="number").columns.tolist()
num = st.selectbox("Filter a numeric field", ["None"] + numbers)
if num != "None":
    values = pd.to_numeric(df[num], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if not values.empty and values.min() < values.max():
        bounds = st.slider("Range", float(values.min()), float(values.max()), (float(values.min()), float(values.max())))
        filtered = filtered[filtered[num].between(*bounds)]
columns = st.multiselect("Visible columns", df.columns.tolist(), default=df.columns.tolist())
st.caption(f"{len(filtered):,} matching rows · preview capped at 2,000; export includes all matching rows")
st.dataframe(filtered[columns].head(2000), width="stretch", hide_index=True)
download_csv("Export filtered data", filtered[columns], "explorer.csv")
st.subheader("Field inventory")
st.dataframe(profile(filtered)["schema"], width="stretch")
