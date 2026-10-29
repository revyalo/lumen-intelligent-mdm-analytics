import pandas as pd

from intelligent_mdm.matching import match


def test_name_only_spelling_variant_is_found_by_fuzzy():
    records = pd.DataFrame({"record_id": ["a", "b"], "name": ["Willow Logistics", "Willow Logistic"]})
    assert match(records, "exact").empty
    result = match(records, "fuzzy")
    assert len(result) == 1 and result.iloc[0].score >= 85
    assert not result.iloc[0].conflict
