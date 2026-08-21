from __future__ import annotations

from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from bridge.product import ProductBridge
from frontend.views.product_list import ProductListView


@pytest.fixture
def product_list_widget(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[ProductListView, None, None]:
    """Create a ProductListView wired to the test database."""
    from di.injector_module import get_injector

    injector = get_injector()
    product_bridge: ProductBridge = injector.get(ProductBridge)

    widget = ProductListView(
        parent=None,
        product_bridge=product_bridge,
    )
    qtbot.addWidget(widget)
    widget.show()
    yield widget
    widget.deleteLater()
