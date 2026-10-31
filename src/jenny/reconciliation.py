"""Independent accounting-control reconciliation; ARR never compared to GL revenue."""
from decimal import Decimal
from datetime import date
from .models import Dataset
import hashlib
from . import __version__
from .arithmetic import financial_context, exact_money, issue
from .validation import validate


def reconcile(dataset: Dataset, start: date, end: date) -> dict:
    errors = validate(dataset)
    if end <= start:
        errors.append(issue('INVALID_PERIOD','reconciliation','End must be after start'))
    invoices = {r.id:r for r in dataset.invoices}
    lines = {r.id:r for r in dataset.line_items}
    results = []
    controls = [c for c in dataset.controls if c.start == start and c.end == end]
    periods = [p for p in dataset.accounting_periods if p.start == start and p.end == end]
    complete = len(periods) == 1 and periods[0].complete
    if not complete:
        errors.append(issue('INCOMPLETE_ACCOUNTING_PERIOD','reconciliation','Exactly one complete accounting period must match the requested bounds'))
    currencies = sorted({c.currency for c in controls} | {i.currency for i in dataset.invoices if start <= i.invoice_date < end})
    if not controls:
        errors.append(issue('MISSING_ACCOUNTING_CONTROL','reconciliation','No independently supplied accounting control for this period'))
    with financial_context():
        for currency in currencies:
            matching = [c for c in controls if c.currency == currency]
            selected = [l for l in dataset.line_items if l.currency == currency and l.invoice_id in invoices and start <= invoices[l.invoice_id].invoice_date < end]
            credits = [c for c in dataset.credit_notes if c.currency == currency and start <= c.issue_date < end]
            adjustments = [a for a in dataset.adjustments if a.currency == currency and a.start == start and a.end == end]
            source = sum((l.amount-l.discount for l in selected),Decimal(0)) - sum((c.amount for c in credits),Decimal(0))
            adjustment = sum((a.amount for a in adjustments),Decimal(0))
            control = matching[0] if len(matching)==1 else None
            difference = source + adjustment - control.amount if control else None
            status = 'INSUFFICIENT_DATA'
            if control and complete and not errors:
                if any(a.reason == 'other' for a in adjustments):
                    status = 'REQUIRES_REVIEW'
                elif abs(difference) > control.materiality:
                    status = 'UNRECONCILED'
                else:
                    status = 'RECONCILED_WITH_ADJUSTMENTS' if adjustments else 'RECONCILED'
            elif len(matching) > 1:
                status = 'REQUIRES_REVIEW'
            evidence = {r.evidence_id for r in [*selected,*credits,*adjustments,*matching]}
            results.append({'currency':currency,'period_start':str(start),'period_end':str(end),
                'source_total':exact_money(source),'comparison_total':exact_money(control.amount) if control else None,
                'comparison_basis':control.basis if control else None,'explained_adjustments':exact_money(adjustment),
                'adjustments':[a.model_dump(mode='json') for a in adjustments],
                'unexplained_difference':exact_money(difference) if difference is not None else None,
                'materiality':str(control.materiality) if control else None,'status':status,
                'source_record_ids':sorted([l.id for l in selected]+[c.id for c in credits]),
                'line_item_ids':sorted(l.id for l in selected),'credit_note_ids':sorted(c.id for c in credits),
                'evidence_ids':sorted(evidence)})
    return {'engine_version':__version__,'input_sha256':hashlib.sha256(dataset.model_dump_json().encode()).hexdigest(),'definition':'billing_accounting_reconciliation_v1','period_start':str(start),'period_end':str(end),
        'policy':'Net billed lines by invoice date less credit notes by issue date plus signed adjustments minus independent accounting control; tax excluded; no ARR/GL equality assumption',
        'results':results,'exceptions':errors,
        'status':'RECONCILED' if results and all(r['status'] in ('RECONCILED','RECONCILED_WITH_ADJUSTMENTS') for r in results) else 'REQUIRES_REVIEW'}
