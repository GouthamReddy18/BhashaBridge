"""Deterministic corpus BLEU and chrF implementations with fixed settings."""
from __future__ import annotations

import math
import unicodedata
from collections import Counter
from collections.abc import Sequence

from app.schemas.evaluation import MetricConfiguration

METRIC_CONFIGURATION = MetricConfiguration()


def normalize_metric_text(value: str) -> str:
    """Apply the metric contract's Unicode NFC and whitespace normalization."""
    return " ".join(unicodedata.normalize("NFC", value).split())


def _validate_corpus(references: Sequence[str], hypotheses: Sequence[str]) -> None:
    if len(references) != len(hypotheses):
        raise ValueError("references and hypotheses must have the same number of rows")
    for index, (reference, hypothesis) in enumerate(zip(references, hypotheses)):
        if not isinstance(reference, str) or not normalize_metric_text(reference):
            raise ValueError(f"reference at index {index} must be nonblank")
        if not isinstance(hypothesis, str) or not normalize_metric_text(hypothesis):
            raise ValueError(f"hypothesis at index {index} must be nonblank")


def _ngrams(tokens: Sequence[str], order: int) -> Counter[tuple[str, ...]]:
    return Counter(tuple(tokens[start:start + order]) for start in range(len(tokens) - order + 1))


def corpus_bleu(references: Sequence[str], hypotheses: Sequence[str]) -> float | None:
    """Corpus BLEU-4 (0..100), whitespace tokenization, exponential smoothing.

    This is corpus aggregation with one reference per hypothesis. An empty
    corpus has no score; blank rows are invalid and must be handled as missing.
    """
    _validate_corpus(references, hypotheses)
    if not references:
        return None

    matches = [0, 0, 0, 0]
    totals = [0, 0, 0, 0]
    hypothesis_length = 0
    reference_length = 0
    for reference, hypothesis in zip(references, hypotheses):
        reference_tokens = normalize_metric_text(reference).split()
        hypothesis_tokens = normalize_metric_text(hypothesis).split()
        hypothesis_length += len(hypothesis_tokens)
        reference_length += len(reference_tokens)
        for order in range(1, 5):
            hyp_counts = _ngrams(hypothesis_tokens, order)
            ref_counts = _ngrams(reference_tokens, order)
            totals[order - 1] += sum(hyp_counts.values())
            matches[order - 1] += sum(
                min(count, ref_counts[ngram]) for ngram, count in hyp_counts.items()
            )

    if hypothesis_length == 0 or reference_length == 0:
        return None
    precisions: list[float] = []
    smoothing = 1.0
    for matched, total in zip(matches, totals):
        if total == 0:
            # Effective order omits n-gram orders unavailable in this corpus.
            continue
        if matched:
            precisions.append(matched / total)
        else:
            smoothing *= 2.0
            precisions.append(1.0 / (smoothing * total))
    if not precisions:
        return None
    brevity_penalty = (
        1.0
        if hypothesis_length > reference_length
        else math.exp(1.0 - reference_length / hypothesis_length)
    )
    return 100.0 * brevity_penalty * math.exp(sum(math.log(p) for p in precisions) / len(precisions))


def _character_ngrams(text: str, order: int) -> Counter[str]:
    characters = [character for character in text if not character.isspace()]
    return Counter(
        "".join(characters[start:start + order])
        for start in range(len(characters) - order + 1)
    )


def corpus_chrf(references: Sequence[str], hypotheses: Sequence[str]) -> float | None:
    """Corpus chrF (0..100): char 1..6 grams, word_order=0, beta=2.

    NFC-normalized, whitespace-collapsed strings are case-sensitive; all
    whitespace is removed before character n-gram extraction. Counts are
    clipped per row and pooled by n-gram order across the corpus.
    """
    _validate_corpus(references, hypotheses)
    if not references:
        return None

    matched = [0] * 6
    hypothesis_totals = [0] * 6
    reference_totals = [0] * 6
    for reference, hypothesis in zip(references, hypotheses):
        ref = normalize_metric_text(reference)
        hyp = normalize_metric_text(hypothesis)
        for order in range(1, 7):
            ref_counts = _character_ngrams(ref, order)
            hyp_counts = _character_ngrams(hyp, order)
            reference_totals[order - 1] += sum(ref_counts.values())
            hypothesis_totals[order - 1] += sum(hyp_counts.values())
            matched[order - 1] += sum(
                min(count, ref_counts[ngram]) for ngram, count in hyp_counts.items()
            )

    active_orders = [
        index for index in range(6)
        if reference_totals[index] or hypothesis_totals[index]
    ]
    if not active_orders:
        return None
    precision = sum(
        matched[i] / hypothesis_totals[i] if hypothesis_totals[i] else 0.0
        for i in active_orders
    ) / len(active_orders)
    recall = sum(
        matched[i] / reference_totals[i] if reference_totals[i] else 0.0
        for i in active_orders
    ) / len(active_orders)
    beta_squared = 4.0
    denominator = beta_squared * precision + recall
    if denominator == 0:
        return 0.0
    return 100.0 * (1.0 + beta_squared) * precision * recall / denominator
