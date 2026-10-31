# Evidence lineage and saved replay

Results identify contributing contract and evidence IDs per currency.
`contributing_records` verifies the dataset digest before returning contract records.
Run ID includes the parsed dataset hash, date, definition, policy and engine version.
CLI additionally hashes exact input bytes. Save uses a storage ID derived from both
calculation ID and raw input hash, so differently formatted source files cannot collide
merely because they parse to identical inputs.

`analyze --save` writes input.json, result.json and manifest.json in a completed run
directory under outputs/runs, using a staging-directory rename. Existing runs are
verified and reused; never modified by this API. `replay --run-id <storage_id>` checks
hashes, parses the retained source, recalculates with the current engine and rejects any
result or version drift. It does not load arbitrary historical engine versions.

This provides retained exact-input snapshots and replay verification. It is not an
OS-enforced immutable store or cryptographically authenticated provenance. A privileged
local actor can change files and hashes; replay detects mismatches with the current
engine but cannot establish original authenticity. Historical versions should be
replayed using the matching source version in an isolated checkout.

Lineage is at contract-record reference level, not cell level. Evidence filenames,
record IDs and hashes are caller assertions; referenced external evidence files are
not opened or verified. Sample evidence uses explicit zero hashes as synthetic markers.


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
