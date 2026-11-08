"""
tools/make_icons.py
-------------------
Generate the PNG icon set used by the GUI, drawn entirely with QPainter
(no external files, no network). Run it to (re)create assets/*.png:

    QT_QPA_PLATFORM=offscreen python tools/make_icons.py

Theme: IT / code / "hacker".
  defender.png -> fingerprint        (identity / authentication) — indigo
  tester.png   -> terminal >_ window (command line / probe)      — green
  locked.png   -> closed padlock                                  — red
  active.png   -> online node (status LED)                        — green

Each icon is rendered on a transparent 96x96 canvas; the GUI scales it
down smoothly, so it stays crisp on high-DPI screens.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (  # noqa: E402
    QColor, QGuiApplication, QImage, QPainter, QPainterPath, QPen,
)

C = 96  # canvas size

INDIGO = "#4f6ef7"
GREEN = "#30a46c"
RED = "#e5484d"
AMBER = "#f5a524"
AMBER_LIGHT = "#ffd27a"

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def _canvas() -> tuple[QImage, QPainter]:
    img = QImage(C, C, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing, True)
    return img, p


def _pen(color: str, width: float) -> QPen:
    pen = QPen(QColor(color))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    return pen


def _save(img: QImage, name: str) -> None:
    path = os.path.join(ASSETS, f"{name}.png")
    img.save(path, "PNG")
    print("wrote", path)


# --- defender: fingerprint -------------------------------------------------

def make_defender() -> None:
    """Firewall: an indigo brick wall with an amber flame."""
    img, p = _canvas()

    # --- brick wall ---
    p.setPen(_pen(INDIGO, 4.2))
    p.setBrush(Qt.NoBrush)
    x0, x1, top, bottom = 16, 80, 44, 82
    rows = 3
    h = (bottom - top) / rows
    p.drawRoundedRect(QRectF(x0, top, x1 - x0, bottom - top), 3, 3)
    ys = [top + h, top + 2 * h]
    for y in ys:
        p.drawLine(QPointF(x0, y), QPointF(x1, y))
    # running-bond vertical mortar (offset every other row)
    verts = [
        (top, ys[0], (32, 48, 64)),
        (ys[0], ys[1], (24, 40, 56, 72)),
        (ys[1], bottom, (32, 48, 64)),
    ]
    for ya, yb, xs in verts:
        for x in xs:
            p.drawLine(QPointF(x, ya), QPointF(x, yb))

    # --- flame ---
    flame = QPainterPath()
    flame.moveTo(48, 44)
    flame.cubicTo(64, 34, 58, 18, 52, 13)
    flame.cubicTo(44, 20, 42, 24, 40, 30)
    flame.cubicTo(36, 37, 42, 42, 48, 44)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(AMBER))
    p.drawPath(flame)

    inner = QPainterPath()
    inner.moveTo(48, 41)
    inner.cubicTo(56, 34, 52, 24, 49, 20)
    inner.cubicTo(45, 25, 44, 30, 43, 33)
    inner.cubicTo(41, 37, 45, 40, 48, 41)
    p.setBrush(QColor(AMBER_LIGHT))
    p.drawPath(inner)

    p.end()
    _save(img, "defender")


# --- tester: terminal window with >_ ---------------------------------------

def make_tester() -> None:
    img, p = _canvas()
    green = QColor(GREEN)

    # window frame
    p.setPen(_pen(GREEN, 5.0))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(14, 22, 68, 52), 10, 10)

    # title bar divider + two "traffic light" dots
    p.drawLine(QPointF(14, 36), QPointF(82, 36))
    p.setPen(Qt.NoPen)
    p.setBrush(green)
    p.drawEllipse(QPointF(23, 29), 2.3, 2.3)
    p.drawEllipse(QPointF(31, 29), 2.3, 2.3)

    # prompt ">" chevron
    p.setBrush(Qt.NoBrush)
    p.setPen(_pen(GREEN, 5.0))
    chevron = QPainterPath()
    chevron.moveTo(25, 47)
    chevron.lineTo(33, 55)
    chevron.lineTo(25, 63)
    p.drawPath(chevron)

    # cursor "_"
    p.drawLine(QPointF(39, 63), QPointF(54, 63))
    p.end()
    _save(img, "tester")


# --- locked: closed padlock ------------------------------------------------

def make_locked() -> None:
    img, p = _canvas()
    red = QColor(RED)

    # shackle (closed, both legs on the body)
    p.setPen(_pen(RED, 5.5))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(33, 36, 30, 30), 0 * 16, 180 * 16)
    p.drawLine(QPointF(33, 51), QPointF(33, 52))
    p.drawLine(QPointF(63, 51), QPointF(63, 52))

    # body
    p.drawRoundedRect(QRectF(26, 50, 44, 32), 7, 7)

    # keyhole
    p.setPen(Qt.NoPen)
    p.setBrush(red)
    p.drawEllipse(QPointF(48, 62), 4.2, 4.2)
    stem = QPainterPath()
    stem.moveTo(48, 63)
    stem.lineTo(51.5, 74)
    stem.lineTo(44.5, 74)
    stem.closeSubpath()
    p.drawPath(stem)
    p.end()
    _save(img, "locked")


# --- active: online node (status LED) --------------------------------------

def make_active() -> None:
    img, p = _canvas()
    green = QColor(GREEN)

    # outer ring
    p.setPen(_pen(GREEN, 5.5))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(48, 48), 24, 24)

    # inner filled dot (centered — a clean status LED)
    p.setPen(Qt.NoPen)
    p.setBrush(green)
    p.drawEllipse(QPointF(48, 48), 11, 11)
    p.end()
    _save(img, "active")


def main() -> None:
    app = QGuiApplication.instance() or QGuiApplication([])
    os.makedirs(ASSETS, exist_ok=True)
    make_defender()
    make_tester()
    make_locked()
    make_active()
    print("done -> ", ASSETS)


if __name__ == "__main__":
    main()
