"""Immutability and lock policy manager ('Ink on Paper')."""

from datetime import date
from typing import Callable, List, Optional
from src.core.config import AppConfig
from src.core.database import Entry, EntryRepository


class LockManager:
    def __init__(self, config: AppConfig, repository: EntryRepository):
        self.config = config
        self.repository = repository
        self._on_locked_callbacks: List[Callable[[Entry], None]] = []

    def register_on_locked_callback(self, callback: Callable[[Entry], None]) -> None:
        """Register hooks to trigger when an entry is locked (e.g. NLP Phase 2)."""
        self._on_locked_callbacks.append(callback)

    def get_today_str(self) -> str:
        return date.today().isoformat()

    def enforce_daily_lock(self, current_date_str: Optional[str] = None) -> int:
        """
        Enforces midnight lock rule: locks any unsubmitted draft from prior days.
        """
        today = current_date_str or self.get_today_str()
        locked_count = self.repository.lock_drafts_before_date(today)
        return locked_count

    def is_editable(self, entry: Entry, current_date_str: Optional[str] = None) -> bool:
        if entry.is_locked:
            return False

        today = current_date_str or self.get_today_str()
        if self.config.diary.lock_policy == "daily_midnight":
            # Only today's draft is editable
            return entry.entry_date == today and entry.status == "DRAFT"

        # In on_submit mode, draft is editable until explicitly submitted
        return entry.status == "DRAFT"

    def get_current_entry(
        self,
        target_language: str,
        entry_date_str: Optional[str] = None,
    ) -> Entry:
        today = entry_date_str or self.get_today_str()
        self.enforce_daily_lock(today)

        if self.config.diary.lock_policy == "daily_midnight":
            return self.repository.get_or_create_draft(today, target_language)

        # on_submit mode:
        draft = self.repository.get_draft_for_date(today, target_language)
        if draft:
            return draft
        return self.repository.create_entry(today, target_language, raw_text="")

    def lock_entry(self, entry_id: int) -> bool:
        """Locks an entry and triggers registered callbacks."""
        success = self.repository.lock_entry(entry_id)
        if success:
            locked_entry = self.repository.get_by_id(entry_id)
            if locked_entry:
                for cb in self._on_locked_callbacks:
                    try:
                        cb(locked_entry)
                    except Exception:
                        pass
        return success
