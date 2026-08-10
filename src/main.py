import logging
import sys
from pathlib import Path

from Custom_Widgets.QCustomQToolTip import QCustomQToolTipFilter
from PySide6.QtWidgets import QApplication

from frontend.app import MainWindow


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
    window = MainWindow()
    window.show()

    # ── Backup check (non-blocking, silent failure) ──────────────────
    try:
        from backend.injector_module import get_injector
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
