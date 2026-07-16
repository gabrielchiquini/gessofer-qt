from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget

from frontend.constants import MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT
from frontend.navbar import NavigationBar
from frontend.order_edit_list import OrderEditListView
from frontend.product_list import ProductListView


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
            order_view.order_edited.connect(self._on_order_edited)
            self.setCentralWidget(order_view)

    def _on_order_edited(self, order_id: str) -> None:
        """Placeholder for order edit action. Future: open editor dialog."""
        pass
