"""Theme and styling definitions for the minimalist diary interface."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ThemeColors:
    window_bg: str
    card_bg: str
    text: str
    subtle_text: str
    border: str
    accent: str
    button_bg: str
    button_hover: str
    button_text: str
    status_dot_draft: str
    status_dot_locked: str


THEMES: Dict[str, ThemeColors] = {
    "sepia": ThemeColors(
        window_bg="#f4ecd8",
        card_bg="#fbf6eb",
        text="#3d312a",
        subtle_text="#8c7e72",
        border="#e2d6c1",
        accent="#8c4b2d",
        button_bg="#ebe0cb",
        button_hover="#ded0b6",
        button_text="#3d312a",
        status_dot_draft="#6a9955",
        status_dot_locked="#a35745",
    ),
    "solarized_light": ThemeColors(
        window_bg="#eee8d5",
        card_bg="#fdf6e3",
        text="#657b83",
        subtle_text="#93a1a1",
        border="#e0d6be",
        accent="#268bd2",
        button_bg="#e2dcbf",
        button_hover="#d3cbab",
        button_text="#586e75",
        status_dot_draft="#859900",
        status_dot_locked="#cb4b16",
    ),
    "paper_dark": ThemeColors(
        window_bg="#191919",
        card_bg="#242424",
        text="#d6d6d6",
        subtle_text="#858585",
        border="#383838",
        accent="#4ec9b0",
        button_bg="#2f2f2f",
        button_hover="#3c3c3c",
        button_text="#e0e0e0",
        status_dot_draft="#4ec9b0",
        status_dot_locked="#e06c75",
    ),
}


def get_theme(theme_name: str) -> ThemeColors:
    return THEMES.get(theme_name, THEMES["sepia"])


def generate_stylesheet(theme_name: str, font_family: str, font_size: int) -> str:
    c = get_theme(theme_name)
    font_stack = f'"{font_family}", "Linux Libertine", "Baskerville", "Georgia", "DejaVu Serif", serif'

    return f"""
    QMainWindow {{
        background-color: {c.window_bg};
    }}

    QWidget#CentralWidget {{
        background-color: {c.window_bg};
    }}

    QFrame#PaperContainer {{
        background-color: {c.card_bg};
        border: 1px solid {c.border};
        border-radius: 8px;
    }}

    QLabel#DateLabel {{
        color: {c.text};
        font-family: {font_stack};
        font-size: {font_size + 2}pt;
        font-weight: 600;
    }}

    QLabel#StatusLabel {{
        color: {c.subtle_text};
        font-family: {font_stack};
        font-size: {max(font_size - 3, 10)}pt;
    }}

    QLabel#LockedBanner {{
        background-color: {c.button_bg};
        color: {c.subtle_text};
        font-family: {font_stack};
        font-size: {max(font_size - 2, 11)}pt;
        font-style: italic;
        padding: 6px 12px;
        border-radius: 4px;
        border: 1px dashed {c.border};
    }}

    QComboBox {{
        background-color: {c.button_bg};
        color: {c.button_text};
        font-family: {font_stack};
        font-size: {max(font_size - 2, 11)}pt;
        border: 1px solid {c.border};
        border-radius: 4px;
        padding: 4px 10px;
        min-width: 70px;
    }}

    QComboBox:hover {{
        background-color: {c.button_hover};
    }}

    QComboBox::drop-down {{
        border: 0px;
    }}

    QPushButton {{
        background-color: {c.button_bg};
        color: {c.button_text};
        font-family: {font_stack};
        font-size: {max(font_size - 2, 11)}pt;
        border: 1px solid {c.border};
        border-radius: 4px;
        padding: 5px 12px;
    }}

    QPushButton:hover {{
        background-color: {c.button_hover};
    }}

    QPushButton:disabled {{
        opacity: 0.5;
        color: {c.subtle_text};
    }}

    QPushButton#FinalizeButton {{
        border: 1px solid {c.accent};
        font-weight: 500;
    }}

    QPlainTextEdit#DiaryEditor {{
        background-color: transparent;
        color: {c.text};
        font-family: {font_stack};
        font-size: {font_size}pt;
        line-height: 1.6;
        border: none;
        selection-background-color: {c.border};
        selection-color: {c.text};
    }}

    QScrollBar:vertical {{
        background: {c.card_bg};
        width: 10px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {c.border};
        min-height: 20px;
        border-radius: 5px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
