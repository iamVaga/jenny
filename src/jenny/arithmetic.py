"""Shared exact arithmetic policies. Financial operations never use binary floats."""
from contextlib import contextmanager
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction


@contextmanager
def financial_context():
    with localcontext() as ctx:
        ctx.prec = 128
        ctx.rounding = ROUND_HALF_EVEN
        yield ctx


def rounded(value, places: int) -> Decimal:
    """Round an exact rational half-even, avoiding repeating-division tie drift."""
    value = Fraction(value)
    scaled = value * (10 ** places)
    sign = -1 if scaled < 0 else 1
    whole, remainder = divmod(abs(scaled.numerator), scaled.denominator)
    if remainder*2 > scaled.denominator or (remainder*2 == scaled.denominator and whole%2):
        whole += 1
    with financial_context():
        return Decimal(sign*whole).scaleb(-places)


def decimal_rate(value) -> Decimal:
    value = Fraction(value)
    with financial_context():
        return Decimal(value.numerator)/Decimal(value.denominator)


def money(value) -> str:
    return format(rounded(value,2),'f')


def ratio(value, denominator) -> str | None:
    return format(rounded(Fraction(value)/Fraction(denominator),8),'f') if denominator else None


def issue(code: str, record_id: str, reason: str) -> dict:
    return {'code':code, 'record_id':record_id, 'reason':reason}



def exact_money(value: Decimal) -> str:
    """At least cents for display, retaining any additional source precision."""
    return money(value) if value.as_tuple().exponent >= -2 else format(value,'f')
