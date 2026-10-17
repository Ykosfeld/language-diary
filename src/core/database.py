"""SQLite database setup, schema management, and repositories."""

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from typing import Generator, List, Optional


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL,            -- Formato YYYY-MM-DD
    target_language TEXT NOT NULL,       -- Ex: 'de', 'en'
    status TEXT NOT NULL DEFAULT 'DRAFT',-- 'DRAFT' | 'LOCKED' | 'ANALYZED'
    raw_text TEXT NOT NULL,              -- Texto original imutável do usuário
    annotated_text TEXT,                 -- Texto com tags <err ...> gerado na Fase 2
    word_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS error_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    target_language TEXT NOT NULL,       -- Ex: 'de', 'en'
    category TEXT NOT NULL,              -- Macro-categoria: 'GRAMMAR', 'TYPOS', 'CASING', 'SYNTAX'
    rule_id TEXT NOT NULL,               -- Regra específica: 'DE_AGREEMENT', 'GERMAN_SPELLER_RULE', 'NON3PRS_VERB'
    rule_description TEXT,               -- Descrição amigável da regra violada
    message TEXT,                        -- Mensagem pedagógica explicativa
    original_span TEXT NOT NULL,         -- Trecho original incorreto
    expected_span TEXT,                  -- Correção prioritária recomendada
    sentence_context TEXT NOT NULL,      -- Frase completa onde o erro ocorreu
    word_target TEXT,                    -- Palavra-alvo correta normalizada/minúscula
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    target_language TEXT NOT NULL,
    period_start TEXT NOT NULL,          -- YYYY-MM-DD
    period_end TEXT NOT NULL,            -- YYYY-MM-DD
    report_markdown TEXT NOT NULL,       -- Feedback qualitativo gerado pelo LLM
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_entries_date_lang ON entries(entry_date, target_language);
CREATE INDEX IF NOT EXISTS idx_errors_lang_rule ON error_logs(target_language, rule_id);
CREATE INDEX IF NOT EXISTS idx_errors_word_target ON error_logs(target_language, word_target);
CREATE INDEX IF NOT EXISTS idx_errors_entry_id ON error_logs(entry_id);
"""


@dataclass
class ErrorLogRecord:
    id: Optional[int]
    entry_id: int
    target_language: str
    category: str
    rule_id: str
    original_span: str
    sentence_context: str
    rule_description: Optional[str] = None
    message: Optional[str] = None
    expected_span: Optional[str] = None
    word_target: Optional[str] = None
    created_at: Optional[str] = None


@dataclass
class Entry:
    id: Optional[int]
    entry_date: str
    target_language: str
    status: str
    raw_text: str
    annotated_text: Optional[str] = None
    word_count: int = 0
    created_at: Optional[str] = None
    locked_at: Optional[str] = None

    @property
    def is_locked(self) -> bool:
        return self.status in ("LOCKED", "ANALYZED")


def count_words(text: str) -> int:
    return len(text.strip().split()) if text.strip() else 0


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    @contextmanager
    def session(self) -> Generator[sqlite3.Cursor, None, None]:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.session() as cursor:
            cursor.executescript(SCHEMA_SQL)
            self._migrate_error_logs_if_needed(cursor)
            cursor.executescript(INDEXES_SQL)

    def _migrate_error_logs_if_needed(self, cursor: sqlite3.Cursor) -> None:
        cursor.execute("PRAGMA table_info(error_logs);")
        columns = {row["name"] for row in cursor.fetchall()}
        if "category" not in columns and "error_type" in columns:
            cursor.execute("ALTER TABLE error_logs RENAME TO error_logs_old;")
            cursor.execute("""
                CREATE TABLE error_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
                    target_language TEXT NOT NULL,
                    category TEXT NOT NULL,
                    rule_id TEXT NOT NULL,
                    rule_description TEXT,
                    message TEXT,
                    original_span TEXT NOT NULL,
                    expected_span TEXT,
                    sentence_context TEXT NOT NULL,
                    word_target TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                INSERT INTO error_logs (
                    id, entry_id, target_language, category, rule_id, rule_description,
                    message, original_span, expected_span, sentence_context, word_target, created_at
                )
                SELECT 
                    id, entry_id, target_language, error_type, error_type, '',
                    '', COALESCE(original_span, ''), expected_span, sentence_context, NULL, created_at
                FROM error_logs_old;
            """)
            cursor.execute("DROP TABLE error_logs_old;")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_lang_rule ON error_logs(target_language, rule_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_word_target ON error_logs(target_language, word_target);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_errors_entry_id ON error_logs(entry_id);")


class EntryRepository:
    def __init__(self, database: Database):
        self.db = database

    def _row_to_entry(self, row: sqlite3.Row) -> Entry:
        return Entry(
            id=row["id"],
            entry_date=row["entry_date"],
            target_language=row["target_language"],
            status=row["status"],
            raw_text=row["raw_text"],
            annotated_text=row["annotated_text"],
            word_count=row["word_count"],
            created_at=row["created_at"],
            locked_at=row["locked_at"],
        )

    def get_by_id(self, entry_id: int) -> Optional[Entry]:
        with self.db.session() as cursor:
            cursor.execute("SELECT * FROM entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None

    def get_draft_for_date(self, entry_date: str, target_language: str) -> Optional[Entry]:
        with self.db.session() as cursor:
            cursor.execute(
                """
                SELECT * FROM entries 
                WHERE entry_date = ? AND target_language = ? AND status = 'DRAFT'
                ORDER BY id DESC LIMIT 1
                """,
                (entry_date, target_language),
            )
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None

    def get_latest_entry(self, target_language: str) -> Optional[Entry]:
        with self.db.session() as cursor:
            cursor.execute(
                """
                SELECT * FROM entries 
                WHERE target_language = ?
                ORDER BY entry_date DESC, id DESC LIMIT 1
                """,
                (target_language,),
            )
            row = cursor.fetchone()
            return self._row_to_entry(row) if row else None

    def get_or_create_draft(self, entry_date: str, target_language: str) -> Entry:
        draft = self.get_draft_for_date(entry_date, target_language)
        if draft:
            return draft
        return self.create_entry(entry_date, target_language, raw_text="")

    def create_entry(self, entry_date: str, target_language: str, raw_text: str = "") -> Entry:
        word_count = count_words(raw_text)
        with self.db.session() as cursor:
            cursor.execute(
                """
                INSERT INTO entries (entry_date, target_language, status, raw_text, word_count)
                VALUES (?, ?, 'DRAFT', ?, ?)
                """,
                (entry_date, target_language, raw_text, word_count),
            )
            entry_id = cursor.lastrowid

        entry = self.get_by_id(entry_id)
        if not entry:
            raise RuntimeError(f"Failed to fetch newly created entry {entry_id}")
        return entry

    def update_raw_text(self, entry_id: int, raw_text: str) -> bool:
        """
        Updates raw_text only if the entry is still DRAFT.
        Guarantees immutability for LOCKED or ANALYZED entries.
        """
        word_count = count_words(raw_text)
        with self.db.session() as cursor:
            cursor.execute(
                """
                UPDATE entries 
                SET raw_text = ?, word_count = ?
                WHERE id = ? AND status = 'DRAFT'
                """,
                (raw_text, word_count, entry_id),
            )
            return cursor.rowcount > 0

    def lock_entry(self, entry_id: int) -> bool:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with self.db.session() as cursor:
            cursor.execute(
                """
                UPDATE entries 
                SET status = 'LOCKED', locked_at = ?
                WHERE id = ? AND status = 'DRAFT'
                """,
                (now_utc, entry_id),
            )
            return cursor.rowcount > 0

    def lock_drafts_before_date(self, today_date_str: str) -> int:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with self.db.session() as cursor:
            cursor.execute(
                """
                UPDATE entries 
                SET status = 'LOCKED', locked_at = ?
                WHERE entry_date < ? AND status = 'DRAFT'
                """,
                (now_utc, today_date_str),
            )
            return cursor.rowcount

    def list_entries(
        self,
        target_language: Optional[str] = None,
        limit: int = 100,
    ) -> List[Entry]:
        with self.db.session() as cursor:
            if target_language:
                cursor.execute(
                    """
                    SELECT * FROM entries 
                    WHERE target_language = ?
                    ORDER BY entry_date DESC, id DESC LIMIT ?
                    """,
                    (target_language, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM entries 
                    ORDER BY entry_date DESC, id DESC LIMIT ?
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]

    def save_analysis_results(
        self,
        entry_id: int,
        annotated_text: str,
        errors: List[ErrorLogRecord],
    ) -> bool:
        """
        Atomically saves annotated_text, transitions status to ANALYZED,
        and persists all detected error logs.
        """
        with self.db.session() as cursor:
            cursor.execute(
                """
                UPDATE entries
                SET annotated_text = ?, status = 'ANALYZED'
                WHERE id = ? AND status IN ('LOCKED', 'ANALYZED')
                """,
                (annotated_text, entry_id),
            )
            if cursor.rowcount == 0:
                return False

            # Clear previously registered errors for idempotency
            cursor.execute("DELETE FROM error_logs WHERE entry_id = ?", (entry_id,))

            for err in errors:
                cursor.execute(
                    """
                    INSERT INTO error_logs (
                        entry_id, target_language, category, rule_id, rule_description,
                        message, original_span, expected_span, sentence_context, word_target
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry_id,
                        err.target_language,
                        err.category,
                        err.rule_id,
                        err.rule_description,
                        err.message,
                        err.original_span,
                        err.expected_span,
                        err.sentence_context,
                        err.word_target,
                    ),
                )
        return True

    def get_errors_for_entry(self, entry_id: int) -> List[ErrorLogRecord]:
        with self.db.session() as cursor:
            cursor.execute(
                """
                SELECT * FROM error_logs
                WHERE entry_id = ?
                ORDER BY id ASC
                """,
                (entry_id,),
            )
            rows = cursor.fetchall()
            return [
                ErrorLogRecord(
                    id=row["id"],
                    entry_id=row["entry_id"],
                    target_language=row["target_language"],
                    category=row["category"],
                    rule_id=row["rule_id"],
                    rule_description=row["rule_description"],
                    message=row["message"],
                    original_span=row["original_span"],
                    expected_span=row["expected_span"],
                    sentence_context=row["sentence_context"],
                    word_target=row["word_target"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

    def get_entries_by_status(
        self,
        status: str,
        target_language: Optional[str] = None,
    ) -> List[Entry]:
        with self.db.session() as cursor:
            if target_language:
                cursor.execute(
                    """
                    SELECT * FROM entries
                    WHERE status = ? AND target_language = ?
                    ORDER BY entry_date ASC, id ASC
                    """,
                    (status, target_language),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM entries
                    WHERE status = ?
                    ORDER BY entry_date ASC, id ASC
                    """,
                    (status,),
                )
            rows = cursor.fetchall()
            return [self._row_to_entry(row) for row in rows]
