"""Orchestrator engine for Phase 2 NLP pipeline."""

import logging
from typing import Optional
from src.core.config import AppConfig
from src.nlp.annotator import annotate_text, build_clean_text
from src.nlp.base_engine import AnalysisResult, BaseNLPEngine
from src.nlp.languagetool_client import LanguageToolClient

logger = logging.getLogger(__name__)


class NLPEngine(BaseNLPEngine):
    """
    Daily analytical engine executing the Phase 2 cascade pipeline.
    In the initial setup, Stage 1 (LanguageTool mechanical filter) is active.
    Stage 2 (LLM syntax judge) can be plugged in when enabled.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        lt_client: Optional[LanguageToolClient] = None,
    ):
        self.config = config
        if lt_client:
            self.lt_client = lt_client
        elif config:
            lt_cfg = config.nlp.languagetool
            self.lt_client = LanguageToolClient(
                server_url=lt_cfg.server_url,
                timeout_seconds=lt_cfg.timeout_seconds,
            )
        else:
            self.lt_client = LanguageToolClient()

    def analyze(self, text: str, target_language: str) -> AnalysisResult:
        if not text or not text.strip():
            return AnalysisResult(
                annotated_text="",
                spans=[],
                clean_text="",
                success=True,
            )

        # Check if LanguageTool is enabled in configuration
        is_enabled = True
        if self.config and hasattr(self.config.nlp, "languagetool"):
            is_enabled = self.config.nlp.languagetool.enabled

        if not is_enabled:
            logger.info("LanguageTool analysis is disabled in configuration.")
            return AnalysisResult(
                annotated_text=text,
                spans=[],
                clean_text=text,
                success=True,
            )

        try:
            # Stage 1: Mechanical Filter via LanguageTool
            spans = self.lt_client.check_text(text, target_language)

            # Generate inline XML tags (<err>) and clean staging text
            annotated = annotate_text(text, spans)
            clean = build_clean_text(text, spans)

            # Note: Stage 2 (LLM Syntax Judge) will be chained here when enabled,
            # taking `clean` as input and augmenting `spans` with macro-syntactic tags.

            return AnalysisResult(
                annotated_text=annotated,
                spans=spans,
                clean_text=clean,
                success=True,
            )
        except Exception as e:
            logger.exception("Failed to analyze text for %s: %s", target_language, e)
            return AnalysisResult(
                annotated_text=text,
                spans=[],
                clean_text=text,
                success=False,
                error_message=str(e),
            )
