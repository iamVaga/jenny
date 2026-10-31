# Current limitations

Implemented: typed contracts, contract-snapshot MRR/ARR, per-currency opening-cohort
retention/churn, movement attribution, ARR bridge, local snapshot persistence and replay
for analyze results. Storage is append-only through the API, not OS-enforced immutable.
Compare results cannot yet be saved/replayed by storage ID.

Still absent: billing-derived metrics and ingestion, recognized revenue, acquisition
cohort matrices, management comparisons, independent accounting reconciliation,
FX conversion, Excel export and a 50-scenario financial benchmark. Preliminary unused
schemas do not imply these features exist. No production security or compliance claims.

All identity mappings and multiple active fixed commitments require review. Unmarked
duplicate customer identities cannot be detected. Currency codes are syntax checked.
External evidence hashes remain assertions. Completeness is caller-declared and cannot
be established from the supplied dataset alone. Historical events between comparison
endpoints are not measured. Reactivations are new to the opening cohort, not necessarily
new acquisitions. See RETENTION.md for treatment of zero commitments and rounding.

Blocking input/identity/FX-policy errors suppress metrics. Empty opening cohorts return
null ratios with review exceptions and provisional bridge amounts. No independent
validation is implied by CALCULATED_UNRECONCILED. Financial policy approval remains
necessary before analyst reliance, including reporting precision and eligibility.
