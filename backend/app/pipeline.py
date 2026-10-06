"""
FactLens pipeline orchestrator.

Chains every NLP stage in the correct order and passes the right
data between them:

    User text
      │
      ▼
    1. Coreference Resolution   (resolver.py)
      │  replaces pronouns → self-contained text
      ▼
    2. Claim Extraction          (detector.py)
      │  splits into sentences, classifies Fact vs Opinion
      │  ── opinions are tagged and SKIPPED ──
      ▼
    3. Sentence Decomposition    (decomposition/)
      │  breaks complex sentences into atomic sub-claims
      ▼
    4. Evidence Retrieval        (searcher.py)
      │  BM25 + embedding search over an evidence corpus
      ▼
    5. Verification              (verifier.py)
      │  NLI cross-encoder → Supported / Refuted / NEE
      ▼
    Final aggregated result

Run standalone:
    python -m app.pipeline
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.coreference.resolver import resolve, CoreferenceResult
from app.claims.detector import extract_claims, ClassifiedSentence
from app.retrieval.searcher import retrieve, RetrievedPassage
from app.verification.verifier import verify_claim, VerificationResult

logger = logging.getLogger("factlens")


# ---------------------------------------------------------------------------
# Decomposition stub
# ---------------------------------------------------------------------------
# The decomposition module (app.decomposition) is not implemented yet.
# This thin wrapper isolates the rest of the pipeline from that, so when
# the real decomposer is written it can be swapped in here and nothing
# else needs to change.

def _decompose(sentence: str) -> list[str]:
    """
    Break a single sentence into atomic sub-claims.

    Currently a pass-through (returns the sentence unchanged) because
    the real decomposition logic hasn't been written yet.  Replace the
    body of this function with the actual implementation when ready.
    """
    # TODO: replace with real decomposition logic from app.decomposition
    return [sentence]


# ---------------------------------------------------------------------------
# Per-claim result that travels through the pipeline
# ---------------------------------------------------------------------------

@dataclass
class ClaimResult:
    """Everything the pipeline knows about one atomic claim."""
    original_sentence: str          # sentence as it came out of claim extraction
    decomposed_text: str            # atomic sub-claim (may == original_sentence)
    status: str                     # "Fact" | "Opinion"
    reason: str                     # why it was classified this way
    retrieval: RetrievedPassage | None = None
    verification: VerificationResult | None = None


@dataclass
class PipelineResult:
    """Aggregated output of the full pipeline."""
    input_text: str
    coreference: CoreferenceResult
    claims: list[ClaimResult] = field(default_factory=list)
    overall_verdict: str = "Not Applicable"
    overall_confidence: int | None = None
    all_opinion: bool = False


# ---------------------------------------------------------------------------
# Default evidence corpus (same seed set used by the API layer)
# ---------------------------------------------------------------------------

DEFAULT_EVIDENCE_CORPUS: list[tuple[str, str]] = [
    (
        "Clinical trials and observational studies of over 1.2 million individuals confirm that "
        "the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        "SciFact starter seed (ID: 4128)",
    ),
    (
        "The COVID-19 vaccine received official emergency use authorization and subsequent full regulatory approval "
        "following Phase 3 multinational randomized clinical trials.",
        "FEVEROUS starter seed (ID: 9811)",
    ),
    (
        "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure at sea level.",
        "Wikipedia starter seed (Physical Sciences)",
    ),
    (
        "Antibiotics are medicines that fight bacterial infections in people and animals. "
        "They do not work against viral infections such as colds or flu.",
        "SciFact starter seed (ID: 1042)",
    ),
    (
        "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. "
        "It was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        "FEVER starter seed (ID: 10839)",
    ),
    (
        "Paris is the capital and most populous city of France, with an estimated population "
        "of over 2.1 million residents within city limits.",
        "FEVER starter seed (ID: 7421)",
    ),
    (
        "The Great Wall of China is a series of fortifications that were built across "
        "the historical northern borders of ancient Chinese states.",
        "FEVER starter seed (ID: 3912)",
    ),
    (
        "Apple announced the iPhone 15 series in September 2023, introducing an "
        "aerospace-grade titanium design and USB-C connectivity.",
        "FEVEROUS corpus (ID: 5543)",
    ),
    (
        "Graphene is a single layer of carbon atoms arranged in a two-dimensional honeycomb "
        "lattice with exceptional electrical and thermal conductivity.",
        "SciFact corpus (ID: 8820)",
    ),
    (
        "Python is a high-level, general-purpose programming language developed by "
        "Guido van Rossum and first released in 1991.",
        "Wikipedia (Computer Science)",
    ),
]


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def run_pipeline(
    text: str,
    corpus: list[tuple[str, str]] | None = None,
    top_k: int = 1,
) -> PipelineResult:
    """
    Execute the full FactLens pipeline on *text* and return a
    `PipelineResult` with every intermediate artefact attached.

    Parameters
    ----------
    text : str
        Raw user input (may contain pronouns, multiple sentences, etc.).
    corpus : list[tuple[str, str]] | None
        Evidence corpus as (passage_text, source_name) pairs.
        Falls back to `DEFAULT_EVIDENCE_CORPUS` when not provided.
    top_k : int
        How many evidence passages to retrieve per claim (default 1).
    """
    if corpus is None:
        corpus = DEFAULT_EVIDENCE_CORPUS

    result = PipelineResult(input_text=text, coreference=None)  # type: ignore[arg-type]

    # ── Stage 1: Coreference Resolution ──────────────────────────
    logger.info("Stage 1  Coreference resolution")
    coref = resolve(text)
    result.coreference = coref
    resolved_text = coref.resolved_text
    logger.info("  resolved: %s", resolved_text)

    # ── Stage 2: Claim Extraction & Fact/Opinion Classification ──
    logger.info("Stage 2  Claim extraction & classification")
    classified: list[ClassifiedSentence] = extract_claims(resolved_text)

    for item in classified:
        tag = "FACT" if item.is_checkable else "OPINION"
        logger.info("  [%s] %s", tag, item.text)

        if not item.is_checkable:
            # Opinion → record it and skip all downstream stages
            result.claims.append(
                ClaimResult(
                    original_sentence=item.text,
                    decomposed_text=item.text,
                    status="Opinion",
                    reason=item.reason,
                )
            )
            continue

        # ── Stage 3: Decomposition ──────────────────────────────
        logger.info("Stage 3  Decomposing: %s", item.text)
        sub_claims = _decompose(item.text)

        for sub in sub_claims:
            logger.info("  sub-claim: %s", sub)

            # ── Stage 4: Evidence Retrieval ──────────────────────
            logger.info("Stage 4  Retrieving evidence for: %s", sub)
            passages = retrieve(sub, corpus, top_k=top_k)
            top_passage = passages[0] if passages else None

            if top_passage:
                logger.info(
                    "  top evidence (%.3f): %s",
                    top_passage.combined_score,
                    top_passage.text[:80],
                )

            # ── Stage 5: Verification ────────────────────────────
            logger.info("Stage 5  Verifying: %s", sub)
            ver = verify_claim(sub, top_passage)
            logger.info(
                "  verdict=%s  confidence=%d%%",
                ver.verdict,
                ver.confidence,
            )

            result.claims.append(
                ClaimResult(
                    original_sentence=item.text,
                    decomposed_text=sub,
                    status="Fact",
                    reason=item.reason,
                    retrieval=top_passage,
                    verification=ver,
                )
            )

    # ── Aggregate overall verdict ────────────────────────────────
    facts = [c for c in result.claims if c.status == "Fact"]
    result.all_opinion = len(facts) == 0 and len(result.claims) > 0

    if result.all_opinion:
        result.overall_verdict = "Not Applicable"
        result.overall_confidence = None
    elif not facts:
        result.overall_verdict = "Not Applicable"
        result.overall_confidence = None
    else:
        if any(f.verification and f.verification.verdict == "Refuted" for f in facts):
            result.overall_verdict = "Refuted"
        elif any(f.verification and f.verification.verdict == "Supported" for f in facts):
            result.overall_verdict = "Supported"
        else:
            result.overall_verdict = "Not Enough Evidence"

        confidences = [
            f.verification.confidence
            for f in facts
            if f.verification and f.verification.confidence is not None
        ]
        result.overall_confidence = (
            int(sum(confidences) / len(confidences)) if confidences else None
        )

    return result


# ---------------------------------------------------------------------------
# CLI entry point for quick manual testing
# ---------------------------------------------------------------------------

def _print_result(res: PipelineResult) -> None:
    """Pretty-print a pipeline result to the terminal."""
    print("=" * 72)
    print(f"INPUT:    {res.input_text}")
    print(f"RESOLVED: {res.coreference.resolved_text}")
    if res.coreference.clusters:
        print(f"CLUSTERS: {res.coreference.clusters}")
    print("-" * 72)

    for i, c in enumerate(res.claims, 1):
        print(f"\n  Claim {i}: {c.decomposed_text}")
        print(f"    Status : {c.status}")
        print(f"    Reason : {c.reason}")
        if c.status == "Fact" and c.verification:
            v = c.verification
            print(f"    Verdict: {v.verdict} ({v.confidence}%)")
            print(f"    Evidence: {v.evidence_text[:100]}...")
            print(f"    Source : {v.evidence_source}")
        if c.status == "Opinion":
            print("    ↳ Skipped retrieval & verification (opinion)")

    print()
    print(f"  OVERALL VERDICT   : {res.overall_verdict}")
    print(f"  OVERALL CONFIDENCE: {res.overall_confidence}")
    print(f"  ALL OPINION?      : {res.all_opinion}")
    print("=" * 72)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    samples = [
        "Ali is a good boy. He is fat.",
        "The new vaccine was approved last week, and it causes infertility in most patients.",
        "I think the president did a great job this year.",
        "Water boils at 100 degrees Celsius at sea level. The Eiffel Tower was built in 1889.",
        "This woman is evil.",
    ]

    for sample in samples:
        res = run_pipeline(sample)
        _print_result(res)
        print()
