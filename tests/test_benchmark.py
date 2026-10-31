import pytest
from jenny.benchmark import cases, run_case

@pytest.mark.parametrize('case',cases(),ids=lambda c:c['name'])
def test_independent_benchmark(case):
    run_case(case)
