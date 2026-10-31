"""Versioned opening-cohort comparison of contract snapshots, without FX conversion."""
import hashlib
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from .arithmetic import money as exact_money, ratio as exact_ratio
from .engine import calculate
from .models import Dataset

DEFINITION = "contract_retention_v1"
POLICY = "Positive opening MRR cohort; endpoint changes; new logos excluded from NRR; complete contract history asserted; no FX; monetary movements rounded half-even to 0.01 with explicit bridge rounding residual; ratios are fractions rounded to 8 decimals"


def compare(dataset: Dataset, opening: date, closing: date, *, complete_history: bool = False, basis: str = "contract") -> dict:
    if basis not in ("contract", "billing"):
        raise ValueError("Unsupported retention basis")
    calculator = calculate
    if basis == "billing":
        from .billing import calculate as calculator
    definition = DEFINITION if basis == "contract" else "billing_retention_v1"
    first = calculator(dataset, opening)
    last = calculator(dataset, closing)
    run_id = hashlib.sha256(f"{first['run_id']}|{last['run_id']}|{definition}|{POLICY}|{complete_history}".encode()).hexdigest()
    exceptions = []
    if opening >= closing:
        exceptions.append({"code": "INVALID_COMPARISON_DATES", "record_id": "comparison", "reason": "Opening must precede closing"})
    if not complete_history:
        exceptions.append({"code": "INCOMPLETE_HISTORY", "record_id": "comparison", "reason": "Confirm complete customer and contract history for both dates; absence cannot otherwise mean zero"})
    for endpoint, snapshot in (("opening", first), ("closing", last)):
        exceptions.extend(dict(e, endpoint=endpoint) for e in snapshot["exceptions"])
    result = {"run_id": run_id, "definition": definition, "policy": POLICY,
              "engine_version": first["engine_version"], "input_sha256": first["input_sha256"],
              "opening_date": opening.isoformat(), "closing_date": closing.isoformat(),
              "opening_run_id": first["run_id"], "closing_run_id": last["run_id"],
              "complete_history_asserted": complete_history,
              "status": "REQUIRES_REVIEW", "exceptions": exceptions, "metrics": None,
              "lineage_granularity": first["lineage_granularity"]}
    if exceptions:
        return result
    with localcontext() as ctx:
        ctx.prec = 60
        ctx.rounding = ROUND_HALF_EVEN
        def endpoint(snapshot):
            if basis == "billing":
                from types import SimpleNamespace
                rows = {}
                for row in snapshot['customers']:
                    customer = row['customer_id']
                    if customer in rows:
                        exceptions.append({'code':'MULTI_CURRENCY_CUSTOMER','record_id':customer,'reason':'Customer has simultaneous currencies; retention policy requires review'})
                    rows[customer] = SimpleNamespace(customer_id=customer,currency=row['currency'],amount=Decimal(row['mrr']),cadence_months=1,rate=Fraction(int(row['mrr_numerator']),int(row['mrr_denominator'])),
                        source_contract_ids=[],source_line_ids=row['line_item_ids'],source_credit_ids=row['credit_note_ids'],evidence_ids=row['evidence_ids'])
                return rows
            ids = {cid for m in snapshot["metrics"].values() for cid in m["contract_ids"]}
            return {c.customer_id: c for c in dataset.contracts if c.id in ids}
        opening_records, closing_records = endpoint(first), endpoint(last)
        old = {key: c for key, c in opening_records.items() if c.amount > 0}
        new = {key: c for key, c in closing_records.items() if c.amount > 0}
        for customer in sorted(old.keys() & new.keys()):
            if old[customer].currency != new[customer].currency:
                exceptions.append({"code": "CUSTOMER_CURRENCY_CHANGE", "record_id": customer,
                                   "reason": "Currency migration requires an approved FX/retention policy"})
        if exceptions:
            return result
        def monthly(contract):
            return (contract.rate if basis == "billing" else Fraction(contract.amount)/contract.cadence_months) if contract else Fraction(0)
        def money(value):
            return exact_money(value)
        def ratio(value, denominator):
            return exact_ratio(value,denominator)
        currencies = sorted(set(first["metrics"]) | set(last["metrics"]))
        metrics = {}
        for currency in currencies:
            opening_total = ending_total = expansion = contraction = churn = new_revenue = Fraction(0)
            opening_logos = lost_logos = 0
            movements = []
            for customer in sorted(old.keys() | new.keys()):
                a, b = old.get(customer), new.get(customer)
                if (a or b).currency != currency:
                    continue
                av, bv = monthly(a), monthly(b)
                opening_total += av
                ending_total += bv
                if av > 0:
                    opening_logos += 1
                    if bv == 0:
                        kind = "churn"
                        churn += av
                        lost_logos += 1
                    elif bv > av:
                        kind = "expansion"
                        expansion += bv - av
                    elif bv < av:
                        kind = "contraction"
                        contraction += av - bv
                    else:
                        kind = "retained"
                else:
                    kind = "new_to_opening_cohort"
                    new_revenue += bv
                records = [c for c in (opening_records.get(customer), closing_records.get(customer)) if c is not None]
                movements.append({"customer_id": customer, "movement": kind,
                                  "opening_mrr": money(av), "closing_mrr": money(bv),
                                  "contract_ids": sorted({cid for c in records for cid in (c.source_contract_ids if basis == "billing" else [c.id])}),
                                  "line_item_ids": sorted({lid for c in records for lid in (c.source_line_ids if basis == "billing" else [])}),
                                  "credit_note_ids": sorted({cid for c in records for cid in (c.source_credit_ids if basis == "billing" else [])}),
                                  "evidence_ids": sorted({eid for c in records for eid in (c.evidence_ids if basis == "billing" else [c.evidence_id])})})
            gross_loss = churn + contraction
            opening_arr = Decimal(first["metrics"].get(currency, {"arr": "0"})["arr"])
            closing_arr = Decimal(last["metrics"].get(currency, {"arr": "0"})["arr"])
            # Round component annualized changes and expose the residual required to
            # reconcile to the independently rounded snapshot ARR endpoints.
            bridge = {"opening_arr": str(opening_arr), "new_arr": money(new_revenue * 12),
                      "expansion_arr": money(expansion * 12), "contraction_arr": money(contraction * 12),
                      "churn_arr": money(churn * 12), "closing_arr": str(closing_arr)}
            implied = opening_arr + Decimal(bridge["new_arr"]) + Decimal(bridge["expansion_arr"]) - Decimal(bridge["contraction_arr"]) - Decimal(bridge["churn_arr"])
            bridge["rounding_residual_arr"] = money(closing_arr - implied)
            metrics[currency] = {"opening_mrr": money(opening_total), "closing_mrr": money(ending_total),
                "expansion_mrr": money(expansion), "contraction_mrr": money(contraction),
                "churn_mrr": money(churn), "new_mrr": money(new_revenue),
                "grr": ratio(opening_total - gross_loss, opening_total),
                "nrr": ratio(opening_total - gross_loss + expansion, opening_total),
                "gross_revenue_churn": ratio(gross_loss, opening_total),
                "net_revenue_churn": ratio(gross_loss - expansion, opening_total),
                "opening_logos": opening_logos, "lost_logos": lost_logos,
                "logo_churn": ratio(Decimal(lost_logos), Decimal(opening_logos)),
                "arr_bridge": bridge, "customer_movements": movements}
            if opening_total == 0:
                exceptions.append({"code": "EMPTY_OPENING_COHORT", "record_id": currency,
                                   "reason": "Retention and churn ratios are undefined; bridge remains provisional"})
        result["metrics"] = metrics
        result["status"] = "REQUIRES_REVIEW" if exceptions else "CALCULATED_UNRECONCILED"
    return result
