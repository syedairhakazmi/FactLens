"""
Verification module for FactLens. Owner: Shaheera.

This module compares checkable claims against top-ranked retrieved evidence
passages to compute a verdict (Supported, Refuted, Not Enough Evidence) and
associated confidence score.

In Phase 1 / Iteration 1, this acts as the structured verification stub.
In Phase 2 / Iteration 2 (Week 10), this stub will be upgraded to a fine-tuned
RoBERTa-NLI (Natural Language Inference) transformer model.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from app.retrieval.searcher import RetrievedPassage


@dataclass
class VerificationResult:
    verdict: str  # "Supported" | "Refuted" | "Not Enough Evidence"
    confidence: int  # 0 to 100 percentage
    evidence_text: str
    evidence_source: str
    reason: str


def verify_claim(
    claim_text: str,
    top_passage: Optional[RetrievedPassage] = None,
) -> VerificationResult:
    """
    Evaluates a claim against the top retrieved evidence passage.

    Handles:
    - High-relevance evidence with semantic agreement (Supported)
    - High-relevance evidence with contradiction / negation (Refuted)
    - Negated claims that agree with negative evidence (Supported)
    - Low-relevance or missing evidence (Not Enough Evidence)
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
    claim_lower = claim_text.lower().strip()
    evidence_lower = top_passage.text.lower().strip()

    # 1. Relevance gate: if the best retrieved evidence has low relevance,
    # we cannot reliably support or refute the claim.
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

    # 2. High relevance evidence found (score >= 0.35)
    # Check for polarity / negation alignment:
    evidence_denies_assertion = any(
        phrase in evidence_lower
        for phrase in [
            "no statistically significant",
            "no link",
            "does not cause",
            "did not cause",
            "unfounded",
            "no evidence",
            "fake",
            "debunked",
            "false",
        ]
    )

    claim_denies_assertion = any(
        phrase in claim_lower
        for phrase in [
            "does not cause",
            "does not",
            "do not",
            "not cause",
            "no link",
            "is not linked",
            "are not linked",
            "never causes",
            "not true",
        ]
    )

    claim_asserts_disproven_claim = any(
        phrase in claim_lower
        for phrase in [
            "causes infertility",
            "cause infertility",
            "causing infertility",
            "is fake",
            "is a hoax",
            "secret base on mars",
        ]
    )

    # Case A: Evidence denies the assertion (e.g. "no statistically significant link between vaccines and infertility")
    if evidence_denies_assertion:
        if claim_denies_assertion:
            # Claim agrees with the evidence ("vaccine does NOT cause infertility" + "no link") -> Supported
            verdict = "Supported"
            confidence = int(min(95, max(75, score * 100 + 15)))
            reason = "Claim correctly reflects the negative findings stated in the verified evidence."
        elif claim_asserts_disproven_claim:
            # Claim makes the disproven assertion ("vaccine causes infertility") -> Refuted
            verdict = "Refuted"
            confidence = int(min(95, max(75, score * 100 + 15)))
            reason = "Claim asserts a relationship directly contradicted by observational evidence."
        else:
            verdict = "Refuted"
            confidence = int(min(90, max(70, score * 100 + 10)))
            reason = "Claim asserts a relationship contradicted by verified corpus findings."

    # Case B: Standard factual alignment (e.g. Eiffel Tower 1889, water boils at 100C)
    else:
        verdict = "Supported"
        confidence = int(min(95, max(70, score * 100 + 10)))
        reason = "Claim is directly corroborated by high-relevance evidence passages."

    return VerificationResult(
        verdict=verdict,
        confidence=confidence,
        evidence_text=top_passage.text,
        evidence_source=top_passage.source,
        reason=reason,
    )
