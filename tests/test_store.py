from datetime import date
from pathlib import Path
import json
import pytest
from jenny.cli import main
from jenny.store import save_run, replay_run

AS_OF = date(2026, 6, 1)

@pytest.fixture
def source():
    return Path('data/sample.json').read_bytes()

def test_save_replay_and_idempotence(tmp_path, source):
    storage_id, result = save_run(tmp_path, source, AS_OF)
    assert replay_run(tmp_path, storage_id) == result
    assert save_run(tmp_path, source, AS_OF) == (storage_id, result)
    assert len(list(tmp_path.iterdir())) == 1

@pytest.mark.parametrize('filename', ['input.json', 'result.json', 'manifest.json'])
def test_tampering_detected(tmp_path, source, filename):
    storage_id, _ = save_run(tmp_path, source, AS_OF)
    (tmp_path / storage_id / filename).write_text('{}')
    with pytest.raises((ValueError, KeyError)):
        replay_run(tmp_path, storage_id)

def test_corrupt_existing_run_not_overwritten(tmp_path, source):
    storage_id, _ = save_run(tmp_path, source, AS_OF)
    target = tmp_path / storage_id / 'input.json'
    target.write_text('{}')
    with pytest.raises(ValueError):
        save_run(tmp_path, source, AS_OF)
    assert target.read_text() == '{}'

def test_raw_bytes_distinguish_storage_ids(tmp_path, source):
    first_id, first = save_run(tmp_path, source, AS_OF)
    second_id, second = save_run(tmp_path, source + b'\n', AS_OF)
    assert first['run_id'] == second['run_id']
    assert first_id != second_id
    assert replay_run(tmp_path, first_id) == first
    assert replay_run(tmp_path, second_id) == second

@pytest.mark.parametrize('identifier', ['../escape', '/absolute', 'bad', 'A'*64])
def test_invalid_storage_id(tmp_path, identifier):
    with pytest.raises(ValueError):
        replay_run(tmp_path, identifier)

def test_replay_requires_same_result(tmp_path, source):
    from jenny.store import digest, encode
    storage_id, _ = save_run(tmp_path, source, AS_OF)
    directory = tmp_path / storage_id
    saved = json.loads((directory / 'result.json').read_bytes())
    saved['metrics']['USD']['arr'] = '9999.00'
    saved_raw = encode(saved)
    (directory / 'result.json').write_bytes(saved_raw)
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    manifest['result_sha256'] = digest(saved_raw)
    (directory / 'manifest.json').write_bytes(encode(manifest))
    with pytest.raises(ValueError, match='differs'):
        replay_run(tmp_path, storage_id)

def test_cli_saved_flow(tmp_path, monkeypatch, capsys, source):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'source.json').write_bytes(source)
    assert main(['analyze','--input','source.json','--as-of','2026-06-01','--save']) == 0
    result = json.loads(capsys.readouterr().out)
    assert main(['replay','--run-id',result['storage_id']]) == 0
    replayed = json.loads(capsys.readouterr().out)
    assert replayed['replay_verified'] is True
    assert replayed['metrics'] == result['metrics']

def test_cli_external_store_rejected(tmp_path, monkeypatch, capsys, source):
    working = tmp_path / 'work'
    working.mkdir()
    monkeypatch.chdir(working)
    (working / 'source.json').write_bytes(source)
    assert main(['analyze','--input','source.json','--as-of','2026-06-01','--save','--store','../outside']) == 2
    assert not (tmp_path / 'outside').exists()

def test_review_run_can_be_preserved(tmp_path, source):
    dataset = json.loads(source)
    dataset['contracts'][0]['customer_id'] = 'missing'
    raw = json.dumps(dataset).encode()
    storage_id, result = save_run(tmp_path, raw, AS_OF)
    assert result['metrics'] is None
    assert replay_run(tmp_path, storage_id)['status'] == 'REQUIRES_REVIEW'
