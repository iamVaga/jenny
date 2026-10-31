# Benchmark actually implemented

A hand-authored synthetic JSON dataset has two customers, one monthly 100 USD
commitment and one annual 1200 USD commitment. Independently specified total:
200.00 MRR, 2400.00 ARR on 2026-06-01.

46 pytest cases cover explicit monthly/annual values, expansion/contraction snapshots,
zero amount, annual normalization, half-even ties, aggregate totals, future/expired/
cancelled/one-time exclusions, start inclusion, unsupported classifications, malformed
values/dates, missing amounts, duplicate IDs, references, organizations, precision,
overlapping commitments, identities, parents, currency separation, Decimal context
isolation, repeatability, ARR identity, order-independent metrics, lineage, CLI,
malformed JSON, path containment and empty eligibility. These are 46 test cases,
not 50 independently specified end-to-end SaaS scenarios.

Executed: 46 passed. Mutation checks temporarily removed annual normalization:
10 failed / 36 passed. Changing ARR multiplier to 11: 10 failed / 36 passed.
Both mutants were restored; full suite rerun. No coverage percentage claimed.
Hypothesis is an optional test dependency but was unavailable locally; no Hypothesis
or stochastic property tests were run. No network installation attempted.


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


## Contract comparison slice

retention.py adds contract_retention_v1 with opening-cohort NRR/GRR, logo and revenue
churn, expansion/contraction and a balanced ARR bridge. See RETENTION.md for formulas,
rounding residual and explicit completeness assertion. Earlier statements that these
metrics are unimplemented are superseded here; acquisition cohort matrices remain absent.
CLI compare preserves source SHA-256 and source record/evidence IDs; saved comparison
replay is not implemented. Currency migrations and endpoint validation exceptions block
metrics. Empty opening cohorts return null ratios with provisional bridge amounts.

Checked-in retention.json has four synthetic customer histories with hand-derived
expectations in retention_expected.json. New tests cover retained/expanded/contracted/
churned/zero customers, new-cohort exclusion, empty denominators, completeness, date
ordering, currency migration/separation, exception propagation, rounding, lineage,
repeatability, CLI and bridge invariants. This is not a 50-scenario financial benchmark.

Final local suite: 89 passed (29 comparison cases plus 60 previous cases). Deliberately
including new customer revenue in NRR caused 8 comparison failures / 19 passes before
two final lineage/definition regressions were added. The mutation was restored.
Zero-valued closing commitments remain in movement lineage even when the paying logo
is classified as churn. Comparison definitions cannot be silently selected as snapshots.
