"""Unit tests for LanguageToolClient."""

import json
from unittest.mock import MagicMock, patch
import urllib.error

from src.nlp.languagetool_client import LanguageToolClient


SAMPLE_LT_RESPONSE = {
    "software": {"name": "LanguageTool", "version": "6.0"},
    "matches": [
        {
            "message": "Der bestimmte Artikel passt hier nicht zum Kasus.",
            "offset": 12,
            "length": 3,
            "replacements": [{"value": "den"}],
            "context": {
                "text": "Ich gehe in das Park.",
                "offset": 12,
                "length": 3,
            },
            "rule": {
                "id": "DE_AGREEMENT",
                "description": "Kongruenz von Artikel und Nomen",
                "category": {
                    "id": "GRAMMAR",
                    "name": "Grammatik",
                },
            },
        }
    ],
}


def test_parse_matches():
    client = LanguageToolClient()
    text = "Ich gehe in das Park."
    spans = client.parse_matches(SAMPLE_LT_RESPONSE["matches"], text, "de")

    assert len(spans) == 1
    span = spans[0]
    assert span.offset == 12
    assert span.length == 3
    assert span.original_span == "das"
    assert span.expected_span == "den"
    assert span.error_type == "declination"
    assert span.category == "GRAMMAR"
    assert span.rule_id == "DE_AGREEMENT"
    assert span.word_target == "park"


def test_check_text_mocked_success():
    client = LanguageToolClient(server_url="http://localhost:8010/v2")
    text = "Ich gehe in das Park."

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps(SAMPLE_LT_RESPONSE).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        spans = client.check_text(text, "de")
        assert len(spans) == 1
        assert spans[0].expected_span == "den"


def test_check_text_offline_server_fallback():
    client = LanguageToolClient(server_url="http://localhost:9999/v2", timeout_seconds=0.1)

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        spans = client.check_text("Some text", "en")
        # Should gracefully return empty list without crashing or raising exceptions
        assert spans == []


def test_check_health():
    client = LanguageToolClient()
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert client.check_health() is True

    with patch("urllib.request.urlopen", side_effect=Exception("Server down")):
        assert client.check_health() is False
