from math import floor


def cents_to_display(cents: int) -> str:
    """
    Convert integer cents to Brazilian currency display string.
    Example: 123456 -> "1234,56"
    Example: -123456 -> "-1234,56"
    Example: 0 -> "0,00"
    Example: 99 -> "0,99"
    """
    if cents < 0:
        sign = "-"
        abs_cents = -cents
    else:
        sign = ""
        abs_cents = cents

    # Integer part: group by thousands with "." separator
    integer_part = abs_cents // 100
    decimal_part = abs_cents % 100

    return f"{sign}{integer_part},{decimal_part:02d}"


def parse_currency_to_cents(value: str) -> int:
    value_normalized = value.strip().replace(",", ".")
    try:
        result = floor(float(value_normalized) * 100)
        return result
    except ValueError:
        return 0
