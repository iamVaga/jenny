"""Validated data contracts. Dates are ISO calendar dates; money is decimal text."""
from datetime import date
from decimal import Decimal
import re
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, BeforeValidator, model_validator, StrictBool


def decimal_input(value):
    if isinstance(value, (float, bool)):
        raise ValueError("Use decimal text, Decimal, or integer; floats are forbidden")
    return value


def calendar_date(value):
    if type(value) is date:
        return value
    if not isinstance(value,str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}",value) is None:
        raise ValueError("Use an ISO calendar date YYYY-MM-DD")
    return date.fromisoformat(value)


def cadence(value):
    if type(value) is not int:
        raise ValueError("Cadence must be integer months")
    return value


CalendarDate = Annotated[date, BeforeValidator(calendar_date)]
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
    approved: StrictBool = False


class PeriodRecord(Record):
    start: CalendarDate
    end: CalendarDate  # exclusive

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
    cadence_months: Annotated[Literal[1, 12], BeforeValidator(cadence)]
    classification: Literal["fixed_recurring", "one_time", "usage", "hybrid", "unknown"]
    cancelled_on: CalendarDate | None = None
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
    invoice_date: CalendarDate
    payment_date: CalendarDate | None = None
    currency: Currency
    amount: Amount
    evidence_id: Identifier


class InvoiceLineItem(Record):
    invoice_id: Identifier
    currency: Currency
    amount: Nonnegative
    discount: Nonnegative = Decimal("0")
    tax: Nonnegative = Decimal("0")
    classification: Literal["fixed_recurring", "one_time", "usage", "hybrid", "unknown"]
    service_start: CalendarDate | None = None
    service_end: CalendarDate | None = None
    normalization_months: Positive | None = None
    contract_id: Identifier | None = None
    evidence_id: Identifier

    @model_validator(mode="after")
    def valid_line(self):
        if self.discount > self.amount:
            raise ValueError("Discount exceeds line amount")
        if self.service_start and self.service_end and self.service_end <= self.service_start:
            raise ValueError("Service end must be after start")
        return self


class CreditNote(Record):
    invoice_id: Identifier
    line_item_id: Identifier | None = None
    issue_date: CalendarDate
    currency: Currency
    amount: Nonnegative
    evidence_id: Identifier


class Refund(Record):
    invoice_id: Identifier
    credit_note_id: Identifier | None = None
    payment_date: CalendarDate
    currency: Currency
    amount: Nonnegative
    evidence_id: Identifier


class CurrencyRate(Record):
    rate_date: CalendarDate
    source_currency: Currency
    target_currency: Currency
    rate: Positive
    evidence_id: Identifier


class RevenueAdjustment(PeriodRecord):
    currency: Currency
    amount: Amount
    reason: Literal["deferred_revenue", "accrued_revenue", "credits", "timing", "taxes", "fx", "recognition", "other"]
    evidence_id: Identifier


class AccountingPeriod(PeriodRecord):
    complete: StrictBool


class FinancialMetricDefinition(Record):
    version: Identifier
    methodology: str


class CalculationRun(Record):
    input_sha256: str
    measurement_date: CalendarDate
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


class AccountingControl(PeriodRecord):
    currency: Currency
    amount: Amount
    basis: Literal["recognized_revenue", "billing_net", "general_ledger"]
    materiality: Nonnegative = Decimal("0.01")
    evidence_id: Identifier


class ManagementMetric(Record):
    measurement_date: CalendarDate
    currency: Currency
    metric: Literal["mrr", "arr"]
    amount: Nonnegative
    methodology: str | None = None
    evidence_id: Identifier


class BillingPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    usage: Literal["exclude", "review"] = "review"
    credits: Literal["deduct", "exclude"] = "deduct"


class Dataset(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    organization: Organization
    customers: tuple[Customer, ...]
    contracts: tuple[Contract, ...]
    evidence: tuple[EvidenceReference, ...]
    mappings: tuple[CustomerIdentityMapping, ...] = ()

    invoices: tuple[Invoice, ...] = ()
    line_items: tuple[InvoiceLineItem, ...] = ()
    credit_notes: tuple[CreditNote, ...] = ()
    refunds: tuple[Refund, ...] = ()
    currency_rates: tuple[CurrencyRate, ...] = ()
    adjustments: tuple[RevenueAdjustment, ...] = ()
    accounting_periods: tuple[AccountingPeriod, ...] = ()
    controls: tuple[AccountingControl, ...] = ()
    management_metrics: tuple[ManagementMetric, ...] = ()
    billing_policy: BillingPolicy = BillingPolicy()
