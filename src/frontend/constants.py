from __future__ import annotations

from typing import Any

NAV_GROUPS: list[dict[str, Any]] = [
    {"title": "Notas", "items": [
        {"label": "Pedidos", "group": "Notas"},
        {"label": "Cadastrar", "group": "Notas"},
    ]},
    {"title": "Despesas", "items": [
        {"label": "Lista", "group": "Despesas"},
        {"label": "Cadastrar", "group": "Despesas"},
    ]},
]

SIDEBAR_WIDTH: int = 200
SIDEBAR_HEADER_HEIGHT: int = 56
NAV_ITEM_HEIGHT: int = 40
CONTENT_MARGINS: int = 40
MIN_WINDOW_WIDTH: int = 1024
MIN_WINDOW_HEIGHT: int = 768
PRODUCT_PAGE_SIZE: int = 50
