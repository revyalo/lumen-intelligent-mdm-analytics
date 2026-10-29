import numpy as np
import pandas as pd
import pytest

from intelligent_mdm.analytics import rfm
from intelligent_mdm.ingestion import generate
from intelligent_mdm.machine_learning import cluster_customers, detect_anomalies
from intelligent_mdm.machine_learning.semantic import semantic_match


def test_clustering_reproducible_and_label_free():
    values = rfm(generate())
    first, second = cluster_customers(values), cluster_customers(values)
    assert first["selected_k"] == second["selected_k"]
    assert first["assignments"].cluster.equals(second["assignments"].cluster)
    assert first["features"] == ["recency", "frequency", "monetary"]
    assert -1 <= first["scores"].silhouette.max() <= 1
    assert first["rfm_comparison"].to_numpy().sum() == len(first["assignments"])
    assert first["profiles"].customers.sum() == len(first["assignments"])


def test_anomaly_eligibility_and_determinism():
    frame = pd.DataFrame({"x": list(range(40))+[10000, np.nan], "y": list(range(40))+[9000, 2]})
    first = detect_anomalies(frame, ["x", "y"], contamination=.05)
    second = detect_anomalies(frame, ["x", "y"], contamination=.05)
    pd.testing.assert_frame_equal(first, second)
    assert first.loc[40, "anomaly"]
    assert not first.loc[41, "eligible"] and pd.isna(first.loc[41, "anomaly_score"])


def test_small_and_degenerate_inputs():
    values = rfm(generate()).head(2)
    with pytest.raises(ValueError):
        cluster_customers(values)
    with pytest.raises(ValueError):
        detect_anomalies(pd.DataFrame({"x": [1, 2]}), ["x"])
    with pytest.raises(ValueError):
        semantic_match(pd.DataFrame(), "/nonexistent-model")
