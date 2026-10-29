import io

import pandas as pd
import pytest

from intelligent_mdm.eda import frequency
from intelligent_mdm.ingestion import read_csv


def test_invalid_dates_are_preserved_for_review():
    frame = read_csv(io.StringIO("record_id,updated_at\na,2026-01-01\nb,not-a-date\n"))
    assert frame.loc[1, "updated_at"] == "not-a-date"
    assert frame.loc[0, "updated_at"] == "2026-01-01"


def test_nullable_numeric_frequency():
    frame = pd.DataFrame({"x": pd.Series([1, None, 1], dtype="Int64")})
    assert frequency(frame, "x")["count"].sum() == 3


def test_missing_csv_schema_is_visible():
    with pytest.raises(ValueError, match="Missing columns"):
        read_csv(io.StringIO("name\nExample\n"), required=("record_id",))
