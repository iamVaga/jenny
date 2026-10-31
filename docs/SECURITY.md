# Security baseline and limitations

Synthetic sample only. No outbound requests, secrets, telemetry, macros or spreadsheet
exports. CLI restricts resolved input paths to --root (default current directory), reads
at most 5 MiB, rejects duplicate JSON keys and malformed schemas, and avoids printing
raw invalid inputs. Inputs and generated stdout are separate; source data is not rewritten.
JSON is not an Excel formula execution surface. CSV/XLSX injection protection must be
implemented with the future exporters. Do not paste raw untrusted strings into spreadsheets.

This is not an OS sandbox: authorized callers choose root; symlink/path races and
resource exhaustion beyond the file size bound are not fully mitigated. Output contains
financial totals and IDs and must be handled as sensitive if real data is used later.
There is no authentication, encryption, access audit, immutable store or certification.
Schema validation and file hashes do not establish economic completeness or authenticity.


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
