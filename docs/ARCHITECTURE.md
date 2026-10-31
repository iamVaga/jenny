# Architecture and initial inspection

The workspace was empty. No README, dependencies, tests, engine, data models,
or Git metadata existed. Git reported that the directory is not a repository;
there was no branch or status to preserve. Python 3.13.1, Pydantic 2.10.5 and
pytest 9.1.1 were installed. Hypothesis was absent. No external services accessed.

A Python modular monolith keeps models (Pydantic contracts), engine (pure
calculation and cross-record checks), and CLI (bounded local JSON parsing) separate.
No database, frontend, LLM, agents, or network runtime is introduced.
Structured results carry definition, engine version, input digest and evidence IDs.
Decimal computations use a local 60-digit context and explicit half-even rounding.
Inputs remain unchanged. The CLI writes only stdout.

This slice deliberately does not implement persistence, FX conversion, billing-derived
metrics, reconciliation or Excel. Successful results are labelled unreconciled.
The canonical dataset hash identifies parsed inputs; a separate CLI hash identifies
exact source bytes. Ordering changes may change run IDs even if metrics are unchanged.


## Snapshot slice update

Added ingestion.py for shared strict JSON parsing and store.py for retained raw-input
snapshots, manifests and verified replay. CLI supports analyze --save and replay by
storage ID. Outputs remain inside the workspace and outside Git. Storage is append-only
through the API, not OS-enforced immutable storage; caller-supplied evidence hashes
remain unverified. Earlier first-slice persistence limitations above are superseded
by this update. Other financial limitations remain unchanged.

Full local suite: 60 passed, including 14 new snapshot/replay cases covering round-trip,
idempotence, input/result/manifest alteration, refusal to overwrite corrupted runs,
raw-byte identity, invalid IDs, recalculation mismatches, CLI replay, workspace bounds
and retained review exceptions. This is not a 60-scenario financial benchmark.
GitHub Actions is configured for Python 3.12/3.13; remote results are not yet verified.
