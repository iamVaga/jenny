# Phased implementation plan

1. Completed bounded slice: typed contract foundation, fixed commitment MRR/ARR,
   synthetic fixture, deterministic CLI, tests, documentation and adversarial review.
2. Next, after explicit instruction: approve financial policies; improve identity and
   amendment validation; add verified local immutable snapshots and persisted run replay.
3. Add separately versioned billing-derived definition, transaction classifications,
   service periods, credit/refund policies and expanded independent scenario fixtures.
4. Add retention, churn, cohort and bridge metrics with opening-cohort invariants.
5. Add independent accounting reconciliation with explained adjustment evidence.
6. Reach at least 50 independently specified benchmark scenarios and broader property tests.
7. Add safe Excel export and independently verify formulas and workbook layout.

Do not start the next slice until instructed. The immediate financial policy decisions
are documented in METRIC_DEFINITIONS.md; do not extend these experimental defaults
silently to unsupported cases.


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
