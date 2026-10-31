# Security baseline

Synthetic fixtures only. The runtime performs no network requests, telemetry, authentication,
external service calls, secret lookup or LLM inference. All output is local unless a user
explicitly publishes source through development tooling. No real customer data is bundled.
CLI JSON results intentionally include financial totals/IDs; there are no routine application
logs echoing malformed inputs, sensitive records or arbitrary path details.

Input files resolve under --root. Output files and stores resolve within the workspace;
source inputs cannot be saved from inside the output store, and workbook outputs cannot
replace snapshot members. The CLI reads at most 5 MiB, rejects duplicate JSON keys, malformed
schemas, floats as money, nonfinite values and extreme precision/exponents before arithmetic.
Retention/report history is bounded to 240 months. Identity conflicts and ambiguous joins
produce exceptions. Third-party data never grants access or instructions to the runtime.

Workbook source strings are forced to Excel string cells, including strings starting with
=,+,-,@. Only internally constructed Formula values become formulas; no source text is
interpolated into formulas. No macros or external workbook links are produced. XML control
characters are escaped visibly, not executed. Original source bytes remain in the snapshot.
No CSV or arbitrary XLSX ingestion is supported; this avoids implying safety for those formats.

Snapshot directories are append-only through the API, with integrity checks and full replay.
Export uses a validated temporary workbook and exclusive destination creation, never overwrite.
The final copy is not an atomic durable transaction; a process crash could leave a partial
export, which must be removed/re-exported by the user. Saved JSON remains the authoritative data.

This is not an OS sandbox. A trusted library caller can choose file paths; the CLI provides
containment guards. Local symlink/path races, resource exhaustion beyond current bounds,
permissions, backups, disk encryption, authentication, access audit and malicious privileged
actors are not comprehensively addressed. Exact rational arithmetic can be computationally
costly on adversarial normalization denominators. Do not expose this CLI as an untrusted public
service. No SOC 2, production-grade security or financial-compliance certification is claimed.
