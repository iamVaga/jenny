import copy
import json
from datetime import date
from decimal import Decimal, localcontext, ROUND_DOWN
from pathlib import Path
import pytest
from pydantic import ValidationError
from jenny.models import Dataset
from jenny.engine import calculate, contributing_records
from jenny.cli import main, load_input

AS_OF = date(2026, 6, 1)

@pytest.fixture
def raw():
    return json.loads(Path("data/sample.json").read_text())

def run(raw):
    return calculate(Dataset.model_validate(raw), AS_OF)

def metric(raw):
    return run(raw)["metrics"]["USD"]

# Expectations below are explicit arithmetic, never production-generated.
@pytest.mark.parametrize("amount,cadence,mrr,arr", [
    ("100",1,"100.00","1200.00"),
    ("1200",12,"100.00","1200.00"),
    ("120",1,"120.00","1440.00"),
    ("80",1,"80.00","960.00"),
    ("0",1,"0.00","0.00"),
    ("100",12,"8.33","99.96"),
    ("1.005",1,"1.00","12.00"),
    ("1.015",1,"1.02","12.24"),
])
def test_hand_calculated_commitments(raw, amount, cadence, mrr, arr):
    raw["contracts"] = raw["contracts"][:1]
    raw["contracts"][0].update(amount=amount,cadence_months=cadence)
    assert metric(raw)["mrr"] == mrr
    assert metric(raw)["arr"] == arr

def test_combined(raw):
    assert metric(raw)["mrr"] == "200.00"
    assert metric(raw)["arr"] == "2400.00"

@pytest.mark.parametrize("changes", [
    {"start":"2026-06-02"}, {"end":"2026-06-01"},
    {"cancelled_on":"2026-06-01"}, {"classification":"one_time"},
])
def test_exclusions(raw, changes):
    raw["contracts"][0].update(changes)
    assert metric(raw)["mrr"] == "100.00"

def test_start_inclusive(raw):
    raw["contracts"][0]["start"] = "2026-06-01"
    assert metric(raw)["mrr"] == "200.00"

@pytest.mark.parametrize("classification", ["usage","hybrid","unknown"])
def test_unsupported(raw, classification):
    raw["contracts"][0]["classification"] = classification
    assert run(raw)["metrics"] is None
    assert run(raw)["exceptions"][0]["code"] == "UNSUPPORTED_CLASSIFICATION"

@pytest.mark.parametrize("field,value", [
    ("amount",-1), ("amount",1.1), ("amount",True), ("amount","NaN"),
    ("amount","Infinity"), ("currency","usd"), ("cadence_months",3),
    ("end","2025-01-01"), ("start","2026-02-30"), ("cancelled_on","2028-01-01")
])
def test_invalid(raw, field, value):
    raw["contracts"][0][field] = value
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)

def test_missing_amount(raw):
    del raw["contracts"][0]["amount"]
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)

@pytest.mark.parametrize("collection", ["contracts","customers","evidence"])
def test_duplicates(raw, collection):
    raw[collection].append(copy.deepcopy(raw[collection][0]))
    assert run(raw)["metrics"] is None
    assert any(e["code"] == "DUPLICATE_ID" for e in run(raw)["exceptions"])

@pytest.mark.parametrize("field,value,code", [
    ("customer_id","absent","MISSING_CUSTOMER"),
    ("evidence_id","absent","MISSING_EVIDENCE"),
    ("organization_id","absent","ORGANIZATION_MISMATCH"),
    ("amount","1e100","AMOUNT_PRECISION")
])
def test_referential_failures(raw, field, value, code):
    raw["contracts"][0][field] = value
    result = run(raw)
    assert result["metrics"] is None
    assert any(e["code"] == code for e in result["exceptions"])

def test_overlap(raw):
    raw["contracts"][1]["customer_id"] = "monthly"
    assert run(raw)["exceptions"][0]["code"] == "OVERLAPPING_COMMITMENTS"

def test_identity(raw):
    raw["mappings"] = [{"id":"map","source_customer_id":"old","relationship":"ambiguous"}]
    assert run(raw)["metrics"] is None

def test_parent(raw):
    raw["customers"][0]["parent_id"] = "annual"
    assert run(raw)["exceptions"][0]["code"] == "IDENTITY_REVIEW"

def test_currency_separation(raw):
    raw["contracts"][1]["currency"] = "EUR"
    result = run(raw)
    assert result["metrics"]["EUR"]["mrr"] == "100.00"
    assert result["metrics"]["USD"]["mrr"] == "100.00"

def test_reproducible_context(raw):
    first = run(raw)
    with localcontext() as context:
        context.prec = 4
        context.rounding = ROUND_DOWN
        assert run(raw) == first
    assert first["status"] == "CALCULATED_UNRECONCILED"

def test_arr_invariant_and_order(raw):
    first = run(raw)
    raw["contracts"].reverse()
    second = run(raw)
    assert first["metrics"] == second["metrics"]
    m = first["metrics"]["USD"]
    assert Decimal(m["arr"]) == 12 * Decimal(m["mrr"])

def test_lineage(raw):
    dataset = Dataset.model_validate(raw)
    result = calculate(dataset, AS_OF)
    assert {c["id"] for c in contributing_records(dataset,result,"USD")} == {"c-monthly","c-annual"}
    raw["contracts"][0]["amount"] = "999"
    with pytest.raises(ValueError):
        contributing_records(Dataset.model_validate(raw),result,"USD")

def test_cli(capsys):
    assert main(["analyze","--input","data/sample.json","--as-of","2026-06-01"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["metrics"]["USD"]["arr"] == "2400.00"
    assert len(result["source_file_sha256"]) == 64

def test_bad_json(tmp_path,capsys):
    (tmp_path / "bad.json").write_text('{"a":1,"a":2}')
    assert main(["validate","--root",str(tmp_path),"--input","bad.json","--as-of","2026-06-01"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "INVALID_INPUT"

def test_path_escape(tmp_path):
    with pytest.raises(ValueError):
        load_input(tmp_path, str(Path("data/sample.json").resolve()))

def test_no_eligible_contracts(raw):
    raw["contracts"] = []
    assert run(raw)["metrics"] == {}
