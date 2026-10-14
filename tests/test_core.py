from datetime import date, timedelta
from pathlib import Path
import pytest
from src.core.config import AppConfig, DiaryConfig, load_config, save_config
from src.core.database import Database, EntryRepository
from src.core.lock_manager import LockManager


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    db_file = tmp_path / "test_diary.db"
    return Database(db_file)


@pytest.fixture
def entry_repo(temp_db: Database) -> EntryRepository:
    return EntryRepository(temp_db)


@pytest.fixture
def sample_config(tmp_path: Path) -> AppConfig:
    cfg = AppConfig()
    cfg.diary.lock_policy = "daily_midnight"
    return cfg


def test_database_initialization(temp_db: Database):
    with temp_db.session() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        assert "entries" in tables
        assert "error_logs" in tables
        assert "weekly_reports" in tables


def test_entry_repository_crud(entry_repo: EntryRepository):
    today = date.today().isoformat()
    entry = entry_repo.get_or_create_draft(today, "de")
    assert entry.id is not None
    assert entry.entry_date == today
    assert entry.target_language == "de"
    assert entry.status == "DRAFT"
    assert entry.raw_text == ""
    assert entry.word_count == 0

    # Update raw text
    updated = entry_repo.update_raw_text(entry.id, "Hallo Welt! Ich lerne Deutsch.")
    assert updated is True

    fetched = entry_repo.get_by_id(entry.id)
    assert fetched is not None
    assert fetched.raw_text == "Hallo Welt! Ich lerne Deutsch."
    assert fetched.word_count == 5


def test_immutability_on_lock(entry_repo: EntryRepository):
    today = date.today().isoformat()
    entry = entry_repo.create_entry(today, "de", "Das ist ein Test.")
    assert entry.status == "DRAFT"

    # Lock entry
    locked = entry_repo.lock_entry(entry.id)
    assert locked is True

    fetched = entry_repo.get_by_id(entry.id)
    assert fetched.status == "LOCKED"
    assert fetched.locked_at is not None
    assert fetched.is_locked is True

    # Try to modify locked entry - must be rejected
    cant_update = entry_repo.update_raw_text(entry.id, "Modification attempt")
    assert cant_update is False

    refetched = entry_repo.get_by_id(entry.id)
    assert refetched.raw_text == "Das ist ein Test."  # unchanged


def test_lock_manager_midnight_enforcement(sample_config: AppConfig, entry_repo: EntryRepository):
    lock_mgr = LockManager(sample_config, entry_repo)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    today = date.today().isoformat()

    old_entry = entry_repo.create_entry(yesterday, "de", "Gestern geschrieben.")
    assert old_entry.status == "DRAFT"

    # Run enforcement for today
    locked_count = lock_mgr.enforce_daily_lock(today)
    assert locked_count >= 1

    checked = entry_repo.get_by_id(old_entry.id)
    assert checked.status == "LOCKED"
    assert not lock_mgr.is_editable(checked, today)


def test_config_load_and_save(tmp_path: Path):
    cfg_file = tmp_path / "config.yaml"
    cfg = AppConfig()
    cfg.user.active_target_language = "en"
    cfg.diary.theme = "solarized_light"
    save_config(cfg, cfg_file)

    loaded = load_config(cfg_file)
    assert loaded.user.active_target_language == "en"
    assert loaded.diary.theme == "solarized_light"
