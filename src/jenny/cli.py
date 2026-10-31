"""Local CLI. Results are JSON; review, integrity and input failures exit nonzero."""
import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from .engine import calculate, DEFINITION
from .retention import compare, DEFINITION as RETENTION_DEFINITION
from .ingestion import MAX_BYTES, parse_dataset
from .store import confined, read_bounded, replay_run, save_run


def load_input(root: Path, name: str):
    root = root.resolve(strict=True)
    path = confined(root, root / name)
    if not path.is_file():
        raise ValueError("Input must be a file within --root")
    raw = read_bounded(path)
    return parse_dataset(raw), hashlib.sha256(raw).hexdigest()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="jenny")
    parser.add_argument("command", choices=["validate", "analyze", "replay", "compare"])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--input")
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--definition", choices=[DEFINITION, RETENTION_DEFINITION])
    parser.add_argument("--store", type=Path, default=Path("outputs/runs"))
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--run-id", help="Storage ID returned by analyze --save")
    parser.add_argument("--opening", type=date.fromisoformat)
    parser.add_argument("--closing", type=date.fromisoformat)
    parser.add_argument("--confirm-complete-history", action="store_true")
    args = parser.parse_args(argv)
    expected_definition = RETENTION_DEFINITION if args.command == "compare" else DEFINITION
    if args.definition is not None and args.definition != expected_definition:
        parser.error("Metric definition does not match command")
    if args.command != "compare" and (args.opening or args.closing or args.confirm_complete_history):
        parser.error("opening, closing and complete-history flags require compare")
    if args.command == "compare":
        if not args.input or not args.opening or not args.closing or args.as_of or args.run_id or args.save:
            parser.error("compare requires input, opening and closing; save, as-of and run-id are unsupported")
    elif args.command == "replay":
        if not args.run_id or args.input or args.as_of or args.save:
            parser.error("replay requires --run-id; input, as-of and save are not accepted")
    elif not args.input or not args.as_of or args.run_id:
        parser.error("validate/analyze require --input and --as-of; run-id is for replay")
    if args.command == "validate" and args.save:
        parser.error("--save is only supported by analyze")
    try:
        # Output storage must remain within the current workspace.
        store = confined(Path.cwd(), Path.cwd() / args.store)
        if args.command == "replay":
            result = replay_run(store, args.run_id)
            result["storage_id"] = args.run_id
            result["replay_verified"] = True
        else:
            path = confined(args.root, args.root / args.input)
            raw = read_bounded(path)
            if args.command == "compare":
                result = compare(parse_dataset(raw), args.opening, args.closing,
                                 complete_history=args.confirm_complete_history)
                result["source_file_sha256"] = hashlib.sha256(raw).hexdigest()
            elif args.save:
                # Do not overwrite source data by choosing it as a store member.
                if path.is_relative_to(store):
                    raise ValueError("Source input must be outside output store")
                storage_id, result = save_run(store, raw, args.as_of)
                result["storage_id"] = storage_id
            else:
                dataset = parse_dataset(raw)
                result = calculate(dataset, args.as_of)
                result["source_file_sha256"] = hashlib.sha256(raw).hexdigest()
            if args.command == "validate":
                result.pop("metrics")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2 if result["exceptions"] else 0
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        print(json.dumps({"status": "INVALID_INPUT", "reason": "Input or saved run failed validation or integrity checks"}))
        return 2
