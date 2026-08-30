from pathlib import Path

is_compiled = "__compiled__" in globals()

if is_compiled:
    _base = Path(__file__).parent.parent
else:
    _base = Path(__file__).parent.parent

ASSETS_DIR = _base / "assets"
TRANSLATIONS_DIR = _base / "translations"

