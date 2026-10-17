"""Configuration loader and schema definitions for language-diary."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class UserConfig:
    native_language: str = "pt-BR"
    active_target_language: str = "de"
    available_languages: List[str] = field(default_factory=lambda: ["de", "en"])


@dataclass
class DiaryConfig:
    lock_policy: str = "daily_midnight"  # "daily_midnight" | "on_submit"
    theme: str = "sepia"  # "sepia" | "solarized_light" | "paper_dark"
    font_family: str = "Noto Serif"
    font_size: int = 14
    auto_save_delay_ms: int = 1000


@dataclass
class LanguageToolConfig:
    enabled: bool = True
    server_url: str = "http://localhost:8010/v2"
    timeout_seconds: float = 4.0


@dataclass
class NLPConfig:
    run_on_lock: bool = True
    languagetool: LanguageToolConfig = field(default_factory=LanguageToolConfig)
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b"


@dataclass
class AppConfig:
    user: UserConfig = field(default_factory=UserConfig)
    diary: DiaryConfig = field(default_factory=DiaryConfig)
    nlp: NLPConfig = field(default_factory=NLPConfig)
    project_root: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    db_path: Path = field(default_factory=lambda: Path("data/diary.db"))

    def get_absolute_db_path(self) -> Path:
        if self.db_path.is_absolute():
            return self.db_path
        return self.project_root / self.db_path


def get_default_config_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "config.yaml"


def load_config(config_path: Optional[Path] = None) -> AppConfig:
    path = config_path or get_default_config_path()
    project_root = path.resolve().parent

    if not path.exists():
        return AppConfig(project_root=project_root)

    with open(path, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = yaml.safe_load(f) or {}

    user_data = data.get("user", {})
    diary_data = data.get("diary", {})
    nlp_data = data.get("nlp", {})

    available_langs = user_data.get("available_languages", ["de", "en"])
    active_lang = user_data.get("active_target_language", "de")
    if active_lang not in available_langs:
        available_langs.append(active_lang)

    user_cfg = UserConfig(
        native_language=user_data.get("native_language", "pt-BR"),
        active_target_language=active_lang,
        available_languages=available_langs,
    )

    diary_cfg = DiaryConfig(
        lock_policy=diary_data.get("lock_policy", "daily_midnight"),
        theme=diary_data.get("theme", "sepia"),
        font_family=diary_data.get("font_family", "Noto Serif"),
        font_size=int(diary_data.get("font_size", 14)),
        auto_save_delay_ms=int(diary_data.get("auto_save_delay_ms", 1000)),
    )

    lt_data = nlp_data.get("languagetool", {})
    lt_cfg = LanguageToolConfig(
        enabled=bool(lt_data.get("enabled", True)),
        server_url=str(lt_data.get("server_url", "http://localhost:8010/v2")),
        timeout_seconds=float(lt_data.get("timeout_seconds", 4.0)),
    )

    nlp_cfg = NLPConfig(
        run_on_lock=bool(nlp_data.get("run_on_lock", True)),
        languagetool=lt_cfg,
        llm_provider=nlp_data.get("llm_provider", "ollama"),
        llm_model=nlp_data.get("llm_model", "llama3.1:8b"),
    )

    return AppConfig(
        user=user_cfg,
        diary=diary_cfg,
        nlp=nlp_cfg,
        project_root=project_root,
        db_path=Path("data/diary.db"),
    )


def save_config(config: AppConfig, config_path: Optional[Path] = None) -> None:
    path = config_path or get_default_config_path()
    data = {
        "user": {
            "native_language": config.user.native_language,
            "active_target_language": config.user.active_target_language,
            "available_languages": config.user.available_languages,
        },
        "diary": {
            "lock_policy": config.diary.lock_policy,
            "theme": config.diary.theme,
            "font_family": config.diary.font_family,
            "font_size": config.diary.font_size,
            "auto_save_delay_ms": config.diary.auto_save_delay_ms,
        },
        "nlp": {
            "run_on_lock": config.nlp.run_on_lock,
            "languagetool": {
                "enabled": config.nlp.languagetool.enabled,
                "server_url": config.nlp.languagetool.server_url,
                "timeout_seconds": config.nlp.languagetool.timeout_seconds,
            },
            "llm_provider": config.nlp.llm_provider,
            "llm_model": config.nlp.llm_model,
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
