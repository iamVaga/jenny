# Billing-to-accounting reconciliation

Source = net invoice line amounts by invoice date - net credit notes by issue date in
[start,end). Taxes are excluded; cash receipts/refunds and ARR do not enter this total.
Comparison = exactly one separately supplied accounting control per currency and period.
Complete source/control accounting-period information is required. Missing controls or
incomplete periods never silently become zero or a reconciled status.

Unexplained difference = source + signed explained adjustments - comparison.
Each adjustment is in the same control currency and exact period, with evidence and reason:
deferred_revenue, accrued_revenue, credits, timing, taxes, fx, recognition or other.
Example: net billings 1200, GL 1100 and deferred adjustment -100 reconcile. An accrued
amount of +100 bridges billings 1200 to GL 1300. Adjustments must be supplied, not inferred.
No ARR-to-GL equality assumption is made, and no plug is generated to force a tie.

Statuses per currency:
- RECONCILED: no adjustment and absolute exact difference <= materiality.
- RECONCILED_WITH_ADJUSTMENTS: explained adjustments and difference within materiality.
- UNRECONCILED: valid data but unexplained difference exceeds materiality.
- INSUFFICIENT_DATA: missing control, incomplete period or invalid source relationships.
- REQUIRES_REVIEW: multiple controls or an adjustment categorized as other.

A review result propagates to the application status and structured exception report.
Each result contains source/control totals, comparison basis, individual adjustments,
unexplained difference, threshold, status, contributing record IDs and evidence IDs.
Amounts preserve sub-cent precision for mathematical balancing; thresholds use exact values.
Even a reconciled billing control does not independently validate contractual ARR or establish
authenticity/completeness of source evidence. Caller-supplied controls must be independently
obtained in an actual engagement; demo controls are explicitly synthetic fixtures.
