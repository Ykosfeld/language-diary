"""Abstract base engine and data contracts for Phase 2 NLP pipeline."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AnalysisSpan:
    offset: int
    length: int
    original_span: str
    expected_span: Optional[str] = None
    error_type: str = "orthography"  # mapped for <err type="..."> XML attribute
    category: str = "TYPOS"          # macro category for error_logs table
    rule_id: str = "SPELLCHECK"      # rule identifier (e.g. DE_AGREEMENT)
    rule_description: str = ""
    message: str = ""
    sentence_context: str = ""
    word_target: Optional[str] = None

    @property
    def end_offset(self) -> int:
        return self.offset + self.length


@dataclass
class AnalysisResult:
    annotated_text: str
    spans: List[AnalysisSpan] = field(default_factory=list)
    clean_text: str = ""
    success: bool = True
    error_message: Optional[str] = None


class BaseNLPEngine(ABC):
    @abstractmethod
    def analyze(self, text: str, target_language: str) -> AnalysisResult:
        """
        Analyzes raw text and returns annotated text with structured error spans.
        Must never modify or overwrite the original raw text.
        """
        pass
