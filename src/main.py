import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from frontend.app import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
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
