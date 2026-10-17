"""Unit tests for NLP normalizer and XML annotator."""

from src.nlp.annotator import (
    annotate_text,
    build_clean_text,
    format_err_tag,
    resolve_overlapping_spans,
)
from src.nlp.base_engine import AnalysisSpan
from src.nlp.normalizer import derive_error_type, extract_word_target


def test_derive_error_type():
    # Substitution declination
    assert derive_error_type("DE_AGREEMENT", "GRAMMAR", "das", "den") == "declination"
    assert derive_error_type("GERMAN_SPELLER_RULE", "TYPOS", "muede", "müde") == "orthography"

    # Conjugation
    assert derive_error_type("NON3PRS_VERB", "GRAMMAR", "gehst", "geht") == "conjugation"

    # Word order
    assert derive_error_type("DE_VERB_POSITION", "SYNTAX", "bin müde", "müde bin") == "word_order"

    # Preposition
    assert derive_error_type("PRAEP_MIT_DAT", "GRAMMAR", "zu", "nach") == "preposition"

    # Omission (empty original)
    assert derive_error_type("MISSING_PREP", "GRAMMAR", "", "auf") == "preposition_missing"
    assert derive_error_type("MISSING_WORD", "GRAMMAR", "", "ich") == "missing_word"

    # Insertion / unnecessary word
    assert derive_error_type("REDUNDANT_WORD", "STYLE", "zu", "") == "unnecessary_word"


def test_extract_word_target():
    # Compound phrase with article stripped
    assert extract_word_target("den Park", "das Park", "de") == "park"
    assert extract_word_target("müde", "muede", "de") == "müde"
    assert extract_word_target("the book", "book", "en") == "book"
    assert extract_word_target("", "zu", "de") == "zu"
    assert extract_word_target(None, "Haus", "de") == "haus"

    # Context lookahead: when span is only an article, grabs the head noun from sentence context
    assert extract_word_target(
        "den", "das", "de",
        sentence_context="Ich gehe in das Park.",
        match_offset_in_context=12,
        match_length=3,
    ) == "park"


def test_format_err_tag_escaping():
    span = AnalysisSpan(
        offset=0,
        length=5,
        original_span='A & "B"',
        expected_span='C < "D"',
        error_type="orthography",
    )
    tag = format_err_tag(span, 'A & "B"')
    assert 'expected="C &lt; &quot;D&quot;"' in tag
    assert 'A &amp; "B"' in tag


def test_format_err_tag_variations():
    # 1. Substitution
    span_sub = AnalysisSpan(
        offset=12,
        length=3,
        original_span="das",
        expected_span="den",
        error_type="declination",
    )
    assert format_err_tag(span_sub, "das") == '<err type="declination" expected="den">das</err>'

    # 2. Omission
    span_omiss = AnalysisSpan(
        offset=10,
        length=0,
        original_span="",
        expected_span="auf",
        error_type="preposition_missing",
    )
    assert format_err_tag(span_omiss, "") == '<err type="preposition_missing" expected="auf"></err>'

    # 3. Insertion
    span_ins = AnalysisSpan(
        offset=9,
        length=2,
        original_span="zu",
        expected_span="",
        error_type="unnecessary_word",
    )
    assert format_err_tag(span_ins, "zu") == '<err type="unnecessary_word" expected="">zu</err>'

    # 4. Word Order
    span_wo = AnalysisSpan(
        offset=15,
        length=8,
        original_span="bin müde",
        expected_span="müde bin",
        error_type="word_order",
    )
    assert format_err_tag(span_wo, "bin müde") == '<err type="word_order" expected="müde bin">bin müde</err>'


def test_annotate_text_clean_sequence():
    # Multiple distinct errors in a sentence
    raw = "Ich gehe in das Park und ich habe zu gegessen."
    spans = [
        AnalysisSpan(
            offset=12,
            length=3,
            original_span="das",
            expected_span="den",
            error_type="declination",
        ),
        AnalysisSpan(
            offset=34,
            length=2,
            original_span="zu",
            expected_span="",
            error_type="unnecessary_word",
        ),
    ]

    annotated = annotate_text(raw, spans)
    expected = (
        'Ich gehe in <err type="declination" expected="den">das</err> Park '
        'und ich habe <err type="unnecessary_word" expected="">zu</err> gegessen.'
    )
    assert annotated == expected


def test_overlapping_spans_priority():
    raw = "weil ich bin müde."
    wo_span = AnalysisSpan(
        offset=9,
        length=8,
        original_span="bin müde",
        expected_span="müde bin",
        error_type="word_order",
    )
    typo_span = AnalysisSpan(
        offset=13,
        length=4,
        original_span="müde",
        expected_span="müde",
        error_type="orthography",
    )

    resolved = resolve_overlapping_spans([wo_span, typo_span])
    assert len(resolved) == 1
    assert resolved[0].error_type == "word_order"

    annotated = annotate_text(raw, [wo_span, typo_span])
    assert annotated == 'weil ich <err type="word_order" expected="müde bin">bin müde</err>.'


def test_build_clean_text():
    raw = "Ich gehe in das Park."
    spans = [
        AnalysisSpan(
            offset=12,
            length=3,
            original_span="das",
            expected_span="den",
            error_type="declination",
        )
    ]
    clean = build_clean_text(raw, spans)
    assert clean == "Ich gehe in den Park."
