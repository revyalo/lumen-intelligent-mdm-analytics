"""Descriptive ML experiments. No supervised or production performance claims."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler


def cluster_customers(rfm: pd.DataFrame, seed: int = 42, max_k: int = 6) -> dict:
    """Fit log-scaled R/F/M for purchasers; select k by in-sample silhouette."""
    buyers = rfm[rfm.frequency.gt(0)].copy()
    cols = ["recency", "frequency", "monetary"]
    values = buyers[cols].astype(float)
    if len(buyers) < 8 or values.isna().any().any() or (values < 0).any().any():
        raise ValueError("Clustering needs at least eight purchasing customers with finite nonnegative RFM")
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError("RFM contains infinite values")
    scaler = StandardScaler()
    x = scaler.fit_transform(np.log1p(values))
    unique = len(np.unique(x, axis=0))
    upper = min(max_k, len(x)-1, unique-1)
    if upper < 2:
        raise ValueError("Insufficient distinct RFM patterns for silhouette selection")
    candidates, fitted = [], {}
    for k in range(2, upper+1):
        model = KMeans(n_clusters=k, random_state=seed, n_init=10)
        labels = model.fit_predict(x)
        score = silhouette_score(x, labels, sample_size=min(2000, len(x)), random_state=seed)
        candidates.append({"k": k, "silhouette": float(score), "inertia": float(model.inertia_)})
        fitted[k] = (model, labels)
    scores = pd.DataFrame(candidates)
    best = int(scores.sort_values(["silhouette", "k"], ascending=[False, True]).iloc[0].k)
    model, labels = fitted[best]
    buyers["cluster"] = labels
    description = buyers.groupby("cluster").agg(customers=("customer_id", "size"),
        recency=("recency", "mean"), frequency=("frequency", "mean"), monetary=("monetary", "mean"))
    comparison = pd.crosstab(buyers.cluster, buyers.segment)
    return {"assignments": buyers, "scores": scores, "selected_k": best, "profiles": description,
            "rfm_comparison": comparison, "ari_vs_rfm": float(adjusted_rand_score(buyers.segment, labels)),
            "scaler": scaler, "model": model, "features": cols,
            "limitation": "In-sample descriptive silhouette; clusters and RFM rules answer different questions."}


def detect_anomalies(frame: pd.DataFrame, features: list[str], contamination: float = .03, seed: int = 42) -> pd.DataFrame:
    if not features or any(c not in frame or c.endswith("_id") for c in features):
        raise ValueError("Choose numeric measurements, excluding identifiers")
    if not 0 < contamination <= .5:
        raise ValueError("Contamination must be in (0, 0.5]")
    values = frame[features].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    eligible = values.notna().all(axis=1)
    if eligible.sum() < 8:
        raise ValueError("Anomaly detection needs at least eight complete finite rows")
    # Trees do not require scaling; keep original units, exclude incomplete rows with an explicit flag.
    model = IsolationForest(n_estimators=120, contamination=contamination, random_state=seed, n_jobs=1)
    x = values.loc[eligible]
    labels = model.fit_predict(x)
    result = pd.DataFrame(index=frame.index)
    result["eligible"] = eligible
    result["anomaly"] = False
    result["anomaly_score"] = np.nan
    result.loc[eligible, "anomaly"] = labels == -1
    result.loc[eligible, "anomaly_score"] = -model.score_samples(x)
    return result
