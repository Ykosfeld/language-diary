from datetime import date, timedelta
from pathlib import Path
import pytest
from src.core.config import AppConfig, DiaryConfig, load_config, save_config
from src.core.database import Database, EntryRepository, ErrorLogRecord
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


def test_save_analysis_results_and_retrieve(entry_repo: EntryRepository):
    today = date.today().isoformat()
    entry = entry_repo.create_entry(today, "de", "Ich gehe in das Park.")
    entry_repo.lock_entry(entry.id)

    errors = [
        ErrorLogRecord(
            id=None,
            entry_id=entry.id,
            target_language="de",
            category="GRAMMAR",
            rule_id="DE_AGREEMENT",
            rule_description="Genusfehler",
            message="Der Artikel stimmt nicht mit dem Nomen überein.",
            original_span="das",
            expected_span="den",
            sentence_context="Ich gehe in das Park.",
            word_target="park",
        )
    ]
    annotated = 'Ich gehe in <err type="declination" expected="den">das</err> Park.'
    success = entry_repo.save_analysis_results(entry.id, annotated, errors)
    assert success is True

    updated_entry = entry_repo.get_by_id(entry.id)
    assert updated_entry.status == "ANALYZED"
    assert updated_entry.annotated_text == annotated

    saved_errors = entry_repo.get_errors_for_entry(entry.id)
    assert len(saved_errors) == 1
    assert saved_errors[0].category == "GRAMMAR"
    assert saved_errors[0].rule_id == "DE_AGREEMENT"
    assert saved_errors[0].word_target == "park"


def test_error_logs_schema_migration(tmp_path: Path):
    import sqlite3
    db_file = tmp_path / "legacy_diary.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            target_language TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'DRAFT',
            raw_text TEXT NOT NULL,
            annotated_text TEXT,
            word_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            locked_at TIMESTAMP
        );
    """)
    conn.execute("""
        CREATE TABLE error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            target_language TEXT NOT NULL,
            error_type TEXT NOT NULL,
            original_span TEXT,
            expected_span TEXT,
            sentence_context TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.execute("INSERT INTO entries (id, entry_date, target_language, raw_text) VALUES (1, '2026-10-10', 'de', 'Test');")
    conn.execute("INSERT INTO error_logs (entry_id, target_language, error_type, original_span, expected_span, sentence_context) VALUES (1, 'de', 'declination', 'das', 'den', 'Test frase');")
    conn.commit()
    conn.close()

    # Now open with Database class, which should run migration
    db = Database(db_file)
    with db.session() as cursor:
        cursor.execute("PRAGMA table_info(error_logs);")
        cols = {row["name"] for row in cursor.fetchall()}
        assert "category" in cols
        assert "word_target" in cols
        assert "rule_id" in cols
        assert "error_type" not in cols

        cursor.execute("SELECT * FROM error_logs WHERE entry_id = 1;")
        row = cursor.fetchone()
        assert row["original_span"] == "das"
        assert row["expected_span"] == "den"
        assert row["category"] == "declination"
