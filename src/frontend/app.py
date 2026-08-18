from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QWidget

from injector_module import get_injector
from bridge.product import ProductBridge
from bridge.order import OrderBridge
from bridge.order_summary import OrderSummaryBridge
from bridge.expense import ExpenseBridge
from bridge.certificate import CertificateBridge
from bridge.nfe import NfeBridge
from frontend.business import BusinessService
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
        # ── DI initialization ──────────────────────────────────────────
        injector = get_injector()
        self._product_bridge: ProductBridge = injector.get(ProductBridge)
        self._order_bridge: OrderBridge = injector.get(OrderBridge)
        self._order_summary_bridge: OrderSummaryBridge = injector.get(OrderSummaryBridge)
        self._expense_bridge: ExpenseBridge = injector.get(ExpenseBridge)
        self._certificate_bridge: CertificateBridge = injector.get(CertificateBridge)
        self._nfe_bridge: NfeBridge = injector.get(NfeBridge)
        self._business_service: BusinessService = injector.get(BusinessService)
        # ────────────────────────────────────────────────────────────────
        self._build_ui()
        

    def _build_ui(self) -> None:
        """Build the main window UI."""
        self.nav_bar = NavigationBar(self)
        self.setMenuBar(self.nav_bar)
        
        
        
        product_list = ProductListView(self, product_bridge=self._product_bridge)
        self.setCentralWidget(product_list)

        
        self.nav_bar.item_clicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, label: str, group_title: str) -> None:
        """Handle navigation item clicks."""
        if label == "Pedidos" and group_title == "Notas":
            product_list = ProductListView(self, product_bridge=self._product_bridge)
            self.setCentralWidget(product_list)

        elif label == "Cadastrar" and group_title == "Notas":
            order_view = OrderEditListView(
                self,
                order_bridge=self._order_bridge,
                order_summary_bridge=self._order_summary_bridge,
                business_service=self._business_service,
                nfe_bridge=self._nfe_bridge,
            )
            self.setCentralWidget(order_view)

        elif label == "Status" and group_title == "Certificado":
            cert_view = CertificateStatusView(
                self,
                certificate_bridge=self._certificate_bridge,
            )
            self.setCentralWidget(cert_view)

        elif label == "Lista" and group_title == "Despesas":
            expense_view = ExpenseListView(
                self,
                expense_bridge=self._expense_bridge,
            )
            self.setCentralWidget(expense_view)

        elif label == "Cadastrar" and group_title == "Despesas":
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Em desenvolvimento",
                "A tela de cadastro de despesas ainda está em desenvolvimento.",
            )
