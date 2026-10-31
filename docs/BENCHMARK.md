# Independent benchmark and executed tests

70 named independently specified scenarios are checked into
src/jenny/fixtures/benchmark.json. scripts/build_benchmark.py materializes input fixtures
and literal expected answers; it never calls the production engine to generate expectations.
The installed package exposes these fixtures through `jenny benchmark`, without network access.

Scenarios cover monthly/annual/six-month/quarterly/fractional normalization, explicit zero,
half-even ties, discounts, tax, one-time fees, usage exclusion/review, hybrid/unknown classes,
missing service dates/normalization, duplicate invoices/customers/lines/evidence, missing
references, currency mismatch, negative invoice, invoice balancing, malformed dates/money,
matched/unmatched/excess credits, matched/unmatched refunds, renamed/duplicate customer
resolution, ambiguous/parent/reseller/incorrect identities, parent relationships, direct/missing
FX, clean/unexplained/adjusted/incomplete accounting reconciliations, conflicting unknown
management ARR, future billing, exclusive service ends, clean/cancelled contracts, customer
retention/expansion/contraction/full/partial churn, contract/invoice conflicts, overlaps,
identity cycles/conflicts and original multi-currency totals. Additional hand-calculated
retention fixtures remain in data/retention.json and data/retention_expected.json.

Executed final local suite: 189 passed. This count includes the 70 benchmark cases, the
previous foundation/regression cases and new unit/integration/security/reporting cases.
Three Hypothesis properties exercise recurring normalization/ARR/repeatability, signed
reconciliation balance, and invariance when an annual invoice is split into additive lines.
They use deterministic settings with configured maxima of 75, 60 and 50 examples.
No coverage percentage, customer-testing outcome or universal financial certification is claimed.

Deliberate mutation checks on the 70-case benchmark:
- Removing monthly billing normalization: 14 failed, 56 passed.
- Reversing reconciliation adjustment signs: 2 failed, 68 passed.
Both mutations were restored and the full suite rerun. Earlier slices also detected annual
normalization, ARR multiplier and new-logo-in-NRR mutations, documented in repository history.

The sample full report has closing USD MRR 430.00 / ARR 5160.00. Opening cohort MRR is
300; retained cohort ending MRR 230 gives NRR 230/300 = 0.76666667. Gross retained MRR
180 gives GRR 0.60. One of three opening logos churns. Net billed total 4380 equals the
explicitly independent synthetic control: 1800 first-half invoices + 2580 second-half invoices.
These expected figures are derived independently of production functions.

Packaging was verified by building/installing a local wheel into an isolated target and
running all 70 embedded scenarios from outside the source directory. Spreadsheet package
and formula checks are covered in tests; the demonstration was additionally recalculated
and rendered with the bundled spreadsheet engine. Native Microsoft Excel was not used.
