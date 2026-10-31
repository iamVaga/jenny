# Data contract

All record models reject extra fields and are frozen. IDs are nonempty strings,
dates are ISO calendar dates, periods use inclusive start and exclusive end.
Currencies are three uppercase letters, not an ISO currency registry check.
Amounts accept Decimal, integer, or decimal strings; binary floats and booleans
are rejected. Amounts must be finite. Input precision is preserved in source models.
The engine supports at most 28 amount digits and scale 12; larger values trigger review.
Cadence is exactly one or twelve months. Contract amount is the net fixed commitment
for one cadence, after contractual discounts and excluding taxes and variable fees.
Contract start/end are effective dates, distinct from invoice dates, line service
periods, payment dates and adjustment recognition periods.

All 18 requested schemas are in models.py. Non-dataset schemas are preliminary and
are not integrated or independently reconciled. Source invoices may carry negative
amounts for future validation; they cannot enter this calculation dataset.
No management-reported figures are accepted or inferred in this slice.

Customers belong to one organization. Duplicate IDs, missing customer/evidence
references, parent relationships and every explicit identity mapping block calculation.
Even approved mappings require a future resolution policy. Renames, duplicate entities
under different IDs, subsidiaries and resellers are never automatically merged.
Duplicate entities without explicit mappings cannot yet be detected.
Multiple active fixed commitments for one customer block calculation because the
engine cannot distinguish additive subscriptions from superseding amendments.
No missing required amount is replaced with zero. Explicit zero commitments are valid.
An empty eligible set yields an empty currency map, not an invented currency total.
