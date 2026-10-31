# Experimental metric definition

`contract_snapshot_v1` measures fixed recurring commitments active on a date:
start <= date < end, and date < cancellation date when present.
Monthly amount / 1; annual amount / 12. Sum by original currency, round currency
MRR to 0.01 using ROUND_HALF_EVEN, then ARR = 12 * rounded MRR.
This makes the displayed ARR/MRR identity exact but can differ from the annual
commitment: 100 annual -> 8.33 MRR -> 99.96 ARR. No FX aggregation occurs.
The fixed two-decimal reporting policy is provisional; it is not a claim that all
currencies have two minor-unit digits. Original amounts retain their precision.

One-time commitments are excluded. Active usage, hybrid and unknown classifications
block calculation. No prorating is performed. Expansions or contractions require
nonoverlapping effective commitments; multiple concurrent commitments require review.
Credits/refunds do not alter contractual MRR automatically. Billing, recognized revenue,
cash, and accounting revenue are outside this definition. ARR is a run-rate, not revenue.

Before financial reliance, decide between: (1) rounded displayed MRR times twelve
(current experimental policy), and (2) separately rounded unrounded MRR/annualized
commitment totals. Also decide currency minor units, amendment treatment and contract
eligibility rules. This slice chooses neither policy as universally authoritative.
Changing methodology requires a new definition ID; its ID and policy enter the run hash.
Billing definition B, retention, churn, cohorts and ARR bridges remain unimplemented.
