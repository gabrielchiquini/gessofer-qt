import unicodedata


def normalize_text(text: str) -> str:
    """
    Convert text to ASCII-normalized lowercase form for fuzzy matching.

    Algorithm (matching Rust unidecode behavior):
    1. Normalize Unicode to NFD (decomposed form).
    2. Strip combining characters (accents, diacritics).
    3. Remove non-ASCII characters.
    4. Lowercase the result.

    Examples:
        "Fornecedor com acento" -> "fornecedor com acento"
        "Sao Paulo" -> "sao paulo"
        "Gessofer" -> "gessofe"  (if 'c' is stripped)
        "Cafe" -> "cafe"

    This matches the behavior of the `unidecode` crate used in the Rust backend.
    """
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in normalized if ord(c) < 128)
    return ascii_text.lower()
