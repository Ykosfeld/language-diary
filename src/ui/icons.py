"""Vector icons tailored for the minimalist diary paper aesthetic."""

from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer


def _svg_to_icon(svg_str: str, size: int = 24) -> QIcon:
    renderer = QSvgRenderer(QByteArray(svg_str.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def get_quill_idle_icon(color: str, size: int = 24) -> QIcon:
    """Resting fountain pen nib / quill representing saved state."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 19l7-7 3 3-7 7-3-3z"/>
        <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18"/>
        <path d="M2 2l7.586 7.586"/>
        <circle cx="11" cy="11" r="1" fill="{color}"/>
    </svg>
    """
    return _svg_to_icon(svg, size)


def get_quill_writing_icon(color: str, ink_color: str, size: int = 24) -> QIcon:
    """Tilted pen nib actively writing with an ink flow accent."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 19l7-7 3 3-7 7-3-3z"/>
        <path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18"/>
        <path d="M2 2l7.586 7.586"/>
        <circle cx="11" cy="11" r="1.5" fill="{ink_color}" stroke="{ink_color}"/>
        <path d="M2 22c1-2 3-3 5-3" stroke="{ink_color}" stroke-width="2"/>
    </svg>
    """
    return _svg_to_icon(svg, size)


def get_book_history_icon(color: str, size: int = 24) -> QIcon:
    """Journal / bound book representing entry history."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
        <line x1="8" y1="6" x2="16" y2="6"/>
        <line x1="8" y1="10" x2="14" y2="10"/>
    </svg>
    """
    return _svg_to_icon(svg, size)


def get_bookmark_today_icon(color: str, size: int = 24) -> QIcon:
    """Ribbon bookmark representing returning to today's page."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
        <line x1="12" y1="7" x2="12" y2="11"/>
        <line x1="10" y1="9" x2="14" y2="9"/>
    </svg>
    """
    return _svg_to_icon(svg, size)


def get_wax_seal_icon(color: str, is_locked: bool = False, size: int = 24) -> QIcon:
    """Wax seal or vintage lock stamp representing finalized/locked status."""
    fill_color = color if is_locked else "none"
    inner_stroke = "#fbf6eb" if is_locked else color
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="{fill_color}" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="9"/>
        <rect x="9" y="11" width="6" height="5" rx="1" fill="{fill_color}" stroke="{inner_stroke}"/>
        <path d="M10 11V9a2 2 0 0 1 4 0v2" stroke="{inner_stroke}"/>
    </svg>
    """
    return _svg_to_icon(svg, size)


def get_midnight_clock_icon(color: str, size: int = 24) -> QIcon:
    """Subtle moon/clock icon representing midnight lock policy."""
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
    """
    return _svg_to_icon(svg, size)
