"""First-observed customer acquisition cohorts, never inferred lifetime acquisition."""
from calendar import monthrange
from datetime import date
from decimal import Decimal
from fractions import Fraction
from . import __version__
from .models import Dataset
from .arithmetic import issue, financial_context, money, ratio
from .engine import calculate as contract_snapshot
from .billing import calculate as billing_snapshot


def month_end(value: date) -> date:
    return date(value.year,value.month,monthrange(value.year,value.month)[1])


def next_month(value: date) -> date:
    return date(value.year + (value.month == 12),value.month % 12 + 1,1)


def balances(dataset: Dataset, snapshot: dict, basis: str) -> dict:
    if basis == 'billing':
        return {(r['customer_id'],r['currency']):Fraction(int(r['mrr_numerator']),int(r['mrr_denominator'])) for r in snapshot['customers']}
    ids = {cid for m in snapshot['metrics'].values() for cid in m['contract_ids']}
    return {(c.customer_id,c.currency):Fraction(c.amount)/c.cadence_months for c in dataset.contracts if c.id in ids}


def cohorts(dataset: Dataset, as_of: date, *, basis: str='contract', complete_history: bool=False) -> dict:
    if basis not in ('contract','billing'):
        raise ValueError('Unsupported cohort basis')
    errors = []
    if not complete_history:
        errors.append(issue('INCOMPLETE_HISTORY','cohorts','First-observed cohorts require complete-history assertion'))
    calculator = contract_snapshot if basis == 'contract' else billing_snapshot
    latest = calculator(dataset,as_of)
    errors.extend(latest['exceptions'])
    output = {'engine_version':__version__,'input_sha256':latest['input_sha256'],'definition':f'{basis}_observed_cohorts_v1','measurement_date':str(as_of),
              'policy':'First observed positive fixed-recurring eligibility month, baseline at cohort month-end (or measurement date for current month); subsequent month-end customer and revenue retention; not lifetime acquisition',
              'exceptions':errors,'rows':None,'status':'REQUIRES_REVIEW'}
    if errors:
        return output
    first_seen = {}
    if basis == 'contract':
        for c in dataset.contracts:
            if c.classification == 'fixed_recurring' and c.amount > 0 and c.start <= as_of and c.start < min(c.end,c.cancelled_on or c.end):
                key = (c.customer_id,c.currency)
                first_seen[key] = min(first_seen.get(key,c.start),c.start)
    else:
        invoices = {r.id:r for r in dataset.invoices}
        for line in dataset.line_items:
            invoice = invoices[line.invoice_id]
            if line.classification != 'fixed_recurring' or line.amount-line.discount <= 0:
                continue
            start = max(line.service_start,invoice.invoice_date)
            if start <= as_of and start < line.service_end:
                key = (invoice.customer_id,line.currency)
                first_seen[key] = min(first_seen.get(key,start),start)
    groups = {}
    for key,start in first_seen.items():
        groups.setdefault((start.replace(day=1),key[1]),[]).append(key)
    snapshots = {}
    snapshot_results = {}
    def snapshot(at):
        if at not in snapshots:
            result = calculator(dataset,at)
            snapshot_results[at] = result
            if result['exceptions']:
                errors.extend(dict(e,measurement_date=str(at)) for e in result['exceptions'])
                snapshots[at] = None
            else:
                snapshots[at] = balances(dataset,result,basis)
        return snapshots[at]
    def references(at, members):
        snapshot = snapshot_results[at]
        if basis == 'billing':
            selected = [r for r in snapshot['customers'] if (r['customer_id'],r['currency']) in members]
            return {key:sorted({value for row in selected for value in row.get(key,[])}) for key in ('contract_ids','line_item_ids','credit_note_ids','evidence_ids')}
        ids = {cid for metric in snapshot['metrics'].values() for cid in metric['contract_ids']}
        selected = [c for c in dataset.contracts if c.id in ids and (c.customer_id,c.currency) in members]
        return {'contract_ids':sorted(c.id for c in selected),'line_item_ids':[],'credit_note_ids':[], 'evidence_ids':sorted({c.evidence_id for c in selected})}
    rows = []
    with financial_context():
        for (cohort_month,currency),keys in sorted(groups.items()):
            # Bound temporal expansion for malformed/very old histories.
            if (as_of.year-cohort_month.year)*12 + as_of.month-cohort_month.month > 240:
                errors.append(issue('HISTORY_LIMIT',str(cohort_month),'Cohort reports support at most 240 months'))
                continue
            baseline_at = min(month_end(cohort_month),as_of)
            baseline = snapshot(baseline_at)
            if baseline is None:
                continue
            members = [k for k in keys if baseline.get(k,Fraction(0)) > 0]
            initial = sum((baseline[k] for k in members),Fraction(0))
            if not members:
                errors.append(issue('EMPTY_COHORT_BASELINE',str(cohort_month),'Customers first seen in this month have no positive month-end baseline'))
                continue
            month = cohort_month
            while month <= as_of:
                at = min(month_end(month),as_of)
                current = snapshot(at)
                if current is not None:
                    ending = sum((current.get(k,Fraction(0)) for k in members),Fraction(0))
                    logos = sum(current.get(k,Fraction(0)) > 0 for k in members)
                    rows.append({'cohort_month':str(cohort_month),'measurement_date':str(at),'currency':currency,
                        'opening_logos':len(members),'retained_logos':logos,'logo_retention':ratio(Decimal(logos),Decimal(len(members))),
                        'baseline_mrr':money(initial),'cohort_mrr':money(ending),'revenue_retention':ratio(ending,initial),
                        'customer_ids':sorted(k[0] for k in members),
                        'baseline_run_id':snapshot_results[baseline_at]['run_id'],'measurement_run_id':snapshot_results[at]['run_id'],
                        **{key:sorted(set(references(baseline_at,members)[key]) | set(references(at,members)[key])) for key in ('contract_ids','line_item_ids','credit_note_ids','evidence_ids')}})
                month = next_month(month)
    output['rows'] = rows if not errors else None
    output['status'] = 'REQUIRES_REVIEW' if errors else 'CALCULATED_UNRECONCILED'
    return output
