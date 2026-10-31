"""Local JSON CLI. Source inputs and generated outputs remain separate."""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from .engine import DEFINITION
from .retention import DEFINITION as RETENTION_DEFINITION
from .ingestion import parse_dataset
from .store import confined, read_bounded, replay_run, save_run
from .application import RunConfig, execute


def load_input(root: Path, name: str):
    root = root.resolve(strict=True)
    path = confined(root, root / name)
    if not path.is_file():
        raise ValueError('Input must be a file within --root')
    raw = read_bounded(path)
    return parse_dataset(raw), hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None=None) -> int:
    parser = argparse.ArgumentParser(prog='jenny')
    parser.add_argument('command',choices=['validate','analyze','compare','cohorts','reconcile','report','replay','export','sample','benchmark'])
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--input')
    parser.add_argument('--as-of',type=date.fromisoformat)
    parser.add_argument('--definition',choices=[DEFINITION,RETENTION_DEFINITION,'billing_v1','billing_retention_v1'])
    parser.add_argument('--store',type=Path,default=Path('outputs/runs'))
    parser.add_argument('--save',action='store_true')
    parser.add_argument('--run-id')
    parser.add_argument('--opening',type=date.fromisoformat)
    parser.add_argument('--closing',type=date.fromisoformat)
    parser.add_argument('--confirm-complete-history',action='store_true')
    parser.add_argument('--reporting-currency')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--format',choices=['xlsx'],default='xlsx')
    args=parser.parse_args(argv)
    if args.output and args.command not in ('sample','export'):
        parser.error('output is supported only for sample and export')
    if args.reporting_currency and args.command != 'analyze':
        parser.error('reporting-currency is supported only for analyze snapshots')
    if args.save and args.command not in ('analyze','compare','cohorts','reconcile','report'):
        parser.error('save requires a calculation command')
    if args.command in ('sample','benchmark') and (args.input or args.run_id or args.as_of or args.opening or args.closing or args.definition):
        parser.error('sample/benchmark do not accept calculation inputs or dates')
    if (args.command in ('replay','export') or (args.command=='reconcile' and args.run_id)) and args.definition:
        parser.error('Stored runs use their retained definition; overrides are not allowed')
    if args.command in ('export','replay') or (args.command=='reconcile' and args.run_id):
        if not args.run_id or args.input or args.as_of or args.opening or args.closing or args.save:
            parser.error('Stored-run commands require run-id, without input, date or save flags')
    elif args.command not in ('sample','benchmark'):
        if not args.input or args.run_id:
            parser.error('Source commands require input and do not accept run-id')
        if args.command in ('compare','reconcile','report'):
            if not args.opening or not args.closing or args.as_of:
                parser.error('Period commands require opening and closing, without as-of')
        elif not args.as_of or args.opening or args.closing:
            parser.error('Snapshot/cohort commands require as-of, without opening or closing')
    if args.command=='validate' and args.save:
        parser.error('Validation does not save a calculation run')
    if args.command not in ('compare','cohorts','report') and args.confirm_complete_history:
        parser.error('Complete-history flag requires compare, cohorts or report')
    if args.definition in (RETENTION_DEFINITION,'billing_retention_v1') and args.command!='compare':
        parser.error('Retention definitions require compare')
    if args.command=='compare' and args.definition==DEFINITION:
        parser.error('Use contract_retention_v1 for contract comparisons')
    try:
        store=confined(Path.cwd(),Path.cwd()/args.store)
        if args.command=='sample':
            from .synthetic import demo_dataset
            path=confined(Path.cwd(),Path.cwd()/(args.output or Path('outputs/sample.json')))
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('x',encoding='utf-8') as handle:
                json.dump(demo_dataset(),handle,indent=2)
            print(json.dumps({'status':'CREATED','output':str(path)}))
            return 0
        if args.command=='benchmark':
            from .benchmark import run_benchmark
            result=run_benchmark()
            print(json.dumps(result,indent=2))
            return 0 if result['failed']==0 else 2
        if args.command in ('replay','export') or (args.command=='reconcile' and args.run_id):
            result=replay_run(store,args.run_id)
            if args.command=='export':
                from .export import export_workbook
                raw=read_bounded(confined(store,store/args.run_id/'input.json'))
                output=confined(Path.cwd(),Path.cwd()/(args.output or Path('outputs')/f'{args.run_id}.xlsx'))
                if output.is_relative_to(store):
                    raise ValueError('Exports must be outside snapshot store')
                path=export_workbook(parse_dataset(raw),result,output)
                print(json.dumps({'status':'EXPORTED','output':str(path),'run_status':result['status'],'formula_recalculation':'Required in Excel; Python values independently calculated'}))
                return 0
            if args.command=='reconcile':
                if 'reconciliation' not in result:
                    raise ValueError('Saved run has no reconciliation; save a report or reconciliation job')
                result=result['reconciliation']
                print(json.dumps(result,indent=2,sort_keys=True))
                return 0 if result['status']=='RECONCILED' else 2
            result['storage_id']=args.run_id
            result['replay_verified']=True
        else:
            raw=read_bounded(confined(args.root,args.root/args.input))
            definition='billing_v1' if args.definition in ('billing_v1','billing_retention_v1') else DEFINITION
            config=RunConfig(action='analyze' if args.command=='validate' else args.command,definition=definition,
                as_of=args.as_of,opening=args.opening,closing=args.closing,complete_history=args.confirm_complete_history,
                reporting_currency=args.reporting_currency)
            if args.save:
                source=confined(args.root,args.root/args.input)
                if source.is_relative_to(store):
                    raise ValueError('Source input must be outside output store')
                storage_id,result=save_run(store,raw,config=config)
                result['storage_id']=storage_id
            else:
                result=execute(raw,config)
            if args.command=='validate':
                result.pop('metrics')
        print(json.dumps(result,indent=2,sort_keys=True))
        return 2 if result['status']=='REQUIRES_REVIEW' or result.get('exceptions') else 0
    except (OSError,ValueError,TypeError,KeyError,RecursionError):
        print(json.dumps({'status':'INVALID_INPUT','reason':'Input, configuration, output path or saved-run integrity failed validation'}))
        return 2
