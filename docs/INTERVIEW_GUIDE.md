# Interview walkthrough

Lead with an actual business question, then trace its denominator, transformation and validation.

**Why separate operational masters from source observations?** A customer is an entity; a departmental row is an observation. Transactions reference the canonical operational IDs. Generated canonical masters are fixture inputs, not a claimed matching achievement. Label mappings are held separately and never used as matching or clustering features.

**Why DuckDB and pandas together?** SQL demonstrates joins, CTEs, HAVING, distinct counts, temporal aggregation and window functions on a relational model. pandas handles profiling, cleaning and feature engineering. Invoice totals reconcile with every revenue aggregation, making grain mistakes detectable.

**What does a quality score mean?** An explicit weighted average of applicable tests. A rule can be wrong for a domain and requires stewardship. Nonapplicable integrity/freshness tests remain null. Invalid data becoming missing can lower one metric while improving another. Show the cell audit and eligible denominators.

**How would you explain a matching score of 98?** It is a rule weight assigned to a shared key, not a 98% chance of identity. Other fields can contradict it. The evaluation measures pair-level precision/recall over all labelled positives, including missed candidates. Open the hand-labelled challenge: fuzzy spelling variants improve recall, but aliases without overlap can still be missed.

**What makes consolidation reversible?** Immutable input rows, an append-only decision history scoped by a dataset fingerprint, latest decisions as graph edges, reproducible survivorship and per-field source IDs. Revoking an edge can split a component. Transitive conflicts can block unions; a conflict override is explicit and recorded.

**Why log-transform and scale RFM?** Revenue/order frequency are right-skewed and use very different units. K-Means is distance-based, so log1p reduces tail dominance and StandardScaler balances dimensions. Excluding nonbuyers avoids invented recency values. Silhouette selects an internal descriptive partition; it is not predictive accuracy. ARI compares with rule-based RFM without claiming one is ground truth.

**Is Isolation Forest better than a z-score?** Not necessarily. The executed bulk-purchase target is a constructed, legitimate univariate quantity pattern, so a simple z-score can outperform a multivariate forest on that target. The forest can identify other unusual combinations. A contamination setting produces review workload, not a fraud rate.

**What would you improve with real data?** Business-owned identity rules; representative pair labels with entity-separated train/validation/test sets if learning thresholds; alias-aware candidate retrieval with measured recall; authenticated stewardship; durable transaction/version semantics; out-of-time analytics; profiling across larger workloads; source-specific schemas and business calendars. Do not claim those are already implemented.

**What was actually checked?** Open `docs/VALIDATION.md`, raw experiment CSVs, pytest JUnit results and executed notebooks. CI is configured but has not run remotely. The exact local environment is recorded. The original assessment was used only as context; no original materials are distributed.
