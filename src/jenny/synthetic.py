"""Deterministic entirely synthetic demonstration; expected answers live separately."""

def demo_dataset() -> dict:
    data={'organization':{'id':'synthetic-org','name':'Synthetic SaaS'},'customers':[],
        'contracts':[],'invoices':[],'line_items':[],'evidence':[],
        'accounting_periods':[{'id':'year-2026','start':'2026-01-01','end':'2027-01-01','complete':True}],
        'controls':[],'billing_policy':{'usage':'exclude','credits':'deduct'}}
    def evidence(identifier):
        data['evidence'].append({'id':identifier,'dataset_id':'synthetic-demo-v1','sha256':'0'*64,'source_file':'synthetic generator','record_id':identifier})
    pairs=[('expand','100','150'),('contract','100','80'),('churn','100',None),('new',None,'200')]
    for customer,opening,closing in pairs:
        data['customers'].append({'id':customer,'organization_id':'synthetic-org','name':f'Synthetic {customer}'})
        for suffix,amount,start,end,months in [('a',opening,'2026-01-01','2026-07-01',6),('b',closing,'2026-07-01','2027-01-01',6)]:
            if amount is None:
                continue
            cid=f'{customer}-{suffix}'
            evidence(cid)
            data['contracts'].append({'id':cid,'organization_id':'synthetic-org','customer_id':customer,'currency':'USD','amount':amount,
                'cadence_months':1,'classification':'fixed_recurring','start':start,'end':end,'evidence_id':cid})
            # Six monthly service commitments prepaid in one six-month invoice.
            billed=str(int(amount)*months)
            data['invoices'].append({'id':f'inv-{cid}','customer_id':customer,'invoice_date':start,'currency':'USD','amount':billed,'evidence_id':cid})
            data['line_items'].append({'id':f'line-{cid}','invoice_id':f'inv-{cid}','currency':'USD','amount':billed,
                'classification':'fixed_recurring','service_start':start,'service_end':end,'normalization_months':str(months),'contract_id':cid,'evidence_id':cid})
    evidence('independent-control')
    data['controls'].append({'id':'gl-2026','start':'2026-01-01','end':'2027-01-01','currency':'USD','amount':'4380',
        'basis':'billing_net','materiality':'0.01','evidence_id':'independent-control'})
    return data
