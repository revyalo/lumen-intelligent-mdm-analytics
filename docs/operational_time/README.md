# Operational Time Analytics

An additive Lumen workspace for shared-resource presence, interval overlap and utilization. Original synthetic fixtures and documentation; no external assessment materials or source datasets are distributed. No additional runtime or development dependencies.

## Run

From the repository root, with the existing environment activated:

```bash
python -m pip install -e ".[dev]"
python -m streamlit run dashboard/app.py
```

Choose **Operational Time Analytics** in navigation. The default known-result demo has six fictional identities, one resource and two separated activity periods. Set daily availability to 08:00–12:00; optionally configure capacity 2.

```csv
Employee,Start,End,Room,Date
Person 01,08:15,09:15,Atlas,2026-09-30
Person 02,08:45,09:45,Atlas,2026-09-30
Person 03,09:00,09:30,Atlas,2026-09-30
```

The three-row excerpt above occupies 08:15–09:45: 90 minutes of resource usage and a peak of three people, not the sum of person-time. The complete [six-person demo](../../data/operational_time/visits.csv) has these independently specified answers:

| Metric | Complete demo result |
|---|---:|
| Distinct people / qualifying unique pairs | 6 / 6 |
| Occupied resource-hours / person-hours | 2 / 3⅓ |
| Explicit availability / idle resource-hours | 4 / 2 |
| Utilization | 50% |
| Peak people in the resource | 3 |
| Every peak interval | 09:00–09:15; 11:10–11:20 |
| Time above explicitly configured capacity 2 | 25 minutes |
| Contact ranking | All six tie with 2 distinct people |
| Mean / median consolidated stay | 33⅓ / 30 minutes |

Expected results are separate from input under `data/operational_time/evaluation_only/`. Corrupt examples and identity aliases have separate files. The generator's expected answers are checked by tests and benchmarks, never used as computed results.

## Input contract

Required exact headers: `Employee,Start,End`. Optional `Room,Date`; other original metadata survive in the source export. Missing Room means **Shared resource**. Names are exact case-sensitive labels; surrounding whitespace is reported and preserved. A shared name is not proof of shared identity. Prefer stable pseudonymous source identifiers in Employee when available.

Supported timestamps: a file-wide consistent `HH:MM`, `HH:MM:SS`, `YYYY-MM-DDTHH:MM[:SS]`, or the same ISO form with a space separator. Date, when supplied, is strict YYYY-MM-DD; with complete timestamps it must match the start date. Native timestamps must be serialized into this CSV contract before validation. Fractional seconds, mixed formats and timezone offsets are unsupported.

Time-only rows without Date share the explicit reference date; default **2026-09-30**. End must be after Start. A time-only 23:00→01:00 row is invalid; cross-day stays need complete timestamps. Naive values represent one local clock. Timezone/DST transitions require upstream disambiguation; the module does not infer offsets or convert durations into elapsed UTC time.

Validation returns original input, valid records and row-ID error/warning evidence. Required-column failures, invalid/absent values, nonpositive duration and simultaneous same-identity presence in different resources are errors. The API refuses analysis until fixed or explicitly allowed to quarantine rows. The interface has the same opt-in. A consolidated stay that overlaps another resource quarantines its contributing rows conservatively. Duplicate and same-person overlapping records in one resource are warnings: all originals remain; calculations union them with lineage. Adjacent fragments are one continuous presence.

## Scope and metrics

- All intervals use **[Start, End)**. End/start ties create no simultaneous presence.
- Availability is explicitly supplied as nonoverlapping resource windows. Clip visits against those windows before union; export retained/excluded durations per row. Lunch gaps can be expressed through multiple windows in the Python API. The interface/CLI use a repeated daily opening/closing schedule for all chosen dates, including weekends; choose appropriate dates or supply windows through the API for custom calendars.
- Without availability, occupancy is computed within each observed resource/day span. **Idle time and utilization remain undefined.** No opening hours or capacity are inferred.
- Resource usage is the union of occupied time within each room. Totals across parallel rooms are **resource-hours**, not wall-clock hours. Person-time integrates occupancy over time; it is a different measure.
- Union each exact person/resource's overlapping or adjacent records; split at local midnight. Stay statistics use the clipped union **before** midnight splitting. Employee accumulated time sums these nonoverlapping stays; cross-resource identity conflicts are rejected.
- A qualifying pair needs **one continuous intersection strictly longer than 60 seconds in one resource/local date**. Exactly 60 seconds fails. Short separated contacts never accumulate to pass. Midnight splits can change whether an overlap qualifies on a particular day.
- Pair tables are unique per resource/day; evidence retains every qualifying segment and contributing source IDs. Overall pair count and contact ranking deduplicate people across the selected period and rooms. Everyone with retained presence is ranked, including zero contacts; ties use competition rank.
- Peak intervals show **every daily maximum plateau per resource**, merging adjacent equal counts even when occupants change. Period peak is the largest single-resource count. It does not sum occupancy across rooms or imply site-wide distinct people. Zero-person days have no occupied peak interval.
- Hourly means weight each count by its duration, including explicitly observed empty time. Multi-room heatmaps divide summed person-seconds by summed observed resource-seconds.
- Capacity is a positive integer supplied per resource. Overcapacity means strictly more people than that value; unconfigured capacity results remain missing.
- Date filters clip visits to selected full local dates, including cross-midnight visits. Employee filters change occupancy to the selected population; the UI warns and the report records the selection. Input quality findings refer to the full input, not just retained population.

## Identity mapping and MDM boundary

The existing matching engine accepts named records, but commercial matching keys, source priorities and survivorship rules do not define employee identity reliably. The commercial MDM is preserved. Upload an exact reviewed map:

```csv
Alias,Canonical
Person 01 alias,Person 01
```

No automatic fuzzy acceptance. Duplicate aliases, empty labels, chains/cycles or mappings creating simultaneous cross-resource presence are rejected. Many aliases may map directly to one canonical label. Labels not in the map are unchanged. The UI shows a before/after comparison using the same scope; the evidence ZIP includes the map, row-level changes and comparison. An uncomputable baseline due to the explicit pair-work budget is reported as unavailable, never fabricated. Raw records remain untouched. The module does not claim employee authentication, authoritative identity proof or an enterprise audit service.

## Architecture and algorithms

```text
UTF-8 CSV / seeded generator
    → validation + quarantine evidence
    → explicit population/date/resource selection
    → reviewed identity map + observation clipping
    → per-person/resource union + local-date split
    → occupancy event sweep / active-interval pair evidence
    → metrics, weighted hourly series, tied ranking
    → ninth Streamlit page / CLI / shared ZIP packaging
```

- `validation.py`: strict input and row-level diagnostics.
- `intervals.py`: union, day split, cross-resource conflict detection, occupancy and pair algorithms.
- `analysis.py`: typed result contract, identity mapping, clipping, metric definitions and provenance.
- `synthetic.py`: original reproducible records and separated corrupt/evaluation cases.
- `report.py`: domain-specific evidence, using `reporting/archive.py` shared with existing reports.
- `benchmarks.py`, `commands.py`: measured experiments and CLI.
- `dashboard/operational.py`, `dashboard/pages/operational_time.py`: selection and presentation, preserving the commercial sidebar context.

For n records and m day-split unioned visits: validation and union sorting are O(n log n); observation clipping uses sorted windows, O(n log w + retained fragments); occupancy is O(m log m). Pair enumeration is O(m log m + c), where c is the number of actual intersecting interval candidates, **including subthreshold overlaps**, and can be quadratic in dense data. Storing e qualifying evidence segments needs O(e); total working/output storage is O(n + m + e) plus windows and hourly splits. Long date spans also contribute day/hour fragments. This is an in-memory batch application, not distributed processing or streaming.

The pair sweep stops visibly above **1,000,000** interval comparisons by default; it never returns an incomplete success. The benchmark uses an explicit 2,000,000 budget. The interactive date range is capped at 366 dates. Timeline previews at most 1,000 consolidated visits; ranking chart previews 30; tables/CSV calculations retain the full selected result. Report HTML previews 200 rows per table; CSVs are complete. Synthetic results do not establish real-world scalability.

## CLI and reproducible experiments

```bash
intelligent-mdm time-generate --demo --output runtime/operational-demo
intelligent-mdm time-analyze --input runtime/operational-demo/visits.csv --opening 08:00 --closing 12:00 --capacity 2 --output runtime/operational-report.zip
intelligent-mdm time-generate --rows 10000 --seed 42 --output runtime/operational-large
intelligent-mdm time-benchmarks --sizes 100 1000 10000 50000 --seeds 42 123 --output runtime/operational-benchmarks
python -m pytest tests/test_operational_time.py tests/test_operational_dashboard.py
```

Use `--identity-map`, `--assumed-date` and explicit `--allow-quarantined` when appropriate. CLI availability dates default to the full visit date span; `--start-date/--end-date` change availability, not the input employee population. Empty-data availability with explicit resource labels is supported by the Python API.

Python API:

```python
from intelligent_mdm.operational_time import analyze, observation_windows, read_time_csv, validate_records
from intelligent_mdm.operational_time.report import build_time_report

validated = validate_records(read_time_csv(open("visits.csv", "rb")))
windows = observation_windows(["Atlas"], ["2026-09-30"], "08:00", "12:00")
result = analyze(validated, windows=windows, capacities={"Atlas": 2})
print(result.summary)
open("operational-report.zip", "wb").write(build_time_report(result))
```

[Measured runs](experiments/performance.csv), [environment/measurement limits](experiments/summary.json) and [independent fixture check](experiments/demo-check.json) record actual execution. Load, validation, union, occupancy and coincidence timings are separate. Memory values are deep DataFrame storage; **not peak process RAM**. One local run per seed/size is a reproducibility record, not a statistically estimated capacity guarantee.

The [delivery audit](DELIVERY.md) records final regression results, files, screenshots, decisions and release boundaries. Package version remains **0.1.0**. This branch is unreleased; a later additive release could be **0.2.0**, after review and successful hosted validation. No push/publication is authorized by local implementation.
