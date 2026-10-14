"""Minimalist writer window ('The Diary') adhering to zero-friction pedagogical principles."""

from datetime import date, datetime
from typing import Dict, Optional
from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import AppConfig, save_config
from src.core.database import Entry, EntryRepository
from src.core.lock_manager import LockManager
from src.ui.icons import (
    get_book_history_icon,
    get_bookmark_today_icon,
    get_midnight_clock_icon,
    get_quill_idle_icon,
    get_quill_writing_icon,
    get_wax_seal_icon,
)
from src.ui.theme import generate_stylesheet, get_theme


DATE_LOCALIZATIONS = {
    "de": {
        "weekdays": ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
        "months": [
            "Januar", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ],
        "format": lambda d, w, m: f"{w}, {d.day}. {m} {d.year}",
    },
    "en": {
        "weekdays": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "months": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        "format": lambda d, w, m: f"{w}, {m} {d.day}, {d.year}",
    },
    "pt-BR": {
        "weekdays": ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"],
        "months": [
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        ],
        "format": lambda d, w, m: f"{w}, {d.day} de {m} de {d.year}",
    },
    "fr": {
        "weekdays": ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"],
        "months": [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
        ],
        "format": lambda d, w, m: f"{w} {d.day} {m} {d.year}",
    },
    "es": {
        "weekdays": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
        "months": [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julho", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
        ],
        "format": lambda d, w, m: f"{w}, {d.day} de {m} de {d.year}",
    },
    "it": {
        "weekdays": ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"],
        "months": [
            "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
            "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
        ],
        "format": lambda d, w, m: f"{w} {d.day} {m} {d.year}",
    },
}

PLACEHOLDERS = {
    "de": "Liebes Tagebuch... (Tinte auf Papier, ohne Korrekturen oder Ablenkungen)",
    "en": "Dear Diary... (Ink on paper, zero distractions or corrections)",
    "pt-BR": "Querido diário... (Tinta no papel, sem correções ou distrações)",
    "fr": "Cher journal... (Encre sur papier, zéro distraction)",
    "es": "Querido diario... (Tinta sobre papel, sin distracciones)",
    "it": "Caro diario... (Inchiostro su carta, senza distrazioni)",
}


class WriterWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        repository: EntryRepository,
        lock_manager: LockManager,
    ):
        super().__init__()
        self.config = config
        self.repository = repository
        self.lock_manager = lock_manager

        self.current_entry: Optional[Entry] = None
        self._is_loading = False
        self._lang_buttons: Dict[str, QPushButton] = {}

        # Autosave timer
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(self.config.diary.auto_save_delay_ms)
        self.autosave_timer.timeout.connect(self._perform_autosave)

        # Midnight checker timer (every 60s)
        self.midnight_timer = QTimer(self)
        self.midnight_timer.setInterval(60000)
        self.midnight_timer.timeout.connect(self._check_midnight_rollover)
        self.midnight_timer.start()

        self._init_ui()
        self._load_active_entry()

    def _init_ui(self) -> None:
        self.setWindowTitle("Diário de Idiomas")
        self.resize(980, 800)
        self.setMinimumSize(640, 500)

        # Central widget and horizontal layout
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 24, 32, 28)
        main_layout.setSpacing(18)

        # --- Left Side Rail (Dock) ---
        sidebar = QFrame()
        sidebar.setObjectName("SideBar")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 8, 0, 8)
        sidebar_layout.setSpacing(14)
        sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        theme = get_theme(self.config.diary.theme)

        # 1. Status / Ink Icon (top)
        self.status_icon_btn = QPushButton()
        self.status_icon_btn.setObjectName("StatusIconButton")
        self.status_icon_btn.setProperty("class", "IconButton")
        self.status_icon_btn.setIcon(get_quill_idle_icon(theme.subtle_text))
        self.status_icon_btn.setToolTip("Tudo salvo na página")
        sidebar_layout.addWidget(self.status_icon_btn)

        # 2. History Button (Notebook icon)
        self.history_btn = QPushButton()
        self.history_btn.setObjectName("HistoryButton")
        self.history_btn.setProperty("class", "IconButton")
        self.history_btn.setIcon(get_book_history_icon(theme.subtle_text))
        self.history_btn.setToolTip("Páginas Anteriores")
        self.history_btn.clicked.connect(self._open_history_menu)
        sidebar_layout.addWidget(self.history_btn)

        # 3. Return to Today Bookmark (only visible on past entries)
        self.today_btn = QPushButton()
        self.today_btn.setObjectName("TodayBookmarkButton")
        self.today_btn.setProperty("class", "IconButton")
        self.today_btn.setIcon(get_bookmark_today_icon(theme.accent))
        self.today_btn.setToolTip("Voltar para a página de hoje")
        self.today_btn.clicked.connect(self._on_today_clicked)
        self.today_btn.setVisible(False)
        sidebar_layout.addWidget(self.today_btn)

        # 4. Language Pills (Vertical)
        lang_container = QVBoxLayout()
        lang_container.setSpacing(6)
        lang_container.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        for lang_code in self.config.user.available_languages:
            pill = QPushButton(lang_code.upper())
            pill.setProperty("class", "LangPill")
            is_active = (lang_code == self.config.user.active_target_language)
            pill.setProperty("active", "true" if is_active else "false")
            pill.setToolTip(f"Escrever em {lang_code.upper()}")
            pill.clicked.connect(lambda _, l=lang_code: self._on_language_pill_clicked(l))
            self._lang_buttons[lang_code] = pill
            lang_container.addWidget(pill)

        sidebar_layout.addLayout(lang_container)

        # Push bottom controls down
        sidebar_layout.addStretch()

        # 5. Bottom action: Finalize (on_submit) or Midnight indicator
        if self.config.diary.lock_policy == "on_submit":
            self.finalize_btn = QPushButton()
            self.finalize_btn.setObjectName("FinalizeButton")
            self.finalize_btn.setProperty("class", "IconButton")
            self.finalize_btn.setIcon(get_wax_seal_icon(theme.accent, is_locked=False))
            self.finalize_btn.setToolTip("Finalizar e selar página (tinta permanente)")
            self.finalize_btn.clicked.connect(self._on_finalize_clicked)
            sidebar_layout.addWidget(self.finalize_btn)
        else:
            self.policy_indicator = QPushButton()
            self.policy_indicator.setObjectName("PolicyIndicator")
            self.policy_indicator.setProperty("class", "IconButton")
            self.policy_indicator.setEnabled(False)
            self.policy_indicator.setIcon(get_midnight_clock_icon(theme.subtle_text))
            self.policy_indicator.setToolTip("Esta página será selada à meia-noite")
            sidebar_layout.addWidget(self.policy_indicator)

        main_layout.addWidget(sidebar)

        # --- Right Paper Page Container ---
        paper_frame = QFrame()
        paper_frame.setObjectName("PaperContainer")
        paper_layout = QVBoxLayout(paper_frame)
        paper_layout.setContentsMargins(48, 36, 48, 40)
        paper_layout.setSpacing(16)

        # Paper Header Row: Clean Date Label + Discreet Wax Seal (when locked)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 8)

        self.date_label = QLabel()
        self.date_label.setObjectName("DateLabel")
        header_row.addWidget(self.date_label)

        header_row.addStretch()

        # Wax seal watermark / stamp on the paper when locked
        self.paper_wax_seal = QLabel()
        self.paper_wax_seal.setObjectName("PaperWaxSeal")
        self.paper_wax_seal.setPixmap(get_wax_seal_icon(theme.accent, is_locked=True, size=28).pixmap(28, 28))
        self.paper_wax_seal.setToolTip("Página selada. O texto é imutável.")
        self.paper_wax_seal.setVisible(False)
        header_row.addWidget(self.paper_wax_seal)

        paper_layout.addLayout(header_row)

        # The Writing Area (Pure Paper)
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("DiaryEditor")
        self.editor.textChanged.connect(self._on_text_changed)
        paper_layout.addWidget(self.editor, 1)

        main_layout.addWidget(paper_frame, 1)

        self._apply_theme()

    def _apply_theme(self) -> None:
        stylesheet = generate_stylesheet(
            self.config.diary.theme,
            self.config.diary.font_family,
            self.config.diary.font_size,
        )
        self.setStyleSheet(stylesheet)

    def _format_date(self, date_str: str, lang_code: str = "de") -> str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            loc = (
                DATE_LOCALIZATIONS.get(lang_code)
                or DATE_LOCALIZATIONS.get(lang_code.split("-")[0])
                or DATE_LOCALIZATIONS["en"]
            )
            weekday = loc["weekdays"][d.weekday()]
            month = loc["months"][d.month - 1]
            return loc["format"](d, weekday, month)
        except Exception:
            return date_str

    def _load_active_entry(self) -> None:
        self._is_loading = True
        lang = self.config.user.active_target_language
        today = date.today().isoformat()

        # Enforce lock policies and retrieve or create current entry
        self.current_entry = self.lock_manager.get_current_entry(lang, today)

        self._update_ui_for_entry(self.current_entry)
        self._update_language_pills(lang)
        self.today_btn.setVisible(False)
        self._is_loading = False

    def _update_language_pills(self, active_lang: str) -> None:
        for code, pill in self._lang_buttons.items():
            pill.setProperty("active", "true" if code == active_lang else "false")
            pill.style().unpolish(pill)
            pill.style().polish(pill)

    def _update_ui_for_entry(self, entry: Entry) -> None:
        self._is_loading = True
        theme = get_theme(self.config.diary.theme)

        # Date header
        self.date_label.setText(self._format_date(entry.entry_date, entry.target_language))

        # Dynamic placeholder in target language
        placeholder = (
            PLACEHOLDERS.get(entry.target_language)
            or PLACEHOLDERS.get(entry.target_language.split("-")[0])
            or PLACEHOLDERS["en"]
        )
        self.editor.setPlaceholderText(placeholder)
        self.editor.setPlainText(entry.raw_text)

        is_editable = self.lock_manager.is_editable(entry)
        self.editor.setReadOnly(not is_editable)

        # Paper wax seal stamp
        self.paper_wax_seal.setVisible(not is_editable)

        # Update sidebar status icon
        if is_editable:
            self.status_icon_btn.setIcon(get_quill_idle_icon(theme.subtle_text))
            self.status_icon_btn.setToolTip("Tudo salvo na página")
            if hasattr(self, "finalize_btn"):
                self.finalize_btn.setEnabled(len(entry.raw_text.strip()) > 0)
                self.finalize_btn.setIcon(get_wax_seal_icon(theme.accent, is_locked=False))
        else:
            self.status_icon_btn.setIcon(get_wax_seal_icon(theme.subtle_text, is_locked=True))
            self.status_icon_btn.setToolTip("Página selada (somente leitura)")
            if hasattr(self, "finalize_btn"):
                self.finalize_btn.setEnabled(False)
                self.finalize_btn.setIcon(get_wax_seal_icon(theme.subtle_text, is_locked=True))

        self._is_loading = False

    def _on_text_changed(self) -> None:
        if self._is_loading:
            return

        if not self.current_entry or self.editor.isReadOnly():
            return

        theme = get_theme(self.config.diary.theme)
        # Visual writing feedback: active pen with fresh ink
        self.status_icon_btn.setIcon(get_quill_writing_icon(theme.text, theme.accent))
        self.status_icon_btn.setToolTip("Salvando tinta no papel...")

        if hasattr(self, "finalize_btn"):
            self.finalize_btn.setEnabled(len(self.editor.toPlainText().strip()) > 0)

        self.autosave_timer.start()

    def _perform_autosave(self) -> None:
        if not self.current_entry or self.editor.isReadOnly():
            return

        theme = get_theme(self.config.diary.theme)
        raw_text = self.editor.toPlainText()
        saved = self.repository.update_raw_text(self.current_entry.id, raw_text)

        if saved:
            self.status_icon_btn.setIcon(get_quill_idle_icon(theme.subtle_text))
            self.status_icon_btn.setToolTip("Tudo salvo na página")
            self.current_entry.raw_text = raw_text
        else:
            # Locked entry
            self.status_icon_btn.setIcon(get_wax_seal_icon(theme.subtle_text, is_locked=True))
            self.status_icon_btn.setToolTip("Página selada (imutável)")
            self.editor.setReadOnly(True)
            self.paper_wax_seal.setVisible(True)

    def _on_language_pill_clicked(self, new_lang: str) -> None:
        if new_lang == self.config.user.active_target_language:
            return

        # Flush autosave first
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        self.config.user.active_target_language = new_lang
        save_config(self.config)
        self._load_active_entry()

    def _open_history_menu(self) -> None:
        # Flush autosave before opening history
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        active_lang = self.config.user.active_target_language
        entries = self.repository.list_entries(active_lang, limit=30)

        menu = QMenu(self)
        if not entries:
            empty_action = QAction("Nenhuma página anterior", self)
            empty_action.setEnabled(False)
            menu.addAction(empty_action)
        else:
            for ent in entries:
                status_icon = "🔒" if ent.is_locked else "✏️"
                date_fmt = self._format_date(ent.entry_date, ent.target_language)
                action_text = f"{status_icon} {date_fmt} ({ent.word_count} palavras)"
                action = menu.addAction(action_text)
                action.setData(ent.id)

        # Position menu next to history button
        pos = self.history_btn.mapToGlobal(QPoint(self.history_btn.width() + 6, 0))
        selected_action = menu.exec(pos)

        if selected_action and selected_action.data() is not None:
            entry_id = selected_action.data()
            selected_entry = self.repository.get_by_id(entry_id)
            if selected_entry:
                self.current_entry = selected_entry
                self._update_ui_for_entry(selected_entry)
                today = date.today().isoformat()
                self.today_btn.setVisible(
                    selected_entry.entry_date != today or selected_entry.is_locked
                )

    def _on_today_clicked(self) -> None:
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        self._load_active_entry()

    def _on_finalize_clicked(self) -> None:
        if not self.current_entry or self.current_entry.is_locked:
            return

        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        confirm = QMessageBox.question(
            self,
            "Selar Página",
            "Deseja selar esta página?\n\n"
            "Uma vez selada, a tinta se torna permanente e o texto imutável.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            success = self.lock_manager.lock_entry(self.current_entry.id)
            if success:
                self.current_entry = self.repository.get_by_id(self.current_entry.id)
                if self.current_entry:
                    self._update_ui_for_entry(self.current_entry)

    def _check_midnight_rollover(self) -> None:
        today = date.today().isoformat()
        if self.current_entry and self.current_entry.entry_date != today:
            if self.config.diary.lock_policy == "daily_midnight":
                self.lock_manager.enforce_daily_lock(today)
                self._load_active_entry()

    def closeEvent(self, event) -> None:
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()
        super().closeEvent(event)
