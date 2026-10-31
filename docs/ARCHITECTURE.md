# Architecture

Initial inspection found an empty workspace, no financial engine or Git repository,
and Python 3.13/Pydantic v2/pytest available. The project now uses a modular Python
monolith with no runtime network dependencies.

models.py owns frozen Pydantic schemas; ingestion.py performs bounded duplicate-key
rejecting JSON ingestion. validation.py checks cross-record integrity and implements
explicit approved rename/duplicate identity resolution. Parent, reseller and ambiguous
mappings require review, as do conflicts and cycles. Every source record remains in
retained raw bytes; transformations are recorded rather than silently rewriting sources.

engine.py is the contract snapshot definition. billing.py is the independent billing
run-rate definition and exact-date reporting FX view. arithmetic.py provides half-even
rounding and local Decimal contexts. Exact rational rate intermediates prevent repeating
monthly divisions from drifting across half-cent ties; money enters and leaves as Decimal
or decimal text. No binary floating-point financial arithmetic is used.

retention.py compares snapshots; cohorts.py groups first-observed acquisition months;
reconciliation.py compares net billed amounts to separately supplied accounting controls.
definitions.py exposes an inspectable versioned metric-definition registry.
application.py validates typed job configuration and orchestrates deterministic jobs.
store.py saves complete directories of raw input, request, result and hash manifest;
replay checks bytes and reruns the matching configuration against the current engine.
export.py produces the 13 required diligence worksheets without macros or network links.
cli.py exposes the complete local lifecycle and explicit nonzero review statuses.

Tests separate independently specified benchmark expectations from production arithmetic.
The installed package contains fixtures/benchmark.json. scripts/build_benchmark.py
materializes the named hand-specified scenarios and never calls production calculations.

Changes in engine version, input bytes, definition/configuration or review assumptions
produce distinct application run IDs. Existing historical engine versions are not bundled;
use a matching source checkout for historical replay. Version 0.1.0 snapshots may fail
replay after schema/engine upgrades; this is surfaced as an integrity/version mismatch.
