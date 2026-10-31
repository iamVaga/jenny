"""Macro-free diligence workbook. Decimal results are authoritative; Excel is a presentation/check surface."""
import json
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import date
from tempfile import NamedTemporaryFile
from .models import Dataset
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.workbook.properties import CalcProperties
from openpyxl.utils import get_column_letter

SHEETS = ['Executive Summary','Source Data','Customer Mapping','Revenue Classification','Monthly Revenue',
          'ARR Bridge','NRR and GRR','Cohort Analysis','Reconciliation','Exceptions and Review',
          'Metric Definitions','Evidence Lineage','Calculation Metadata']
NUMBER = '#,##0.00;(#,##0.00);"-"'


class Formula(str):
    pass


def safe_value(value):
    if value is None:
        return 'Unavailable'
    if isinstance(value,(dict,list,tuple)):
        value = json.dumps(value,sort_keys=True,default=str)
    if isinstance(value,str):
        value = ''.join(c if ord(c)>=32 or c in '\n\t\r' else f'\\u{ord(c):04x}' for c in value)
        if len(value)>32767:
            raise ValueError('Source record exceeds Excel cell capacity; inspect saved JSON instead')
    return value


def numeric(value):
    if value is None:
        return None
    amount = Decimal(str(value))
    # Excel has only 15 significant decimal digits. Refuse misleading numeric exports.
    digits=list(amount.as_tuple().digits)
    while len(digits)>1 and digits[-1]==0:
        digits.pop()
    if len(digits)>15:
        raise ValueError('Amount exceeds Excel numeric precision; use JSON results')
    return amount


def export_workbook(dataset: Dataset, result: dict, path: Path) -> Path:
    path = Path(path)
    if path.suffix.lower() != '.xlsx' or path.exists():
        raise ValueError('Output must be a new .xlsx file')
    workbook = Workbook()
    workbook.remove(workbook.active)
    workbook.calculation = CalcProperties(calcId=191029,fullCalcOnLoad=True,forceFullCalc=True)
    notes = 'Python Decimal results are authoritative. Excel formulas require recalculation; formulas do not recalculate the full source model.'
    def table(name, headers, rows, note=None):
        ws = workbook.create_sheet(name)
        ws.sheet_view.showGridLines = False
        ws['A2'] = name
        ws['A2'].font = Font(name='Arial',size=16,bold=True,color='17233B')
        ws['A3'] = safe_value(note or 'Record-level evidence; review exceptions before relying on financial results.')
        ws['A3'].font = Font(name='Arial',size=10,italic=True,color='596579')
        ws.row_dimensions[3].height=32
        ws['A3'].alignment = Alignment(wrap_text=True,vertical='top')
        ws.merge_cells(start_row=3,start_column=1,end_row=3,end_column=max(3,len(headers)))
        for column,header in enumerate(headers,1):
            cell=ws.cell(5,column,header)
            cell.font=Font(name='Arial',size=10,bold=True,color='FFFFFF')
            cell.fill=PatternFill('solid',fgColor='253858')
            cell.alignment=Alignment(horizontal='center',vertical='center',wrap_text=True)
        ws.row_dimensions[5].height=32
        for row_number,row in enumerate(rows,6):
            for column,value in enumerate(row,1):
                formula=isinstance(value,Formula)
                cell=ws.cell(row_number,column,safe_value(value))
                if isinstance(value,str) and not formula:
                    cell.data_type='s'
                    cell.number_format='@'  # prevents =,+,-,@ source strings becoming formulas
                cell.font=Font(name='Arial',size=10,color=('00804A' if formula and "'" in value and name!='Executive Summary' else '17233B'))
                if isinstance(value,Decimal) or formula:
                    cell.number_format=NUMBER
                cell.alignment=Alignment(vertical='top',wrap_text=True)
                if row_number%2==0:
                    cell.fill=PatternFill('solid',fgColor='F2F5F9')
            ws.row_dimensions[row_number].height=32
        ws.freeze_panes='B6'
        ws.auto_filter.ref=f'A5:{get_column_letter(len(headers))}{max(5,ws.max_row)}'
        for column in range(1,len(headers)+1):
            ws.column_dimensions[get_column_letter(column)].width=24 if column>1 else 27
        ws.print_options.horizontalCentered=True
        ws.sheet_properties.pageSetUpPr.fitToPage=True
        ws.page_setup.orientation='landscape'
        ws.page_setup.paperSize=ws.PAPERSIZE_A3
        ws.page_setup.fitToWidth=1
        ws.page_setup.fitToHeight=0
        ws.print_title_rows='1:5'
        ws.print_area=ws.dimensions
        return ws
    monthly = result.get('monthly', [result.get('snapshot',result)])
    monthly_rows=[]
    latest_rows={}
    for snapshot in monthly:
        for currency,metric in (snapshot.get('metrics') or {}).items():
            row_number=6+len(monthly_rows)
            monthly_rows.append([date.fromisoformat(snapshot['measurement_date']) if snapshot.get('measurement_date') else None,currency,snapshot.get('definition'),numeric(metric['mrr']),
                Formula(f'=ROUND(D{row_number}*12,2)'),numeric(metric['arr']),metric.get('contract_ids',metric.get('line_item_ids',[]))])
            latest_rows[currency]=row_number
    summary=[]
    metrics=result.get('metrics') or {}
    for currency,metric in metrics.items():
        if 'mrr' not in metric:
            continue
        row=latest_rows.get(currency)
        summary.append([currency,numeric(metric['mrr']),numeric(metric['arr']),Formula(f"='Monthly Revenue'!E{row}") if row else None,result['status']])
    if not summary:
        summary=[['No snapshot metrics available',None,None,None,result['status']]]
    table('Executive Summary',['Currency','MRR · Python','ARR · Python','ARR · Excel check','Run status'],summary,notes)
    source=[]
    for name in ('customers','contracts','invoices','line_items','credit_notes','refunds','currency_rates','adjustments','accounting_periods','controls','management_metrics'):
        for row in getattr(dataset,name):
            for key,value in row.model_dump(mode='json').items():
                source.append([name,row.id,getattr(row,'customer_id',None),getattr(row,'currency',None),str(getattr(row,'amount','')),key,value])
    table('Source Data',['Record type','ID','Customer','Currency','Original amount · exact text','Source field','Source value'],source,'Original amounts and complete records retained as text; exact source bytes are in the saved run.').column_dimensions['G'].width=65
    table('Customer Mapping',['Mapping ID','Source ID','Canonical ID','Relationship','Approved'],
        [[r.id,r.source_customer_id,r.canonical_customer_id,r.relationship,r.approved] for r in dataset.mappings] or [['No explicit mappings supplied',None,None,None,None]])
    table('Revenue Classification',['Source ID','Classification','Amount · exact text','Normalization months','Evidence ID'],
        [[c.id,c.classification,str(c.amount),str(c.cadence_months),c.evidence_id] for c in dataset.contracts]+
        [[l.id,l.classification,str(l.amount),str(l.normalization_months),l.evidence_id] for l in dataset.line_items])
    table('Monthly Revenue',['Measurement date','Currency','Definition','MRR · Python','ARR · Excel','ARR · Python','Source record IDs'],monthly_rows or [['Not calculated in this run',None,None,None,None,None,None]],notes)
    comparison=result.get('comparison',result if 'opening_date' in result else {})
    bridges=[]
    retention=[]
    for currency,metric in (comparison.get('metrics') or {}).items():
        if 'arr_bridge' not in metric:
            continue
        b=metric['arr_bridge']; n=6+len(bridges)
        bridges.append([currency,*[numeric(b[k]) for k in ('opening_arr','new_arr','expansion_arr','contraction_arr','churn_arr','rounding_residual_arr','closing_arr')],Formula(f'=B{n}+C{n}+D{n}-E{n}-F{n}+G{n}-H{n}')])
        retention.append([currency,*[numeric(metric[k]) for k in ('opening_mrr','expansion_mrr','contraction_mrr','churn_mrr','nrr','grr','logo_churn','gross_revenue_churn','net_revenue_churn')]])
    ws=table('ARR Bridge',['Currency','Opening ARR','New ARR','Expansion ARR','Contraction ARR','Churn ARR','Rounding residual','Closing ARR','Balance check'],bridges or [['Not calculated in this run']])
    ws.conditional_formatting.add(f'I6:I{max(6,ws.max_row)}',CellIsRule(operator='notEqual',formula=['0'],fill=PatternFill('solid',fgColor='FCE1E1')))
    ws=table('NRR and GRR',['Currency','Opening MRR','Expansion MRR','Contraction MRR','Churn MRR','NRR','GRR','Logo churn','Gross revenue churn','Net revenue churn'],retention or [['Not calculated in this run']], 'Ratios are Python-calculated on unrounded rates. New-to-opening-cohort revenue is excluded from NRR.')
    for row in ws.iter_rows(min_row=6,min_col=6,max_col=10):
        for c in row:
            c.number_format='0.00%'
    cohort=result.get('cohorts',{})
    table('Cohort Analysis',['Cohort month','Measurement date','Currency','Opening logos','Retained logos','Logo retention','Baseline MRR','Cohort MRR','Revenue retention','Customer IDs'],
        [[date.fromisoformat(r[k]) if k in ('cohort_month','measurement_date') else r[k] if k not in ('logo_retention','baseline_mrr','cohort_mrr','revenue_retention') else numeric(r[k]) for k in ('cohort_month','measurement_date','currency','opening_logos','retained_logos','logo_retention','baseline_mrr','cohort_mrr','revenue_retention','customer_ids')] for r in cohort.get('rows') or []] or [['Not calculated or requires review; see exceptions']],cohort.get('policy'))
    reconciliation=result.get('reconciliation',{})
    table('Reconciliation',['Currency','Source total','Control total','Signed adjustments','Unexplained difference','Materiality','Status','Evidence IDs'],
        [[r['currency'],*[numeric(r[k]) for k in ('source_total','comparison_total','explained_adjustments','unexplained_difference','materiality')],r['status'],r['evidence_ids']] for r in reconciliation.get('results',[])] or [['No independent reconciliation in this run']],reconciliation.get('policy'))
    exceptions=list(result.get('exceptions',[]))
    exceptions.extend({'code':'MANAGEMENT_COMPARISON','record_id':r['id'],'reason':r} for r in result.get('management_comparisons',[]) if r['status']=='REQUIRES_REVIEW')
    table('Exceptions and Review',['Code','Record ID','Reason','Review status'],[[e['code'],e['record_id'],e['reason'],'UNREVIEWED'] for e in exceptions] or [['No detected exceptions','Run','This does not certify completeness or independent validation','UNREVIEWED']])
    definitions=[['Selected definition',result['definition']],['Usage treatment',dataset.billing_policy.usage],['Credit treatment',dataset.billing_policy.credits],['Complete history asserted',(result.get('request') or {}).get('complete_history',False)],['Snapshot policy',monthly[-1].get('policy','Not calculated')],['Retention policy',comparison.get('policy','Not calculated')],['Run status',result['status']],['Rounding','Half-even, two decimal display; originals retained'],['Excel checks',notes]]
    table('Metric Definitions',['Definition / assumption','Value'],definitions).column_dimensions['B'].width=110
    lineage=[[e.id,e.dataset_id,e.source_file,'sha256:'+e.sha256,e.record_id,'CALLER_ASSERTED'] for e in dataset.evidence]
    table('Evidence Lineage',['Evidence ID','Dataset ID','Source file','Declared SHA-256','Source record','Verification'],lineage,result.get('lineage_granularity'))
    metadata=[['Run ID',result['run_id']],['Engine version',result['engine_version']],['Input SHA-256',result.get('source_file_sha256')],['Request',result.get('request',{})],['Transformations',result.get('transformations',[])],['Excel recalculation','Required on open; openpyxl does not evaluate formulas'],['Evidence review','Unreviewed; source-file hashes are not independently verified']]
    table('Calculation Metadata',['Key','Value'],metadata).column_dimensions['B'].width=110
    for row in workbook['Cohort Analysis'].iter_rows(min_row=6):
        for column in ('F','I'):
            workbook['Cohort Analysis'][f'{column}{row[0].row}'].number_format='0.00%'
    workbook['Executive Summary'].column_dimensions['E'].width=36
    workbook['Monthly Revenue'].column_dimensions['G'].width=60
    workbook['Cohort Analysis'].column_dimensions['J'].width=50
    workbook['Reconciliation'].column_dimensions['H'].width=60
    workbook['Evidence Lineage'].column_dimensions['D'].width=68
    for ws in workbook:
        for row in ws.iter_rows(min_row=6):
            height=32
            for cell in row:
                if cell.data_type=='s' and cell.value is not None:
                    width=ws.column_dimensions[cell.column_letter].width or 24
                    lines=sum(max(1,(len(line)+int(width)-2)//max(1,int(width)-1)) for line in str(cell.value).split('\n'))
                    height=max(height,lines*14+8)
            if height>409:
                raise ValueError('Source text exceeds readable Excel row height; use saved JSON for this dataset')
            ws.row_dimensions[row[0].row].height=height
    for ws_name,column in [('ARR Bridge','I'),('Reconciliation','E')]:
        for row in workbook[ws_name].iter_rows(min_row=6):
            workbook[ws_name][f'{column}{row[0].row}'].number_format='0.00;(0.00);0.00'
    assert workbook.sheetnames == SHEETS
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with NamedTemporaryFile(suffix='.xlsx',dir=path.parent,delete=False) as handle:
            temporary=Path(handle.name)
        workbook.save(temporary)
        # Package integrity and formula-reference checks, not a claim of Excel recalculation.
        saved=load_workbook(temporary,data_only=False)
        if saved.sheetnames != SHEETS or saved.vba_archive is not None:
            raise ValueError('Workbook package verification failed')
        for ws in saved:
            for row in ws:
                for cell in row:
                    if cell.data_type=='f' and '#REF!' in cell.value:
                        raise ValueError('Broken workbook formula')
        saved.close()
        # Exclusive creation never overwrites an existing destination and works in
        # restricted Windows environments that prohibit hard-link creation.
        with path.open('xb') as destination, temporary.open('rb') as source:
            shutil.copyfileobj(source,destination)
    finally:
        workbook.close()
        if temporary and temporary.exists():
            temporary.unlink()
    return path
