from __future__ import annotations

from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from frontend.factories.order_edit_list_view_factory import OrderEditListViewFactory
from frontend.views.order_edit.order_edit_list import OrderEditListView


@pytest.fixture
def order_list_widget(
    temp_engine: Engine,
    qtbot: QtBot,
) -> Generator[OrderEditListView, None, None]:
    """Create an OrderEditListView wired to the test database."""
    from di.injector_module import get_injector

    injector = get_injector()
    factory: OrderEditListViewFactory = injector.get(OrderEditListViewFactory)

    widget = factory(parent=None)
    qtbot.addWidget(widget)
    widget.show()
    yield widget
    widget.deleteLater()
