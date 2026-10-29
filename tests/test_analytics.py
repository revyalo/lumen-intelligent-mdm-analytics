import pandas as pd
import pytest

from intelligent_mdm.analytics import business_summary, filter_bundle, rfm
from intelligent_mdm.ingestion import generate
from intelligent_mdm.sql import query, run_named


@pytest.fixture(scope="module")
def bundle():
    return generate()


def test_sql_totals_reconcile(bundle):
    total = bundle.tables["sales"].amount.sum()
    for name, field in [("monthly_sales", "revenue"), ("customer_summary", "revenue"),
                        ("product_performance", "revenue"), ("category_margin", "revenue")]:
        assert run_named(bundle, name)[field].sum() == pytest.approx(total)
    assert business_summary(bundle)["orders"] == len(bundle.tables["sales"])
    assert business_summary(bundle)["inactive_customers"] >= 12


def test_rfm_transaction_grain_and_boundary(bundle):
    out = rfm(bundle)
    cutoff = pd.Timestamp(bundle.metadata["as_of"])-pd.DateOffset(days=364)
    sales = bundle.tables["sales"]
    orders = bundle.tables["orders"]
    eligible = sales[sales.sale_date.ge(cutoff)].merge(orders[["order_id", "customer_id"]], on="order_id")
    assert out.frequency.sum() == len(eligible)
    assert out.monetary.sum() == pytest.approx(eligible.amount.sum())
    assert out.customer_id.nunique() == len(bundle.tables["customers"])
    assert (out[out.segment.eq("No purchases")].frequency == 0).all()


def test_filters_and_empty_scope(bundle):
    scoped = filter_bundle(bundle, "2026-09-01", "2026-09-30", ["North"])
    assert scoped.tables["orders"].order_date.ge("2026-09-01").all()
    assert scoped.tables["customers"].region.eq("North").all()
    empty = filter_bundle(bundle, "2030-01-01", "2030-01-31", [])
    assert business_summary(empty)["revenue"] == 0
    assert rfm(empty).empty


def test_query_read_only_and_no_file_access(bundle):
    with pytest.raises(ValueError):
        query(bundle, "DROP TABLE customers")
    with pytest.raises(ValueError):
        query(bundle, "SELECT 1; SELECT 2")
    with pytest.raises(ValueError):
        query(bundle, "SELECT * FROM read_csv_auto('/etc/passwd')")
