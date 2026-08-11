from datetime import date, datetime

BR_DATE_FORMAT = "%d/%m/%Y"
ISO_DATE_FORMAT = "%Y-%m-%d"
MONTH_ORDER_FORMAT = "%m/%Y"        # MM/yyyy for orders
MONTH_EXPENSE_FORMAT = "%Y-%m"      # YYYY-MM for expenses


def br_date_to_iso(br_date: str) -> str:
    """
    Convert BR format 'dd/MM/yyyy' to ISO 'yyyy-MM-dd'.
    Returns empty string if parsing fails.
    """
    try:
        return date.strptime(br_date, BR_DATE_FORMAT).strftime(ISO_DATE_FORMAT)
    except ValueError:
        return ""


def iso_to_br_date(iso_date: str) -> str:
    """
    Convert ISO 'yyyy-MM-dd' to BR 'dd/MM/yyyy'.
    Returns empty string if parsing fails.
    """
    try:
        return date.strptime(iso_date, ISO_DATE_FORMAT).strftime(BR_DATE_FORMAT)
    except ValueError:
        return ""

def datetime_to_br_date(date_obj: date) -> str:
    """
    Convert DATETIME to BR 'dd/MM/yyyy'.
    Returns empty string if parsing fails.
    """
    try:
        return date_obj.strftime(BR_DATE_FORMAT)
    except ValueError:
        return ""


def parse_month_for_orders(month: str) -> tuple[int, int]:
    """
    Parse month string in 'MM/yyyy' format to (month, year) tuple.
    Example: "07/2024" -> (7, 2024)

    Returns (month: int, year: int).

    Raises ValueError for invalid format.
    """
    parts = month.strip().split("/")
    if len(parts) != 2:
        raise ValueError(f"Formato de mes invalido: '{month}'. Esperado 'MM/yyyy'.")

    m = int(parts[0])
    y = int(parts[1])

    if not (1 <= m <= 12):
        raise ValueError(f"Mes invalido: {m}. Deve estar entre 1 e 12.")
    if y < 1900 or y > 2100:
        raise ValueError(f"Ano invalido: {y}. Deve estar entre 1900 e 2100.")

    return m, y


def parse_month_for_expenses(month: str) -> str:
    """
    Validate and return month string in 'YYYY-MM' format.
    Example: "2024-07" -> "2024-07"

    Raises ValueError for invalid format.
    """
    try:
        date.strptime(month, "%Y-%m")
        return month
    except ValueError:
        raise ValueError(f"Formato de mes invalido: '{month}'. Esperado 'YYYY-MM'.")


def current_month_orders() -> str:
    """Return the current month in 'MM/yyyy' format for orders."""
    now = datetime.now()
    return now.strftime("%m/%Y")

def format_time_now() -> str:
    """Return current time in 'HH:mm' format for save messages."""
    return datetime.now().strftime("%H:%M")
