import pandas as pd
import pytest

from intelligent_mdm.cleaning import impute, normalize
from intelligent_mdm.ingestion import generate, load_bundle, save_bundle, validate_bundle


@pytest.fixture(scope="module")
def bundle():
    return generate()


def test_reproducible_and_relational(bundle):
    other = generate()
    for name in bundle.tables:
        pd.testing.assert_frame_equal(bundle.tables[name], other.tables[name])
    assert validate_bundle(bundle).empty
    assert len(bundle.tables["orders"]) > len(bundle.tables["customers"])
    assert not set(bundle.tables["customer_sources"]) & {"entity_id", "customer_id"}


def test_accounting_and_inventory(bundle):
    t = bundle.tables
    expected = t["order_lines"].groupby("order_id").net_amount.sum()
    sales = t["sales"].set_index("order_id")
    assert (expected.loc[sales.index].round(2) == sales.amount).all()
    balance = t["stock_movements"].groupby("product_id").quantity.sum()
    inv = t["inventory"].set_index("product_id")
    assert balance.eq(inv.on_hand).all()
    assert inv.on_hand.ge(0).all()
    assert t["sales"].sale_date.le(pd.Timestamp(bundle.metadata["as_of"])).all()


def test_normalization_is_audited_and_non_destructive(bundle):
    raw = bundle.tables["customer_sources"]
    original = raw.copy(deep=True)
    clean, audit = normalize(raw)
    pd.testing.assert_frame_equal(original, raw)
    assert len(clean) == len(raw)
    assert not audit.empty
    again, audit2 = normalize(clean)
    pd.testing.assert_frame_equal(again, clean)
    assert audit2.empty
    assert not clean.email.dropna().str.contains("invalid").any()


def test_explicit_imputation():
    raw = pd.DataFrame({"value": [1., None, 9.], "customer_id": ["A", None, "C"]})
    clean, log = impute(raw, "value", "median", "Robust univariate demonstration")
    assert clean.value.iloc[1] == 5
    assert len(log) == 1 and pd.isna(raw.value.iloc[1])
    with pytest.raises(ValueError):
        impute(raw, "customer_id", "mode", "Do not invent a customer")
    with pytest.raises(ValueError):
        impute(raw, "value", "median", "")


def test_roundtrip_and_orphan_detection(bundle, tmp_path):
    save_bundle(bundle, tmp_path)
    restored = load_bundle(tmp_path)
    assert validate_bundle(restored).empty
    restored.tables["orders"].loc[0, "customer_id"] = "unknown"
    assert "orphan_foreign_key" in validate_bundle(restored).issue.values


def test_unknown_scale():
    with pytest.raises(ValueError):
        generate("unknown")
