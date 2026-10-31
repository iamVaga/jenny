# Known limitations

First coherent slice only. No billing ingestion, recognized revenue, retention/churn,
cohorts, ARR bridge, management comparisons, reconciliation engine, FX conversion,
immutable snapshots, Excel workbook, or run-ID persistence. Preliminary unused schemas
are not claims of implemented functionality. No 50-scenario benchmark or coverage claim.
No partial metric results are emitted if review exceptions exist.

Input completeness and declared classification cannot be independently verified.
Evidence hashes are unverified assertions except the CLI input hash. Currency codes
are syntax-checked only. Contract overlaps are conservatively rejected at measurement
date, not checked across all historical periods. Contract datasets cannot prove that
all recurring commitments were supplied. This implementation is not production ready.


## Snapshot slice update

Added ingestion.py for shared strict JSON parsing and store.py for retained raw-input
snapshots, manifests and verified replay. CLI supports analyze --save and replay by
storage ID. Outputs remain inside the workspace and outside Git. Storage is append-only
through the API, not OS-enforced immutable storage; caller-supplied evidence hashes
remain unverified. Earlier first-slice persistence limitations above are superseded
by this update. Other financial limitations remain unchanged.

Full local suite: 60 passed, including 14 new snapshot/replay cases covering round-trip,
idempotence, input/result/manifest alteration, refusal to overwrite corrupted runs,
raw-byte identity, invalid IDs, recalculation mismatches, CLI replay, workspace bounds
and retained review exceptions. This is not a 60-scenario financial benchmark.
GitHub Actions is configured for Python 3.12/3.13; remote results are not yet verified.
