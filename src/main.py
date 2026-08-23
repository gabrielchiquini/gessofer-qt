import logging
import sys
from pathlib import Path

from PySide6 import QtCore
from PySide6.QtWidgets import QApplication

from backend.services.backup_service import BackupService
from di.injector_module import get_injector
from frontend.app import MainWindow
from frontend.factories.certificate_status_view_factory import CertificateStatusViewFactory
from frontend.factories.expense_list_view_factory import ExpenseListViewFactory
from frontend.factories.order_edit_list_view_factory import OrderEditListViewFactory
from frontend.factories.product_list_view_factory import ProductListViewFactory


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='{asctime} | {levelname:<8} | {name:<12} | {message}'
    )
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # 2. Map Qt message types to Python log levels
    def qt_message_handler(mode, context, message):
        logger = logging.getLogger("QT")
        if mode == QtCore.QtMsgType.QtDebugMsg:
            logger.debug(message)
        elif mode == QtCore.QtMsgType.QtInfoMsg:
            logger.info(message)
        elif mode == QtCore.QtMsgType.QtWarningMsg:
            logger.warning(message)
        elif mode == QtCore.QtMsgType.QtCriticalMsg:
            logger.error(message)
        elif mode == QtCore.QtMsgType.QtFatalMsg:
            logger.critical(message)

    # 3. Register the handler before creating the QApplication
    QtCore.qInstallMessageHandler(qt_message_handler)
    app = QApplication(sys.argv)

    app.setStyle("FluentUI3")
    app.setApplicationName("Gessofer")
    app.setOrganizationName("Gessofer")
    src_dir = Path(__file__).resolve().parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    # Initialize DI container and resolve factory types
    injector = get_injector()

    product_list_view_factory: ProductListViewFactory = injector.get(ProductListViewFactory)
    order_edit_list_view_factory: OrderEditListViewFactory = injector.get(OrderEditListViewFactory)
    expense_list_view_factory: ExpenseListViewFactory = injector.get(ExpenseListViewFactory)
    certificate_status_view_factory: CertificateStatusViewFactory = injector.get(CertificateStatusViewFactory)

    window = MainWindow(
        product_list_view_factory=product_list_view_factory,
        order_edit_list_view_factory=order_edit_list_view_factory,
        expense_list_view_factory=expense_list_view_factory,
        certificate_status_view_factory=certificate_status_view_factory,
    )
    window.show()

    # ── Backup check (non-blocking, silent failure) ──────────────────
    try:

        injector = get_injector()
        backup_service = injector.get(BackupService)
        backup_service.create_backup()
        backup_service.prune_backups()
    except Exception as exc:
        # Backup failure must NOT prevent the app from launching.
        logging.getLogger(__name__).error(
            "Falha ao realizar backup do banco de dados: %s", exc
        )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
