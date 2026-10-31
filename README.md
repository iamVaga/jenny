# JENNY Revenue Quality Engine

An evidence-first local Python backend for synthetic SaaS revenue diligence. Version
0.1.1 implements two explicit recurring-revenue definitions, customer retention,
cohorts, an ARR bridge, accounting-control reconciliation, retained input snapshots,
verified replay and a macro-free Excel diligence workbook. It is an experimental
financial computation tool, with review boundaries described in docs/LIMITATIONS.md.
No frontend, LLM, microservices or production deployment is included.

## Install and test

Python 3.12+:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
python -m pytest -q
jenny benchmark
```

For a local checkout without installation, set `$env:PYTHONPATH = "$PWD/src"` and
replace `jenny` with `python -m jenny`. Runtime dependencies are Pydantic v2 and
openpyxl. requirements.txt and requirements-dev.txt pin the verified runtime/test environment. Tests additionally require pytest and Hypothesis. The installed package
includes all 70 independent benchmark cases; the benchmark command needs no network.

## Complete demonstration

```powershell
jenny sample --output outputs/sample.json
jenny validate --input outputs/sample.json --as-of 2026-12-31 --definition billing_v1
jenny report --input outputs/sample.json --definition billing_v1 --opening 2026-01-01 --closing 2027-01-01 --confirm-complete-history --save
```

Copy the **storage_id** from the report JSON (it differs from the calculation run_id):

```powershell
jenny replay --run-id <storage_id>
jenny reconcile --run-id <storage_id>
jenny export --run-id <storage_id> --format xlsx --output outputs/diligence.xlsx
```

Output paths must be new and inside the current workspace. Existing exports are never
overwritten. Input files default to the current directory; `--root` narrows the input
boundary. Saved runs default to outputs/runs and remain outside Git. Success exits 0;
review/invalid-input exits 2. `export` exits 0 when a workbook was produced, with the
financial run status explicitly preserved in its JSON response and workbook.

The demonstration closes at USD MRR 430.00 / ARR 5160.00, with NRR 76.666667%,
GRR 60%, and logo churn 33.333333%. Net billed totals of 4380 reconcile to the
separately specified synthetic billing control. This does not make ARR equal billed
or recognized revenue, and no real-world financial validation is claimed.

## Individual calculations

```powershell
jenny analyze --input data/demo.json --as-of 2026-08-01 --definition contract_snapshot_v1 --save
jenny analyze --input data/demo.json --as-of 2026-08-01 --definition billing_v1
jenny compare --input data/demo.json --opening 2026-01-01 --closing 2026-12-31 --definition billing_retention_v1 --confirm-complete-history --save
jenny cohorts --input data/demo.json --as-of 2026-12-31 --definition billing_v1 --confirm-complete-history --save
jenny reconcile --input data/demo.json --opening 2026-01-01 --closing 2027-01-01 --save
```

`analyze --reporting-currency EUR` adds a reporting view if exactly one direct EUR
exchange rate exists for each source currency on the measurement date. Original
currency figures remain visible; retention ratios do not combine currencies.
Report dates are calendar-month boundaries, closing exclusive. Compare dates are
strictly ordered measurement dates, both measured directly at the given endpoint.
History completeness is a caller assertion required for retention and cohorts, not
something JENNY can infer from the absence of records.

## Engineering documentation

- docs/ARCHITECTURE.md: modules, boundaries and run lifecycle.
- docs/DATA_CONTRACT.md: schemas, money, dates and linkage rules.
- docs/METRIC_DEFINITIONS.md and docs/RETENTION.md: exact formulas and assumptions.
- docs/RECONCILIATION.md: signs, controls, statuses and materiality.
- docs/EVIDENCE_LINEAGE.md: hashes, source records and replay guarantees.
- docs/SECURITY.md: local access, formula injection and security limitations.
- docs/BENCHMARK.md and docs/REVIEW.md: independent fixtures and executed checks.
- docs/LIMITATIONS.md: financial and operational boundaries.

Excel contains independently calculated Python values and a small set of real Excel
check formulas. openpyxl does not calculate or cache formulas. Excel is configured to
recalculate on opening; editing workbook source cells does not rerun the Python model.
Exact original amounts remain text in source rows; Excel numeric outputs are limited
to 15 significant digits and oversized exports fail explicitly instead of losing precision.
