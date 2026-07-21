import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from frontend.app import MainWindow
import logging

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
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
