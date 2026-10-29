# Executed validation — 2026-10-29

This record describes locally executed checks, not planned work. Dataset reference date: **2026-09-30**. All business data are synthetic. GitHub Actions has been configured but has not run remotely. No publication or push was performed.

## Milestone acceptance

| Milestone | Executed evidence | Result |
|---|---|---|
| H1 · Foundation | 6 foundation tests: generation determinism, PK/FK checks, sales/stock reconciliation, audit/idempotence, imputation, CSV round-trip | Passed |
| H2 · EDA & quality | 4 hand-calculated statistics, missingness, constant/nonfinite outliers, applicable quality weights/freshness/FK tests | Passed |
| H3 · BI | 4 SQL revenue reconciliation, transaction-grain RFM, empty/date/region scope and SELECT-only/external-access checks | Passed |
| H4 · MDM | 6 conflict/review/lineage/revocation/fingerprint/evaluation/budget tests; 1 additional spelling-variant regression | Passed |
| H5 · ML | 3 reproducibility, feature/eligibility and small/degenerate-input checks | Passed |
| H6 · Dashboard | 8 page smoke checks + search and cross-page table-selection tests; later SQL and report-button checks | 12 passed |
| H7 · Experiments & reports | 2 evidence-report/insight tests; two executed notebooks; both dataset scales × seeds 42/123, three source-master domains and three matching thresholds | Executed |
| H8 · Release | Complete suite + 3 CSV-import edge checks; editable install, console CLI, launcher readiness, byte compilation, browser visual review | Passed locally |

Final pytest run: **41 passed**, no failures or warnings (62.60 seconds; includes Streamlit simulated pages). The exact JUnit artifact is `docs/test-results.xml`. Production plotting/formatting refinements were then checked with the affected UI/report tests. Final targeted verification: **11 passed** (55.64 seconds), covering the eight pages, report button and report evidence tests after those refinements. A subsequent EDA transaction-page check passed after choosing meaningful default variables and suppressing almost-unique identifier charts. Dependency consistency and all saved notebook code cells were also verified.

Both notebooks contain executed code outputs, with no error cells:

- `01_exploration_and_quality.ipynb` — original observations, descriptive statistics, missing patterns, plots, quality comparisons and audit.
- `02_business_mdm_and_ml.ipynb` — actual SQL, RFM, K-Means profiles, challenge matching, anomalies and measured multi-scale results.

## Environment

```json
{
  "python": "3.12.14",
  "platform": "macOS-13.7.8-x86_64-i386-64bit",
  "pandas": "2.3.3",
  "numpy": "2.5.4",
  "duckdb": "1.5.6",
  "scikit-learn": "1.9.1",
  "rapidfuzz": "3.14.6"
}
```

Installed editable package: `intelligent-mdm-analytics==0.1.0`. Dependency versions are recorded in `requirements-lock.txt`; optional sentence-transformers is not installed. The sandbox emitted Arrow CPU-cache introspection messages during some runs, without failed computations. Local server binding and notebook kernel execution were run with the necessary host permissions.

## Matching at threshold 85

Conflict-marked proposals are excluded from predicted matches. Recall counts every labelled positive pair, including candidates missed by blocking. These are pair metrics, not cluster-merge accuracy. Thresholds are predeclared descriptive settings, not tuned on a held-out production dataset.

| Dataset / domain | Method | TP | FP | FN | Precision | Recall | F1 | Candidate pairs |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| demo / customer_sources | exact | 138 | 2 | 6 | 0.9857 | 0.9583 | 0.9718 | 149 |
| demo / customer_sources | fuzzy | 140 | 6 | 4 | 0.9589 | 0.9722 | 0.9655 | 10,521 |
| large / customer_sources | exact | 2064 | 40 | 96 | 0.9810 | 0.9556 | 0.9681 | 2,247 |
| large / customer_sources | fuzzy | 2092 | 62 | 68 | 0.9712 | 0.9685 | 0.9699 | 18,301 |
| challenge / customers | exact | 2 | 0 | 3 | 1.0000 | 0.4000 | 0.5714 | 4 |
| challenge / customers | fuzzy | 3 | 0 | 2 | 1.0000 | 0.6000 | 0.7500 | 6 |

Fuzzy matching improves recall on the challenge but also introduces more false positives in the identifier-rich base case. It is not universally better than exact matching. Human review is therefore an essential workflow. Aliases without token/key overlap remain missed; another challenge spelling variant falls below threshold. No accepted consolidation is inferred from these experiments.

## Quality before/after

| Size / seed | Original | Normalized | Audited cell changes |
|---|---:|---:|---:|
| demo / 42 | 78.110 | 83.835 | 245 |
| demo / 123 | 78.110 | 83.835 | 245 |
| large / 42 | 78.123 | 83.852 | 3,676 |
| large / 123 | 78.123 | 83.852 | 3,676 |

Normalization changes formats and quarantines malformed emails. It preserves every original row and does not resolve duplicates or identity conflicts. Completeness falls slightly while validity rises. Identical quality scores across seeds are expected: source-defect positions follow deterministic index-based rules, while operational purchasing is stochastic.

## Clustering

| Size / seed | Selected K | Best silhouette | ARI vs RFM | Seconds |
|---|---:|---:|---:|---:|
| demo / 42 | 2 | 0.4388 | 0.2043 | 0.409 |
| demo / 123 | 2 | 0.4595 | 0.1327 | 0.252 |
| large / 42 | 2 | 0.4120 | 0.3084 | 0.699 |
| large / 123 | 2 | 0.4281 | 0.2595 | 0.835 |

These are in-sample internal separation measurements, not out-of-sample accuracy. Cluster candidate scores/profiles are separate CSVs for each scale and seed.

## Anomalies, demo / seed 42

Target: constructed **legitimate bulk purchases**, not data errors or fraud. No target label is a model feature.

| Method | Flags | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| IQR_quantity | 99 | 0.2121 | 1.0000 | 0.3500 |
| Z_quantity | 20 | 1.0000 | 0.9524 | 0.9756 |
| IsolationForest | 126 | 0.1667 | 1.0000 | 0.2857 |

Z-score works particularly well for this constructed univariate target. Isolation Forest also flags unusual multivariate combinations that are not labelled bulk purchases. The 3% contamination setting cannot be interpreted as an error prevalence.

## Scale and observed processing time

| Size / seed | Total rows | Dataframe MiB | Generation s | EDA s | Monthly SQL s | Anomaly comparison s |
|---|---:|---:|---:|---:|---:|---:|
| demo / 42 | 11,622 | 2.40 | 0.107 | 0.028 | 0.114 | 0.433 |
| demo / 123 | 11,542 | 2.39 | 0.106 | 0.030 | 0.107 | 0.483 |
| large / 42 | 194,025 | 39.75 | 1.151 | 0.152 | 0.143 | 2.085 |
| large / 123 | 194,363 | 39.82 | 1.063 | 0.155 | 0.155 | 2.523 |

Times are one observed run per seed/scale, measured with perf_counter on this environment. They are not latency guarantees. Dataframe memory is deep estimated table storage, not peak process memory. Matching runtimes/candidate counts are in matching.csv. Larger production workloads require independent profiling.

## Report and UI verification

`docs/sample_report.zip` was produced using the included CSV bundle and contains HTML, Markdown, JSON, original/normalized observations, complete audit, field statistics, quality rules, business tables, RFM and a Matplotlib PNG. The automated report test reopens the archive and reconciles revenue with actual invoices. Selected-source master proposals are exported; invalid matching schemas/budgets produce an explicit status file rather than fabricated matches.

The local dashboard was opened in the in-app browser and visually checked. Screenshots are included under docs/screenshots/. Screenshots demonstrate layout, while AppTest checks execute pages, interactions, SQL and report generation. Browser testing and notebook execution required local sockets; no external hosting was involved.

## Explicitly not executed / not included

- Semantic matching: **NOT RUN**, no local model supplied. Optional adapter exists; core functionality does not depend on it.
- Forecasting: intentionally omitted; no defensible predictive evaluation is claimed.
- GitHub-hosted CI: configured, not executed remotely.
- Production multiuser/authentication/load testing and deployment: outside this local portfolio release.
- Original assessment PDF, original business datasets, branding and templates: excluded.

## Reproduce

```bash
python -m pip install -e ".[dev]"
python -m pytest --junitxml=runtime/test-results.xml
intelligent-mdm generate --size demo --seed 42 --output runtime/demo
intelligent-mdm experiments --scales demo large --seeds 42 123 --output runtime/experiments
intelligent-mdm report --input runtime/demo --output runtime/evidence_report.zip
python scripts/execute_notebooks.py
```
