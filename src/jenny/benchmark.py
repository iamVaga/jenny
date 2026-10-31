"""Independent checked-in scenario expectations, usable offline from installed package."""
import json
from importlib.resources import files
from pydantic import ValidationError
from .application import execute, RunConfig


def cases() -> list[dict]:
    return json.loads(files('jenny').joinpath('fixtures/benchmark.json').read_text(encoding='utf-8'))


def run_case(case: dict) -> None:
    try:
        result=execute(json.dumps(case['input']).encode(),RunConfig.model_validate(case['request']))
    except (ValidationError,ValueError):
        if case['invalid']:
            return
        raise
    if case['invalid']:
        raise AssertionError('Invalid input was accepted')
    for path,expected in case['expected'].items():
        actual=result
        for key in path.split('.'):
            actual=actual[int(key)] if isinstance(actual,list) else actual[key]
        if actual != expected:
            raise AssertionError(f'{path}: expected {expected!r}, got {actual!r}')
    codes={e['code'] for e in result['exceptions']}
    if not set(case['expected_codes']).issubset(codes):
        raise AssertionError(f"Missing exception codes {set(case['expected_codes'])-codes}")
    if not case['expected_codes'] and result['exceptions']:
        raise AssertionError(f'Unexpected exceptions: {sorted(codes)}')


def run_benchmark() -> dict:
    failures=[]
    scenarios=cases()
    for case in scenarios:
        try:
            run_case(case)
        except (AssertionError,ValueError,KeyError,TypeError) as error:
            failures.append({'case':case['name'],'reason':str(error)})
    return {'total':len(scenarios),'passed':len(scenarios)-len(failures),'failed':len(failures),'failures':failures}
