"""Client for local LanguageTool HTTP Server (/v2/check)."""

import json
import logging
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.parse
import urllib.request

from src.nlp.base_engine import AnalysisSpan
from src.nlp.normalizer import derive_error_type, extract_word_target

logger = logging.getLogger(__name__)

# Mapping from internal target language codes to LanguageTool locale codes
LANGUAGE_MAP = {
    "de": "de-DE",
    "en": "en-US",
    "pt-BR": "pt-BR",
    "pt": "pt-BR",
    "fr": "fr",
    "es": "es",
    "it": "it",
}


class LanguageToolClient:
    def __init__(
        self,
        server_url: str = "http://localhost:8010/v2",
        timeout_seconds: float = 4.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _resolve_lang_code(self, lang: str) -> str:
        return LANGUAGE_MAP.get(lang, LANGUAGE_MAP.get(lang.split("-")[0], "auto"))

    def check_health(self) -> bool:
        """Pings LanguageTool server to verify availability."""
        url = f"{self.server_url}/languages"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return resp.status == 200
        except Exception:
            return False

    def parse_matches(self, matches: List[Dict[str, Any]], text: str, target_language: str) -> List[AnalysisSpan]:
        """Converts raw LanguageTool JSON matches into structured AnalysisSpan instances."""
        spans: List[AnalysisSpan] = []

        for m in matches:
            offset = int(m.get("offset", 0))
            length = int(m.get("length", 0))

            # Extract original slice safely
            if 0 <= offset <= len(text):
                original_span = text[offset : offset + length]
            else:
                original_span = ""

            replacements = m.get("replacements", [])
            expected_span = replacements[0].get("value") if replacements else None

            rule = m.get("rule", {})
            rule_id = str(rule.get("id", "UNKNOWN_RULE"))
            rule_description = str(rule.get("description", ""))

            category_info = rule.get("category", {})
            category = str(category_info.get("id", "GRAMMAR"))

            message = str(m.get("message", ""))
            context_info = m.get("context", {})
            sentence_context = str(context_info.get("text", text))

            # Determine taxonomy error_type for <err type="..."> tag
            error_type = derive_error_type(rule_id, category, original_span, expected_span)

            # Determine normalized target word for analytical vocabulary tracking
            context_offset = int(context_info.get("offset", offset))
            context_length = int(context_info.get("length", length))
            word_target = extract_word_target(
                expected_span,
                original_span,
                target_language,
                sentence_context=sentence_context,
                match_offset_in_context=context_offset,
                match_length=context_length,
            )

            span = AnalysisSpan(
                offset=offset,
                length=length,
                original_span=original_span,
                expected_span=expected_span,
                error_type=error_type,
                category=category,
                rule_id=rule_id,
                rule_description=rule_description,
                message=message,
                sentence_context=sentence_context,
                word_target=word_target,
            )
            spans.append(span)

        return spans

    def check_text(self, text: str, target_language: str) -> List[AnalysisSpan]:
        """
        Sends text to LanguageTool /v2/check endpoint and returns extracted spans.
        Catches network errors gracefully and logs them without crashing the host application.
        """
        if not text or not text.strip():
            return []

        lt_lang = self._resolve_lang_code(target_language)
        endpoint = f"{self.server_url}/check"

        payload = {
            "text": text,
            "language": lt_lang,
        }
        encoded_data = urllib.parse.urlencode(payload).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=encoded_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    logger.warning(
                        "LanguageTool server returned non-200 status: %d", response.status
                    )
                    return []

                raw_bytes = response.read()
                data = json.loads(raw_bytes.decode("utf-8"))
                matches = data.get("matches", [])
                return self.parse_matches(matches, text, target_language)

        except urllib.error.URLError as e:
            logger.warning("LanguageTool server unreachable at %s: %s", endpoint, e)
            return []
        except Exception as e:
            logger.warning("Error querying LanguageTool at %s: %s", endpoint, e)
            return []
