"""Billing run-rate definition, distinct from billed and recognized revenue."""
import hashlib
from decimal import Decimal
from datetime import date
from fractions import Fraction
from . import __version__
from .models import Dataset
from .arithmetic import financial_context, money, issue, decimal_rate
from .validation import validate

DEFINITION = 'billing_v1'
POLICY = 'Eligible issued fixed recurring lines active in [service_start,service_end); net amount divided by explicit normalization_months; taxes excluded; matched credits optionally deducted; matched cash refunds not deducted twice; original currency retained'


def calculate(dataset: Dataset, as_of: date) -> dict:
    errors = validate(dataset)
    digest = hashlib.sha256(dataset.model_dump_json().encode()).hexdigest()
    run_id = hashlib.sha256(f'{digest}|{as_of}|{DEFINITION}|{__version__}|{POLICY}'.encode()).hexdigest()
    result = {'run_id':run_id,'input_sha256':digest,'measurement_date':as_of.isoformat(),
              'definition':DEFINITION,'engine_version':__version__,'policy':POLICY,
              'status':'REQUIRES_REVIEW' if errors else 'CALCULATED_UNRECONCILED',
              'exceptions':errors,'metrics':None,'customers':[],
              'lineage_granularity':'Invoice-line and matched credit record IDs; external evidence file hashes are caller assertions'}
    if errors:
        return result
    invoices = {r.id:r for r in dataset.invoices}
    totals, customers = {}, {}
    with financial_context():
        for line in sorted(dataset.line_items,key=lambda r:r.id):
            invoice = invoices[line.invoice_id]
            if line.classification != 'fixed_recurring' or invoice.invoice_date > as_of or not line.service_start <= as_of < line.service_end:
                continue
            credits = [c for c in dataset.credit_notes if c.line_item_id == line.id and c.issue_date <= as_of]
            credit_amount = sum((c.amount for c in credits),Decimal(0)) if dataset.billing_policy.credits == 'deduct' else Decimal(0)
            amount = Fraction(line.amount-line.discount-credit_amount)/Fraction(line.normalization_months)
            key = (invoice.customer_id,line.currency)
            row = customers.setdefault(key,{'customer_id':invoice.customer_id,'currency':line.currency,'mrr':Fraction(0),
                'line_item_ids':[],'contract_ids':[],'credit_note_ids':[],'evidence_ids':[]})
            row['mrr'] += amount
            row['line_item_ids'].append(line.id)
            row['credit_note_ids'].extend(c.id for c in credits if dataset.billing_policy.credits == 'deduct')
            row['evidence_ids'].append(line.evidence_id)
            row['evidence_ids'].append(invoice.evidence_id)
            row['evidence_ids'].extend(c.evidence_id for c in credits if dataset.billing_policy.credits == 'deduct')
            total = totals.setdefault(line.currency,{'mrr':Fraction(0),'line_item_ids':[],'evidence_ids':[]})
            total['mrr'] += amount
            total['line_item_ids'].append(line.id)
            total['evidence_ids'].extend(row['evidence_ids'])
        result['metrics'] = {}
        for currency,row in sorted(totals.items()):
            mrr = Decimal(money(row['mrr']))
            result['metrics'][currency] = {'mrr':money(mrr),'arr':money(mrr*12),
                'line_item_ids':sorted(row['line_item_ids']),'evidence_ids':sorted(set(row['evidence_ids']))}
        for key,row in sorted(customers.items()):
            row['mrr_numerator'] = str(row['mrr'].numerator)
            row['mrr_denominator'] = str(row['mrr'].denominator)
            row['mrr'] = str(decimal_rate(row['mrr']))  # display approximation; exact ratio also retained
            row['evidence_ids'] = sorted(set(row['evidence_ids']))
            result['customers'].append(row)
    return result


def convert_reporting(dataset: Dataset, result: dict, currency: str, as_of: date) -> dict:
    """Exact date direct FX, only as an additional reporting view, never a source replacement."""
    if result.get('metrics') is None:
        return result
    rates = {}
    for row in dataset.currency_rates:
        if row.rate_date == as_of and row.target_currency == currency:
            rates.setdefault(row.source_currency,[]).append(row)
    errors = []
    converted = Decimal(0)
    evidence = []
    with financial_context():
        for source, row in result['metrics'].items():
            rate = Decimal(1)
            if source != currency:
                candidates = rates.get(source,[])
                if len(candidates) != 1:
                    errors.append(issue('MISSING_OR_AMBIGUOUS_FX',source,'Exactly one direct FX rate is required on measurement date'))
                    continue
                rate = candidates[0].rate
                evidence.append(candidates[0].evidence_id)
            converted += Decimal(row['mrr'])*rate
        result['reporting_currency'] = currency
        result['reporting_metrics'] = None if errors else {'mrr':money(converted),'arr':money(Decimal(money(converted))*12),
            'evidence_ids':sorted(set(evidence)), 'policy':'Convert rounded source MRR at exact-date direct rates; half-even cents; ARR = displayed MRR * 12'}
    if errors:
        result['exceptions'].extend(errors)
        result['status'] = 'REQUIRES_REVIEW'
    return result
