# Data contract

The 18 original requested record types are defined in models.py, along with
AccountingControl, ManagementMetric, BillingPolicy and the Dataset envelope. Job requests
are validated with application.RunConfig. Unknown fields are rejected; schemas are frozen
and record arrays are tuples. All records need nonempty IDs unique within their type.
Dataset-level duplicate checks cannot be bypassed by dictionaries overwriting records.

Money is finite Decimal text, Decimal, or integer; binary floats and booleans are rejected.
Inputs retain their original currency and precision. Computations reject values with over
28 significant input digits, scale greater than 12 or exponent above 12 before arithmetic.
Currencies use three-uppercase-letter syntax; no external ISO registry is consulted.

Dates are ISO calendar dates. Effective and service intervals are [start,end), distinct
from invoice date, payment date, credit issue date and recognition-adjustment period.
Contracts use net fixed commitments per one-month or twelve-month cadence. Cancellation
is exclusive on its date. Parent organizations and resellers are not implicitly aggregated.

Invoices carry gross amount. Lines carry pre-discount net-of-tax amount, discount, tax,
classification, optional contract link, service_start/service_end and normalization_months.
An invoice must equal sum(line amount - discount + tax). Recurring lines require both
service dates and a positive explicit normalization period. A six-month prepaid amount
of 600 with normalization_months 6 means a monthly run-rate of 100. Fractional months
must be explicitly supplied for prorated service; the engine does not invent them.
One-time and explicitly excluded usage lines never enter MRR. Hybrid/unknown lines
must be split/reclassified. Missing service data produces exceptions, not zero revenue.

Credit notes are net-of-tax reductions and must match invoice and line IDs; total credits
cannot exceed the original net line. A refund must link to a matching credit, currency
and invoice, and total refunds cannot exceed it. Matched refunds are cash movements,
not a second revenue deduction. Credit/refund dates cannot precede their parent records.

Linked recurring invoice lines in one service window must collectively agree with the
contractual net monthly commitment and its customer, currency, classification and effective
period. Unlinked lines are not assumed to have a verified contractual basis. Multiple active
contract commitments require review; billable line components may be additive when valid.

AccountingControl specifies currency, period, basis, amount, materiality and evidence.
AccountingPeriod.complete asserts completeness of source billing and control information
for the full period; JENNY cannot establish that externally. RevenueAdjustment is a signed
period-level bridge in the control currency, with one of the documented reason categories.
Management figures remain separate, with unknown methodology represented explicitly.
