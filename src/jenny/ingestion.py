"""Bounded strict JSON parsing shared by ingestion and snapshot replay."""
import json
from .models import Dataset

MAX_BYTES = 5 * 1024 * 1024


def parse_dataset(raw: bytes) -> Dataset:
    if len(raw) > MAX_BYTES:
        raise ValueError("Input exceeds 5 MiB limit")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON object key")
            result[key] = value
        return result
    return Dataset.model_validate(json.loads(raw, object_pairs_hook=pairs))
