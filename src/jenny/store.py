"""Append-only through this API; hashes detect alteration, not authenticated provenance."""
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import date
from pathlib import Path
from .engine import calculate
from .ingestion import MAX_BYTES, parse_dataset


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, indent=2).encode("utf-8")


def confined(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError("Store path escapes root")
    return resolved


def read_bounded(path: Path) -> bytes:
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Stored record exceeds size limit")
    return raw


def analyze_bytes(raw: bytes, as_of: date) -> dict:
    result = calculate(parse_dataset(raw), as_of)
    result["source_file_sha256"] = digest(raw)
    return result


def save_run(root: Path, raw: bytes, as_of: date | None = None, *, config=None) -> tuple[str, dict]:
    """Content-derived storage ID includes exact source bytes, unlike calculation ID."""
    if config is None:
        result = analyze_bytes(raw, as_of)
    else:
        from .application import execute
        result = execute(raw, config)
    storage_id = digest((result["run_id"] + digest(raw)).encode())
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = confined(root, root / storage_id)
    if destination.exists():
        existing = replay_run(root, storage_id)
        if existing != result:
            raise ValueError("Existing run does not match")
        return storage_id, result
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=root))
    try:
        result_raw = encode(result)
        if len(result_raw)>MAX_BYTES:
            raise ValueError("Saved result exceeds 5 MiB replay limit")
        (staging / "input.json").write_bytes(raw)
        (staging / "result.json").write_bytes(result_raw)
        (staging / "manifest.json").write_bytes(encode({
            "format_version": 1, "storage_id": storage_id,
            "source_sha256": digest(raw), "result_sha256": digest(result_raw),
        }))
        if config is not None:
            (staging / "request.json").write_bytes(encode(config.model_dump(mode='json')))
        # Rename the complete directory; never update a saved run in place.
        os.rename(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(confined(root, staging))
    return storage_id, result


def replay_run(root: Path, storage_id: str) -> dict:
    if re.fullmatch(r"[a-f0-9]{64}", storage_id) is None:
        raise ValueError("Invalid storage ID")
    root = root.resolve(strict=True)
    directory = confined(root, root / storage_id)
    raw = read_bounded(confined(root, directory / "input.json"))
    saved_raw = read_bounded(confined(root, directory / "result.json"))
    manifest = json.loads(read_bounded(confined(root, directory / "manifest.json")))
    if manifest != {"format_version": 1, "storage_id": storage_id,
                    "source_sha256": digest(raw), "result_sha256": digest(saved_raw)}:
        raise ValueError("Snapshot integrity check failed")
    saved = json.loads(saved_raw)
    request_path = confined(root, directory / 'request.json')
    if 'request' in saved:
        from .application import RunConfig, execute
        request = RunConfig.model_validate_json(read_bounded(request_path))
        actual = execute(raw, request)
    else:
        actual = analyze_bytes(raw, date.fromisoformat(saved["measurement_date"]))
    expected_id = digest((actual["run_id"] + digest(raw)).encode())
    if expected_id != storage_id or actual != saved:
        raise ValueError("Saved run differs from current engine replay")
    return actual
