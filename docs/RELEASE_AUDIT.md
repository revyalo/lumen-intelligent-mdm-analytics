# Lumen v0.1.0 — publication preparation audit

Audit date: **2026-10-29**. Verdict: **ready for a first private push and GitHub CI validation, subject to the owner's approval**. This is a new local verification run using a fresh environment, not an external independent review. No new application features were added.

The preparation repository is [revyalo/lumen-intelligent-mdm-analytics](https://github.com/revyalo/lumen-intelligent-mdm-analytics). It was created **private and empty**. Its private/empty state was verified through GitHub; no code was pushed. [Recorded state](audit/repository-state.json).

## Findings resolved

| Finding in the original delivery | Resolution |
|---|---|
| Launcher searched an environment belonging to the original development session | It now uses this checkout's `.venv` or the active installed interpreter; otherwise it creates a local `.venv`. |
| Five import-order lint errors in the Streamlit bootstrap/notebook setup | Scoped E402 annotations explain why source-path setup precedes those imports; no global lint rule was disabled. |
| No project license or package license metadata | MIT LICENSE, SPDX package metadata and dependency notice review added. |
| CI lacked lint and dependency consistency checks | Added Ruff, pip check, publication-tree audit and license inventory, plus existing test/CLI/notebook checks. Official actions are pinned to verified release commit SHAs. |
| Ignore rules covered only part of generated/private content | Excluded runtime uploads, downloaded models, environment secrets, databases, build outputs, plotting caches and non-demo generated data. A generated Matplotlib cache was removed from the candidate. The downloaded-model rule is anchored to the repository root so the source `intelligent_mdm/models` package is retained. Ignore behavior was checked with representative paths. |
| JUnit evidence contained a local machine hostname | The published JUnit artifact omits the hostname; test counts, failures and elapsed time are preserved. |

## Executed verification

| Check | Actual result |
|---|---|
| Fresh source installation | Passed: a new Python 3.12.14 virtual environment installed the project and development dependencies from `pyproject.toml`. No existing application environment was reused. |
| Dependency consistency | `python -m pip check`: no broken requirements. |
| Lint | `python -m ruff check .`: passed for production modules, dashboard, tests, notebooks and release scripts. |
| Full tests | **41 passed**, 0 failures, 0 errors, 0 skips; 211.565 seconds on the cold environment. [JUnit](test-results.xml). This includes the eight pages, search, page/table state, SQL execution and report generation. |
| Notebooks | Both rerun successfully: 10 + 12 code cells executed, no error outputs. Saved notebook outputs are included. |
| Source provenance | All **17** demo bundle/label/manifest files regenerated **byte for byte** using the documented generator and seed 42. [Hashes and result](audit/synthetic-provenance.json). |
| Multi-scale experiments | Demo/large × seeds 42/123 executed again. Non-timing matching, quality, clustering and anomaly results reproduce the original delivery. [Fresh results](audit/experiments/summary.json). |
| Scale reached | 11,622 / 11,542 demo rows; **194,025 / 194,363** large rows. Timing is environment-specific; [fresh performance measurements](audit/experiments/performance.csv) are not capacity guarantees. |
| Installed distribution | Built a wheel, installed it, and used Python isolated mode to verify import from the environment rather than the checkout; all six packaged SQL queries executed. [Wheel check](audit/wheel-check.json). The wheel contains the reusable library/CLI; the dashboard is run from the repository checkout. |
| Streamlit server | Started with the fresh environment, opened in a real browser, and visually checked. The overview screenshot was refreshed from that run; the temporary server was stopped after inspection. |
| Publication contents | Known credential/key signatures, hard-coded personal paths, original-reference markers, file budgets and nested ZIP contents scanned without findings. [Summary](audit/release-scan-summary.json). |
| Dependency licenses | **83** installed third-party/tooling distributions inventoried; no unknown declared license metadata. Direct runtime notices and bundled numerical/font/runtime caveats reviewed. [Third-party notices](../THIRD_PARTY_NOTICES.md). |
| GitHub status | Repository private and empty; **remote CI has not run**, because the owner has not approved a push. |

The publication scan is heuristic, not a guarantee against every possible secret. Screenshots were visually inspected; the source includes original Lumen assets and newly generated synthetic business data, not original assessment resources. The source release excludes downloaded packages/models and the local review database. Synthetic fixtures contain reserved `.example` email addresses and intentionally malformed test strings, not private contacts.

The data generator, quality definitions, business metrics, matching thresholds and model features were not expanded during this audit. The initial statistical experiment write-up remains in [VALIDATION.md](VALIDATION.md); `docs/audit/experiments/` records the new verification timings and results. Its non-timing metrics were compared against `docs/experiments/` using dataframe assertions.

## CI prepared, not claimed as passed

The workflow targets Ubuntu Python 3.11/3.12 and Windows Python 3.12. It installs from source, validates dependency consistency, runs Ruff, audits the publication tree, records license metadata, runs all tests and smoke-tests the CLI. Ubuntu Python 3.12 additionally runs experiments and notebooks. It uses read-only repository permissions and stores diagnostic artifacts.

Action refs were verified against the official repositories:

- checkout v7.0.1: `3d3c42e5aac5ba805825da76410c181273ba90b1`
- setup-python v7.0.0: `5fda3b95a4ea91299a34e894583c3862153e4b97`
- upload-artifact v7.0.2: `cf430e030ddbb5b0abf93d22962f4752f3646cd9`

These workflow files have been reviewed locally; they have **not** been executed by GitHub. Python 3.11/Linux/Windows behavior remains pending that run. A dependency inventory/pip check does not constitute an online vulnerability database scan.

## Remaining publication gates

1. Owner approves the first push of the prepared local commit to the **private** repository.
2. GitHub Actions completes on that exact commit. Investigate any platform/dependency failures before proceeding.
3. Owner reviews the results and separately decides public visibility and publication/tagging as `v0.1.0`.

Optional embeddings remain **NOT RUN**. No model was downloaded, and the semantic extra/model license graph is outside the core inventory. Forecasting, authentication/multiuser deployment and production load validation are outside this release. Matching scores are heuristics, not calibrated probabilities; synthetic benchmark results are not real-world performance claims.

No unresolved local test/lint/install failure remains. The pending remote CI and optional semantic evaluation are explicit verification boundaries, not successful results.

## Reproduce from a clean checkout

```bash
python -m venv .venv
source .venv/bin/activate                 # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m pip check
python -m ruff check .
python -m pytest --junitxml=runtime/test-results.xml
python scripts/execute_notebooks.py
python scripts/release_audit.py
python scripts/dependency_inventory.py
intelligent-mdm experiments --scales demo large --seeds 42 123 --output runtime/experiments
python -m streamlit run dashboard/app.py
```

[README](../README.md) · [Changelog](../CHANGELOG.md) · [Proposed GitHub description/topics](GITHUB_METADATA.md) · [MIT license](../LICENSE)
