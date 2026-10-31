# JENNY Revenue Quality Engine v0.1

Local, evidence-aware financial computation foundation. Synthetic inputs only.
This is an experimental contract snapshot calculator, not a validated diligence product.

## Run

Python 3.12+ and Pydantic v2 are required. From this directory in PowerShell:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m jenny validate --input data/sample.json --as-of 2026-06-01
python -m jenny analyze --input data/sample.json --as-of 2026-06-01 --definition contract_snapshot_v1
python -m pytest -q
```

Optional installation when dependency access is authorized: `python -m pip install -e ".[test]"`.
That registers the `jenny` command. Local execution needs no network access.
Use `--root` to restrict input to a chosen local directory. Input paths resolve beneath it.
Success exits 0; review or invalid input exits 2. JSON goes to stdout.
The sample produces USD MRR 200.00 and ARR 2400.00, explicitly unreconciled.
`validate` includes reference checks and measurement-date eligibility checks; it does not certify completeness.

## Scope

Typed schemas for all 18 requested record types; only Organization, Customer,
Contract, EvidenceReference, and CustomerIdentityMapping are accepted in calculation datasets.
Other schemas are preliminary contracts, not working invoice/reconciliation subsystems.
Fixed recurring contract snapshots and opening-cohort retention comparisons are calculated. See docs for exact rules and limits.
No frontend, production deployment, exports, or real customer data are included.

## Documentation

Start with [architecture](docs/ARCHITECTURE.md), [definitions](docs/METRIC_DEFINITIONS.md),
[data contract](docs/DATA_CONTRACT.md), and [limitations](docs/LIMITATIONS.md).
The execution plan and adversarial review are in docs.

## Saved runs and verified replay

```powershell
python -m jenny analyze --input data/sample.json --as-of 2026-06-01 --save
python -m jenny replay --run-id <storage_id>
```

Use the `storage_id` from the analyze response. Outputs default to `outputs/runs/`
and are excluded from Git. `--store` selects another directory within the current
workspace. Each saved run contains exact input bytes, result JSON and a hash manifest.
Replay validates hashes and reruns the current engine, requiring an identical result.
Review-blocked runs can also be saved; replay preserves their nonzero exit status.
Saved source bytes are sensitive if real data is introduced. Storage is append-only
through the application API, not OS-enforced immutable or authenticated storage.

GitHub Actions configuration runs pytest on Python 3.12 and 3.13. Remote CI results
must be checked after publication; local success does not imply CI has run.

## Retention and ARR bridge

```powershell
python -m jenny compare --input data/retention.json --opening 2026-01-01 --closing 2026-07-01 --confirm-complete-history
```

This uses `contract_retention_v1`. The flag asserts that supplied customer/contract
history is complete at both endpoints; JENNY cannot independently establish that.
Without the flag the engine returns a structured review exception, not assumed zeroes.
The synthetic example has NRR 76.666667%, GRR 60%, logo churn 33.333333%, and an
ARR bridge from 3600 to 5160 USD. JSON ratios are fractions, so NRR is 0.76666667.
Hand-derived expected values are in data/retention_expected.json.

Customer movements include source contract/evidence IDs. Currency migrations require
review; currencies are never combined. Comparison output is not yet supported by
saved-run replay (`compare --save` is rejected). No accounting validation is claimed.
See [retention methodology](docs/RETENTION.md) for cohort boundaries and rounding.
