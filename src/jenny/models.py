"""Validated data contracts. Dates are ISO calendar dates; money is decimal text."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, model_validator


def decimal_input(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Use decimal text, Decimal, or integer; floats are forbidden")
    return value


Amount = Annotated[Decimal, BeforeValidator(decimal_input), Field(allow_inf_nan=False)]
Nonnegative = Annotated[Amount, Field(ge=0)]
Positive = Annotated[Amount, Field(gt=0)]
Identifier = Annotated[str, Field(min_length=1, max_length=256)]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: Identifier


class EvidenceReference(Record):
    dataset_id: Identifier
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    source_file: Identifier
    record_id: Identifier


class Organization(Record):
    name: Identifier


class Customer(Record):
    organization_id: Identifier
    name: Identifier
    parent_id: Identifier | None = None


class CustomerIdentityMapping(Record):
    source_customer_id: Identifier
    canonical_customer_id: Identifier | None = None
    relationship: Literal["rename", "duplicate", "parent", "reseller", "ambiguous"]
    approved: bool = False


class PeriodRecord(Record):
    start: date
    end: date  # exclusive

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("end must be after start (exclusive end)")
        return self


class Contract(PeriodRecord):
    organization_id: Identifier
    customer_id: Identifier
    currency: Currency
    amount: Nonnegative  # net commitment for one cadence, excluding tax
    cadence_months: Literal[1, 12]
    classification: Literal["fixed_recurring", "one_time", "usage", "hybrid", "unknown"]
    cancelled_on: date | None = None
    evidence_id: Identifier

    @model_validator(mode="after")
    def cancellation(self):
        if self.cancelled_on is not None and not self.start <= self.cancelled_on <= self.end:
            raise ValueError("cancellation must fall within contract period")
        return self


class Subscription(Record):
    contract_id: Identifier
    customer_id: Identifier


class Invoice(Record):
    customer_id: Identifier
    invoice_date: date
    payment_date: date | None = None
    currency: Currency
    amount: Amount
    evidence_id: Identifier


class InvoiceLineItem(PeriodRecord):
    invoice_id: Identifier
    amount: Amount
    classification: Literal["fixed_recurring", "one_time", "usage", "hybrid", "unknown"]


class CreditNote(Record):
    invoice_id: Identifier
    issue_date: date
    currency: Currency
    amount: Nonnegative
    evidence_id: Identifier


class Refund(Record):
    invoice_id: Identifier
    payment_date: date
    currency: Currency
    amount: Nonnegative
    evidence_id: Identifier


class CurrencyRate(Record):
    rate_date: date
    source_currency: Currency
    target_currency: Currency
    rate: Positive
    evidence_id: Identifier


class RevenueAdjustment(PeriodRecord):
    currency: Currency
    amount: Amount
    reason: Identifier
    evidence_id: Identifier


class AccountingPeriod(PeriodRecord):
    complete: bool


class FinancialMetricDefinition(Record):
    version: Identifier
    methodology: str


class CalculationRun(Record):
    input_sha256: str
    measurement_date: date
    definition_id: Identifier
    engine_version: Identifier


class ReconciliationResult(Record):
    currency: Currency
    source_total: Amount | None
    comparison_total: Amount | None
    explained_adjustments: Amount | None
    unexplained_difference: Amount | None
    materiality: Nonnegative
    status: Literal["RECONCILED", "RECONCILED_WITH_ADJUSTMENTS", "UNRECONCILED", "INSUFFICIENT_DATA", "REQUIRES_REVIEW"]
    evidence_ids: tuple[Identifier, ...]


class ReviewException(BaseModel):
    code: str
    record_id: str
    reason: str


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    organization: Organization
    customers: tuple[Customer, ...]
    contracts: tuple[Contract, ...]
    evidence: tuple[EvidenceReference, ...]
    mappings: tuple[CustomerIdentityMapping, ...] = ()
