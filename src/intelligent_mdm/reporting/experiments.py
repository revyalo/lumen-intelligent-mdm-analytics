"""Run empirical experiments. Every result is computed, including failures of recall."""
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from intelligent_mdm.analytics import rfm
from intelligent_mdm.cleaning import normalize
from intelligent_mdm.data_quality import assess
from intelligent_mdm.eda import outliers, profile
from intelligent_mdm.ingestion import generate, validate_bundle
from intelligent_mdm.machine_learning import cluster_customers, detect_anomalies
from intelligent_mdm.matching import evaluate, match
from intelligent_mdm.sql import run_named


def challenge() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = [
        ("a1", "Harbor Industrial Supplies", "SYN001", "office@harbor.example", "A"),
        ("a2", "Harbour Industrial Supply", None, None, "A"),
        ("b1", "Amber Warehouse", "SYN002", "hi@amber.example", "B"),
        ("b2", " Amber WAREHOUSE ", None, None, "B"),
        ("c1", "Kepler Office", "SYN003", "team@kepler.example", "C"),
        ("c2", "Keplr Office", "SYN003", None, "C"),
        ("d1", "Nova Trading", "SYN004", "x@nova.example", "D"),
        ("d2", "Nova Trading", "SYN005", "y@nova.example", "E"),
        ("e1", "Willow Logistics", None, None, "F"),
        ("e2", "Willow Logistic", None, None, "F"),
        ("f1", "Cedar Materials", "SYN006", "a@cedar.example", "G"),
        ("f2", "Cedar Materials", "SYN007", "b@cedar.example", "H"),
        ("g1", "Tangent Distributors", None, None, "I"),
        ("g2", "TD Wholesale", None, None, "I"),
    ]
    full = pd.DataFrame(rows, columns=["record_id", "name", "tax_id", "email", "entity_id"])
    return full.drop(columns="entity_id"), full[["record_id", "entity_id"]]


def run_experiments(output: str | Path, scales: tuple[str, ...] = ("demo", "large"),
                    seeds: tuple[int, ...] = (42, 123), semantic_model: str | None = None) -> dict:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    matching, quality, cluster_rows, anomaly_rows, timings = [], [], [], [], []
    for size in scales:
        for seed in seeds:
            started = perf_counter()
            bundle = generate(size, seed)
            elapsed = perf_counter()-started
            issues = validate_bundle(bundle)
            if not issues.empty:
                raise ValueError(f"Structural validation failed: {issues.to_dict('records')}")
            timing = {"size": size, "seed": seed, "generation_seconds": elapsed,
                      "rows": sum(len(t) for t in bundle.tables.values()),
                      "dataframe_bytes": sum(int(t.memory_usage(deep=True).sum()) for t in bundle.tables.values())}
            raw = bundle.tables["customer_sources"]
            clean, audit = normalize(raw)
            for label, data in [("original", raw), ("normalized", clean)]:
                result = assess(data, as_of=bundle.metadata["as_of"])
                quality.append({"size": size, "seed": seed, "stage": label, "score": result["score"],
                                "changed_cells": 0 if label == "original" else len(audit), **result["dimensions"]})
            for domain in ["customer_sources", "product_sources", "supplier_sources"]:
                for method in ["exact", "fuzzy"]:
                    pairs = match(bundle.tables[domain], method)
                    for threshold in [80., 85., 95.]:
                        matching.append({"size": size, "seed": seed, "domain": domain, "method": method,
                                         **evaluate(pairs, bundle.truth[domain], threshold)})
            started = perf_counter()
            profile(bundle.tables["order_lines"])
            timing["eda_seconds"] = perf_counter()-started
            started = perf_counter()
            monthly = run_named(bundle, "monthly_sales")
            timing["monthly_sql_seconds"] = perf_counter()-started
            if abs(monthly.revenue.sum()-bundle.tables["sales"].amount.sum()) > .01:
                raise AssertionError("SQL does not reconcile with invoices")
            started = perf_counter()
            clusters = cluster_customers(rfm(bundle), seed=seed)
            cluster_rows.append({"size": size, "seed": seed, "k": clusters["selected_k"],
                                 "silhouette": clusters["scores"].silhouette.max(),
                                 "ari_vs_rfm": clusters["ari_vs_rfm"], "seconds": perf_counter()-started})
            clusters["scores"].to_csv(out/f"cluster_candidates_{size}_{seed}.csv", index=False)
            clusters["profiles"].to_csv(out/f"cluster_profiles_{size}_{seed}.csv")
            lines = bundle.tables["order_lines"]
            started = perf_counter()
            forest = detect_anomalies(lines, ["quantity", "unit_price", "net_amount"], seed=seed)
            statistical = outliers(lines.quantity)
            labels = bundle.truth["bulk_purchases"].set_index("line_id").loc[lines.line_id, "is_bulk"].to_numpy(bool)
            for method, flags in [("IQR_quantity", statistical.iqr), ("Z_quantity", statistical.z_flag), ("IsolationForest", forest.anomaly)]:
                pr, rc, f1, _ = precision_recall_fscore_support(labels, flags.to_numpy(bool), average="binary", zero_division=0)
                anomaly_rows.append({"size": size, "seed": seed, "method": method, "flags": int(flags.sum()),
                                     "bulk_labels": int(labels.sum()), "precision": pr, "recall": rc, "f1": f1,
                                     "target": "Constructed legitimate bulk purchases; NOT error or fraud labels"})
            timing["anomaly_comparison_seconds"] = perf_counter()-started
            timings.append(timing)
            print(f"Completed {size}, seed {seed}: {timing['rows']:,} rows", flush=True)
    raw, labels = challenge()
    raw.to_csv(out/"challenge_records.csv", index=False)
    labels.to_csv(out/"challenge_labels.csv", index=False)
    for method in ["exact", "fuzzy"]:
        pairs = match(raw, method)
        matching.append({"size": "challenge", "seed": None, "domain": "customers", "method": method,
                         **evaluate(pairs, labels, 85.)})
    semantic_status = "NOT RUN — no local embedding model provided"
    if semantic_model:
        from intelligent_mdm.machine_learning.semantic import semantic_match
        pairs = semantic_match(raw, semantic_model)
        matching.append({"size": "challenge", "seed": None, "domain": "customers", "method": "semantic",
                         **evaluate(pairs, labels, 85.)})
        semantic_status = "EXECUTED on challenge records with provided local model"
    frames = {"matching": matching, "quality": quality, "clustering": cluster_rows,
              "anomalies": anomaly_rows, "performance": timings}
    for name, rows in frames.items():
        pd.DataFrame(rows).to_csv(out/f"{name}.csv", index=False)
    summary = {"status": "EXECUTED", "scales": list(scales), "seeds": list(seeds), "as_of": "2026-09-30",
               "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                               **{p: version(p) for p in ["pandas", "numpy", "duckdb", "scikit-learn", "rapidfuzz"]}},
               "semantic": semantic_status, "forecasting": "OMITTED — no defensible real-world predictive evaluation",
               "limitations": ["All observations are synthetic; numbered names make base matching relatively easy",
                               "Challenge cases expose blocking misses and ambiguous names",
                               "Silhouette and anomaly evaluation are descriptive in-sample experiments",
                               "Timings are single runs per seed, not capacity guarantees; dataframe_bytes is not peak RSS"],
               "result_files": [f"{k}.csv" for k in frames]}
    (out/"summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
