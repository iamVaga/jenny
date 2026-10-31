import copy
import json
from datetime import date
from decimal import Decimal, localcontext, ROUND_DOWN
from pathlib import Path
import pytest
from jenny.models import Dataset
from jenny.retention import compare
from jenny.cli import main

OPEN = date(2026, 1, 1)
CLOSE = date(2026, 7, 1)


def history(pairs):
    raw = {'organization': {'id': 'org', 'name': 'Synthetic retention'}, 'customers': [], 'contracts': [], 'evidence': []}
    for index, (opening, closing) in enumerate(pairs):
        customer = f'customer-{index}'
        raw['customers'].append({'id': customer, 'organization_id': 'org', 'name': customer})
        for suffix, amount, start, end in [('a', opening, '2026-01-01', '2026-07-01'), ('b', closing, '2026-07-01', '2027-01-01')]:
            if amount is None:
                continue
            cid = f'{customer}-{suffix}'
            raw['contracts'].append({'id': cid, 'organization_id': 'org', 'customer_id': customer,
                'amount': amount, 'currency': 'USD', 'cadence_months': 1, 'classification': 'fixed_recurring',
                'start': start, 'end': end, 'evidence_id': cid})
            raw['evidence'].append({'id': cid, 'dataset_id': 'synthetic-retention-v1', 'sha256': '0'*64,
                'source_file': 'synthetic history', 'record_id': cid})
    return raw


def run(raw, **kwargs):
    return compare(Dataset.model_validate(raw), OPEN, CLOSE, complete_history=True, **kwargs)

@pytest.mark.parametrize('opening,closing,nrr,grr,churn,expansion,contraction', [
    ('100','100','1.00000000','1.00000000','0.00','0.00','0.00'),
    ('100','150','1.50000000','1.00000000','0.00','50.00','0.00'),
    ('100','80','0.80000000','0.80000000','0.00','0.00','20.00'),
    ('100',None,'0.00000000','0.00000000','100.00','0.00','0.00'),
    ('100','0','0.00000000','0.00000000','100.00','0.00','0.00'),
    ('1','3','3.00000000','1.00000000','0.00','2.00','0.00'),
])
def test_hand_calculated_retention(opening, closing, nrr, grr, churn, expansion, contraction):
    metric = run(history([(opening, closing)]))['metrics']['USD']
    assert metric['nrr'] == nrr
    assert metric['grr'] == grr
    assert metric['churn_mrr'] == churn
    assert metric['expansion_mrr'] == expansion
    assert metric['contraction_mrr'] == contraction


def test_combined_independent_expectations():
    result = run(history([('100','150'), ('100','80'), ('100',None), (None,'200')]))
    m = result['metrics']['USD']
    assert m['opening_mrr'] == '300.00'
    assert m['closing_mrr'] == '430.00'
    assert m['nrr'] == '0.76666667'
    assert m['grr'] == '0.60000000'
    assert m['gross_revenue_churn'] == '0.40000000'
    assert m['net_revenue_churn'] == '0.23333333'
    assert m['logo_churn'] == '0.33333333'
    assert m['opening_logos'] == 3
    assert m['lost_logos'] == 1
    assert m['arr_bridge'] == {'opening_arr':'3600.00', 'new_arr':'2400.00', 'expansion_arr':'600.00',
        'contraction_arr':'240.00', 'churn_arr':'1200.00', 'closing_arr':'5160.00', 'rounding_residual_arr':'0.00'}


def test_new_logos_excluded_from_retention():
    a = run(history([('100','80')]))['metrics']['USD']
    b = run(history([('100','80'), (None,'999999')]))['metrics']['USD']
    for key in ('nrr','grr','logo_churn','gross_revenue_churn','net_revenue_churn'):
        assert a[key] == b[key]


def test_complete_history_required():
    result = compare(Dataset.model_validate(history([('100','100')])), OPEN, CLOSE)
    assert result['metrics'] is None
    assert result['exceptions'][0]['code'] == 'INCOMPLETE_HISTORY'

@pytest.mark.parametrize('opening,closing', [(CLOSE,OPEN),(OPEN,OPEN)])
def test_invalid_dates(opening, closing):
    result = compare(Dataset.model_validate(history([('100','100')])), opening, closing, complete_history=True)
    assert result['metrics'] is None
    assert result['exceptions'][0]['code'] == 'INVALID_COMPARISON_DATES'


def test_empty_opening_cohort():
    result = run(history([(None,'100')]))
    m = result['metrics']['USD']
    assert m['nrr'] is None and m['grr'] is None and m['logo_churn'] is None
    assert m['arr_bridge']['new_arr'] == '1200.00'
    assert result['status'] == 'REQUIRES_REVIEW'
    assert result['exceptions'][0]['code'] == 'EMPTY_OPENING_COHORT'


def test_currency_migration_requires_review():
    raw = history([('100','150')])
    raw['contracts'][1]['currency'] = 'EUR'
    result = run(raw)
    assert result['metrics'] is None
    assert result['exceptions'][0]['code'] == 'CUSTOMER_CURRENCY_CHANGE'


def test_separate_currency_retention():
    raw = history([('100','150'),('200','100')])
    for c in raw['contracts'][2:]:
        c['currency'] = 'EUR'
    m = run(raw)['metrics']
    assert m['USD']['nrr'] == '1.50000000'
    assert m['EUR']['nrr'] == '0.50000000'


def test_endpoint_exceptions_propagate():
    raw = history([('100','150')])
    raw['contracts'][1]['classification'] = 'usage'
    result = run(raw)
    assert result['metrics'] is None
    assert result['exceptions'][0]['endpoint'] == 'closing'


def test_annual_rounding_bridge():
    raw = history([('100','200')])
    for c in raw['contracts']:
        c['cadence_months'] = 12
    m = run(raw)['metrics']['USD']
    assert m['nrr'] == '2.00000000'
    b = m['arr_bridge']
    assert b['opening_arr'] == '99.96'
    assert b['closing_arr'] == '200.04'
    assert b['expansion_arr'] == '100.00'
    assert b['rounding_residual_arr'] == '0.08'
    assert Decimal(b['opening_arr']) + Decimal(b['expansion_arr']) + Decimal(b['rounding_residual_arr']) == Decimal(b['closing_arr'])


def test_lineage():
    m = run(history([('100','150')]))['metrics']['USD']['customer_movements'][0]
    assert m['contract_ids'] == ['customer-0-a', 'customer-0-b']
    assert m['evidence_ids'] == m['contract_ids']


def test_context_isolation_and_repeatability():
    raw = history([('100','150'), ('100',None)])
    first = run(raw)
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = ROUND_DOWN
        assert run(raw) == first
    raw['contracts'].reverse()
    assert run(raw)['metrics'] == first['metrics']


def test_negative_net_churn_is_valid():
    m = run(history([('100','150')]))['metrics']['USD']
    assert m['net_revenue_churn'] == '-0.50000000'
    assert m['logo_churn'] == '0.00000000'


def test_cli_compare(tmp_path, capsys):
    path = tmp_path / 'history.json'
    path.write_text(json.dumps(history([('100','150')])))
    args = ['compare','--root',str(tmp_path),'--input','history.json','--opening','2026-01-01','--closing','2026-07-01']
    assert main(args) == 2
    assert json.loads(capsys.readouterr().out)['exceptions'][0]['code'] == 'INCOMPLETE_HISTORY'
    assert main(args + ['--confirm-complete-history']) == 0
    assert json.loads(capsys.readouterr().out)['metrics']['USD']['nrr'] == '1.50000000'


def test_cli_rejects_saving_comparison():
    with pytest.raises(SystemExit) as e:
        main(['compare','--input','x','--opening','2026-01-01','--closing','2026-07-01','--save'])
    assert e.value.code == 2

@pytest.mark.parametrize('opening,closing', [('100','0'),('100','25'),('100','100'),('100','175'),('1200','2400')])
def test_retention_and_bridge_invariants(opening, closing):
    m = run(history([(opening,closing),(None,'50')]))['metrics']['USD']
    assert Decimal(m['grr']) <= 1
    assert Decimal(m['nrr']) == (Decimal(closing)/Decimal(opening)).quantize(Decimal('0.00000001'))
    assert Decimal(m['net_revenue_churn']) == 1 - Decimal(m['nrr'])
    b = {k:Decimal(v) for k,v in m['arr_bridge'].items()}
    assert b['opening_arr'] + b['new_arr'] + b['expansion_arr'] - b['contraction_arr'] - b['churn_arr'] + b['rounding_residual_arr'] == b['closing_arr']


def test_checked_in_benchmark():
    raw = json.loads(Path('data/retention.json').read_text())
    expected = json.loads(Path('data/retention_expected.json').read_text())
    actual = run(raw)['metrics']['USD']
    for key, value in expected.items():
        if key not in ('opening_date','closing_date','currency','derivation'):
            assert actual[key] == value



def test_zero_ending_commitment_kept_in_lineage():
    movement = run(history([('100','0')]))['metrics']['USD']['customer_movements'][0]
    assert movement['movement'] == 'churn'
    assert movement['contract_ids'] == ['customer-0-a', 'customer-0-b']


def test_cli_definition_mismatch():
    with pytest.raises(SystemExit) as e:
        main(['compare','--input','x','--opening','2026-01-01','--closing','2026-07-01','--definition','contract_snapshot_v1'])
    assert e.value.code == 2
