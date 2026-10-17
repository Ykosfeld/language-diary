"""XML inline annotation serializer (<err>) and positional span reconciler."""

import html
from typing import List
from src.nlp.base_engine import AnalysisSpan


# Hierarchy priority for resolving colliding/overlapping spans:
# Macro-structural deviations take precedence over mechanical typos.
ERROR_TYPE_PRIORITY = {
    "word_order": 100,
    "conjugation": 80,
    "declination": 70,
    "preposition": 60,
    "preposition_missing": 60,
    "lexical_choice": 50,
    "missing_word": 40,
    "unnecessary_word": 40,
    "orthography": 10,
}


def resolve_overlapping_spans(spans: List[AnalysisSpan]) -> List[AnalysisSpan]:
    """
    Resolves overlapping or colliding spans to ensure valid, clean XML without nested tags.
    When collisions occur, higher-priority structural errors or longer spans win.
    """
    if not spans:
        return []

    # Sort primarily by start offset ascending.
    # Secondary: Priority descending.
    # Tertiary: Length descending.
    sorted_spans = sorted(
        spans,
        key=lambda s: (
            s.offset,
            -ERROR_TYPE_PRIORITY.get(s.error_type, 0),
            -s.length,
        ),
    )

    accepted: List[AnalysisSpan] = []

    for span in sorted_spans:
        if not accepted:
            accepted.append(span)
            continue

        prev = accepted[-1]

        # Check for overlap: does current span start before the previous span ends?
        if span.offset < prev.end_offset:
            # Conflict detected! Check which one has higher priority
            prev_priority = ERROR_TYPE_PRIORITY.get(prev.error_type, 0)
            curr_priority = ERROR_TYPE_PRIORITY.get(span.error_type, 0)

            if curr_priority > prev_priority or (curr_priority == prev_priority and span.length > prev.length):
                # Replace previous with current if current is strictly superior and encloses or replaces it
                accepted[-1] = span
            # Otherwise, previous span wins; current span is skipped from inline XML
            continue

        accepted.append(span)

    return accepted


def format_err_tag(span: AnalysisSpan, raw_slice: str) -> str:
    """
    Formats a single XML <err> tag following the contract in ROADMAP Section 4.2.
    - Substitution: <err type="declination" expected="den">das</err>
    - Omission:     <err type="preposition_missing" expected="auf"></err>
    - Insertion:    <err type="unnecessary_word" expected="">zu</err>
    - Word Order:   <err type="word_order" expected="müde bin">bin müde</err>
    """
    expected = html.escape(span.expected_span or "", quote=True)
    err_type = html.escape(span.error_type, quote=True)

    # Note: raw_slice inside the tag body does not need quote escaping, but special chars like < > & should be safe
    body = html.escape(raw_slice, quote=False)

    return f'<err type="{err_type}" expected="{expected}">{body}</err>'


def annotate_text(raw_text: str, spans: List[AnalysisSpan]) -> str:
    """
    Injects <err> tags into raw_text using positional offsets.
    Guarantees that raw_text is never modified in-place and offsets are resolved from end to start.
    """
    if not spans or not raw_text:
        return raw_text

    clean_spans = resolve_overlapping_spans(spans)

    # Process spans in reverse offset order (from right to left)
    # so earlier string offsets remain valid as we insert XML tags.
    sorted_spans = sorted(clean_spans, key=lambda s: s.offset, reverse=True)

    result = raw_text
    for span in sorted_spans:
        if span.offset < 0 or span.offset > len(result):
            continue

        end = min(span.end_offset, len(result))
        raw_slice = result[span.offset:end]
        tag = format_err_tag(span, raw_slice)

        result = result[: span.offset] + tag + result[end :]

    return result


def build_clean_text(raw_text: str, spans: List[AnalysisSpan]) -> str:
    """
    Builds a temporary clean text where corrections are applied.
    Useful as staged input for downstream syntax checkers or readers.
    """
    if not spans or not raw_text:
        return raw_text

    clean_spans = resolve_overlapping_spans(spans)
    sorted_spans = sorted(clean_spans, key=lambda s: s.offset, reverse=True)

    result = raw_text
    for span in sorted_spans:
        if span.offset < 0 or span.offset > len(result):
            continue

        end = min(span.end_offset, len(result))
        replacement = span.expected_span or ""
        result = result[: span.offset] + replacement + result[end :]

    return result
