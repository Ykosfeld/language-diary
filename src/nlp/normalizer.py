"""Taxonomy normalization and word_target extraction for Language Diary."""

import re
import string
from typing import Optional


# Set of common articles/particles in target languages to strip when deriving the primary target word
STOPWORDS_ARTICLES = {
    "de": {"der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem", "einer", "eines"},
    "en": {"the", "a", "an"},
    "pt-BR": {"o", "a", "os", "as", "um", "uma", "uns", "umas"},
}

PUNCTUATION_TRANSLATOR = str.maketrans("", "", string.punctuation + "„“”»«‚‘")


def derive_error_type(
    rule_id: str,
    category: str,
    original_span: str,
    expected_span: Optional[str],
) -> str:
    """
    Derives the XML tag type attribute following ROADMAP Section 4.2:
    'declination', 'conjugation', 'word_order', 'preposition', 'orthography',
    'lexical_choice', 'missing_word', 'unnecessary_word'.
    """
    norm_rule = rule_id.upper()
    norm_cat = category.upper()

    # 1. Structural / omission / insertion checks based on span emptiness
    if not original_span.strip() and expected_span:
        if "PRAEP" in norm_rule or "PREP" in norm_rule:
            return "preposition_missing"
        return "missing_word"

    if original_span.strip() and (expected_span is None or expected_span.strip() == ""):
        return "unnecessary_word"

    # 2. Word order rules
    if (
        "WORD_ORDER" in norm_rule
        or "VERB_POSITION" in norm_rule
        or "SYNTAX" in norm_cat
        or "SENTENCE_STRUCTURE" in norm_rule
    ):
        return "word_order"

    # 3. Preposition rules
    if (
        "PRAEP" in norm_rule
        or "PREPOSITION" in norm_rule
        or "PREP" in norm_rule
        or "REGISTRATION" in norm_rule
    ):
        return "preposition"

    # 4. Declination / Agreement (cases, gender, articles, adjective endings)
    if (
        "AGREEMENT" in norm_rule
        or "DECLINATION" in norm_rule
        or "DE_CASE" in norm_rule
        or "ARTIKEL" in norm_rule
        or "KASUS" in norm_rule
        or "GENUS" in norm_rule
        or "ADJEKTIV" in norm_rule
    ):
        return "declination"

    # 5. Verbal Conjugation
    if (
        "CONJUGATION" in norm_rule
        or "NON3PRS_VERB" in norm_rule
        or "VERB" in norm_rule
        or "TENSE" in norm_rule
        or "PARTIZIP" in norm_rule
        or "AUXILIARY" in norm_rule
    ):
        return "conjugation"

    # 6. Lexical choice
    if (
        "CONFUSED" in norm_rule
        or "COLLOCATION" in norm_rule
        or "SEMANTICS" in norm_cat
        or "FALSE_FRIEND" in norm_rule
    ):
        return "lexical_choice"

    # 7. Default to orthography (spelling, typos, casing, punctuation)
    return "orthography"


def extract_word_target(
    expected_span: Optional[str],
    original_span: str,
    target_language: str = "de",
    sentence_context: Optional[str] = None,
    match_offset_in_context: Optional[int] = None,
    match_length: Optional[int] = None,
) -> Optional[str]:
    """
    Extracts a normalized lower-case target word for analytical vocabulary tracking.
    Example:
      'den Park' -> 'park'
      'müde' -> 'müde'
      'gegangen' -> 'gegangen'
      'zu' -> 'zu'
    If the error span is just an article (e.g. 'den'/'das'), inspects sentence_context
    to attach the error to the relevant noun (e.g. 'das' Park -> 'park').
    """
    raw = (expected_span if expected_span and expected_span.strip() else original_span).strip()
    if not raw:
        return None

    # Remove enclosing punctuation
    cleaned = raw.translate(PUNCTUATION_TRANSLATOR).strip().lower()
    if not cleaned:
        return None

    tokens = cleaned.split()
    if not tokens:
        return None

    # If multiple tokens, try to eliminate articles/determiners to isolate the substantive head
    lang_key = target_language.split("-")[0].lower()
    stopwords = STOPWORDS_ARTICLES.get(lang_key, set())

    meaningful_tokens = [tok for tok in tokens if tok not in stopwords]
    if meaningful_tokens:
        # Return the most salient token (usually the noun or last word in compound phrases like 'den Park' -> 'park')
        return meaningful_tokens[-1]

    # If the span consists solely of articles (e.g. expected was just 'den'),
    # look ahead in sentence_context to bind the error to the affected noun
    if sentence_context and match_offset_in_context is not None and match_length is not None:
        after_offset = match_offset_in_context + match_length
        if 0 <= after_offset < len(sentence_context):
            after_text = sentence_context[after_offset:].strip()
            after_cleaned = after_text.translate(PUNCTUATION_TRANSLATOR).strip().lower()
            after_tokens = after_cleaned.split()
            for cand in after_tokens:
                if cand not in stopwords:
                    return cand

    # Fallback to the token itself if no noun was found in context
    return tokens[0]
