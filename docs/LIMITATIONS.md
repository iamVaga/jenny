# Known limitations

This is the v0.1 local backend, not a production SaaS service. No frontend, deployment,
real customer testing, authentication, accounting-system connectors, recognition engine,
automatic methodology inference, tax accounting or compliance certification is included.
JSON is the input contract; source-system CSV/XLSX adapters remain future work.

Usage/hybrid revenue requires explicit exclusion or classification/splitting. Billing lines
require an analyst-supplied normalization period; missing service periods never receive an
invented fallback. Parent/subsidiary and reseller consolidation remain review boundaries.
Approved rename/duplicate mappings work, but unmarked duplicate entities cannot be inferred.
Linked billing windows must match contractual net rates; legitimate unusual amendments need
explicit source representation or review rather than automatic overrides.

History and accounting-period completeness are caller assertions. Cohorts are first observed,
not independently verified lifetime acquisition. A positive month-end baseline is required;
customers that begin and churn within that initial month require review. Retention measures
endpoint changes, not every intervening churn/reactivation. Simultaneous currencies and
currency migrations for a customer require retention review. No FX-neutral retention is inferred.

FX uses exact-date direct rates only for snapshot reporting. Source-currency retention remains
separate. Currency codes are syntax checked, and two-decimal monetary reporting is an explicit
provisional policy. Original values and exact rate fractions remain available in JSON/source
records. Engine schema/definition changes can invalidate old replay; use matching source versions.

External evidence and control independence/authenticity are not verified. Record-level lineage
is implemented; cell-level spreadsheet lineage is not claimed. Storage is not OS-enforced
immutable, cryptographically signed or encrypted. Inputs/results are bounded to 5 MiB and
reports/cohorts to 240 months. Very large or text-heavy Excel exports fail explicitly.

Excel is a presentation/check workbook. Python values are independently calculated; formulas
require recalculation and editing workbook source cells does not rerun Python. Excel numeric
outputs are restricted to 15 significant digits; original precision is retained as source text.
Formula recalculation was tested in the bundled spreadsheet engine, not native Microsoft Excel.
There is no claim of production readiness or independent validation based on tests alone.
