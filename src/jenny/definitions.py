"""Inspectable immutable definition registry; changed semantics require a new ID/version."""
from .models import FinancialMetricDefinition
from .engine import POLICY as CONTRACT_POLICY
from .billing import POLICY as BILLING_POLICY
from .retention import POLICY as RETENTION_POLICY


def metric_definitions() -> tuple[FinancialMetricDefinition, ...]:
    policies = {
        'contract_snapshot_v1':CONTRACT_POLICY,
        'billing_v1':BILLING_POLICY,
        'contract_retention_v1':RETENTION_POLICY,
        'billing_retention_v1':RETENTION_POLICY+'; billing-derived endpoint rates',
        'contract_observed_cohorts_v1':'First-observed positive contract month; month-end positive baseline; subsequent month-end cohorts',
        'billing_observed_cohorts_v1':'First-observed positive billing eligibility month; month-end positive baseline; subsequent month-end cohorts',
        'billing_accounting_reconciliation_v1':'Net billed lines by invoice date less credits by issue date plus signed explained adjustments minus independent control',
    }
    return tuple(FinancialMetricDefinition(id=key,version='1',methodology=value) for key,value in policies.items())
