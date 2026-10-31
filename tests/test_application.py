import json
from datetime import date
from decimal import Decimal
from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st
from openpyxl import load_workbook
from jenny.application import execute, RunConfig, contributing_records
from jenny.synthetic import demo_dataset
from jenny.store import save_run, replay_run
from jenny.export import export_workbook, SHEETS
from jenny.cli import main
from jenny.validation import validate
from jenny.models import Dataset


def raw_demo():
    return json.dumps(demo_dataset()).encode()


def report_config():
    return RunConfig(action='report',definition='billing_v1',opening=date(2026,1,1),closing=date(2027,1,1),complete_history=True)


def test_full_report_saved_replayed_exported(tmp_path):
    raw=raw_demo();config=report_config()
    identifier,result=save_run(tmp_path/'runs',raw,config=config)
    assert result['status']=='CALCULATED_UNRECONCILED'
    assert result['metrics']['USD']==result['monthly'][-1]['metrics']['USD']
    assert result['metrics']['USD']['mrr']=='430.00'
    assert result['comparison']['metrics']['USD']['nrr']=='0.76666667'
    assert result['reconciliation']['results'][0]['source_total']=='4380.00'
    assert result['reconciliation']['results'][0]['unexplained_difference']=='0.00'
    assert result['reconciliation']['status']=='RECONCILED'
    assert result['cohorts']['rows'][-1]['currency']=='USD'
    assert replay_run(tmp_path/'runs',identifier)==result
    path=export_workbook(Dataset.model_validate(demo_dataset()),result,tmp_path/'diligence.xlsx')
    wb=load_workbook(path,data_only=False)
    assert wb.sheetnames==SHEETS
    assert wb['Executive Summary']['B6'].value==430
    assert wb['Executive Summary']['C6'].value==5160
    assert wb['Executive Summary']['D6'].value=="='Monthly Revenue'!E17"
    assert wb['Monthly Revenue']['E6'].value=='=ROUND(D6*12,2)'
    assert wb['ARR Bridge']['I6'].value=='=B6+C6+D6-E6-F6+G6-H6'
    assert wb['NRR and GRR']['F6'].value==Decimal('0.76666667') or str(wb['NRR and GRR']['F6'].value)=='0.76666667'
    assert wb.calculation.fullCalcOnLoad is True
    assert wb.vba_archive is None
    wb.close()


def test_formula_injection_preserved_as_text(tmp_path):
    data=demo_dataset()
    data['customers'][0]['name']='=HYPERLINK("https://invalid.example","click")'
    data['evidence'][0]['source_file']='+CMD|evil'
    result=execute(json.dumps(data).encode(),report_config())
    path=export_workbook(Dataset.model_validate(data),result,tmp_path/'safe.xlsx')
    wb=load_workbook(path,data_only=False)
    for sheet in ('Source Data','Customer Mapping','Revenue Classification','Evidence Lineage','Calculation Metadata'):
        assert all(c.data_type!='f' for row in wb[sheet] for c in row)
    assert wb['Evidence Lineage']['C6'].value=='+CMD|evil'
    assert wb['Evidence Lineage']['C6'].data_type=='s'
    wb.close()


def test_source_records_match_raw_input():
    raw=raw_demo();result=execute(raw,report_config())
    records=contributing_records(raw,result,'USD')
    assert any(r['id']=='line-expand-b' for r in records)
    with pytest.raises(ValueError):
        contributing_records(raw+b' ',result,'USD')


def test_request_tampering_detected(tmp_path):
    identifier,_=save_run(tmp_path,raw_demo(),config=report_config())
    request=tmp_path/identifier/'request.json'
    data=json.loads(request.read_text());data['definition']='contract_snapshot_v1'
    request.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        replay_run(tmp_path,identifier)


def test_cli_full_flow(tmp_path,monkeypatch,capsys):
    monkeypatch.chdir(tmp_path)
    assert main(['sample','--output','data.json'])==0
    capsys.readouterr()
    assert main(['report','--input','data.json','--definition','billing_v1','--opening','2026-01-01','--closing','2027-01-01','--confirm-complete-history','--save'])==0
    saved=json.loads(capsys.readouterr().out)
    assert main(['reconcile','--run-id',saved['storage_id']])==0
    assert json.loads(capsys.readouterr().out)['status']=='RECONCILED'
    assert main(['export','--run-id',saved['storage_id'],'--output','report.xlsx'])==0
    capsys.readouterr()
    assert (tmp_path/'report.xlsx').exists()
    assert main(['export','--run-id',saved['storage_id'],'--output','report.xlsx'])==2


@pytest.mark.parametrize('reason', ['deferred_revenue','accrued_revenue','credits','timing','taxes','fx','recognition'])
def test_reconciliation_signed_adjustment_reasons(reason):
    data=demo_dataset()
    data['controls'][0]['amount']='4390'
    data['adjustments']=[{'id':'adj','start':'2026-01-01','end':'2027-01-01','currency':'USD','amount':'10','reason':reason,'evidence_id':'independent-control'}]
    result=execute(json.dumps(data).encode(),report_config())
    reconciliation=result['reconciliation']['results'][0]
    assert reconciliation['status']=='RECONCILED_WITH_ADJUSTMENTS'
    assert Decimal(reconciliation['source_total'])+Decimal(reconciliation['explained_adjustments'])-Decimal(reconciliation['comparison_total'])==Decimal(reconciliation['unexplained_difference'])


def test_unknown_adjustment_requires_review():
    data=demo_dataset();data['adjustments']=[{'id':'adj','start':'2026-01-01','end':'2027-01-01','currency':'USD','amount':'0','reason':'other','evidence_id':'independent-control'}]
    result=execute(json.dumps(data).encode(),report_config())
    assert result['status']=='REQUIRES_REVIEW'
    assert result['reconciliation']['results'][0]['status']=='REQUIRES_REVIEW'


def test_duplicate_control_not_independently_validated():
    data=demo_dataset();data['controls'].append(dict(data['controls'][0],id='different-control'))
    result=execute(json.dumps(data).encode(),report_config())
    assert result['status']=='REQUIRES_REVIEW'
    assert result['reconciliation']['results'][0]['status']=='REQUIRES_REVIEW'


@settings(max_examples=75,derandomize=True)
@given(cents=st.integers(min_value=0,max_value=10000000),months=st.sampled_from([1,3,6,12]))
def test_billing_arr_and_reproducibility_properties(cents,months):
    data=demo_dataset()
    data['contracts']=[];data['invoices']=data['invoices'][:1];data['line_items']=data['line_items'][:1]
    amount=Decimal(cents)/100
    data['invoices'][0]['amount']=str(amount)
    data['line_items'][0].update(amount=str(amount),normalization_months=str(months),contract_id=None)
    config=RunConfig(action='analyze',definition='billing_v1',as_of=date(2026,3,1))
    raw=json.dumps(data).encode();result=execute(raw,config)
    assert result==execute(raw,config)
    metric=result['metrics']['USD']
    assert Decimal(metric['arr'])==12*Decimal(metric['mrr'])
    assert Decimal(metric['mrr'])==(amount/Decimal(months)).quantize(Decimal('0.01'))


@settings(max_examples=60,derandomize=True)
@given(control=st.integers(-10000,10000),adjustment=st.integers(-10000,10000))
def test_reconciliation_balances_property(control,adjustment):
    data=demo_dataset();data['controls'][0]['amount']=str(control)
    data['adjustments']=[{'id':'adj','start':'2026-01-01','end':'2027-01-01','currency':'USD','amount':str(adjustment),'reason':'recognition','evidence_id':'independent-control'}]
    result=execute(json.dumps(data).encode(),RunConfig(action='reconcile',definition='billing_v1',opening=date(2026,1,1),closing=date(2027,1,1)))
    row=result['reconciliation']['results'][0]
    assert Decimal(row['unexplained_difference'])==Decimal('4380')+adjustment-control


def test_empty_period_missing_controls_is_not_zero_validation():
    data=demo_dataset();data['controls']=[]
    result=execute(json.dumps(data).encode(),report_config())
    assert result['status']=='REQUIRES_REVIEW'
    assert result['reconciliation']['results'][0]['comparison_total'] is None


def test_excel_precision_limit(tmp_path):
    data=demo_dataset();result=execute(json.dumps(data).encode(),report_config())
    result['metrics']['USD']['mrr']='1234567890123456.12'
    with pytest.raises(ValueError,match='precision'):
        export_workbook(Dataset.model_validate(data),result,tmp_path/'too-large.xlsx')
    assert not (tmp_path/'too-large.xlsx').exists()


def test_snapshot_lineage_and_currency_filtering():
    data=demo_dataset()
    data['contracts']=[]
    for line in data['line_items']:
        line['contract_id']=None
    data['invoices'][1]['currency']='EUR';data['line_items'][1]['currency']='EUR'
    raw=json.dumps(data).encode()
    result=execute(raw,RunConfig(definition='billing_v1',as_of=date(2026,8,1)))
    usd=contributing_records(raw,result,'USD')
    assert 'line-expand-b' not in {r['id'] for r in usd}
    assert 'line-new-b' in {r['id'] for r in usd}
    assert 'inv-new-b' in {r['id'] for r in usd}


def test_billing_half_cent_aggregation_regression():
    data=demo_dataset();data['contracts']=[];data['invoices']=data['invoices'][:1];data['line_items']=data['line_items'][:1]
    data['invoices'][0]['amount']='0.06'
    template=dict(data['line_items'][0],amount='0.02',normalization_months='12',contract_id=None)
    data['line_items']=[dict(template,id=f'line-{i}') for i in range(3)]
    result=execute(json.dumps(data).encode(),RunConfig(definition='billing_v1',as_of=date(2026,3,1)))
    assert result['metrics']['USD']['mrr']=='0.00'
    assert result['metrics']['USD']['arr']=='0.00'


@settings(max_examples=50,derandomize=True)
@given(cents=st.integers(0,100000),count=st.integers(1,8))
def test_splitting_annual_lines_preserves_aggregate(cents,count):
    data=demo_dataset();data['contracts']=[];data['invoices']=data['invoices'][:1];data['line_items']=data['line_items'][:1]
    amount=Decimal(cents)/100
    data['invoices'][0]['amount']=str(amount*count)
    template=dict(data['line_items'][0],amount=str(amount),normalization_months='12',contract_id=None)
    data['line_items']=[dict(template,id=f'line-{i}') for i in range(count)]
    config=RunConfig(definition='billing_v1',as_of=date(2026,3,1))
    split=execute(json.dumps(data).encode(),config)['metrics']['USD']
    data['line_items']=[dict(template,amount=str(amount*count))]
    combined=execute(json.dumps(data).encode(),config)['metrics']['USD']
    assert split['mrr']==combined['mrr']
    assert split['arr']==combined['arr']


def test_exact_ratio_rounding_tie():
    from jenny.arithmetic import ratio
    assert ratio(Decimal('200000001'),Decimal('200000000'))=='1.00000000'
    assert ratio(Decimal('200000003'),Decimal('200000000'))=='1.00000002'


def test_fx_large_valid_inputs_remain_structured():
    data=demo_dataset();data['contracts']=[];data['invoices']=data['invoices'][:1];data['line_items']=data['line_items'][:1]
    amount='9999999999999999999999999999e12'
    data['invoices'][0]['amount']=amount
    data['line_items'][0].update(amount=amount,normalization_months='0.000000000001',contract_id=None)
    data['currency_rates']=[{'id':'fx','rate_date':'2026-03-01','source_currency':'USD','target_currency':'EUR','rate':amount,'evidence_id':'expand-a'}]
    result=execute(json.dumps(data).encode(),RunConfig(definition='billing_v1',as_of=date(2026,3,1),reporting_currency='EUR'))
    assert result['snapshot']['reporting_metrics']['mrr'] is not None
    assert result['status']=='CALCULATED_UNRECONCILED'


def test_contract_billing_price_contradiction():
    data=demo_dataset();data['line_items'][0]['amount']='660';data['invoices'][0]['amount']='660'
    result=execute(json.dumps(data).encode(),RunConfig(definition='billing_v1',as_of=date(2026,3,1)))
    assert result['metrics'] is None
    assert 'CONTRACT_PRICE_CONFLICT' in {e['code'] for e in result['exceptions']}


def test_extreme_decimal_exponent_rejected_before_arithmetic():
    data=demo_dataset();data['invoices'][0]['amount']='1e100';data['line_items'][0]['amount']='1e100'
    result=execute(json.dumps(data).encode(),RunConfig(definition='billing_v1',as_of=date(2026,3,1)))
    assert result['metrics'] is None
    assert 'AMOUNT_PRECISION' in {e['code'] for e in result['exceptions']}


@pytest.mark.parametrize('field,value',[('approved','yes'),('approved',1)])
def test_identity_approval_is_strict_boolean(field,value):
    from pydantic import ValidationError
    data=demo_dataset();data['mappings']=[{'id':'map','source_customer_id':'expand','canonical_customer_id':'new','relationship':'rename',field:value}]
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


def test_source_dates_do_not_accept_epoch_numbers():
    from pydantic import ValidationError
    data=demo_dataset();data['invoices'][0]['invoice_date']=0
    with pytest.raises(ValidationError):
        Dataset.model_validate(data)


def test_management_claims_compared_at_their_own_dates():
    data=demo_dataset()
    data['management_metrics']=[{'id':'mid-month-claim','measurement_date':'2026-03-15','currency':'USD','metric':'arr','amount':'3600','methodology':'billing_v1','evidence_id':'expand-a'}]
    result=execute(json.dumps(data).encode(),report_config())
    assert result['management_comparisons'][0]['status']=='MATCHED'
    assert result['management_comparisons'][0]['calculated_amount']=='3600.00'
    assert result['status']=='CALCULATED_UNRECONCILED'
