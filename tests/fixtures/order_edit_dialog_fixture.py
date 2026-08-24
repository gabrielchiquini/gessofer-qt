from __future__ import annotations

from pathlib import Path
from typing import Generator

import pytest
from pytestqt.qtbot import QtBot
from sqlalchemy.engine import Engine

from backend.services.xml_import_service import XmlImportService
from di.injector_module import get_injector
from frontend.factories.nfe_search_dialog_factory import NfeSearchDialogFactory
from frontend.factories.order_edit_dialog_factory import OrderEditDialogFactory
from frontend.views.order_edit.nfe_search_dialog import NfeSearchDialog
from frontend.views.order_edit.order_edit_dialog import OrderEditDialog
from frontend.views.order_edit.product_row_widget import ProductRowWidget

_NFE_XML_PATH = Path(__file__).resolve().parent / "nfe.xml"


@pytest.fixture
def order_edit_dialog_existing(
        temp_engine: Engine,
        qtbot: QtBot,
) -> Generator[OrderEditDialog, None, None]:
    """Create an OrderEditDialog for editing existing Order A (seeded in DB)."""
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    dialog = factory(parent=None, order_id="order-a", order=None)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def order_edit_dialog_blank(
        temp_engine: Engine,
        qtbot: QtBot,
) -> Generator[OrderEditDialog, None, None]:
    """Create a blank OrderEditDialog (no order_id, no order — new order path)."""
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    dialog = factory(parent=None, order_id=None, order=None)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def order_edit_dialog_xml_import(
        temp_engine: Engine,
        qtbot: QtBot,
) -> Generator[OrderEditDialog, None, None]:
    """Create an OrderEditDialog pre-populated from the real nfe.xml.

    Uses BusinessService.import_xml() to parse docs/nfe.xml and produce
    a real Order dataclass (with correct product data, IPI, ICMS-ST
    from the XML).  No SEFAZ network calls are made.
    """
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    business_service: XmlImportService = injector.get(XmlImportService)

    result = business_service.parse_file(str(_NFE_XML_PATH))
    # The nfe.xml contains a single order
    order = result.orders[0]

    dialog = factory(parent=None, order_id=None, order=order)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()


@pytest.fixture
def product_row_widget(
        temp_engine: Engine,
        qtbot: QtBot,
) -> Generator[ProductRowWidget, None, None]:
    """Create a standalone ProductRowWidget for unit testing the row widget.

    Uses the OrderEditDialog's items_card to create a row so that
    the parent hierarchy is correct.
    """
    injector = get_injector()
    factory: OrderEditDialogFactory = injector.get(OrderEditDialogFactory)
    dialog = factory(parent=None, order_id=None, order=None)
    qtbot.addWidget(dialog)
    dialog.show()

    row: ProductRowWidget = dialog.items_card.add_row()
    qtbot.addWidget(row)
    yield row

    row.deleteLater()
    dialog.deleteLater()


@pytest.fixture
def nfe_search_dialog(
        temp_engine: Engine,
        qtbot: QtBot,
) -> Generator[NfeSearchDialog, None, None]:
    """Create an NfeSearchDialog wired to the test database."""
    injector = get_injector()
    factory: NfeSearchDialogFactory = injector.get(NfeSearchDialogFactory)
    dialog = factory(parent=None)
    qtbot.addWidget(dialog)
    dialog.show()
    yield dialog
    dialog.deleteLater()
