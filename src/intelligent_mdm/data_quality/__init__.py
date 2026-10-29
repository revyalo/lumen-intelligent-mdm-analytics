"""Applicable-rule quality scoring; missing dimensions never masquerade as 100%."""
import numpy as np
import pandas as pd

from intelligent_mdm.cleaning import text_key
from intelligent_mdm.models import FOREIGN_KEYS

DEFAULT_WEIGHTS = {"completeness": .25, "uniqueness": .20, "validity": .20,
                   "consistency": .15, "referential_integrity": .10, "freshness": .10}


def assess(frame: pd.DataFrame, *, name: str = "uploaded", tables: dict | None = None,
           as_of: str = "2026-09-30", weights: dict | None = None) -> dict:
    weights = dict(DEFAULT_WEIGHTS if weights is None else weights)
    if set(weights) - set(DEFAULT_WEIGHTS) or any(not np.isfinite(v) or v < 0 for v in weights.values()):
        raise ValueError("Weights must be finite, nonnegative values for recognized dimensions")
    df = frame.copy()
    for col in df.select_dtypes(include=["object", "string"]):
        df[col] = df[col].mask(df[col].astype("string").str.fullmatch(r"\s*", na=False))
    n = len(df)
    dims = dict.fromkeys(DEFAULT_WEIGHTS)
    details = []

    def rule(dimension: str, field: str, valid: pd.Series, eligible: pd.Series, description: str):
        tested = int(eligible.sum())
        if tested:
            failures = int((~valid.fillna(False) & eligible).sum())
            details.append({"dimension": dimension, "field": field, "tested": tested,
                            "failures": failures, "score": 100*(1-failures/tested), "rule": description})

    if n and len(df.columns):
        dims["completeness"] = float(df.notna().to_numpy().mean()*100)
    # Natural keys measure redundant observations, not row-ID uniqueness.
    keys = [x for x in ["tax_id", "sku"] if x in df]
    if not keys:
        keys = [c for c in df if c.endswith("_id")][:1]
    if n and keys:
        key = keys[0]
        known = df[key].notna()
        rule("uniqueness", key, ~df[key].duplicated(), known, "Distinct nonmissing natural/primary key values / known values")
    if "email" in df:
        rule("validity", "email", df.email.astype("string").str.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+"),
             df.email.notna(), "Email syntax only; no deliverability claim")
    if "phone" in df:
        rule("validity", "phone", df.phone.astype("string").str.fullmatch(r"\+?[0-9]{9,15}"),
             df.phone.notna(), "9–15 digits with optional leading +")
    for col in ["unit_price", "unit_cost", "quantity", "amount", "net_amount", "on_hand"]:
        if col in df:
            s = pd.to_numeric(df[col], errors="coerce")
            # Signed stock movements are expected to have negative dispatch quantities.
            valid = np.isfinite(s) if name == "stock_movements" and col == "quantity" else np.isfinite(s) & s.ge(0)
            rule("validity", col, valid, df[col].notna(), "Finite, nonnegative value (signed stock movements excepted)")
    if "discount" in df:
        s = pd.to_numeric(df.discount, errors="coerce")
        rule("validity", "discount", s.between(0, 1), df.discount.notna(), "Fraction between 0 and 1")
    if {"unit_price", "unit_cost"} <= set(df):
        price, cost = pd.to_numeric(df.unit_price, errors="coerce"), pd.to_numeric(df.unit_cost, errors="coerce")
        rule("consistency", "unit_price", price.ge(cost), price.notna() & cost.notna(), "Price ≥ cost; promotional losses need review")
    if {"net_amount", "quantity", "unit_price", "discount"} <= set(df):
        expected = (df.quantity * df.unit_price * (1-df.discount)).round(2)
        rule("consistency", "net_amount", df.net_amount.sub(expected).abs().lt(.011),
             df[["net_amount", "quantity", "unit_price", "discount"]].notna().all(axis=1), "Line arithmetic within €0.01")
    for key in ["tax_id", "sku"]:
        if key in df and "name" in df:
            names = df["name"].map(text_key)
            count = names.groupby(df[key]).transform("nunique")
            rule("consistency", key, count.le(1), df[key].notna() & names.ne(""), "Same natural key has one normalized name; typo can also trigger")
    for col, target, target_key in FOREIGN_KEYS.get(name, []):
        if tables and target in tables and col in df and target_key in tables[target]:
            rule("referential_integrity", col, df[col].isin(tables[target][target_key]),
                 pd.Series(True, index=df.index), f"Required FK references {target}.{target_key}")
    if "updated_at" in df:
        dates = pd.to_datetime(df.updated_at, errors="coerce", utc=True).dt.tz_localize(None)
        days = (pd.Timestamp(as_of)-dates).dt.total_seconds()/86400
        rule("freshness", "updated_at", days.between(0, 365), df.updated_at.notna(), "Updated within 365 days, no future date")
    detail = pd.DataFrame(details, columns=["dimension", "field", "tested", "failures", "score", "rule"])
    for dimension in dims:
        rows = detail[detail.dimension.eq(dimension)]
        if not rows.empty:
            dims[dimension] = float(np.average(rows.score, weights=rows.tested))
    applicable = {k: v for k, v in dims.items() if v is not None and weights.get(k, 0) > 0}
    total = sum(weights[k] for k in applicable)
    aggregate = sum(v*weights[k] for k, v in applicable.items())/total if total else None
    missing = df.isna().mean().mul(100).rename("missing_pct").rename_axis("field").reset_index()
    return {"dimensions": dims, "score": aggregate, "rules": detail, "missing": missing,
            "weights": weights, "rows": n, "as_of": as_of}


def compare_sources(frame: pd.DataFrame, **kwargs) -> pd.DataFrame:
    groups = frame.groupby("source", dropna=False) if "source" in frame else [("all", frame)]
    return pd.DataFrame([{"source": source, "rows": len(group), **assess(group, **kwargs)["dimensions"],
                          "score": assess(group, **kwargs)["score"]} for source, group in groups])
