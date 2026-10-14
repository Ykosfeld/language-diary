"""Settings dialog for configuring language-diary (config.yaml)."""

from typing import List
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config import AppConfig, save_config
from src.ui.theme import generate_stylesheet


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self._init_ui()

    def _init_ui(self) -> None:
        self.setWindowTitle("Configurações do Diário")
        self.resize(540, 430)
        self.setMinimumSize(480, 380)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # Apply current theme
        stylesheet = generate_stylesheet(
            self.config.diary.theme,
            self.config.diary.font_family,
            self.config.diary.font_size,
        )
        self.setStyleSheet(stylesheet)

        # Tab Widget to organize settings cleanly without vertical overcrowding
        self.tabs = QTabWidget()

        # ==========================================
        # Tab 1: Aparência e Política de Escrita
        # ==========================================
        tab_appearance = QWidget()
        app_layout = QFormLayout(tab_appearance)
        app_layout.setContentsMargins(16, 18, 16, 18)
        app_layout.setVerticalSpacing(14)
        app_layout.setHorizontalSpacing(16)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Sépia (Papel Quente)", "sepia")
        self.theme_combo.addItem("Solarized Light", "solarized_light")
        self.theme_combo.addItem("Paper Dark", "paper_dark")
        idx = self.theme_combo.findData(self.config.diary.theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        app_layout.addRow("Tema visual:", self.theme_combo)

        self.font_combo = QComboBox()
        fonts = ["Noto Serif", "Georgia", "DejaVu Serif", "Linux Libertine", "Baskerville", "Serif"]
        for f in fonts:
            self.font_combo.addItem(f, f)
        idx_f = self.font_combo.findData(self.config.diary.font_family)
        if idx_f >= 0:
            self.font_combo.setCurrentIndex(idx_f)
        else:
            self.font_combo.addItem(self.config.diary.font_family, self.config.diary.font_family)
            self.font_combo.setCurrentIndex(self.font_combo.count() - 1)
        app_layout.addRow("Tipografia do diário:", self.font_combo)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(11, 26)
        self.font_size_spin.setValue(self.config.diary.font_size)
        self.font_size_spin.setSuffix(" pt")
        app_layout.addRow("Tamanho da fonte:", self.font_size_spin)

        self.policy_combo = QComboBox()
        self.policy_combo.addItem("Diário (Fecha à meia-noite)", "daily_midnight")
        self.policy_combo.addItem("Manual (Botão para selar a qualquer momento)", "on_submit")
        idx_p = self.policy_combo.findData(self.config.diary.lock_policy)
        if idx_p >= 0:
            self.policy_combo.setCurrentIndex(idx_p)
        app_layout.addRow("Modo de selagem:", self.policy_combo)

        self.tabs.addTab(tab_appearance, "Aparência & Diário")

        # ==========================================
        # Tab 2: Idiomas
        # ==========================================
        tab_lang = QWidget()
        lang_layout = QFormLayout(tab_lang)
        lang_layout.setContentsMargins(16, 18, 16, 18)
        lang_layout.setVerticalSpacing(14)
        lang_layout.setHorizontalSpacing(16)

        self.native_lang_edit = QLineEdit(self.config.user.native_language)
        lang_layout.addRow("Seu idioma nativo:", self.native_lang_edit)

        langs_str = ", ".join(self.config.user.available_languages)
        self.languages_edit = QLineEdit(langs_str)
        self.languages_edit.setToolTip("Separe os códigos por vírgula (ex: de, en, fr)")
        lang_layout.addRow("Idiomas de prática:", self.languages_edit)

        helper_label = QLabel("Dica: você pode alternar o idioma ativo diretamente pelo botão na barra lateral.")
        helper_label.setWordWrap(True)
        helper_label.setStyleSheet("font-style: italic; opacity: 0.8;")
        lang_layout.addRow("", helper_label)

        self.tabs.addTab(tab_lang, "Idiomas")

        # ==========================================
        # Tab 3: Motor Analítico e IA (Fases 2/3)
        # ==========================================
        tab_nlp = QWidget()
        nlp_layout = QFormLayout(tab_nlp)
        nlp_layout.setContentsMargins(16, 18, 16, 18)
        nlp_layout.setVerticalSpacing(14)
        nlp_layout.setHorizontalSpacing(16)

        self.run_on_lock_check = QCheckBox("Disparar análise em segundo plano ao selar a página")
        self.run_on_lock_check.setChecked(self.config.nlp.run_on_lock)
        nlp_layout.addRow("", self.run_on_lock_check)

        self.provider_combo = QComboBox()
        for prov in ["ollama", "openai", "gemini", "anthropic"]:
            self.provider_combo.addItem(prov.capitalize(), prov)
        idx_pr = self.provider_combo.findData(self.config.nlp.llm_provider)
        if idx_pr >= 0:
            self.provider_combo.setCurrentIndex(idx_pr)
        nlp_layout.addRow("Provedor LLM:", self.provider_combo)

        self.model_edit = QLineEdit(self.config.nlp.llm_model)
        nlp_layout.addRow("Modelo LLM:", self.model_edit)

        self.tabs.addTab(tab_nlp, "Inteligência Artificial")

        main_layout.addWidget(self.tabs, 1)

        # --- Action Buttons at Bottom ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Salvar Configurações")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    def _on_save(self) -> None:
        # 1. Update Appearance
        self.config.diary.theme = self.theme_combo.currentData()
        self.config.diary.font_family = self.font_combo.currentData()
        self.config.diary.font_size = self.font_size_spin.value()

        # 2. Update Policy
        self.config.diary.lock_policy = self.policy_combo.currentData()

        # 3. Update Languages
        native_lang = self.native_lang_edit.text().strip() or "pt-BR"
        self.config.user.native_language = native_lang

        langs_raw = self.languages_edit.text()
        langs: List[str] = [l.strip().lower() for l in langs_raw.split(",") if l.strip()]
        if not langs:
            langs = ["de", "en"]
        if self.config.user.active_target_language not in langs:
            langs.append(self.config.user.active_target_language)
        self.config.user.available_languages = langs

        # 4. Update NLP
        self.config.nlp.run_on_lock = self.run_on_lock_check.isChecked()
        self.config.nlp.llm_provider = self.provider_combo.currentData()
        self.config.nlp.llm_model = self.model_edit.text().strip() or "llama3.1:8b"

        # Persist to config.yaml
        save_config(self.config)

        self.accept()
