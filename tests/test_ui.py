import os
import sys
from pathlib import Path
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication
from src.core.config import AppConfig
from src.core.database import Database, EntryRepository
from src.core.lock_manager import LockManager
from src.ui.writer_window import WriterWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def test_setup(tmp_path: Path):
    db_file = tmp_path / "ui_test_diary.db"
    database = Database(db_file)
    repository = EntryRepository(database)
    config = AppConfig(
        project_root=tmp_path,
        db_path=db_file,
    )
    config.diary.lock_policy = "on_submit"
    lock_manager = LockManager(config, repository)
    return config, repository, lock_manager


def test_writer_window_creation(qapp, test_setup):
    config, repository, lock_manager = test_setup

    window = WriterWindow(config, repository, lock_manager)
    assert window is not None
    assert window.windowTitle() == "Diário de Idiomas"
    assert window.current_entry is not None
    assert window.editor.isReadOnly() is False

    # Simulate typing and autosave
    window.editor.setPlainText("Heute habe ich Deutsch gelernt.")
    window._perform_autosave()

    saved_entry = repository.get_by_id(window.current_entry.id)
    assert saved_entry is not None
    assert saved_entry.raw_text == "Heute habe ich Deutsch gelernt."
    assert saved_entry.word_count == 5

    window.close()


def test_writer_window_locked_entry_read_only(qapp, test_setup):
    config, repository, lock_manager = test_setup

    window = WriterWindow(config, repository, lock_manager)
    window.editor.setPlainText("Text before locking.")
    window._perform_autosave()

    # Lock entry
    lock_manager.lock_entry(window.current_entry.id)
    locked_entry = repository.get_by_id(window.current_entry.id)
    window._update_ui_for_entry(locked_entry)

    window.show()
    assert window.editor.isReadOnly() is True
    assert not window.paper_wax_seal.isHidden()
    assert "selada" in window.status_icon_btn.toolTip().lower()

    window.close()


def test_localized_date_formatting(qapp, test_setup):
    config, repository, lock_manager = test_setup
    window = WriterWindow(config, repository, lock_manager)

    # Test German formatting (e.g. 2026-10-13 -> Dienstag, 13. Oktober 2026)
    formatted_de = window._format_date("2026-10-13", "de")
    assert formatted_de == "Dienstag, 13. Oktober 2026"

    # Test English formatting (e.g. 2026-10-13 -> Tuesday, October 13, 2026)
    formatted_en = window._format_date("2026-10-13", "en")
    assert formatted_en == "Tuesday, October 13, 2026"

    # Test Portuguese fallback
    formatted_pt = window._format_date("2026-10-13", "pt-BR")
    assert formatted_pt == "Terça-feira, 13 de Outubro de 2026"

    window.close()


def test_language_selector_switch(qapp, test_setup):
    config, repository, lock_manager = test_setup
    config.user.active_target_language = "de"
    window = WriterWindow(config, repository, lock_manager)

    assert window.lang_btn.text() == "DE"

    # Simulate choosing 'en'
    window.config.user.active_target_language = "en"
    window._load_active_entry()

    assert window.lang_btn.text() == "EN"
    assert window.current_entry.target_language == "en"

    window.close()


def test_settings_dialog_flow(qapp, test_setup):
    from src.ui.settings_dialog import SettingsDialog

    config, repository, lock_manager = test_setup
    dlg = SettingsDialog(config)

    # Change theme, font size, and lock policy
    idx_theme = dlg.theme_combo.findData("solarized_light")
    dlg.theme_combo.setCurrentIndex(idx_theme)
    dlg.font_size_spin.setValue(18)
    idx_pol = dlg.policy_combo.findData("daily_midnight")
    dlg.policy_combo.setCurrentIndex(idx_pol)

    dlg._on_save()

    assert config.diary.theme == "solarized_light"
    assert config.diary.font_size == 18
    assert config.diary.lock_policy == "daily_midnight"

    dlg.close()
