"""Integration tests for NLP Engine, background worker, and SQLite persistence."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock
from PyQt6.QtCore import QCoreApplication
import pytest

from src.core.config import AppConfig
from src.core.database import Database, EntryRepository
from src.nlp.base_engine import AnalysisSpan
from src.nlp.engine import NLPEngine
from src.nlp.worker import AnalysisWorker


@pytest.fixture
def temp_db(tmp_path: Path) -> Database:
    db_file = tmp_path / "integration_diary.db"
    return Database(db_file)


@pytest.fixture
def entry_repo(temp_db: Database) -> EntryRepository:
    return EntryRepository(temp_db)


@pytest.fixture
def mock_lt_client():
    client = MagicMock()
    # Mock returning one error span for "Ich gehe in das Park."
    client.check_text.return_value = [
        AnalysisSpan(
            offset=12,
            length=3,
            original_span="das",
            expected_span="den",
            error_type="declination",
            category="GRAMMAR",
            rule_id="DE_AGREEMENT",
            rule_description="Genusfehler",
            message="Der Artikel stimmt nicht.",
            sentence_context="Ich gehe in das Park.",
            word_target="park",
        )
    ]
    return client


def test_nlp_engine_analysis(mock_lt_client):
    cfg = AppConfig()
    engine = NLPEngine(config=cfg, lt_client=mock_lt_client)

    result = engine.analyze("Ich gehe in das Park.", "de")
    assert result.success is True
    assert len(result.spans) == 1
    assert result.annotated_text == 'Ich gehe in <err type="declination" expected="den">das</err> Park.'
    assert result.clean_text == "Ich gehe in den Park."


def test_full_pipeline_persistence(entry_repo: EntryRepository, mock_lt_client):
    # Ensure QCoreApplication exists for QThread signals
    app = QCoreApplication.instance() or QCoreApplication([])

    today = date.today().isoformat()
    raw_text = "Ich gehe in das Park."
    entry = entry_repo.create_entry(today, "de", raw_text)
    entry_repo.lock_entry(entry.id)

    locked = entry_repo.get_by_id(entry.id)
    assert locked.status == "LOCKED"

    cfg = AppConfig()
    engine = NLPEngine(config=cfg, lt_client=mock_lt_client)

    # Run worker synchronously via run() for deterministic test
    worker = AnalysisWorker(
        entry_id=entry.id,
        raw_text=raw_text,
        target_language="de",
        engine=engine,
        repository=entry_repo,
    )

    finished_signals = []
    worker.analysis_finished.connect(lambda eid, success: finished_signals.append((eid, success)))

    worker.run()

    assert len(finished_signals) == 1
    assert finished_signals[0] == (entry.id, True)

    # Verify entry transitioned to ANALYZED
    analyzed_entry = entry_repo.get_by_id(entry.id)
    assert analyzed_entry.status == "ANALYZED"
    assert analyzed_entry.annotated_text == 'Ich gehe in <err type="declination" expected="den">das</err> Park.'
    assert analyzed_entry.raw_text == raw_text  # Immutable raw_text preserved!

    # Verify error_logs table
    errors = entry_repo.get_errors_for_entry(entry.id)
    assert len(errors) == 1
    err = errors[0]
    assert err.category == "GRAMMAR"
    assert err.rule_id == "DE_AGREEMENT"
    assert err.original_span == "das"
    assert err.expected_span == "den"
    assert err.word_target == "park"
