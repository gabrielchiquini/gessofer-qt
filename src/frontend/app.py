from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget

from frontend.constants import MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from frontend.components.navbar import NavigationBar
from frontend.views.order_edit.order_edit_list import OrderEditListView
from frontend.views.product_list import ProductListView
from frontend.views.certificate_status.certificate_status import CertificateStatusView
from frontend.views.expense_list import ExpenseListView


class MainWindow(QMainWindow):
    """Main application window with menu bar and product list."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Gessofer")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self._build_ui()
        

    def _build_ui(self) -> None:
        """Build the main window UI."""
        self.nav_bar = NavigationBar(self)
        self.setMenuBar(self.nav_bar)
        
        
        
        product_list = ProductListView(self)
        self.setCentralWidget(product_list)

        
        self.nav_bar.item_clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, label: str, group_title: str) -> None:
        """Handle navigation item clicks."""
        if label == "Pedidos" and group_title == "Notas":
            product_list = ProductListView(self)
            self.setCentralWidget(product_list)

        elif label == "Cadastrar" and group_title == "Notas":
            order_view = OrderEditListView(self)
            self.setCentralWidget(order_view)

        elif label == "Status" and group_title == "Certificado":
            cert_view = CertificateStatusView(self)
            self.setCentralWidget(cert_view)

        elif label == "Lista" and group_title == "Despesas":
            expense_view = ExpenseListView(self)
            self.setCentralWidget(expense_view)

        elif label == "Cadastrar" and group_title == "Despesas":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Em desenvolvimento",
                "A tela de cadastro de despesas ainda está em desenvolvimento.",
            )
