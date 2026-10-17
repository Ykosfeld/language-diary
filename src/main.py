import os
from pathlib import Path
import sys

# Ensure project root is always in sys.path regardless of where the script was invoked
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Auto-delegate to local .venv if executed with an interpreter lacking PyQt6
try:
    from PyQt6.QtWidgets import QApplication
except ModuleNotFoundError:
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    if venv_python.exists() and sys.executable != str(venv_python):
        os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    raise

from src.core.config import load_config
from src.core.database import Database, Entry, EntryRepository
from src.core.lock_manager import LockManager
from src.ui.writer_window import WriterWindow


def main() -> None:
    # Load configuration
    config = load_config()

    # Initialize SQLite database and repository
    db_path = config.get_absolute_db_path()
    database = Database(db_path)
    repository = EntryRepository(database)

    # Initialize lock manager and enforce startup midnight locks
    lock_manager = LockManager(config, repository)
    lock_manager.enforce_daily_lock()

    # Initialize Phase 2 NLP Engine and connect background analysis worker
    from src.nlp.engine import NLPEngine
    from src.nlp.worker import start_background_analysis

    nlp_engine = NLPEngine(config)

    if config.nlp.run_on_lock:
        def on_entry_locked(entry: Entry) -> None:
            start_background_analysis(entry, nlp_engine, repository)

        lock_manager.register_on_locked_callback(on_entry_locked)

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Language Diary")
    app.setApplicationDisplayName("Diário de Idiomas")

    icon_path = PROJECT_ROOT / "assets" / "icon.svg"
    if icon_path.exists():
        from PyQt6.QtGui import QIcon
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    window = WriterWindow(config, repository, lock_manager)
    if icon_path.exists():
        window.setWindowIcon(app_icon)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
