from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QPixmap, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def svg_to_pixmap(svg_path: str, width: int, height: int) -> QPixmap:
    # 1. Initialize the SVG renderer with your file
    renderer = QSvgRenderer(svg_path)

    # 2. Create a blank, transparent QImage at your target size
    image = QImage(QSize(width, height), QImage.Format.Format_RGBA8888_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)  # Clears background

    # 3. Use QPainter to paint the vector graphic into the image
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()  # Crucial to close the painter before converting

    # 4. Convert the rendered high-res image into a QPixmap
    return QPixmap.fromImage(image)
