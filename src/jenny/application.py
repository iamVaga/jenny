"""Typed job configuration and deterministic orchestration of the domain modules."""
import hashlib
import json
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator, StrictBool
from . import __version__
from .models import Dataset, Currency
from .arithmetic import financial_context, money, issue, exact_money
from .engine import calculate as contract_snapshot
from .billing import calculate as billing_snapshot, convert_reporting
from .retention import compare
from .cohorts import cohorts, next_month
from .reconciliation import reconcile
from .validation import validate, resolve_identities
from .ingestion import parse_dataset


class RunConfig(BaseModel):
    model_config = ConfigDict(extra='forbid',frozen=True)
    action: Literal['analyze','compare','cohorts','reconcile','report'] = 'analyze'
    definition: Literal['contract_snapshot_v1','billing_v1'] = 'contract_snapshot_v1'
    as_of: date | None = None
    opening: date | None = None
    closing: date | None = None
    complete_history: StrictBool = False
    reporting_currency: Currency | None = None

    @model_validator(mode='after')
    def dates(self):
        if self.action in ('analyze','cohorts') and self.as_of is None:
            raise ValueError('Measurement date required')
        if self.action in ('compare','reconcile','report') and (self.opening is None or self.closing is None or self.opening >= self.closing):
            raise ValueError('Strictly ordered opening and closing dates required')
        if self.action == 'report' and (self.opening.day != 1 or self.closing.day != 1):
            raise ValueError('Reports use calendar month boundaries, closing exclusive')
        if self.opening and self.closing and (self.closing.year-self.opening.year)*12+self.closing.month-self.opening.month > 240:
            raise ValueError('Reports support at most 240 months')
        if self.reporting_currency and self.action != 'analyze':
            raise ValueError('Reporting currency is supported only for snapshot analyze; period ratios retain original currencies')
        return self


def management_comparisons(dataset: Dataset, snapshot: dict, as_of: date) -> list[dict]:
    rows = []
    with financial_context():
        for claim in dataset.management_metrics:
            if claim.measurement_date != as_of:
                continue
            calculated = (snapshot.get('metrics') or {}).get(claim.currency,{}).get(claim.metric)
            comparable = claim.methodology == snapshot['definition']
            rows.append({'id':claim.id,'currency':claim.currency,'metric':claim.metric,
                'management_amount':str(claim.amount),'calculated_amount':calculated,
                'difference':exact_money(Decimal(calculated)-claim.amount) if calculated is not None else None,
                'methodology':claim.methodology or 'UNKNOWN','status':'MATCHED' if comparable and calculated is not None and Decimal(calculated)==claim.amount else 'REQUIRES_REVIEW',
                'evidence_id':claim.evidence_id})
    return rows


def execute(raw: bytes, config: RunConfig) -> dict:
    original = parse_dataset(raw)
    errors = validate(original)
    dataset, identity_errors, transformations = resolve_identities(original)
    # Validate the resolved customer references and overlaps as well.
    if not identity_errors:
        errors.extend(e for e in validate(dataset) if e not in errors)
    basis = 'billing' if config.definition == 'billing_v1' else 'contract'
    calculator = billing_snapshot if basis == 'billing' else contract_snapshot
    request_hash = hashlib.sha256(config.model_dump_json().encode()).hexdigest()
    raw_hash = hashlib.sha256(raw).hexdigest()
    run_id = hashlib.sha256(f'{raw_hash}|{request_hash}|{__version__}|application_v1'.encode()).hexdigest()
    result = {'run_id':run_id,'source_file_sha256':raw_hash,'input_sha256':hashlib.sha256(original.model_dump_json().encode()).hexdigest(),
        'engine_version':__version__,'request':config.model_dump(mode='json'),'transformations':transformations,
        'definition':config.definition,'exceptions':errors,'status':'REQUIRES_REVIEW','metrics':None,
        'review_status':'UNREVIEWED','lineage_granularity':'Source record IDs, input byte hash, identity transformations and versioned domain calculations; external evidence hashes are unverified'}
    if errors:
        return result
    if config.action == 'analyze':
        calculated = calculator(dataset,config.as_of)
        if config.reporting_currency:
            calculated = convert_reporting(dataset,calculated,config.reporting_currency,config.as_of)
        result['snapshot'] = calculated
        result['metrics'] = calculated['metrics']
        result['exceptions'].extend(calculated['exceptions'])
        result['management_comparisons'] = management_comparisons(dataset,calculated,config.as_of)
    elif config.action == 'compare':
        calculated = compare(dataset,config.opening,config.closing,complete_history=config.complete_history,basis=basis)
        result['comparison'] = calculated
        result['metrics'] = calculated['metrics']
        result['exceptions'].extend(calculated['exceptions'])
    elif config.action == 'cohorts':
        calculated = cohorts(dataset,config.as_of,basis=basis,complete_history=config.complete_history)
        result['cohorts'] = calculated
        result['exceptions'].extend(calculated['exceptions'])
    elif config.action == 'reconcile':
        calculated = reconcile(dataset,config.opening,config.closing)
        result['reconciliation'] = calculated
        result['exceptions'].extend(calculated['exceptions'])
    else:
        dates = []
        current = config.opening
        while current < config.closing:
            dates.append(date(current.year,current.month,monthrange(current.year,current.month)[1]))
            current = next_month(current)
        monthly = []
        for at in dates:
            snapshot = calculator(dataset,at)
            monthly.append(snapshot)
            result['exceptions'].extend(dict(e,measurement_date=str(at)) for e in snapshot['exceptions'])
        result['monthly'] = monthly
        result['metrics'] = monthly[-1]['metrics']
        result['comparison'] = compare(dataset,config.opening,config.closing-timedelta(days=1),complete_history=config.complete_history,basis=basis)
        result['cohorts'] = cohorts(dataset,config.closing-timedelta(days=1),basis=basis,complete_history=config.complete_history)
        result['reconciliation'] = reconcile(dataset,config.opening,config.closing)
        for key in ('comparison','cohorts','reconciliation'):
            result['exceptions'].extend(result[key]['exceptions'])
        result['management_comparisons'] = []
        by_date = {snapshot['measurement_date']:snapshot for snapshot in monthly}
        for at in sorted({claim.measurement_date for claim in dataset.management_metrics if config.opening <= claim.measurement_date < config.closing}):
            claimed_snapshot = by_date.get(str(at)) or calculator(dataset,at)
            result['exceptions'].extend(dict(e,measurement_date=str(at)) for e in claimed_snapshot['exceptions'])
            result['management_comparisons'].extend(management_comparisons(dataset,claimed_snapshot,at))
    if 'reconciliation' in result and result['reconciliation']['status'] != 'RECONCILED':
        result['exceptions'].append(issue('RECONCILIATION_REVIEW','reconciliation','Independent control reconciliation is incomplete, unexplained or requires review'))
    for claim in result.get('management_comparisons',[]):
        if claim['status']=='REQUIRES_REVIEW':
            result['exceptions'].append(issue('MANAGEMENT_CLAIM_REVIEW',claim['id'],'Management methodology is unknown/different or its reported amount differs'))
    result['status'] = 'REQUIRES_REVIEW' if result['exceptions'] else 'CALCULATED_UNRECONCILED'
    # A failed independent reconciliation must never silently disappear as a healthy report.
    if 'reconciliation' in result and result['reconciliation']['status'] != 'RECONCILED':
        result['status'] = 'REQUIRES_REVIEW'
    return result


def contributing_records(raw: bytes, result: dict, currency: str) -> list[dict]:
    if hashlib.sha256(raw).hexdigest() != result['source_file_sha256']:
        raise ValueError('Source bytes do not match run')
    dataset = parse_dataset(raw)
    references = {'contract_ids':set(),'line_item_ids':set(),'credit_note_ids':set()}
    def visit(value):
        if isinstance(value,dict):
            if 'currency' in value and value['currency'] != currency:
                return
            for key,item in value.items():
                if key in references and isinstance(item,list):
                    references[key].update(item)
                elif key == 'metrics' and isinstance(item,dict):
                    visit(item.get(currency,{}))
                else:
                    visit(item)
        elif isinstance(value,list):
            for item in value:
                visit(item)
    visit(result)
    selected_lines = [r for r in dataset.line_items if r.id in references['line_item_ids']]
    selected_credits = [r for r in dataset.credit_notes if r.id in references['credit_note_ids']]
    invoice_ids = {r.invoice_id for r in [*selected_lines,*selected_credits]}
    records = [r for r in dataset.contracts if r.id in references['contract_ids']]
    records += selected_lines + selected_credits + [r for r in dataset.invoices if r.id in invoice_ids]
    return [r.model_dump(mode='json') for r in records]
