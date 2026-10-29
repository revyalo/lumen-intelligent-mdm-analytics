import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.common import business_scope, chart, context, download_csv, page_title, proposals
from intelligent_mdm.analytics import rfm
from intelligent_mdm.eda import outliers
from intelligent_mdm.machine_learning import cluster_customers, detect_anomalies
from intelligent_mdm.machine_learning.semantic import semantic_match
from intelligent_mdm.matching import evaluate

bundle, df, name = context()
page_title("Machine Learning", "Do customer patterns form interpretable groups, and which observations deserve investigation?")
tabs = st.tabs(["Customer segmentation", "Anomaly comparison", "Matching evaluation"])


@st.cache_data(show_spinner=False)
def clustering(values):
    result = cluster_customers(values)
    return {k: v for k, v in result.items() if k not in {"model", "scaler"}}


@st.cache_data(show_spinner=False)
def anomalies(values, features, contamination):
    return detect_anomalies(values, features, contamination)


with tabs[0]:
    scoped = business_scope(bundle, "ml")
    try:
        result = clustering(rfm(scoped))
        c1, c2, c3 = st.columns(3)
        c1.metric("Selected K", result["selected_k"])
        c2.metric("Best silhouette", f"{result['scores'].silhouette.max():.3f}")
        c3.metric("Agreement with RFM · ARI", f"{result['ari_vs_rfm']:.3f}")
        a, b = st.columns(2)
        with a:
            points = result["assignments"].copy()
            points["cluster"] = points.cluster.astype(str)
            chart(px.scatter(points, x="frequency", y="monetary", color="cluster", size="recency", hover_name="name"))
        with b:
            chart(px.line(result["scores"], x="k", y="silhouette", markers=True))
        st.subheader("Interpret groups in original units")
        st.dataframe(result["profiles"], width="stretch")
        st.dataframe(result["rfm_comparison"], width="stretch")
        st.caption("Features: log1p recency/frequency/monetary → StandardScaler → seeded K-Means. In-sample silhouette selects K; ARI is agreement with RFM rules, not accuracy.")
        download_csv("Export cluster assignments", result["assignments"], "clusters.csv")
    except ValueError as exc:
        st.info(str(exc))
with tabs[1]:
    nums = [c for c in df.select_dtypes(include="number") if not c.endswith("_id")]
    if nums:
        features = st.multiselect("Numeric measurements · selected analysis table", nums, default=nums[:3])
        contamination = st.slider("Isolation Forest contamination", .01, .20, .03, step=.01)
        try:
            result = anomalies(df, features, contamination)
            field = st.selectbox("Univariate comparison field", nums)
            flags = outliers(df[field])
            compare = pd.DataFrame({"IQR": flags.iqr, "Z-score": flags.z_flag, "Isolation Forest": result.anomaly})
            chart(px.bar(compare.sum().rename_axis("method").reset_index(name="flags"), x="method", y="flags"))
            st.dataframe(df.join(result.add_prefix("iforest_")).join(flags.add_prefix("stat_")).loc[compare.any(axis=1)].head(1000), width="stretch")
            st.caption("IQR and z-score are univariate; Isolation Forest can use several features. Their flag counts need not match. Ineligible rows have no ML score. Anomaly does not mean error or fraud.")
            download_csv("Export anomaly comparison", df.join(result.add_prefix("iforest_")).join(flags.add_prefix("stat_")), "anomaly_comparison.csv")
        except ValueError as exc:
            st.info(str(exc))
    else:
        st.info("Select a table with numeric measurements, such as order_lines.")
with tabs[2]:
    raw = st.session_state._raw
    labels = bundle.truth.get(name)
    if labels is not None and {"record_id", "entity_id"} <= set(labels):
        labels = labels[labels.record_id.isin(raw.record_id)]
        threshold = st.slider("Evaluation threshold", 50, 100, 85)
        metrics = []
        for method in ["exact", "fuzzy"]:
            pairs = proposals(raw, method)
            metrics.append({"method": method, **evaluate(pairs, labels, threshold)})
        st.dataframe(pd.DataFrame(metrics), width="stretch", hide_index=True)
        st.caption("Ground truth is used only to calculate metrics. Recall includes positives missed by blocking. Synthetic numbered names and shared identifiers make this easier than many real-world datasets.")
        with st.expander("Optional local semantic experiment"):
            model = st.text_input("Local sentence-transformers model folder")
            st.caption("Optional extra required. No model is downloaded automatically; absent-model results are NOT RUN.")
            if st.button("Evaluate local embeddings"):
                try:
                    predicted = semantic_match(raw, model, min_score=threshold)
                    st.json(evaluate(predicted, labels, threshold))
                except ValueError as exc:
                    st.error(str(exc))
    else:
        st.info("No entity-resolution labels exist for this table. Select a synthetic source master for reproducible precision/recall/F1.")
