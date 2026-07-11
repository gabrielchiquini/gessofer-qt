import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType

from backend.qml.qml_backend import BackendManager

def main() -> None:
    # High-DPI scaling support
    # QApplication.setHighDpiScaleFactorRoundingPolicy(
    #     1  # PixelExact
    # )

    app = QApplication(sys.argv)
    app.setApplicationName("Gessofer")
    app.setOrganizationName("Gessofer")

    # Resolve the QML file path relative to the script location
    qml_path = Path(__file__).resolve().parent.parent

    # Ensure Python can find the 'backend' package (src/) and the
    # 'App.Backend' QML Python module (App/).  These directories must
    # be on sys.path before any QML that imports App.Backend is loaded.
    src_dir = Path(__file__).resolve().parent  # src/
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    app_dir = qml_path / "App"
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))

    if not qml_path.exists():
        print(f"Error: QML file not found at {qml_path}", file=sys.stderr)
        sys.exit(1)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_path))

    # Register BackendManager as a singleton accessible from QML
    backend = BackendManager()
    engine.rootContext().setContextProperty("BackendManager", backend)

    engine.loadFromModule("App", "Main")

    if not engine.rootObjects():
        print("Error: Failed to load QML", file=sys.stderr)
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
