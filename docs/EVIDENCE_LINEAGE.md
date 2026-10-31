# Evidence lineage and replay

Every application result includes raw input SHA-256, parsed input digest, selected request,
engine version, definition, assumptions, review status and transformation steps. Domain
snapshots retain contract or invoice-line IDs and evidence IDs; matched recurring credit IDs
are retained at customer level. Comparison rows retain both endpoint source references.
Cohort rows retain baseline/current snapshot run IDs and contributing contract/line/credit
and evidence references. Reconciliations retain billed/credit source IDs and control evidence.

application.contributing_records(raw, result, currency) validates the exact input hash and
returns contributing original contract, line, credit and parent invoice records. It filters
currency-specific financial branches rather than silently returning unrelated currencies.
engine.contributing_records retains the original contract-only interface.

Saved directories contain input.json, result.json, manifest.json and request.json for modern
jobs. The storage ID combines calculation identity and source byte hash. Complete staged
directories are renamed into place. Existing saved runs are verified and reused, never
updated by the API. Replay checks manifest/input/result hashes, reconstructs the typed
request and reruns the current engine, rejecting version, request or result drift.

This is source-record lineage and retained exact-input snapshots. It is not spreadsheet
cell-level lineage, a signed provenance chain, authenticated external evidence, or OS-enforced
immutable storage. A privileged local actor could replace files and hashes. External evidence
filenames/hashes are caller assertions; referenced files are never opened automatically.
Source row/record ID and file name are explicitly retained in EvidenceReference. The demo
uses all-zero hashes as synthetic markers, clearly labelled caller-asserted in the workbook.

Historical 0.1.0 runs may reject replay under 0.1.1; use the matching source checkout for
historical engine versions. Save/replay is bounded to 5 MiB per input/result record and fails
explicitly for oversized reports. Identical source bytes, request and engine yield identical
financial results; source ordering/formatting can intentionally change provenance identities.
