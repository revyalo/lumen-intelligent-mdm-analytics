import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.common import business_scope, chart, compact_money, context, page_title, proposals
from intelligent_mdm.analytics import business_summary
from intelligent_mdm.data_quality import assess
from intelligent_mdm.sql import run_named

bundle, frame, name = context()
page_title("From scattered data to clear decisions.", "Monitor business performance and the quality of the data behind it.")
scoped = business_scope(bundle, "overview")
kpi = business_summary(scoped)
raw = bundle.tables["customer_sources"]
q = assess(raw, as_of=bundle.metadata["as_of"])
pairs = proposals(raw)
count = int((pairs.score.ge(85) & ~pairs.conflict).sum())
alerts = int(q["rules"].failures.sum())
cols = st.columns(3) + st.columns(3)
for col, label, value in zip(cols, ["Records", "Customers", "Products", "Revenue", "Source quality", "Candidate pairs"],
                            [f"{sum(len(t) for t in bundle.tables.values()):,}", f"{kpi['customers']:,}",
                             f"{len(bundle.tables['products']):,}", compact_money(kpi['revenue']), f"{q['score']:.1f}/100", f"{count:,}"]):
    col.metric(label, value, help=f"Exact revenue in selected scope: €{kpi['revenue']:,.2f}" if label == "Revenue" else None)
st.caption("Revenue and customers follow the selected scope. Records and products count the full bundle; quality and candidate pairs describe customer sources.")
st.caption(f"{alerts:,} failed rule checks in customer sources (a row may fail multiple checks). Candidate pairs are unreviewed hypotheses.")
left, right = st.columns([1.7, 1])
with left:
    st.subheader("Revenue through time")
    monthly = run_named(scoped, "monthly_sales")
    chart(px.area(monthly, x="month", y="revenue", color_discrete_sequence=["#8B80FF"]))
with right:
    st.subheader("Where quality needs attention")
    scores = pd.DataFrame([{"dataset": n, "score": assess(d, name=n, tables=bundle.tables)["score"]}
                           for n, d in bundle.tables.items()])
    chart(px.bar(scores.sort_values("score").head(7), x="score", y="dataset", orientation="h",
                 color_discrete_sequence=["#48D6BA"], range_x=[0, 100]))
st.subheader("Decisions worth exploring")
c1, c2, c3 = st.columns(3)
with c1:
    st.info(f"**Revenue concentration**\n\nThe top 20% of customer accounts generate {kpi['top20_share']:.1%} of scoped revenue. "
            "Review account dependence before prioritizing retention. This is descriptive, not causal.")
with c2:
    st.info(f"**Customer activity**\n\n{kpi['active_customers']:,} accounts purchased in the final 180 days; "
            f"{kpi['inactive_customers']:,} did not within the selected scope. Explore RFM before choosing outreach.")
with c3:
    st.info(f"**Source stewardship**\n\n{raw.email.isna().mean():.1%} of customer-source emails are missing. "
            "Ask source owners to validate contacts; do not infer them from another customer.")
