"""Non-destructive normalization and explicit, audited imputation."""
import re
import unicodedata

import numpy as np
import pandas as pd

AUDIT_COLUMNS = ["record", "field", "before", "after", "operation", "reason"]


def text_key(value) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def normalize(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Preserve row count and identifiers; log every changed cell, including invalid emails."""
    clean = frame.copy(deep=True)
    audit = []
    for col in frame.columns:
        if col.endswith("_id") or col == "record_id" or pd.api.types.is_datetime64_any_dtype(frame[col]):
            continue
        if not (pd.api.types.is_object_dtype(frame[col]) or pd.api.types.is_string_dtype(frame[col])):
            continue
        values = frame[col].astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
        values = values.mask(values.eq(""))
        if col == "email":
            values = values.str.lower()
            values = values.where(values.str.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", na=True))
        elif col == "phone":
            values = values.str.replace(r"[^0-9+]", "", regex=True)
        elif col == "name":
            values = values.str.title()
        clean[col] = values
    for col in ["tax_id", "sku"]:
        if col in clean:
            clean[col] = clean[col].astype("string").str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)
    for col in clean:
        changed = frame[col].astype("string").fillna("<NA>").ne(clean[col].astype("string").fillna("<NA>"))
        for idx in frame.index[changed]:
            audit.append({"record": str(frame.loc[idx, "record_id"]) if "record_id" in frame else str(idx),
                          "field": col, "before": str(frame.loc[idx, col]), "after": str(clean.loc[idx, col]),
                          "operation": "normalize", "reason": "Canonical format; invalid email becomes missing"})
    return clean, pd.DataFrame(audit, columns=AUDIT_COLUMNS)


def impute(frame: pd.DataFrame, column: str, strategy: str, reason: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Opt-in imputation; identifiers and non-finite numeric inputs are rejected."""
    if not reason.strip():
        raise ValueError("A business/statistical reason is required")
    if column not in frame or column.endswith("_id") or column in {"email", "phone", "sku"}:
        raise ValueError("Imputation of identifiers/contact keys is not supported")
    s = frame[column]
    if strategy == "median" and pd.api.types.is_numeric_dtype(s):
        finite = s[np.isfinite(s)]
        value = finite.median()
    elif strategy == "mode":
        modes = s.mode()
        value = modes.iloc[0] if not modes.empty else np.nan
    else:
        raise ValueError("Use median for numeric data or mode for categorical data")
    if pd.isna(value):
        raise ValueError("Cannot impute a completely missing column")
    result = frame.copy(deep=True)
    mask = s.isna()
    result.loc[mask, column] = value
    audit = [{"record": str(frame.loc[i, "record_id"]) if "record_id" in frame else str(i),
              "field": column, "before": "<NA>", "after": str(value), "operation": strategy, "reason": reason}
             for i in frame.index[mask]]
    return result, pd.DataFrame(audit, columns=AUDIT_COLUMNS)
