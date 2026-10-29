# Changelog

## [0.1.0] — 2026-10-29 (local release candidate)

### Included

- Reproducible distributor data with separate operational masters, departmental observations, transactions and evaluation-only labels.
- Eight Streamlit sections for EDA, quality, SQL BI/RFM, reversible entity resolution, descriptive ML and evidence reports.
- Exact and RapidFuzz baselines, an append-only local review ledger, golden-record provenance and revocation.
- Scaled K-Means, silhouette comparison, Isolation Forest and statistical outlier diagnostics.
- Two executed notebooks and measured demo/large experiments using seeds 42 and 123.

### Release preparation

- Removed the launcher's dependency on the original session's environment directory.
- Added MIT licensing, dependency-license inventory, publication audit tooling and stricter generated/private-file exclusions.
- Resolved five import-order lint findings with scoped bootstrap annotations.
- Added SHA-pinned GitHub Actions for lint, dependency consistency, publication checks, tests, CLI smoke checks and notebook execution.
- Prepared repository description, topics, release notes and a recorded audit.

### Verification boundaries

- Core workflows are locally verified; exact audit commands/results are in `docs/RELEASE_AUDIT.md`.
- GitHub-hosted CI is pending the owner's approval for the first private push.
- Optional semantic matching has not been executed; its model and optional dependency licenses remain unevaluated.
- Forecasting, authenticated multiuser deployment and production load validation are not included.

No public release or push is performed by preparing this candidate.
