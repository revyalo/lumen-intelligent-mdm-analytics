"""State-independent selection rules used by the operational page."""
import pandas as pd

from intelligent_mdm.operational_time import ValidationResult


def select_population(validation: ValidationResult, rooms: list[str], employees: list[str],
                      first_date: str, last_date: str) -> ValidationResult:
    start = pd.Timestamp(first_date)
    end = pd.Timestamp(last_date) + pd.Timedelta(1, unit="D")
    if start >= end:
        raise ValueError("Select an ordered date range")
    records = validation.records
    selected = records.loc[records.Room.isin(rooms) & records.Employee.isin(employees) &
                           records.Start.lt(end) & records.End.gt(start)].copy()
    selected["Start"] = selected.Start.clip(lower=start)
    selected["End"] = selected.End.clip(upper=end)
    return ValidationResult(validation.original, selected, validation.issues,
                            {**validation.metadata, "date_selection": [first_date, last_date],
                             "date_filter_policy": "Visits are clipped to selected full local dates"})
