from __future__ import annotations

from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from backend.services.order_service import OrderService
from frontend.views.product_list import ProductListView


@pytest.fixture
def product_list_widget(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[ProductListView, None, None]:
    """Create a ProductListView wired to the test database."""
    from di.injector_module import get_injector

    injector = get_injector()
    order_service: OrderService = injector.get(OrderService)

    widget = ProductListView(
        parent=None,
        order_service=order_service,
    )
    qtbot.addWidget(widget)
    widget.show()
    yield widget
    widget.deleteLater()
