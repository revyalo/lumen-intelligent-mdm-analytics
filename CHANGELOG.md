# Changelog

## Unreleased — Operational Time Analytics

- Added a ninth workspace with strict local-time input validation, explicit quarantine, source-preserving interval unions and unique-person event sweeps.
- Added continuous-threshold contact evidence, tied rankings, daily peak plateaus, explicit availability/capacity, weighted hourly metrics and exact identity mapping with before/after comparison.
- Added original known-answer/multi-day fixtures, CLI generation/analysis/benchmarks and shared report archive packaging.
- Extended regression tests and CI definitions; uploaded the branch privately with owner approval and opened draft review #1. Hosted runners remain blocked before startup.
- Package version remains 0.1.0; a possible later additive release is 0.2.0, subject to review/validation. No release/tag is created.

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
- Uploaded the candidate to the private preparation repository with owner approval.
- Fixed Actions temporary-directory initialization and validated the workflow with actionlint v1.7.12.

### Verification boundaries

- Core workflows are locally verified; exact audit commands/results are in `docs/RELEASE_AUDIT.md`.
- GitHub-hosted CI was triggered; an account-level restriction prevented all three hosted jobs from starting. Remote tests have not run.
- Optional semantic matching has not been executed; its model and optional dependency licenses remain unevaluated.
- Forecasting, authenticated multiuser deployment and production load validation are not included.

The repository remains private. No public release or version tag has been created.
