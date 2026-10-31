# Adversarial engineering review

Financial findings corrected in this implementation:
- Repeating Decimal divisions could drift across exact half-cent ties. Contract, billing,
  retention and cohort rate aggregation now use exact rational intermediates and explicit
  half-even rounding; monetary source/output values remain Decimal. Three annual 0.02
  commitments are a regression fixture: aggregate MRR is exactly 0.005, rounded to 0.00.
- Currency-scoped source retrieval previously risked missing snapshot records; it now
  traverses only the requested currency, retains typed record references, and includes
  source invoices of contributing lines/credits.
- Billing/control differences must preserve sub-cent precision. Reconciliation now retains
  exact amounts and signs for balancing and evaluates exact materiality before formatting.
- An unreconciled control must not disappear into an apparently healthy report. Application
  review status and a structured reconciliation exception now propagate to the workbook.
- Untrusted source strings must not become Excel formulas. Literal cells are explicitly typed
  as strings; only internal Formula values create formulas. No external-file links or macros.
- Source JSON/evidence lists were clipped in initial workbook previews. Source fields are now
  separate rows; wrapped text rows and widths were adjusted, with explicit size/precision refusal.
- Identity approval and completeness must not accept truthy strings. Source fields use strict
  booleans, calendar dates reject epoch numbers, cycles/conflicting mappings block calculation.
- Excessive input exponents are rejected before arithmetic. Linked contract and billing net
  rates are checked by service window, preventing price contradictions and economic double counts.

Double counting: duplicate IDs are blocked, contract overlaps require review, linked billing
rates must agree with contractual commitments, refunds linked to credits do not deduct twice,
and new-to-opening-cohort revenue is excluded from NRR. Explicit alias resolution retains
transformation records and revalidates canonical customer references/overlaps.

Dates/rounding/FX: half-open service/effective periods, exclusive cancellation, explicit
normalization, exact-date direct reporting rates and original-currency retention are documented.
No recognition, tax, FX-neutral retention or acquisition-completeness assumptions are inferred.

Reproducibility: identical bytes/config/version reproduce financial results; saved requests,
results and source bytes are hashed and verified by actual recalculation. Tampered input,
request, result and manifest tests cover rejection. Requirements pin the verified runtime/test
versions. Old-engine replay requires the matching source version; cross-version migration is
not silently attempted. No real confidential data or unnecessary outbound runtime requests.

Workbook verification: all 13 required tabs, source string typing, formula references, original
precision, non-overwrite behavior, macro absence and full CLI lifecycle were tested. Bundled
spreadsheet recalculation returned ARR 5160 from its monthly input and zero bridge balance;
the formula error scan found no errors and all 13 sheets were rendered/reviewed. Recalculation
of representative MRR/bridge input changes was checked on a disposable imported workbook.
Native Excel behavior was not certified; formulas do not rerun the Python model.

Known open concerns are explicit in SECURITY.md and LIMITATIONS.md: local privileged tampering,
source authenticity/completeness, path races/resource exhaustion, analyst policy approval,
unsupported parent/reseller/usage/hybrid treatment, and precision/size limits. Passing tests
and synthetic controls do not establish production readiness or independently validate ARR.
