"""Pure deterministic point-in-time fixed commitment calculation."""
import hashlib
import json
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from . import __version__
from .models import Dataset, ReviewException

DEFINITION = "contract_snapshot_v1"
POLICY = "Active [start,end); cancellation exclusive; fixed net commitments only; no FX; currency MRR rounded half-even to 0.01, ARR = 12 * rounded MRR"


def calculate(dataset: Dataset, as_of: date) -> dict:
    errors: list[ReviewException] = []

    def issue(code, record_id, reason):
        errors.append(ReviewException(code=code, record_id=record_id, reason=reason))

    for records in (dataset.customers, dataset.contracts, dataset.evidence, dataset.mappings):
        seen = set()
        for record in records:
            if record.id in seen:
                issue("DUPLICATE_ID", record.id, "Duplicate identifier within record type")
            seen.add(record.id)
    customers = {c.id for c in dataset.customers}
    evidence = {e.id for e in dataset.evidence}
    for customer in dataset.customers:
        if customer.organization_id != dataset.organization.id:
            issue("ORGANIZATION_MISMATCH", customer.id, "Customer belongs to another organization")
        if customer.parent_id is not None:
            issue("IDENTITY_REVIEW", customer.id, "Parent/subsidiary aggregation needs an approved policy")
    # Identity application is deliberately outside this slice; never silently merge.
    for mapping in dataset.mappings:
        issue("IDENTITY_REVIEW", mapping.id, "Identity mappings require resolution before this engine can run")
    active = []
    for contract in dataset.contracts:
        if contract.customer_id not in customers:
            issue("MISSING_CUSTOMER", contract.id, "Contract customer does not exist")
        if contract.organization_id != dataset.organization.id:
            issue("ORGANIZATION_MISMATCH", contract.id, "Contract belongs to another organization")
        if contract.evidence_id not in evidence:
            issue("MISSING_EVIDENCE", contract.id, "Contract evidence reference does not exist")
        value = contract.amount.as_tuple()
        if len(value.digits) > 28 or value.exponent < -12 or value.exponent > 12:
            issue("AMOUNT_PRECISION", contract.id, "Supported amounts have at most 28 digits and scale 12")
        if not (contract.start <= as_of < contract.end):
            continue
        if contract.cancelled_on is not None and as_of >= contract.cancelled_on:
            continue
        if contract.classification in ("usage", "hybrid", "unknown"):
            issue("UNSUPPORTED_CLASSIFICATION", contract.id, "No approved recurring policy for this classification")
        elif contract.classification == "fixed_recurring":
            active.append(contract)
    # Multiple active commitments could be additive or superseding; require review.
    seen_customers = set()
    for contract in active:
        if contract.customer_id in seen_customers:
            issue("OVERLAPPING_COMMITMENTS", contract.id, "Multiple active commitments need additive/amendment resolution")
        seen_customers.add(contract.customer_id)
    canonical = dataset.model_dump_json()
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    run_id = hashlib.sha256(f"{digest}|{as_of}|{DEFINITION}|{__version__}|{POLICY}".encode()).hexdigest()
    result = {"run_id": run_id, "input_sha256": digest, "measurement_date": as_of.isoformat(),
              "definition": DEFINITION, "engine_version": __version__, "policy": POLICY,
              "status": "REQUIRES_REVIEW" if errors else "CALCULATED_UNRECONCILED",
              "exceptions": [e.model_dump() for e in errors], "metrics": None,
              "lineage_granularity": "source record references supplied by caller; source file hashes not verified"}
    if errors:
        return result
    totals = {}
    with localcontext() as context:
        context.prec = 60
        context.rounding = ROUND_HALF_EVEN
        for contract in sorted(active, key=lambda c: c.id):
            totals[contract.currency] = totals.get(contract.currency, Decimal(0)) + contract.amount / Decimal(contract.cadence_months)
        result["metrics"] = {}
        for currency, total in sorted(totals.items()):
            mrr = total.quantize(Decimal("0.01"))
            result["metrics"][currency] = {"mrr": str(mrr), "arr": str(mrr * 12),
                "contract_ids": sorted(c.id for c in active if c.currency == currency),
                "evidence_ids": sorted({c.evidence_id for c in active if c.currency == currency})}
    return result


def contributing_records(dataset: Dataset, result: dict, currency: str) -> list[dict]:
    """Retrieve contract records only after verifying they match this calculation input."""
    if hashlib.sha256(dataset.model_dump_json().encode()).hexdigest() != result["input_sha256"]:
        raise ValueError("Dataset does not match calculation input")
    ids = result["metrics"][currency]["contract_ids"]
    return [c.model_dump(mode="json") for c in dataset.contracts if c.id in ids]
