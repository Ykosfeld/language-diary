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
from src.core.database import Database, EntryRepository
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

    # Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Language Diary")
    app.setApplicationDisplayName("Diário de Idiomas")

    window = WriterWindow(config, repository, lock_manager)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
