from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget

from frontend.constants import MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from frontend.components.navbar import NavigationBar
from frontend.factories import (
    ProductListViewFactory,
    OrderEditListViewFactory,
    ExpenseListViewFactory,
    CertificateStatusViewFactory,
)


class MainWindow(QMainWindow):
    """Main application window with menu bar and product list."""

    def __init__(
        self,
        parent: QWidget,
        product_list_view_factory: ProductListViewFactory,
        order_edit_list_view_factory: OrderEditListViewFactory,
        expense_list_view_factory: ExpenseListViewFactory,
        certificate_status_view_factory: CertificateStatusViewFactory,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Gessofer")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self._product_list_view_factory: ProductListViewFactory = product_list_view_factory
        self._order_edit_list_view_factory: OrderEditListViewFactory = order_edit_list_view_factory
        self._expense_list_view_factory: ExpenseListViewFactory = expense_list_view_factory
        self._certificate_status_view_factory: CertificateStatusViewFactory = certificate_status_view_factory
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the main window UI."""
        self.nav_bar = NavigationBar(self)
        self.setMenuBar(self.nav_bar)
        product_list = self._product_list_view_factory(self)
        self.setCentralWidget(product_list)
        self.nav_bar.item_clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, label: str, group_title: str) -> None:
        """Handle navigation item clicks."""
        if label == "Pedidos" and group_title == "Notas":
            view = self._product_list_view_factory(self)
            self.setCentralWidget(view)
        elif label == "Cadastrar" and group_title == "Notas":
            view = self._order_edit_list_view_factory(self)
            self.setCentralWidget(view)
        elif label == "Status" and group_title == "Certificado":
            view = self._certificate_status_view_factory(self)
            self.setCentralWidget(view)
        elif label == "Lista" and group_title == "Despesas":
            view = self._expense_list_view_factory(self)
            self.setCentralWidget(view)
        elif label == "Cadastrar" and group_title == "Despesas":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Em desenvolvimento",
                "A tela de cadastro de despesas ainda está em desenvolvimento.",
            )
