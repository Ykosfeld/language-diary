"""Background async worker (QThread) for processing locked entries."""

import logging
from typing import Dict, List, Optional
from PyQt6.QtCore import QObject, QThread, pyqtSignal

from src.core.database import Entry, EntryRepository, ErrorLogRecord
from src.nlp.base_engine import BaseNLPEngine

logger = logging.getLogger(__name__)


class AnalysisWorker(QThread):
    analysis_finished = pyqtSignal(int, bool)  # entry_id, success
    analysis_error = pyqtSignal(int, str)      # entry_id, error_message

    def __init__(
        self,
        entry_id: int,
        raw_text: str,
        target_language: str,
        engine: BaseNLPEngine,
        repository: EntryRepository,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.entry_id = entry_id
        self.raw_text = raw_text
        self.target_language = target_language
        self.engine = engine
        self.repository = repository

    def run(self) -> None:
        try:
            logger.info("Starting background NLP analysis for entry %d (%s)", self.entry_id, self.target_language)
            result = self.engine.analyze(self.raw_text, self.target_language)

            if not result.success:
                msg = result.error_message or "Analysis returned failure status"
                logger.warning("Analysis failed for entry %d: %s", self.entry_id, msg)
                self.analysis_error.emit(self.entry_id, msg)
                self.analysis_finished.emit(self.entry_id, False)
                return

            error_records: List[ErrorLogRecord] = [
                ErrorLogRecord(
                    id=None,
                    entry_id=self.entry_id,
                    target_language=self.target_language,
                    category=span.category,
                    rule_id=span.rule_id,
                    rule_description=span.rule_description,
                    message=span.message,
                    original_span=span.original_span,
                    expected_span=span.expected_span,
                    sentence_context=span.sentence_context,
                    word_target=span.word_target,
                )
                for span in result.spans
            ]

            saved = self.repository.save_analysis_results(
                self.entry_id,
                result.annotated_text,
                error_records,
            )

            if saved:
                logger.info(
                    "Successfully analyzed entry %d: %d errors recorded",
                    self.entry_id,
                    len(error_records),
                )
                self.analysis_finished.emit(self.entry_id, True)
            else:
                logger.warning("Could not persist analysis results for entry %d", self.entry_id)
                self.analysis_finished.emit(self.entry_id, False)

        except Exception as e:
            logger.exception("Unexpected exception during analysis of entry %d: %s", self.entry_id, e)
            self.analysis_error.emit(self.entry_id, str(e))
            self.analysis_finished.emit(self.entry_id, False)


# Registry to prevent garbage collection of running QThread workers
_ACTIVE_WORKERS: Dict[int, AnalysisWorker] = {}


def start_background_analysis(
    entry: Entry,
    engine: BaseNLPEngine,
    repository: EntryRepository,
) -> Optional[AnalysisWorker]:
    """
    Spawns and tracks an AnalysisWorker for a newly locked entry.
    Ensures GUI remains responsive and workers are cleaned up upon completion.
    """
    if entry.id is None or not entry.raw_text.strip():
        return None

    worker = AnalysisWorker(
        entry_id=entry.id,
        raw_text=entry.raw_text,
        target_language=entry.target_language,
        engine=engine,
        repository=repository,
    )

    _ACTIVE_WORKERS[entry.id] = worker

    def cleanup() -> None:
        _ACTIVE_WORKERS.pop(entry.id, None)

    worker.analysis_finished.connect(lambda _eid, _success: cleanup())
    worker.start()
    return worker
