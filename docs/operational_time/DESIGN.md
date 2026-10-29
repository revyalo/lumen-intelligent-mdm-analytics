# Operational Time Analytics — contracts

Unreleased additive module on `feature/operational-time-analytics`. Package version remains 0.1.0; the commercial dataset and existing eight pages retain their contracts.

## Input and validation

CSV: `Employee,Start,End`; optional `Room,Date` and arbitrary retained metadata. Names are exact identifiers, not inferred identities. Absent Room means `Shared resource`. Time-only rows share an explicitly supplied ISO date (demo reference 2026-09-30), unless Date is supplied per row. Strict consistent HH:MM or HH:MM:SS; alternatively consistent naive ISO timestamps. No automatic overnight interpretation, timezone inference, mixed-format coercion or silent row dropping. Timezone-aware inputs are rejected; naive timestamps represent one declared local clock, with DST transitions outside supported scope.

Validation produces row-level errors/warnings. Analysis refuses errors unless the caller explicitly opts into excluding quarantined rows. Duplicates and same-person overlapping/adjacent records are explicitly unioned, with source-row lineage. An optional exact Alias→Canonical map is validated, exported and audited; no fuzzy merging or alteration of the commercial MDM.

## Temporal semantics

Intervals are [Start, End). Clip against explicitly provided nonoverlapping observation windows, then union each person's intervals within each resource. Split at local midnight. Threshold is one continuous intersection strictly longer than 60 seconds **within one resource and local date**, not a sum of fragments. Pair keys are ordered, unique per resource/day; the overall pair count/ranking deduplicates identities across all selected resources/dates. Preserve qualifying temporal evidence and tied ranks.

Sweep grouped events to count unique people. Merge adjacent equal-count segments. Report every maximum plateau per resource/day. A period's peak is the largest **single-resource** occupancy, not a global person count. Sum occupied resource-seconds across rooms; never treat parallel rooms as one room's elapsed time.

Available time is the sum of supplied observation windows; idle time and utilization are undefined without them. Include zero-visit resource-days when windows exist. Hourly means are duration-weighted. Capacity/overcapacity exist only when explicitly configured. Stay statistics use consolidated, clipped per-person/resource visits (before midnight splitting), not raw rows. Employee filters deliberately change the analyzed population; labels must say so.

## Integration and acceptance

`operational_time/`: validation, interval algorithms, analysis, synthetic fixtures and benchmarks. Shared report archive packaging is reused without injecting commercial metrics into operational outputs. A ninth Streamlit page uses existing chart styling and export controls with its own input/state context.

Acceptance: old 41 tests pass; boundary fixtures and generated reference comparisons pass; input/selection/identity/schedule provenance exported; seeded small fixture has independent expected results; measured larger runs report load, validation, occupancy, overlap time and dataframe storage separately; real UI screenshot and local launch checked. Hosted CI remains unverified while account runners are blocked. No confidential reference files/text/branding are included.
