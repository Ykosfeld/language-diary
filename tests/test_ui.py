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
    assert not window.locked_banner.isHidden()
    assert "Selada" in window.status_label.text()

    window.close()
