# JENNY Revenue Quality Engine v0.1 — first slice

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
Only fixed recurring contract snapshots are calculated. See docs for exact rules and limits.
No frontend, external services, exports, commits, deployment, or real customer data.

## Documentation

Start with [architecture](docs/ARCHITECTURE.md), [definitions](docs/METRIC_DEFINITIONS.md),
[data contract](docs/DATA_CONTRACT.md), and [limitations](docs/LIMITATIONS.md).
The execution plan and adversarial review are in docs. Stop after this slice;
subsequent work requires explicit instruction.

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
