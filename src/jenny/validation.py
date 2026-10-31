"""Cross-record validation and explicit, approved identity resolution."""
from collections import defaultdict
from decimal import Decimal
from fractions import Fraction
from .models import Dataset
from .arithmetic import issue, financial_context


def resolve_identities(dataset: Dataset) -> tuple[Dataset, list[dict], list[dict]]:
    errors, transformations = [], []
    customers = {c.id for c in dataset.customers}
    mapping = {}
    for row in dataset.mappings:
        if not row.approved or row.relationship not in ('rename','duplicate') or row.canonical_customer_id not in customers or row.source_customer_id not in customers:
            errors.append(issue('IDENTITY_REVIEW', row.id, 'Requires approved rename/duplicate with known customer IDs'))
            continue
        if row.source_customer_id in mapping and mapping[row.source_customer_id] != row.canonical_customer_id:
            errors.append(issue('CONFLICTING_IDENTITY', row.id, 'Source identity has conflicting canonical targets'))
        mapping[row.source_customer_id] = row.canonical_customer_id
    resolved = {}
    for source in sorted(mapping):
        seen, target = {source}, mapping[source]
        while target in mapping and target not in seen:
            seen.add(target)
            target = mapping[target]
        if target in seen:
            errors.append(issue('CYCLIC_IDENTITY',source,'Identity mapping contains a cycle'))
        else:
            resolved[source] = target
            transformations.append({'step':'approved_identity_mapping','source_id':source,'canonical_id':target})
    if errors:
        return dataset, errors, transformations
    updates = {name: tuple(r.model_copy(update={'customer_id':resolved.get(r.customer_id,r.customer_id)}) for r in getattr(dataset,name)) for name in ('contracts','invoices')}
    updates['mappings'] = ()
    return dataset.model_copy(update=updates), [], transformations


def validate(dataset: Dataset) -> list[dict]:
    errors = []
    collections = ('customers','contracts','evidence','mappings','invoices','line_items','credit_notes','refunds','currency_rates','adjustments','accounting_periods','controls','management_metrics')
    for name in collections:
        seen = set()
        for record in getattr(dataset,name):
            if record.id in seen:
                errors.append(issue('DUPLICATE_ID',record.id,f'Duplicate {name} identifier'))
            seen.add(record.id)
            for value in record.__dict__.values():
                if isinstance(value,Decimal) and (len(value.as_tuple().digits)>28 or value.as_tuple().exponent < -12 or value.as_tuple().exponent > 12):
                    errors.append(issue('AMOUNT_PRECISION',record.id,'Financial inputs support 28 digits and scale 12'))
    if any(e['code']=='AMOUNT_PRECISION' for e in errors):
        return errors  # reject extreme exponents before any arithmetic or ratio allocation
    evidence = {e.id for e in dataset.evidence}
    customers = {c.id for c in dataset.customers}
    invoices = {r.id:r for r in dataset.invoices}
    lines = {r.id:r for r in dataset.line_items}
    contracts = {r.id:r for r in dataset.contracts}
    credits = {r.id:r for r in dataset.credit_notes}
    for name in collections:
        for row in getattr(dataset,name):
            if hasattr(row,'evidence_id') and row.evidence_id not in evidence:
                errors.append(issue('MISSING_EVIDENCE',row.id,'Evidence reference does not exist'))
            if hasattr(row,'organization_id') and row.organization_id != dataset.organization.id:
                errors.append(issue('ORGANIZATION_MISMATCH',row.id,'Organization does not match dataset'))
            if hasattr(row,'customer_id') and row.customer_id not in customers:
                errors.append(issue('MISSING_CUSTOMER',row.id,'Customer does not exist'))
    for customer in dataset.customers:
        if customer.parent_id is not None:
            errors.append(issue('IDENTITY_REVIEW',customer.id,'Parent/subsidiary aggregation needs an approved policy'))
    grouped = defaultdict(list)
    for line in dataset.line_items:
        invoice = invoices.get(line.invoice_id)
        grouped[line.invoice_id].append(line)
        if invoice is None:
            errors.append(issue('MISSING_INVOICE',line.id,'Invoice line has no parent invoice'))
        elif line.currency != invoice.currency:
            errors.append(issue('CURRENCY_MISMATCH',line.id,'Invoice and line currencies differ'))
        if line.classification == 'fixed_recurring' and (line.service_start is None or line.service_end is None or line.normalization_months is None):
            errors.append(issue('MISSING_SERVICE_PERIOD',line.id,'Recurring line requires service dates and explicit normalization months'))
        if line.classification in ('unknown','hybrid'):
            errors.append(issue('CLASSIFICATION_REVIEW',line.id,'Unknown/hybrid lines must be explicitly split or reclassified'))
        if line.classification == 'usage' and dataset.billing_policy.usage == 'review':
            errors.append(issue('USAGE_POLICY_REVIEW',line.id,'Usage must be excluded explicitly or resolved before calculation'))
        if line.contract_id:
            contract = contracts.get(line.contract_id)
            if contract is None:
                errors.append(issue('MISSING_CONTRACT',line.id,'Linked contract does not exist'))
            elif invoice and (contract.customer_id != invoice.customer_id or contract.currency != line.currency or contract.classification != line.classification or (line.service_start and line.service_start < contract.start) or (line.service_end and line.service_end > min(contract.end,contract.cancelled_on or contract.end))):
                errors.append(issue('CONTRACT_INVOICE_CONFLICT',line.id,'Linked contract contradicts customer, currency, classification or service period'))
    linked_rates = defaultdict(Fraction)
    for line in dataset.line_items:
        contract = contracts.get(line.contract_id)
        if contract and contract.classification == line.classification == 'fixed_recurring' and line.normalization_months is not None:
            linked_rates[(contract.id,line.service_start,line.service_end)] += (Fraction(line.amount)-Fraction(line.discount))/Fraction(line.normalization_months)
    for (contract_id,start,end), rate in linked_rates.items():
        contract=contracts[contract_id]
        if rate != Fraction(contract.amount)/contract.cadence_months:
            errors.append(issue('CONTRACT_PRICE_CONFLICT',contract_id,'Linked net billing rates differ from the contractual commitment for a service window'))
    with financial_context():
        for invoice in dataset.invoices:
            if invoice.amount < 0:
                errors.append(issue('NEGATIVE_INVOICE',invoice.id,'Negative invoices require explicit credit-note classification'))
            if invoice.id not in grouped:
                errors.append(issue('MISSING_INVOICE_LINES',invoice.id,'Invoice has no independently specified lines'))
            elif sum((l.amount-l.discount+l.tax for l in grouped[invoice.id]),Decimal(0)) != invoice.amount:
                errors.append(issue('INVOICE_TOTAL_MISMATCH',invoice.id,'Gross invoice does not equal net lines plus taxes'))
        credits_by_line = defaultdict(Decimal)
        refunds_by_credit = defaultdict(Decimal)
        for credit in dataset.credit_notes:
            invoice = invoices.get(credit.invoice_id)
            line = lines.get(credit.line_item_id)
            if invoice is None:
                errors.append(issue('UNMATCHED_CREDIT',credit.id,'Credit invoice does not exist'))
            elif credit.issue_date < invoice.invoice_date:
                errors.append(issue('CREDIT_DATE_REVIEW',credit.id,'Credit predates its invoice'))
            elif invoice.currency != credit.currency:
                errors.append(issue('CURRENCY_MISMATCH',credit.id,'Credit and invoice currencies differ'))
            if line is None or line.invoice_id != credit.invoice_id:
                errors.append(issue('UNMATCHED_CREDIT',credit.id,'Credit requires a matching invoice line'))
            else:
                credits_by_line[line.id] += credit.amount
        for line_id, amount in credits_by_line.items():
            if amount > lines[line_id].amount-lines[line_id].discount:
                errors.append(issue('EXCESS_CREDIT',line_id,'Credits exceed the net source line amount'))
        for refund in dataset.refunds:
            credit = credits.get(refund.credit_note_id)
            if credit is None or credit.invoice_id != refund.invoice_id:
                errors.append(issue('UNMATCHED_REFUND',refund.id,'Cash refunds require a matched credit; do not double deduct'))
            elif refund.payment_date < credit.issue_date:
                errors.append(issue('REFUND_DATE_REVIEW',refund.id,'Refund predates its credit'))
            elif credit.currency != refund.currency:
                errors.append(issue('CURRENCY_MISMATCH',refund.id,'Refund and credit currencies differ'))
            else:
                refunds_by_credit[credit.id] += refund.amount
        for credit_id, amount in refunds_by_credit.items():
            if amount > credits[credit_id].amount:
                errors.append(issue('EXCESS_REFUND',credit_id,'Cash refunds exceed the matched credit'))
    by_customer = defaultdict(list)
    for contract in dataset.contracts:
        if contract.classification == 'fixed_recurring':
            by_customer[contract.customer_id].append(contract)
    for rows in by_customer.values():
        furthest_end = None
        for row in sorted(rows,key=lambda r:(r.start,r.id)):
            effective_end = min(row.end,row.cancelled_on or row.end)
            if effective_end <= row.start:
                continue
            if furthest_end is not None and row.start < furthest_end:
                errors.append(issue('OVERLAPPING_COMMITMENTS',row.id,'Unresolved additive versus superseding commitments'))
            furthest_end = max(furthest_end or effective_end,effective_end)
    _, identity_errors, _ = resolve_identities(dataset)
    errors.extend(identity_errors)
    return errors
