# Development record

This project was implemented from a blank directory. The historical brief was consulted for context only; no company document, sample dataset, brand asset or template is distributed here. Every name and dataset in this repository is newly generated fiction.

Milestones are verified in order. Executed commands, environment versions, measured results and caveats are recorded in `docs/VALIDATION.md` and `docs/experiments/` after running them. A feature's presence is not evidence of statistical validity on real business data.

| Milestone | Scope | Acceptance gate |
|---|---|---|
| H1 | Synthetic foundation, CSV IO, schema/FK checks, normalization, audit | Foundation tests and monetary/stock reconciliation |
| H2 | EDA, missingness, distributions, IQR/z-score | Hand-calculated statistics and edge cases |
| H3 | SQL, business metrics, customer/product analysis, RFM | SQL/pandas reconciliation and temporal boundaries |
| H4 | Candidate generation, exact/fuzzy matching, review ledger, golden records | Conflicts, reversibility, provenance and matching labels |
| H5 | Scaled K-Means, silhouette selection, Isolation Forest, optional embeddings | Determinism, small/degenerate samples, no label leakage |
| H6 | Eight Streamlit sections, uploads, filters and exports | Every page rendered through Streamlit AppTest |
| H7 | Multi-scale experiments, evidence-backed insights, reports, notebooks | Executed measurements, exported artifact checks |
| H8 | Packaging, CI, README and interview guide | Complete test suite, install check and local UI preview |

## Design decisions

- The operational model contains canonical customer/product/supplier masters; departmental source records are separate, imperfect observations. Orders reference operational customer IDs, not source row IDs. Canonical masters are generated inputs, never outputs claimed to be produced by matching.
- Matching only sees observational source fields. Truth labels are in an `evaluation_only/` directory and used exclusively by experiment metrics.
- Reference date and seeds are explicit and fixed. All money is EUR excluding tax; revenue counts fulfilled orders only. Line-level costs are fixed simulated procurement costs, allowing synthetic gross margin, not audited accounting profit.
- CSV bundles are portable; DuckDB provides isolated in-memory analytic views; a SQLite event ledger provides local durable human review. This uses Python's standard library and introduces no server or new dependency.
- Streamlit runs locally. The Python/scikit-learn backend is intentionally retained rather than translated into a different web runtime. No cloud service or API is required.
- Predictions are omitted: two synthetic seasonal cycles are insufficient evidence of predictive usefulness on real data. Semantic matching is optional, requires a separately obtained local model, and never downloads a model implicitly.
