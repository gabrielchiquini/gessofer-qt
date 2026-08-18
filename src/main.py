import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QWidget

from frontend.app import MainWindow
from di.injector_module import get_injector
from frontend.factories import (
    ProductListViewFactory,
    OrderEditListViewFactory,
    ExpenseListViewFactory,
    CertificateStatusViewFactory,
)


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        style='{',
        format='{asctime} | {levelname:<8} | {name:<12} | {message}'
    )
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
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
        from backend.services.backup_service import BackupService
        from backend.database.connection import discover_database_path
        from backend.utils.backup import discover_backup_dir

        injector = get_injector()
        backup_service = injector.get(BackupService)
        db_path = discover_database_path()
        backup_service.create_backup(db_path)
        backup_service.prune_backups()
    except Exception as exc:
        # Backup failure must NOT prevent the app from launching.
        logging.getLogger(__name__).error(
            "Falha ao realizar backup do banco de dados: %s", exc
        )

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
