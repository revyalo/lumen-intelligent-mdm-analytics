import hashlib
import io
import os
from pathlib import Path

import pandas as pd
import plotly.io as pio
import streamlit as st

from intelligent_mdm.analytics import filter_bundle
from intelligent_mdm.cleaning import normalize
from intelligent_mdm.ingestion import generate, read_csv
from intelligent_mdm.matching import match

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = Path(os.environ.get("MDM_RUNTIME_DIR", str(ROOT / "runtime")))
COLORS = ["#8B80FF", "#48D6BA", "#F6C36A", "#67B6F7", "#F08DA6", "#AFB9D1"]


def _remember(key: str):
    st.session_state["saved_"+key] = st.session_state[key]


def _restore(key: str, default):
    st.session_state[key] = st.session_state.get("saved_"+key, default)


@st.cache_data(show_spinner=False)
def get_bundle(size: str, seed: int):
    return generate(size, seed)


@st.cache_data(show_spinner=False)
def proposals(frame: pd.DataFrame, method: str = "fuzzy"):
    return match(frame, method)


def setup():
    pio.templates.default = "plotly_dark"
    st.markdown("""<style>
    .block-container {padding-top: 4rem; max-width: 1500px;}
    [data-testid="stMetric"] {background:#1A2234; border:1px solid #303B52; border-radius:12px; padding:17px;}
    [data-testid="stMetricLabel"] {color:#AFB9D1; font-size:13px;}
    [data-testid="stMetricValue"] {font-size:27px;}
    h1 {font-size:2.3rem !important; font-weight:650 !important; letter-spacing:-.045em;}
    h2, h3 {font-size:1.3rem !important; font-weight:600 !important;}
    [data-testid="stSidebar"] {border-right:1px solid #303B52;}
    .eyebrow {font-size:11px; letter-spacing:.19em; color:#48D6BA; margin-bottom:8px; font-weight:700;}
    .muted {color:#AFB9D1; font-size:14px; line-height:1.7;}
    </style>""", unsafe_allow_html=True)
    with st.sidebar:
        st.caption("SYNTHETIC DATA LAB")
        _restore("size", "demo")
        _restore("seed", 42)
        size = st.selectbox("Synthetic dataset", ["demo", "large"], key="size", on_change=_remember, args=("size",))
        seed = int(st.number_input("Random seed", min_value=0, max_value=999999, key="seed", on_change=_remember, args=("seed",)))
        bundle = get_bundle(size, seed)
        st.caption(f"Fictional data · EUR · As of {bundle.metadata['as_of']}")
        uploaded = st.file_uploader("Explore your CSV", type=["csv"], key="csv_upload")
        upload = st.session_state.get("uploaded_df")
        if uploaded is not None:
            raw_bytes = uploaded.getvalue()
            digest = hashlib.sha256(raw_bytes).hexdigest()
            if st.session_state.get("upload_digest") != digest:
                try:
                    upload = read_csv(io.BytesIO(raw_bytes))
                    st.session_state.update(uploaded_df=upload, upload_digest=digest, upload_original=raw_bytes)
                except ValueError as exc:
                    st.error(str(exc))
                    upload = None
        names = list(bundle.tables) + (["Uploaded CSV"] if upload is not None else [])
        _restore("table", "customer_sources")
        if st.session_state["table"] not in names:
            st.session_state["table"] = "customer_sources"
        name = st.selectbox("Analysis table", names, key="table", on_change=_remember, args=("table",))
        raw = (upload if name == "Uploaded CSV" else bundle.tables[name]).copy()
        if "source" in raw:
            source_options = ["All sources"] + sorted(raw.source.dropna().astype(str).unique().tolist())
            _restore("source", "All sources")
            if st.session_state["source"] not in source_options:
                st.session_state["source"] = "All sources"
            source = st.selectbox("Department", source_options, key="source", on_change=_remember, args=("source",))
            if source != "All sources":
                raw = raw[raw.source.astype(str).eq(source)].copy()
        else:
            st.session_state["source"] = "All sources"
        _restore("clean_preview", False)
        use_clean = st.toggle("Use normalized preview", key="clean_preview", on_change=_remember, args=("clean_preview",))
        clean, audit = normalize(raw)
        st.caption("Preview preserves every original row. Quality and MDM use their own explicit before/after views.")
    st.session_state.update(_bundle=bundle, _raw=raw, _frame=clean if use_clean else raw,
                            _clean=clean, _audit=audit, _table=name)


def context():
    setup()
    return st.session_state["_bundle"], st.session_state["_frame"], st.session_state["_table"]


def page_title(title: str, question: str):
    st.markdown('<div class="eyebrow">LUMEN / ANALYTICS WORKSPACE</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(question)
    st.caption(f"Analysis table: {st.session_state['_table']} · {len(st.session_state['_frame']):,} rows · "
               + ("Normalized preview" if st.session_state.clean_preview else "Original observations"))


def chart(fig, *, key: str | None = None):
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#CAD3E5", size=12), colorway=COLORS,
                      margin=dict(l=10, r=15, t=35, b=15), height=330,
                      legend=dict(orientation="h", y=-.2))
    st.plotly_chart(fig, width="stretch", key=key)


def download_csv(label: str, frame: pd.DataFrame, filename: str, key: str | None = None):
    st.download_button(label, frame.to_csv(index=False).encode("utf-8-sig"), filename, "text/csv", key=key)


def compact_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"€{value/1_000_000:.2f}M"
    if abs(value) >= 10_000:
        return f"€{value/1000:.1f}K"
    return f"€{value:,.0f}"


def business_scope(bundle, key: str):
    c1, c2 = st.columns([1, 1])
    with c1:
        dates = st.date_input("Transaction period", value=(pd.Timestamp("2024-10-01"), pd.Timestamp(bundle.metadata["as_of"])),
                              key=key+"_dates")
    with c2:
        regions = sorted(bundle.tables["customers"].region.unique().tolist())
        chosen = st.multiselect("Customer regions", regions, default=regions, key=key+"_regions")
    if len(dates) != 2:
        st.info("Choose the start and end date.")
        st.stop()
    st.caption("These filters apply to transactions and the customer population. Inventory remains the full as-of snapshot. "
               "BI uses the relational bundle; the sidebar analysis table is used by Explorer, EDA, Quality and MDM.")
    return filter_bundle(bundle, dates[0], dates[1], chosen)
