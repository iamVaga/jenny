"""Materialize independent, explicit expected fixtures. Never calls production calculations."""
import copy
import json
from pathlib import Path


def base():
    return {'organization':{'id':'org','name':'Synthetic benchmark'},
        'customers':[{'id':'customer','organization_id':'org','name':'Synthetic Customer'}], 'contracts':[],
        'invoices':[{'id':'invoice','customer_id':'customer','invoice_date':'2026-01-01','currency':'USD','amount':'1200','evidence_id':'e'}],
        'line_items':[{'id':'line','invoice_id':'invoice','currency':'USD','amount':'1200','classification':'fixed_recurring',
            'service_start':'2026-01-01','service_end':'2027-01-01','normalization_months':'12','evidence_id':'e'}],
        'evidence':[{'id':'e','dataset_id':'synthetic-benchmark-v1','sha256':'0'*64,'source_file':'hand-specified synthetic fixture','record_id':'record'}],
        'billing_policy':{'usage':'exclude','credits':'deduct'}}

CASES=[]
ANALYZE={'action':'analyze','definition':'billing_v1','as_of':'2026-06-01'}
RECON={'action':'reconcile','definition':'billing_v1','opening':'2026-01-01','closing':'2027-01-01'}

def add(name, data, expected=None, codes=None, config=None, invalid=False):
    CASES.append({'name':name,'input':data,'request':config or ANALYZE,'expected':expected or {},'expected_codes':codes or [],'invalid':invalid})

for name,amount,months,mrr,arr in [
    ('annual subscription','1200','12','100.00','1200.00'),
    ('monthly subscription','100','1','100.00','1200.00'),
    ('six month prepayment','600','6','100.00','1200.00'),
    ('quarterly prepayment','300','3','100.00','1200.00'),
    ('half month proration','50','0.5','100.00','1200.00'),
    ('explicit zero commitment','0','1','0.00','0.00'),
    ('annual fractional normalization','100','12','8.33','99.96'),
    ('half even lower tie','1.005','1','1.00','12.00'),
    ('half even upper tie','1.015','1','1.02','12.24')]:
    d=base();d['invoices'][0]['amount']=amount;d['line_items'][0].update(amount=amount,normalization_months=months)
    add(name,d,{'metrics.USD.mrr':mrr,'metrics.USD.arr':arr})
d=base();d['line_items'][0]['discount']='120';d['invoices'][0]['amount']='1080';add('net contractual discount',d,{'metrics.USD.mrr':'90.00'})
d=base();d['line_items'][0]['tax']='240';d['invoices'][0]['amount']='1440';add('tax excluded from recurring run rate',d,{'metrics.USD.mrr':'100.00'})
for name,classification,code in [('one time implementation excluded','one_time',None),('usage explicitly excluded','usage',None),('hybrid requires split','hybrid','CLASSIFICATION_REVIEW'),('unknown classification','unknown','CLASSIFICATION_REVIEW')]:
    d=base();d['line_items'][0]['classification']=classification
    add(name,d,{'metrics':{}} if code is None else None,[code] if code else [])
d=base();d['line_items'][0]['classification']='usage';d['billing_policy']['usage']='review';add('usage review policy',d,codes=['USAGE_POLICY_REVIEW'])
for field in ['service_start','service_end','normalization_months']:
    d=base();d['line_items'][0].pop(field);add('missing '+field,d,codes=['MISSING_SERVICE_PERIOD'])
for collection in ['invoices','customers','line_items','evidence']:
    d=base();d[collection].append(copy.deepcopy(d[collection][0]));add('duplicate '+collection,d,codes=['DUPLICATE_ID'])
d=base();d['invoices'][0]['customer_id']='missing';add('missing invoice customer',d,codes=['MISSING_CUSTOMER'])
d=base();d['line_items'][0]['evidence_id']='missing';add('missing source evidence',d,codes=['MISSING_EVIDENCE'])
d=base();d['line_items'][0]['currency']='EUR';add('line invoice currency mismatch',d,codes=['CURRENCY_MISMATCH'])
d=base();d['invoices'][0]['amount']='-1200';add('negative invoice',d,codes=['NEGATIVE_INVOICE'])
d=base();d['invoices'][0]['amount']='1199';add('invoice total mismatch',d,codes=['INVOICE_TOTAL_MISMATCH'])
d=base();d['line_items']=[];add('missing invoice detail',d,codes=['MISSING_INVOICE_LINES'])
for name,field,value in [('float money','amount',12.5),('invalid service dates','service_end','2025-01-01'),('negative line','amount','-1'),('zero denominator','normalization_months','0'),('discount exceeds line','discount','1201')]:
    d=base();d['line_items'][0][field]=value;add(name,d,invalid=True)
credit={'id':'credit','invoice_id':'invoice','line_item_id':'line','issue_date':'2026-02-01','currency':'USD','amount':'120','evidence_id':'e'}
d=base();d['credit_notes']=[credit];add('matched credit deducted',d,{'metrics.USD.mrr':'90.00'})
d=base();d['credit_notes']=[credit];d['billing_policy']['credits']='exclude';add('credit exclusion policy',d,{'metrics.USD.mrr':'100.00'})
d=base();d['credit_notes']=[dict(credit,line_item_id='missing')];add('unmatched credit',d,codes=['UNMATCHED_CREDIT'])
d=base();d['credit_notes']=[dict(credit,amount='1300')];add('credit exceeds source',d,codes=['EXCESS_CREDIT'])
d=base();d['credit_notes']=[credit];d['refunds']=[{'id':'refund','invoice_id':'invoice','credit_note_id':'credit','payment_date':'2026-03-01','currency':'USD','amount':'120','evidence_id':'e'}];add('refund is not double deducted',d,{'metrics.USD.mrr':'90.00'})
d=base();d['refunds']=[{'id':'refund','invoice_id':'invoice','payment_date':'2026-03-01','currency':'USD','amount':'120','evidence_id':'e'}];add('unmatched refund review',d,codes=['UNMATCHED_REFUND'])
for name,approved,relationship,target,code in [('renamed customer approved',True,'rename','canonical',None),('duplicate customer approved',True,'duplicate','canonical',None),('ambiguous identity',False,'ambiguous',None,'IDENTITY_REVIEW'),('parent consolidation',True,'parent','canonical','IDENTITY_REVIEW'),('reseller arrangement',True,'reseller','canonical','IDENTITY_REVIEW'),('incorrect identity target',True,'rename','missing','IDENTITY_REVIEW')]:
    d=base();d['customers'].append({'id':'canonical','organization_id':'org','name':'Synthetic Canonical'})
    d['mappings']=[{'id':'map','source_customer_id':'customer','canonical_customer_id':target,'relationship':relationship,'approved':approved}]
    add(name,d,{'metrics.USD.mrr':'100.00'} if code is None else None,[code] if code else [])
d=base();d['customers'][0]['parent_id']='parent';add('parent subsidiary unresolved',d,codes=['IDENTITY_REVIEW'])
for name,rate,expect,codes in [('direct FX conversion','0.5','50.00',[]),('missing exchange rate',None,None,['MISSING_OR_AMBIGUOUS_FX'])]:
    d=base()
    if rate:
        d['currency_rates']=[{'id':'fx','rate_date':'2026-06-01','source_currency':'USD','target_currency':'EUR','rate':rate,'evidence_id':'e'}]
    config=dict(ANALYZE,reporting_currency='EUR')
    add(name,d,{'snapshot.reporting_metrics.mrr':expect} if expect else None,codes,config)
for name,control,adjustment,complete,status in [('clean accounting reconciliation','1200',None,True,'RECONCILED'),('unexplained GL difference','1100',None,True,'UNRECONCILED'),('deferred revenue explanation','1100','-100',True,'RECONCILED_WITH_ADJUSTMENTS'),('accrued revenue explanation','1300','100',True,'RECONCILED_WITH_ADJUSTMENTS'),('incomplete accounting period','1200',None,False,'INSUFFICIENT_DATA')]:
    d=base();d['accounting_periods']=[{'id':'period','start':'2026-01-01','end':'2027-01-01','complete':complete}]
    d['controls']=[{'id':'gl','start':'2026-01-01','end':'2027-01-01','currency':'USD','amount':control,'basis':'general_ledger','evidence_id':'e'}]
    if adjustment:
        d['adjustments']=[{'id':'adjustment','start':'2026-01-01','end':'2027-01-01','currency':'USD','amount':adjustment,'reason':'deferred_revenue' if adjustment=='-100' else 'accrued_revenue','evidence_id':'e'}]
    # Incomplete periods have an explicit application exception but still a structured reconciliation.
    add(name,d,{'reconciliation.results.0.status':status},['INCOMPLETE_ACCOUNTING_PERIOD','RECONCILIATION_REVIEW'] if not complete else ['RECONCILIATION_REVIEW'] if status=='UNRECONCILED' else [],RECON)
d=base();d['management_metrics']=[{'id':'claim','measurement_date':'2026-06-01','currency':'USD','metric':'arr','amount':'9999','evidence_id':'e'}];add('unknown conflicting management ARR',d,codes=['MANAGEMENT_CLAIM_REVIEW'])
d=base();d['invoices'][0]['invoice_date']='2026-07-01';add('future issued billing excluded',d,{'metrics':{}})
d=base();add('service end exclusive',d,{'metrics':{}},config=dict(ANALYZE,as_of='2027-01-01'))
# Contract-specific independently specified lifecycle cases.
for name,amount,start,end,cancel,expected in [('contract clean monthly','100','2026-01-01','2027-01-01',None,'100.00'),('contract clean annual','1200','2026-01-01','2027-01-01',None,'100.00'),('midperiod cancellation exclusive','100','2026-01-01','2027-01-01','2026-06-01',None)]:
    d=base();d['invoices']=[];d['line_items']=[]
    d['contracts']=[{'id':'contract','organization_id':'org','customer_id':'customer','currency':'USD','amount':amount,'cadence_months':12 if amount=='1200' else 1,'classification':'fixed_recurring','start':start,'end':end,'cancelled_on':cancel,'evidence_id':'e'}]
    add(name,d,{'metrics.USD.mrr':expected} if expected else {'metrics':{}},config=dict(ANALYZE,definition='contract_snapshot_v1'))

# Independently specified customer lifecycle/cohort comparisons.
for name,opening,closing,nrr,grr in [
    ('retained customer','100','100','1.00000000','1.00000000'),
    ('customer expansion','100','150','1.50000000','1.00000000'),
    ('customer contraction','100','80','0.80000000','0.80000000'),
    ('full customer churn','100',None,'0.00000000','0.00000000'),
    ('partial revenue churn','200','100','0.50000000','0.50000000')]:
    d=base();d['invoices']=[];d['line_items']=[]
    d['contracts']=[{'id':'opening','organization_id':'org','customer_id':'customer','currency':'USD','amount':opening,'cadence_months':1,'classification':'fixed_recurring','start':'2026-01-01','end':'2026-07-01','evidence_id':'e'}]
    if closing is not None:
        d['contracts'].append(dict(d['contracts'][0],id='closing',amount=closing,start='2026-07-01',end='2027-01-01'))
    request={'action':'compare','definition':'contract_snapshot_v1','opening':'2026-01-01','closing':'2026-07-01','complete_history':True}
    add(name,d,{'metrics.USD.nrr':nrr,'metrics.USD.grr':grr},config=request)
d=base();d['contracts']=[{'id':'linked','organization_id':'org','customer_id':'customer','currency':'USD','amount':'100','cadence_months':1,'classification':'one_time','start':'2026-01-01','end':'2027-01-01','evidence_id':'e'}];d['line_items'][0]['contract_id']='linked';add('one time contract misclassified recurring invoice',d,codes=['CONTRACT_INVOICE_CONFLICT'])
d=base();d['contracts']=[{'id':'one','organization_id':'org','customer_id':'customer','currency':'USD','amount':'100','cadence_months':1,'classification':'fixed_recurring','start':'2026-01-01','end':'2027-01-01','evidence_id':'e'}];d['contracts'].append(dict(d['contracts'][0],id='two'));add('overlapping commitments',d,codes=['OVERLAPPING_COMMITMENTS'])
d=base();d['customers'].append({'id':'other','organization_id':'org','name':'Other synthetic'})
d['mappings']=[{'id':'map1','source_customer_id':'customer','canonical_customer_id':'other','relationship':'rename','approved':True},{'id':'map2','source_customer_id':'other','canonical_customer_id':'customer','relationship':'rename','approved':True}];add('identity cycle',d,codes=['CYCLIC_IDENTITY'])
d=base();d['customers'].extend([{'id':x,'organization_id':'org','name':x} for x in ('a','b')]);d['mappings']=[{'id':'map1','source_customer_id':'customer','canonical_customer_id':'a','relationship':'duplicate','approved':True},{'id':'map2','source_customer_id':'customer','canonical_customer_id':'b','relationship':'duplicate','approved':True}];add('conflicting identity mappings',d,codes=['CONFLICTING_IDENTITY'])
d=base();d['invoices'].append(dict(d['invoices'][0],id='euro',currency='EUR'));d['line_items'].append(dict(d['line_items'][0],id='euro-line',invoice_id='euro',currency='EUR'));add('multi currency original totals retained',d,{'metrics.USD.mrr':'100.00','metrics.EUR.mrr':'100.00'})

if __name__=='__main__':
    target=Path('src/jenny/fixtures/benchmark.json')
    target.write_text(json.dumps(CASES,indent=2)+'\n',encoding='utf-8')
    print(f'{len(CASES)} independently specified benchmark cases')
