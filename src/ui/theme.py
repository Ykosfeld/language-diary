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
        window_bg="#f0e6cf",
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
        window_bg="#e8e0cb",
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
        window_bg="#181818",
        card_bg="#222222",
        text="#d6d6d6",
        subtle_text="#858585",
        border="#363636",
        accent="#4ec9b0",
        button_bg="#2a2a2a",
        button_hover="#383838",
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

    /* Ultra-Slim Left Side Rail */
    QFrame#SideBar {{
        background-color: transparent;
        border: none;
        min-width: 26px;
        max-width: 28px;
    }}

    QPushButton.IconButton {{
        background-color: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 3px;
        min-width: 24px;
        max-width: 24px;
        min-height: 24px;
        max-height: 24px;
    }}

    QPushButton.IconButton:hover {{
        background-color: {c.button_hover};
        border: 1px solid {c.border};
    }}

    QPushButton.IconButton:pressed {{
        background-color: {c.button_bg};
    }}

    QPushButton.IconButton:disabled {{
        opacity: 0.35;
    }}

    /* Compact Language Selector Pill */
    QPushButton.LangSelectorBtn {{
        background-color: transparent;
        color: {c.text};
        font-family: {font_stack};
        font-size: 8pt;
        font-weight: 700;
        border: 1px solid {c.border};
        border-radius: 4px;
        padding: 2px 1px;
        min-width: 24px;
        max-width: 24px;
        min-height: 20px;
        max-height: 20px;
    }}

    QPushButton.LangSelectorBtn:hover {{
        background-color: {c.button_hover};
        border: 1px solid {c.accent};
    }}

    QPushButton.LangSelectorBtn:pressed {{
        background-color: {c.button_bg};
    }}

    /* Paper Page Container */
    QFrame#PaperContainer {{
        background-color: {c.card_bg};
        border: 1px solid {c.border};
        border-radius: 6px;
    }}

    QLabel#DateLabel {{
        color: {c.text};
        font-family: {font_stack};
        font-size: {font_size + 4}pt;
        font-weight: 600;
        background: transparent;
    }}

    QLabel#PaperWaxSeal {{
        background: transparent;
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

    /* Popup Menus (History, Language Selection) */
    QMenu {{
        background-color: {c.card_bg};
        color: {c.text};
        border: 1px solid {c.border};
        border-radius: 6px;
        padding: 6px;
        font-family: {font_stack};
        font-size: {max(font_size - 2, 11)}pt;
    }}

    QMenu::item {{
        padding: 6px 18px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {c.button_hover};
    }}

    /* Minimalist ScrollBar */
    QScrollBar:vertical {{
        background: {c.card_bg};
        width: 8px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {c.border};
        min-height: 24px;
        border-radius: 4px;
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """
