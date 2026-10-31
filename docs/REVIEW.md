# Adversarial review of this slice

Annual normalization and ARR multiplier defect checks both produced test failures.
Duplicate IDs and multiple active commitments block double counting; unmarked duplicate
customers remain undetectable. Missing customer/evidence references block metrics.
Identity mappings and unsupported classes require review. Values remain Decimal and
calculations isolate ambient precision/rounding. Currency totals remain separate.
Source records are retrievable against a matching dataset digest, but source file
hash assertions are not verified. Fixed reporting precision is explicitly provisional.
No workbook exists, so Excel formulas and recalculation have not been validated.

Repeatability is verified for identical datasets and Decimal contexts. Run IDs include
methodology and engine version. Different record order can change provenance hashes.
No retained immutable snapshot exists; caller-controlled data authenticity and
completeness are open risks. The implementation does not claim independent validation.


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
