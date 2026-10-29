# Primary technical references

Consulted during implementation (2026-10-29). Runtime behavior is also verified by tests against the exact versions in requirements-lock.txt.

- [DuckDB Python API](https://duckdb.org/docs/stable/clients/python/overview/) — isolated connections and registered dataframes.
- [DuckDB Python reference](https://duckdb.org/docs/stable/clients/python/reference/) — SQL execution and parsing.
- [Streamlit pages and navigation](https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation) — eight-page local application.
- [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) — simulated page and widget checks.
- [scikit-learn IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) — scoring and contamination behavior.
- [scikit-learn silhouette_score](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.silhouette_score.html) — internal clustering metric.

No original assessment documents, names, artwork, sample files or templates are part of this repository. The implementation was developed with Codex assistance and should be understood and reviewed by its portfolio owner before interview use.

## Release preparation references

- [Building and testing Python with GitHub Actions](https://docs.github.com/en/actions/tutorials/build-and-test-code/python).
- Official action releases: [checkout](https://github.com/actions/checkout/releases), [setup-python](https://github.com/actions/setup-python/releases), [upload-artifact](https://github.com/actions/upload-artifact/releases). The workflow pins the verified tag commit SHAs.
- [MIT license conditions](https://choosealicense.com/licenses/mit/) and the version-specific dependency metadata/notices recorded in `docs/audit/dependency-licenses.json`.
