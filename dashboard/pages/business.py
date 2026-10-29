import plotly.express as px
import streamlit as st

from dashboard.common import business_scope, chart, context, download_csv, page_title
from intelligent_mdm.analytics import business_summary, customer_evolution, period_comparison, rfm
from intelligent_mdm.sql import QUERY_NAMES, query, query_text, run_named

bundle, _, _ = context()
page_title("Business Intelligence", "Who buys, what creates margin, and how does performance change over time?")
scoped = business_scope(bundle, "bi")
kpi = business_summary(scoped)
cols = st.columns(4)
for col, label, val in zip(cols, ["Fulfilled revenue", "Average order", "Active · final 180 days", "Top 20% revenue share"],
                           [f"€{kpi['revenue']:,.0f}", f"€{kpi['average_order']:,.2f}", f"{kpi['active_customers']:,}", f"{kpi['top20_share']:.1%}"]):
    col.metric(label, val)
tabs = st.tabs(["Sales & time", "Customers & RFM", "Products & inventory", "SQL Lab"])
with tabs[0]:
    monthly = run_named(scoped, "monthly_sales")
    chart(px.line(monthly, x="month", y="revenue", markers=True))
    st.dataframe(monthly, width="stretch", hide_index=True)
    st.caption("MoM is undefined without a prior month or when prior sales are zero. Synthetic data contain constructed seasonality.")
    a, b = st.columns(2)
    with a:
        chart(px.bar(period_comparison(scoped), x="quarter", y="revenue", color="year", barmode="group"))
        st.caption("Quarter totals can represent incomplete quarters within the selected period.")
    with b:
        m = monthly.copy()
        if not m.empty:
            m["calendar_month"] = m.month.dt.month
            m["year"] = m.month.dt.year.astype(str)
            chart(px.line(m, x="calendar_month", y="revenue", color="year", markers=True))
    download_csv("Export monthly sales", monthly, "monthly_sales.csv")
with tabs[1]:
    customer = run_named(scoped, "customer_summary")
    a, b = st.columns(2)
    with a:
        chart(px.bar(customer.groupby("region", as_index=False).agg(customers=("customer_id", "size")), x="region", y="customers"))
    with b:
        chart(px.histogram(customer, x="frequency", nbins=25))
    st.subheader("Customer ranking")
    st.dataframe(customer.head(100), width="stretch", hide_index=True)
    evolution = customer_evolution(scoped)
    chart(px.bar(evolution, x="month", y="acquired"))
    st.caption("Acquisition uses master creation dates for the selected customer regions; it is independent of transaction-period controls.")
    segments = rfm(scoped)
    chart(px.bar(segments.groupby("segment", as_index=False).agg(customers=("customer_id", "size"), monetary=("monetary", "sum")), x="segment", y="customers", color="segment"))
    st.dataframe(segments, width="stretch", hide_index=True)
    st.caption("RFM: final 365 days through reference date, intersected with selected scope. R: days since purchase; F: distinct fulfilled orders; M: net revenue. Rules: docs/METHODOLOGY.md.")
    download_csv("Export RFM segments", segments, "rfm.csv")
with tabs[2]:
    performance = run_named(scoped, "product_performance")
    category = run_named(scoped, "category_margin")
    a, b = st.columns(2)
    with a:
        chart(px.bar(performance.head(12), x="units", y="name", orientation="h"))
    with b:
        chart(px.bar(category, x="category", y="gross_margin", color="category"))
    prices = run_named(scoped, "price_history")
    chart(px.line(prices, x="month", y="weighted_unit_price", color="category"))
    st.caption("Price history is quantity-weighted and affected by product mix. Margins use historical simulated costs and exclude operating costs.")
    st.dataframe(performance, width="stretch", hide_index=True)
    low = performance[performance.units.le(performance.units.quantile(.25))]
    st.subheader("Low rotation · bottom quartile of scoped units")
    st.dataframe(low.merge(bundle.tables["inventory"][["product_id", "on_hand"]], on="product_id"), width="stretch", hide_index=True)
    total_units = performance.units.sum()
    st.caption(f"Top 10% of SKUs account for {performance.head(max(1, int(len(performance)*.1))).units.sum()/total_units:.1%} of demand." if total_units else "No demand in this scope.")
    download_csv("Export product performance", performance, "product_performance.csv")
with tabs[3]:
    template = st.selectbox("Analytical query", QUERY_NAMES)
    sql = st.text_area("SQL · single SELECT / WITH", value=query_text(template), height=250, key="sql_"+template)
    st.caption("Tables follow the relational bundle contract. fulfilled_lines is a line-level view of invoiced orders. Results capped at 10,000 rows; external file access disabled.")
    if st.button("Run SQL"):
        try:
            result = query(scoped, sql)
            st.dataframe(result, width="stretch", hide_index=True)
            download_csv("Export query result", result, "query.csv")
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
