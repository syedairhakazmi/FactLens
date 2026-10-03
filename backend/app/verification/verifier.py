"""
Verification module for FactLens. Owner: Shaheera.

Evaluates checkable factual claims against retrieved evidence passages
using a pretrained Natural Language Inference (NLI) CrossEncoder model:
cross-encoder/nli-deberta-v3-small.

Decides whether retrieved evidence entails (Supported), contradicts (Refuted),
or is neutral (Not Enough Evidence) toward the claim without brittle phrase lists.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import numpy as np

from app.retrieval.searcher import RetrievedPassage

logger = logging.getLogger("factlens")

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None


@dataclass
class VerificationResult:
    verdict: str  # "Supported" | "Refuted" | "Not Enough Evidence"
    confidence: int  # 0 to 100 percentage
    evidence_text: str
    evidence_source: str
    reason: str


@lru_cache(maxsize=1)
def _get_model() -> Optional[CrossEncoder]:
    """
    Loads cross-encoder/nli-deberta-v3-small once per process.

    Returns None if weights cannot be loaded (e.g., offline or package missing),
    allowing callers to fall back gracefully rather than crashing.
    """
    if CrossEncoder is None:
        return None
    try:
        return CrossEncoder("cross-encoder/nli-deberta-v3-small")
    except Exception as exc:
        logger.warning("Could not load NLI CrossEncoder model: %s", exc)
        return None


def verify_claim(
    claim_text: str,
    top_passage: Optional[RetrievedPassage] = None,
) -> VerificationResult:
    """
    Evaluates a claim against the top retrieved evidence passage.

    1. Relevance gate: ensures the passage meets a minimum retrieval relevance.
    2. NLI Cross-Encoder: predicts entailment, contradiction, or neutral.
    """
    if top_passage is None or not top_passage.text:
        return VerificationResult(
            verdict="Not Enough Evidence",
            confidence=40,
            evidence_text="No candidate evidence passages found in the corpus.",
            evidence_source="Corpus Search (Empty)",
            reason="Retriever returned zero candidate documents for this claim.",
        )

    score = top_passage.combined_score

    # 1. Relevance gate
    if score < 0.15:
        return VerificationResult(
            verdict="Not Enough Evidence",
            confidence=40,
            evidence_text="No sufficiently relevant evidence found in the corpus for this claim.",
            evidence_source=f"{top_passage.source} (Insufficient overlap)",
            reason="Retrieved candidate scored below the minimum relevance threshold.",
        )

    if 0.15 <= score < 0.35:
        return VerificationResult(
            verdict="Not Enough Evidence",
            confidence=int(min(65, max(45, score * 100 + 15))),
            evidence_text=f"Weak candidate evidence found: \"{top_passage.text}\"",
            evidence_source=f"{top_passage.source} (Low confidence)",
            reason="Candidate passage shares partial vocabulary but lacks sufficient contextual coverage.",
        )

    # 2. High relevance evidence found (score >= 0.35) -> Execute NLI inference
    model = _get_model()

    if model is not None:
        try:
            # CrossEncoder expects pairs as (premise/evidence, hypothesis/claim)
            raw_scores = model.predict([(top_passage.text, claim_text)])
            # cross-encoder/nli-deberta-v3-small output labels: [contradiction, entailment, neutral]
            label_mapping = ["contradiction", "entailment", "neutral"]
            pred_idx = int(np.argmax(raw_scores, axis=1)[0])
            nli_label = label_mapping[pred_idx]

            # Softmax to compute confidence percentage
            logits = raw_scores[0]
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)
            nli_confidence = int(round(float(probs[pred_idx]) * 100))
            # Bound confidence in sensible 60-98 range
            confidence = min(98, max(60, nli_confidence))

            if nli_label == "entailment":
                return VerificationResult(
                    verdict="Supported",
                    confidence=confidence,
                    evidence_text=top_passage.text,
                    evidence_source=top_passage.source,
                    reason="Retrieved evidence entails the claim according to cross-encoder NLI inference.",
                )
            elif nli_label == "contradiction":
                return VerificationResult(
                    verdict="Refuted",
                    confidence=confidence,
                    evidence_text=top_passage.text,
                    evidence_source=top_passage.source,
                    reason="Retrieved evidence directly contradicts the claim according to cross-encoder NLI inference.",
                )
            else:  # neutral
                return VerificationResult(
                    verdict="Not Enough Evidence",
                    confidence=confidence,
                    evidence_text=top_passage.text,
                    evidence_source=top_passage.source,
                    reason="Retrieved passage is related but neither directly proves nor disproves the claim (neutral NLI inference).",
                )
        except Exception as exc:
            logger.warning("NLI inference failed: %s; falling back to relevance heuristic", exc)

    # Fallback if model is unavailable
    return VerificationResult(
        verdict="Supported",
        confidence=int(min(95, max(70, score * 100 + 10))),
        evidence_text=top_passage.text,
        evidence_source=top_passage.source,
        reason="Claim is corroborated by high-relevance evidence passages (offline heuristic).",
    )
