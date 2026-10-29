"""Business definitions shared by the CLI, reports, dashboard and notebooks."""
import numpy as np
import pandas as pd

from intelligent_mdm.models import DatasetBundle
from intelligent_mdm.sql import query, run_named


def filter_bundle(bundle: DatasetBundle, start=None, end=None, regions: list[str] | None = None) -> DatasetBundle:
    result = bundle.copy()
    customers = result.tables["customers"]
    if regions is not None:
        customers = customers[customers.region.isin(regions)]
    orders = result.tables["orders"]
    mask = orders.customer_id.isin(customers.customer_id)
    if start is not None:
        mask &= orders.order_date.ge(pd.Timestamp(start))
    if end is not None:
        mask &= orders.order_date.lt(pd.Timestamp(end)+pd.DateOffset(days=1))
    orders = orders[mask]
    result.tables["customers"] = customers
    result.tables["orders"] = orders
    for name in ["order_lines", "sales"]:
        result.tables[name] = result.tables[name][result.tables[name].order_id.isin(orders.order_id)]
    result.metadata["filters"] = {"start": str(start), "end": str(end), "regions": regions}
    return result


def business_summary(bundle: DatasetBundle, active_days: int = 180) -> dict:
    if active_days < 1:
        raise ValueError("active_days must be positive")
    customers = run_named(bundle, "customer_summary")
    ref = pd.Timestamp(bundle.metadata["as_of"])
    age = (ref-pd.to_datetime(customers.last_purchase)).dt.days
    active = age.between(0, active_days-1)
    revenue = float(bundle.tables["sales"].amount.sum())
    invoices = len(bundle.tables["sales"])
    top_n = max(1, int(np.ceil(len(customers)*.2))) if len(customers) else 0
    top_share = float(customers.head(top_n).revenue.sum()/revenue) if revenue else 0.
    return {"revenue": revenue, "orders": invoices, "customers": len(customers),
            "active_customers": int(active.sum()), "inactive_customers": int((~active).sum()),
            "average_order": revenue/invoices if invoices else 0., "top20_share": top_share,
            "active_days": active_days, "as_of": str(ref.date())}


def rfm(bundle: DatasetBundle, window_days: int = 365) -> pd.DataFrame:
    if window_days < 1:
        raise ValueError("window_days must be positive")
    end = pd.Timestamp(bundle.metadata["as_of"])
    start = end-pd.DateOffset(days=window_days-1)
    scoped = filter_bundle(bundle, start, end)
    out = run_named(scoped, "customer_summary").rename(columns={"revenue": "monetary"})
    out["recency"] = (end-pd.to_datetime(out.last_purchase)).dt.days.astype("Int64")
    out["r_score"] = np.select([out.recency.le(30).fillna(False), out.recency.le(90).fillna(False),
                                out.recency.le(180).fillna(False)], [4, 3, 2], default=1)
    out["f_score"] = np.select([out.frequency.ge(6), out.frequency.ge(3), out.frequency.ge(2)], [4, 3, 2], default=1)
    buyers = out.loc[out.frequency.gt(0), "monetary"]
    if buyers.empty:
        out["m_score"] = 0
        median = np.inf
    else:
        q1, median, q3 = buyers.quantile([.25, .5, .75])
        out["m_score"] = np.select([out.monetary.ge(q3), out.monetary.ge(median), out.monetary.ge(q1)], [4, 3, 2], default=1)
    out["segment"] = np.select([
        out.frequency.eq(0), out.recency.gt(180).fillna(False),
        out.recency.le(90).fillna(False) & out.frequency.ge(3) & out.monetary.ge(median),
        out.frequency.ge(3), out.recency.le(90).fillna(False) & out.frequency.eq(1),
    ], ["No purchases", "At risk", "Champions", "Loyal", "New"], default="Occasional")
    return out


def customer_evolution(bundle: DatasetBundle) -> pd.DataFrame:
    return query(bundle, """SELECT date_trunc('month', created_at) AS month, count(*) AS acquired
                             FROM customers GROUP BY 1 ORDER BY 1""")


def period_comparison(bundle: DatasetBundle) -> pd.DataFrame:
    return query(bundle, """SELECT year(sale_date) AS year, quarter(sale_date) AS quarter,
                             sum(amount) AS revenue, count(*) AS invoices
                             FROM sales GROUP BY 1,2 ORDER BY 1,2""")
