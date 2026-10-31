# Contract retention v1

The calculation uses one complete-history dataset at opening and closing dates and
the unchanged contract_snapshot_v1 eligibility rules. Customer IDs must be stable;
identity mappings, unresolved overlapping commitments and unsupported classifications
block both endpoint comparisons. Dates must be strictly increasing.
Completeness is an explicit caller assertion, not verification by the engine.

For each original currency, use positive unrounded MRR at opening as the cohort.
Let O be opening MRR, X expansion from existing customers, C contraction among
retained customers, L full churn and N ending MRR from customers outside the opening
cohort. Zero-MRR customers are not active logos. Missing active contracts imply zero
only under the completeness assertion. An explicitly zero ending commitment means
loss of the paying logo under this definition.

- GRR = (O - C - L) / O.
- NRR = (O - C - L + X) / O. N is excluded.
- Gross revenue churn = (C + L) / O.
- Net revenue churn = (C + L - X) / O; negative churn is valid.
- Logo churn = lost positive-MRR opening customers / positive-MRR opening customers.

Ratios are fractions rounded half-even to eight decimals; money is decimal text,
rounded to two decimals for display. GRR cannot exceed one; NRR may exceed one.
Empty opening cohorts yield null ratios and EMPTY_OPENING_COHORT review exceptions;
amounts and bridge remain explicitly provisional. A completely empty set of both
snapshots yields an empty currency map. No missing ratio is replaced by zero.

ARR bridge: closing = opening + new + expansion - contraction - churn + rounding
residual. Endpoints use existing snapshot ARR (12 times rounded aggregate MRR).
Movement ARR is twelve times unrounded monthly movement, rounded to cents. An explicit
residual balances these policies; it is not an unexplained accounting adjustment.
For a 100-to-200 annual commitment, opening ARR is 99.96, closing ARR 200.04,
expansion ARR 100.00 and residual 0.08. Ratios use unrounded amounts.
Displayed customer rows can have their own rounding differences from aggregate amounts.

A customer currency change blocks the comparison because conversion could otherwise
masquerade as churn/new revenue. Customer IDs absent at opening but present at closing
are labelled new_to_opening_cohort: this includes reactivations and is not a claim of
lifetime new-logo acquisition. Endpoint comparisons cannot detect churn and reactivation
between endpoints or all intervening events. No annualization of retention ratios occurs.

Every movement includes the contributing endpoint contract IDs and evidence IDs.
Result includes input digest, both snapshot run IDs, comparison definition/version,
engine version, policy and complete-history assertion. External evidence-file hashes
remain unverified. No acquisition-cohort matrix or independent reconciliation is supplied.


## Billing, exact rates and saved jobs

billing_retention_v1 applies the same opening-cohort formulas to billing_v1 endpoints.
Exact rational rate numerators/denominators avoid repeating-division tie drift. Displayed
money remains Decimal rounded half-even to cents. Billing source line/credit IDs and
both endpoint evidence references are retained. Simultaneous currencies or currency
migration for a customer require review. The compare CLI now supports --save and replay
by storage ID through the typed application/store lifecycle.

First-observed cohort reports use positive eligible acquisition-month-end baselines and
subsequent month ends, with a 240-month bound. They require complete-history assertion,
retain baseline/current snapshot IDs and source references, and do not claim verified
lifetime acquisition. Empty initial month-end baselines are review exceptions. Pure endpoint
retention and cohort matrices measure different boundaries; they are not interchangeable.
