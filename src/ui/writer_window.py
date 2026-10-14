"""Minimalist writer window ('The Diary') adhering to zero-friction pedagogical principles."""

from datetime import date, datetime
from typing import Optional
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.core.config import AppConfig, save_config
from src.core.database import Entry, EntryRepository
from src.core.lock_manager import LockManager
from src.ui.theme import generate_stylesheet


LANGUAGE_NAMES = {
    "de": "Alemão (DE)",
    "en": "Inglês (EN)",
    "pt-BR": "Português (PT)",
    "fr": "Francês (FR)",
    "es": "Espanhol (ES)",
    "it": "Italiano (IT)",
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
        self.resize(960, 780)
        self.setMinimumSize(640, 500)

        # Central widget and layout
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(40, 24, 40, 32)
        root_layout.setSpacing(16)

        # --- Top Header Bar ---
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        # Left header: Date and status
        date_box = QVBoxLayout()
        date_box.setSpacing(2)

        self.date_label = QLabel()
        self.date_label.setObjectName("DateLabel")
        date_box.addWidget(self.date_label)

        self.status_label = QLabel("Salvo")
        self.status_label.setObjectName("StatusLabel")
        date_box.addWidget(self.status_label)

        header_layout.addLayout(date_box)
        header_layout.addStretch()

        # Right header: History, Language selector, Finalize button
        self.today_btn = QPushButton("Página de Hoje")
        self.today_btn.clicked.connect(self._on_today_clicked)
        self.today_btn.setVisible(False)
        header_layout.addWidget(self.today_btn)

        self.history_combo = QComboBox()
        self.history_combo.setToolTip("Páginas Anteriores")
        self.history_combo.currentIndexChanged.connect(self._on_history_selected)
        header_layout.addWidget(self.history_combo)

        self.lang_combo = QComboBox()
        for lang_code in self.config.user.available_languages:
            display_name = LANGUAGE_NAMES.get(lang_code, lang_code.upper())
            self.lang_combo.addItem(display_name, lang_code)

        # Set active language
        active_idx = self.lang_combo.findData(self.config.user.active_target_language)
        if active_idx >= 0:
            self.lang_combo.setCurrentIndex(active_idx)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        header_layout.addWidget(self.lang_combo)

        # Finalize button (only in on_submit mode)
        self.finalize_btn = QPushButton("Finalizar Página")
        self.finalize_btn.setObjectName("FinalizeButton")
        self.finalize_btn.clicked.connect(self._on_finalize_clicked)
        if self.config.diary.lock_policy != "on_submit":
            self.finalize_btn.setVisible(False)
        header_layout.addWidget(self.finalize_btn)

        root_layout.addLayout(header_layout)

        # --- Locked Banner (Hidden by default) ---
        self.locked_banner = QLabel("🔒 Página selada. O texto é imutável e não pode ser editado.")
        self.locked_banner.setObjectName("LockedBanner")
        self.locked_banner.setVisible(False)
        root_layout.addWidget(self.locked_banner)

        # --- Paper Sheet Container ---
        paper_frame = QFrame()
        paper_frame.setObjectName("PaperContainer")
        paper_layout = QVBoxLayout(paper_frame)
        paper_layout.setContentsMargins(36, 32, 36, 32)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("DiaryEditor")
        self.editor.setPlaceholderText("Escreva livremente aqui... (tinta no papel, sem correções ou distrações)")
        self.editor.textChanged.connect(self._on_text_changed)

        paper_layout.addWidget(self.editor)
        root_layout.addWidget(paper_frame, 1)

        self._apply_theme()

    def _apply_theme(self) -> None:
        stylesheet = generate_stylesheet(
            self.config.diary.theme,
            self.config.diary.font_family,
            self.config.diary.font_size,
        )
        self.setStyleSheet(stylesheet)

    def _format_date(self, date_str: str) -> str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Format in friendly date representation
            weekday_pt = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"][d.weekday()]
            months_pt = [
                "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
            ]
            return f"{weekday_pt}, {d.day} de {months_pt[d.month - 1]} de {d.year}"
        except Exception:
            return date_str

    def _refresh_history_combo(self) -> None:
        self.history_combo.blockSignals(True)
        self.history_combo.clear()
        self.history_combo.addItem("Histórico de Páginas...", None)

        entries = self.repository.list_entries(self.config.user.active_target_language, limit=30)
        for ent in entries:
            status_symbol = "🔒" if ent.is_locked else "✏️"
            label = f"{status_symbol} {ent.entry_date} ({ent.word_count} palavras)"
            self.history_combo.addItem(label, ent.id)

        self.history_combo.blockSignals(False)

    def _load_active_entry(self) -> None:
        self._is_loading = True
        lang = self.config.user.active_target_language
        today = date.today().isoformat()

        # Enforce lock policies and retrieve or create current entry
        self.current_entry = self.lock_manager.get_current_entry(lang, today)

        self._update_ui_for_entry(self.current_entry)
        self._refresh_history_combo()
        self.today_btn.setVisible(False)
        self._is_loading = False

    def _update_ui_for_entry(self, entry: Entry) -> None:
        self._is_loading = True
        self.date_label.setText(self._format_date(entry.entry_date))

        self.editor.setPlainText(entry.raw_text)

        is_editable = self.lock_manager.is_editable(entry)
        self.editor.setReadOnly(not is_editable)
        self.locked_banner.setVisible(not is_editable)

        if is_editable:
            self.status_label.setText("Rascunho (Salvo)")
            if self.config.diary.lock_policy == "on_submit":
                self.finalize_btn.setEnabled(len(entry.raw_text.strip()) > 0)
                self.finalize_btn.setVisible(True)
        else:
            self.status_label.setText("Página Selada (Leitura)")
            self.finalize_btn.setEnabled(False)

        self._is_loading = False

    def _on_text_changed(self) -> None:
        if self._is_loading:
            return

        if not self.current_entry or self.editor.isReadOnly():
            return

        self.status_label.setText("Salvando...")
        if self.config.diary.lock_policy == "on_submit":
            self.finalize_btn.setEnabled(len(self.editor.toPlainText().strip()) > 0)
        self.autosave_timer.start()

    def _perform_autosave(self) -> None:
        if not self.current_entry or self.editor.isReadOnly():
            return

        raw_text = self.editor.toPlainText()
        saved = self.repository.update_raw_text(self.current_entry.id, raw_text)
        if saved:
            self.status_label.setText("Salvo")
            self.current_entry.raw_text = raw_text
        else:
            # Entry could not be updated because it's locked
            self.status_label.setText("Não editável (Bloqueado)")
            self.editor.setReadOnly(True)
            self.locked_banner.setVisible(True)

    def _on_language_changed(self, index: int) -> None:
        new_lang = self.lang_combo.itemData(index)
        if not new_lang or new_lang == self.config.user.active_target_language:
            return

        # Flush any pending autosave
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        self.config.user.active_target_language = new_lang
        save_config(self.config)
        self._load_active_entry()

    def _on_finalize_clicked(self) -> None:
        if not self.current_entry or self.current_entry.is_locked:
            return

        # Flush autosave first
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        confirm = QMessageBox.question(
            self,
            "Finalizar Página",
            "Deseja finalizar e selar esta página?\n\n"
            "Uma vez selada, o texto se tornará imutável (tinta no papel) "
            "e ficará disponível para a análise do professor.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            success = self.lock_manager.lock_entry(self.current_entry.id)
            if success:
                self.current_entry = self.repository.get_by_id(self.current_entry.id)
                if self.current_entry:
                    self._update_ui_for_entry(self.current_entry)
                self._refresh_history_combo()

    def _on_history_selected(self, index: int) -> None:
        if self._is_loading:
            return

        entry_id = self.history_combo.itemData(index)
        if entry_id is None:
            return

        # Flush current entry autosave
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        selected_entry = self.repository.get_by_id(entry_id)
        if selected_entry:
            self.current_entry = selected_entry
            self._update_ui_for_entry(selected_entry)
            today = date.today().isoformat()
            self.today_btn.setVisible(selected_entry.entry_date != today or selected_entry.is_locked)

    def _on_today_clicked(self) -> None:
        # Flush current entry autosave
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()

        self._load_active_entry()

    def _check_midnight_rollover(self) -> None:
        """Periodic check in case the day changes while the app is running."""
        today = date.today().isoformat()
        if self.current_entry and self.current_entry.entry_date != today:
            if self.config.diary.lock_policy == "daily_midnight":
                self.lock_manager.enforce_daily_lock(today)
                self._load_active_entry()

    def closeEvent(self, event) -> None:
        # Guarantee autosave on window close
        if self.autosave_timer.isActive():
            self.autosave_timer.stop()
            self._perform_autosave()
        super().closeEvent(event)
