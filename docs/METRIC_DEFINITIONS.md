# Versioned financial definitions

The programmatic registry is definitions.metric_definitions(). Definitions and selected
policies, configuration, input hash and engine version are retained with every job.
Neither contract nor billing definition is universally authoritative. Both produce
unreconciled run-rate measurements; recognized revenue is never inferred from MRR.

## contract_snapshot_v1

Include positive/zero fixed recurring net commitments active on the measurement date:
start <= date < end, and date < cancellation if present. Monthly rate = cadence amount
/ cadence_months (1 or 12). Exclude one-time fees. Usage, hybrid and unknown contracts
require review. No intra-month averaging or automatic proration. Expansion/contraction
is represented with nonoverlapping effective commitments. Unresolved overlaps block results.

## billing_v1

Include issued fixed-recurring invoice lines active in their explicit service interval.
Monthly rate = (amount - discount - eligible posted matched credits) / normalization_months.
Exclude taxes and one-time fees. Usage policy is explicitly exclude or review; hybrid
pricing must be split into fixed and usage lines. Missing dates/normalization never fall
back to the invoice date or zero. Credits deduct or exclude according to BillingPolicy;
matched refunds do not deduct again. No recognized-revenue calculation is implied.

## Rounding, retention and reporting FX

Sum exact rates by original currency; half-even MRR to 0.01; ARR = displayed MRR * 12.
For an annual 100 commitment this gives 8.33 MRR and 99.96 ARR. This provisional two-decimal
reporting policy is explicit and does not assert that all currencies have two minor units.
Exact rational intermediates prevent cumulative repeating-division half-cent drift.
For example 3 annual 0.02 commitments sum to 0.005 MRR and round to 0.00, not 0.01.
Original monetary values remain Decimal; rational numerator/denominator is retained for
billing customer rates used by retention. No financial operation uses binary floats.

Retention/churn and first-observed cohort formulas are in RETENTION.md. Ratios are fractions
rounded half-even to eight decimals; NRR may exceed one and net churn may be negative.
Each period uses the selected definition consistently; new-cohort revenue is excluded from NRR.

Snapshot analyze can add reporting-currency MRR using exactly one direct measurement-date
rate per source currency. Rate means target units per source unit. Convert rounded source
MRR, sum, round half-even to cents, then ARR = displayed reporting MRR * 12. Preserve source
currency totals and FX evidence. Missing/duplicate rates require review; no nearest-date,
inverse, triangulated or FX-neutral retention assumptions are silently supplied.

Management claims are separate. A claim matches only when its declared methodology equals
the selected definition and its amount matches the calculation. Unknown methodology or
numeric disagreement requires review; a numerical gap is not proof of a management error.
