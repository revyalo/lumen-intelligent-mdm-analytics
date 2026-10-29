import numpy as np
import pandas as pd
import pytest

from intelligent_mdm.data_quality import assess
from intelligent_mdm.eda import missing_patterns, outliers, profile


def test_hand_calculated_statistics():
    df = pd.DataFrame({"x": [1., 2., 2., 3., np.nan], "y": [2., 4., 4., 6., 8.], "text": list("abcde")})
    p = profile(df)
    x = p["numeric"].set_index("field").loc["x"]
    assert p["records"] == 5 and p["variables"] == 3
    assert x["mean"] == x["median"] == x["mode"] == 2
    assert x["variance"] == pytest.approx(2/3)
    assert p["correlation"].loc["x", "y"] == pytest.approx(1)
    assert p["schema"].loc["x", "missing_pct"] == 20
    assert missing_patterns(df).rows.sum() == 5


def test_outlier_edge_cases():
    constant = outliers(pd.Series([2., 2., 2., np.nan]))
    assert not constant.iqr.any() and not constant.z_flag.any()
    s = pd.Series([1.]*20+[100., np.inf, np.nan])
    result = outliers(s)
    assert result.loc[20, "iqr"] and result.loc[20, "z_flag"]
    assert result.eligible.sum() == 21
    assert profile(pd.DataFrame({"a": []}))["records"] == 0


def test_quality_applicability_and_weights():
    df = pd.DataFrame({"tax_id": ["A", "A", "B", None], "email": ["a@x.example", "bad", None, None]})
    q = assess(df, weights={"validity": 1})
    assert q["score"] == 50
    assert q["dimensions"]["uniqueness"] == pytest.approx(100*2/3)
    assert q["dimensions"]["referential_integrity"] is None
    assert assess(df.iloc[:0])["score"] is None
    with pytest.raises(ValueError):
        assess(df, weights={"validity": -1})


def test_quality_freshness_and_fk():
    df = pd.DataFrame({"customer_id": ["C1", "bad"], "updated_at": ["2026-09-01", "2027-01-01"]})
    q = assess(df, name="orders", tables={"customers": pd.DataFrame({"customer_id": ["C1"]})})
    assert q["dimensions"]["freshness"] == 50
    assert q["dimensions"]["referential_integrity"] == 50
