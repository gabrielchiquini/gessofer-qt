def cents_to_display(cents: int) -> str:
    """
    Convert integer cents to Brazilian currency display string.
    Example: 123456 -> "1.234,56"
    Example: -123456 -> "-1.234,56"
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

    # Format integer part with dots as thousand separators
    int_str = str(integer_part)
    formatted = ""
    while len(int_str) > 3:
        formatted = "." + int_str[-3:] + formatted
        int_str = int_str[:-3]
    formatted = int_str + formatted

    return f"{sign}{formatted},{decimal_part:02d}"


def parse_currency_to_cents(value: str) -> int:
    """
    Parse a Brazilian currency display string to integer cents.
    Handles both "." as thousand separator and "," as decimal separator.
    Also handles raw numbers without separators.

    Examples:
        "1.234,56" -> 123456
        "1234.56"  -> 123456 (if comma is used as thousand sep)
        "123456"   -> 123456 (raw number, treated as cents)
        "0,99"     -> 99
        "0,00"     -> 0
        ""          -> 0 (empty string -> zero)

    Returns 0 for empty or unparseable input.
    """
    if not value or not value.strip():
        return 0

    s = value.strip()

    # Determine separators
    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # Determine which is the decimal separator
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma > last_dot:
            # Brazilian format: "1.234,56"
            s = s.replace(".", "").replace(",", ".")
        else:
            # European format: "1,234.56"
            s = s.replace(",", "").replace(".", ",")
    elif has_comma:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif has_dot:
        parts = s.rsplit(".", 1)
        if len(parts) == 2 and len(parts[1]) == 3:
            s = s.replace(".", "")
        else:
            pass

    try:
        result = round(float(s) * 100)
        return result
    except ValueError:
        return 0
