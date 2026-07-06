import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine



def main():
    # High-DPI scaling support
    # QApplication.setHighDpiScaleFactorRoundingPolicy(
    #     1  # PixelExact
    # )

    app = QApplication(sys.argv)
    app.setApplicationName("Gessofer")
    app.setOrganizationName("Gessofer")

    # Resolve the QML file path relative to the script location
    qml_path = Path(__file__).resolve().parent.parent
    if not qml_path.exists():
        print(f"Error: QML file not found at {qml_path}", file=sys.stderr)
        sys.exit(1)

    engine = QQmlApplicationEngine()
    engine.addImportPath(qml_path)
    print(qml_path)
    engine.loadFromModule("App", "Main")

    if not engine.rootObjects():
        print("Error: Failed to load QML", file=sys.stderr)
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
