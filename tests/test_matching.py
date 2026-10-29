import pandas as pd
import pytest

from intelligent_mdm.ingestion import generate
from intelligent_mdm.matching import ReviewLedger, consolidate, evaluate, match


def records():
    return pd.DataFrame({"record_id": ["a", "b", "c"], "name": ["Acme Limited", " Acme LIMITED ", "Other House"],
                         "tax_id": ["SYN1", "SYN1", "SYN2"], "email": ["a@x.example", None, "a@x.example"],
                         "source": ["administration", "sales", "sales"]})


def test_exact_fuzzy_and_conflict():
    pairs = match(records(), "exact")
    ab = pairs[(pairs.left_id == "a") & (pairs.right_id == "b")].iloc[0]
    ac = pairs[(pairs.left_id == "a") & (pairs.right_id == "c")].iloc[0]
    assert ab.score >= 95 and not ab.conflict
    assert ac.conflict
    labels = pd.DataFrame({"record_id": ["a", "b", "c"], "entity_id": ["X", "X", "Y"]})
    assert evaluate(pairs, labels)["f1"] == 1


def test_reversible_audit_and_provenance(tmp_path):
    raw = records()
    original = raw.copy()
    ledger = ReviewLedger(tmp_path/"reviews.sqlite")
    ledger.record(raw, "a", "b", "accept", "Analyst", "Same verified key")
    result = consolidate(raw, ledger)
    assert len(result["golden_records"]) == 2
    assert len(result["membership"]) == 3
    assert set(result["provenance"].source_record_id) <= set(raw.record_id)
    ledger.record(raw, "a", "b", "revoke", "Analyst", "Reopen for review")
    assert len(consolidate(raw, ledger)["golden_records"]) == 3
    assert len(ledger.history(raw)) == 2
    pd.testing.assert_frame_equal(raw, original)
    changed = raw.copy()
    changed.loc[0, "name"] = "Different data version"
    assert ledger.history(changed).empty


def test_conflicts_require_override_and_transitive_conflicts_are_blocked(tmp_path):
    raw = records()
    ledger = ReviewLedger(tmp_path/"reviews.sqlite")
    with pytest.raises(ValueError):
        ledger.record(raw, "a", "c", "accept", "Analyst", "Insufficient evidence")
    raw.loc[1, "tax_id"] = None
    ledger.record(raw, "a", "b", "accept", "Analyst", "Reviewed")
    ledger.record(raw, "b", "c", "accept", "Analyst", "Reviewed")
    assert len(consolidate(raw, ledger)["blocked"]) == 1


def test_evaluation_counts_candidate_misses():
    labels = pd.DataFrame({"record_id": ["a", "b", "c"], "entity_id": ["X", "X", "X"]})
    pairs = match(records())
    assert evaluate(pairs, labels)["fn"] == 2


def test_budget_and_input_validation():
    bad = records()
    bad.loc[1, "record_id"] = "a"
    with pytest.raises(ValueError):
        match(bad)
    with pytest.raises(ValueError):
        match(records(), max_pairs=1)


def test_synthetic_matching_does_not_receive_truth():
    bundle = generate()
    pairs = match(bundle.tables["customer_sources"])
    metrics = evaluate(pairs, bundle.truth["customer_sources"])
    assert metrics["recall"] > .85
    assert metrics["precision"] > .90
