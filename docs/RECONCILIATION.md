# Reconciliation boundary

There is no reconciliation engine in this slice. The preliminary result schema contains
source and comparison totals, explained adjustments, unexplained difference, materiality,
status and evidence IDs. It does not enforce balancing or validate those values yet.
Successful calculations carry CALCULATED_UNRECONCILED, never independently validated.
Future billing-to-accounting reconciliation must separate taxes, deferrals, accruals,
credits, timing, FX and recognition adjustments; ARR must not be forced to equal GL revenue.
