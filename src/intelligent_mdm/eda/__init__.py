"""Descriptive statistics and statistical flags, with no automatic data deletion."""
from io import BytesIO

import numpy as np
import pandas as pd
import plotly.express as px


def numeric_data(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)


def profile(frame: pd.DataFrame) -> dict:
    numeric = numeric_data(frame)
    schema = pd.DataFrame({"dtype": frame.dtypes.astype(str), "non_null": frame.notna().sum(),
                           "missing_pct": frame.isna().mean()*100, "cardinality": frame.nunique(dropna=True)})
    rows = []
    for col in numeric:
        s = numeric[col].dropna()
        mode = s.mode()
        rows.append({"field": col, "count": len(s), "mean": s.mean(), "median": s.median(),
                     "mode": mode.iloc[0] if not mode.empty else np.nan,
                     "std": s.std(ddof=1), "variance": s.var(ddof=1), "min": s.min(),
                     "p05": s.quantile(.05), "q1": s.quantile(.25), "q3": s.quantile(.75),
                     "p95": s.quantile(.95), "max": s.max()})
    return {"records": len(frame), "variables": len(frame.columns), "schema": schema,
            "numeric": pd.DataFrame(rows), "correlation": numeric.corr(method="pearson", min_periods=3)}


def missing_patterns(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["missing_fields", "rows", "pct"])
    keys = frame.isna().apply(lambda r: ", ".join(frame.columns[r]) or "Complete row", axis=1)
    out = keys.value_counts().rename_axis("missing_fields").reset_index(name="rows")
    out["pct"] = out.rows / len(frame) * 100
    return out


def missing_by_source(frame: pd.DataFrame, source: str = "source") -> pd.DataFrame:
    if source not in frame:
        return pd.DataFrame()
    return frame.groupby(source, dropna=False).apply(
        lambda g: g.isna().mean()*100, include_groups=False
    )


def outliers(series: pd.Series, iqr_multiplier: float = 1.5, z_threshold: float = 3.) -> pd.DataFrame:
    if iqr_multiplier <= 0 or z_threshold <= 0:
        raise ValueError("Outlier thresholds must be positive")
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
    q1, q3 = s.quantile(.25), s.quantile(.75)
    spread = q3-q1
    sd = s.std(ddof=1)
    z = (s-s.mean()) / sd if pd.notna(sd) and sd > 0 else pd.Series(np.nan, index=s.index)
    return pd.DataFrame({"value": s, "iqr": ((s < q1-iqr_multiplier*spread) | (s > q3+iqr_multiplier*spread)).fillna(False),
                         "z_score": z, "z_flag": z.abs().gt(z_threshold).fillna(False),
                         "eligible": s.notna()})


def frequency(frame: pd.DataFrame, column: str, limit: int = 30) -> pd.DataFrame:
    out = frame[column].astype("string").fillna("(missing)").value_counts(dropna=False)
    return out.head(limit).rename_axis(column).reset_index(name="count")


def distribution(frame: pd.DataFrame, column: str, kind: str = "histogram", group: str | None = None):
    color = group if group in frame else None
    if pd.api.types.is_numeric_dtype(frame[column]):
        data = frame.replace([np.inf, -np.inf], np.nan)
        if kind == "box":
            return px.box(data, y=column, x=color, color=color, points=False)
        return px.histogram(data, x=column, color=color, nbins=35, barmode="overlay")
    if pd.api.types.is_datetime64_any_dtype(frame[column]):
        s = frame.set_index(column).resample("MS").size().rename("records").reset_index()
        return px.line(s, x=column, y="records", markers=True)
    return px.bar(frequency(frame, column), x=column, y="count")


def static_distribution(series: pd.Series) -> bytes:
    """A standalone Matplotlib PNG for reproducible, non-interactive reporting."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.8), layout="constrained")
    s = pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    ax.hist(s, bins=35, color="#7267EF", edgecolor="white")
    ax.set(xlabel=str(series.name), ylabel="Observations", title=f"Distribution of {series.name}")
    stream = BytesIO()
    fig.savefig(stream, format="png", dpi=140)
    plt.close(fig)
    return stream.getvalue()
