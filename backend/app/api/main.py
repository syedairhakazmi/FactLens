"""
FastAPI backend for FactLens. Owner: Shaheera.

This API connects the core NLP modules into an end-to-end pipeline:
1. Coreference Resolution (`resolver.py` - Irha)
2. Fact vs Opinion & Claim Extraction (`detector.py` - Areesha)
3. BM25 + Embedding Evidence Retrieval (`searcher.py` - Irha)
"""

from __future__ import annotations

import logging
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.coreference.resolver import resolve
from app.claims.detector import extract_claims
from app.retrieval.searcher import retrieve
from app.verification.verifier import verify_claim

logger = logging.getLogger("factlens")

app = FastAPI(
    title="FactLens API",
    description="Fact-checking and claim verification API with coreference, claim extraction, and evidence retrieval",
    version="1.0.0",
)

# Enable CORS for local Vite development and deployed clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard starter evidence corpus spanning general, scientific, and news domains
# (Precursor to full FEVER / SciFact corpus integration in Week 2)
DEFAULT_EVIDENCE_CORPUS: list[tuple[str, str]] = [
    # Health & Medical (SciFact / WHO)
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
        "Antibiotics are medicines that fight bacterial infections in people and animals. They do not work against viral infections such as colds or flu.",
        "SciFact starter seed (ID: 1042)",
    ),
    # Geography & History (FEVER / Wikipedia)
    (
        "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. It was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        "FEVER starter seed (ID: 10839)",
    ),
    (
        "Paris is the capital and most populous city of France, with an estimated population of over 2.1 million residents within city limits.",
        "FEVER starter seed (ID: 7421)",
    ),
    (
        "The Great Wall of China is a series of fortifications that were built across the historical northern borders of ancient Chinese states.",
        "FEVER starter seed (ID: 3912)",
    ),
    # Technology
    (
        "Apple announced the iPhone 15 series in September 2023, introducing an aerospace-grade titanium design and USB-C connectivity.",
        "FEVEROUS corpus (ID: 5543)",
    ),
    (
        "Graphene is a single layer of carbon atoms arranged in a two-dimensional honeycomb lattice with exceptional electrical and thermal conductivity.",
        "SciFact corpus (ID: 8820)",
    ),
    (
        "Python is a high-level, general-purpose programming language developed by Guido van Rossum and first released in 1991.",
        "Wikipedia (Computer Science)",
    ),
]


class AnalyzeRequest(BaseModel):
    text: str


class CorefLink(BaseModel):
    from_mention: str
    to_mention: str


class SubClaimResult(BaseModel):
    text: str
    resolved_text: Optional[str] = None
    status: str  # "Fact" | "Opinion"
    verdict: Optional[str] = None  # "Supported" | "Refuted" | "Not Enough Evidence"
    confidence: Optional[int] = None
    evidence: Optional[str] = None
    source: Optional[str] = None
    reason: Optional[str] = None
    bm25_score: Optional[float] = None
    embedding_score: Optional[float] = None


class FactCheckResponse(BaseModel):
    overall_verdict: str
    overall_confidence: Optional[int] = None
    all_opinion: bool
    used_retry: bool = False
    used_wikipedia_fallback: bool = False
    coref_resolutions: List[CorefLink]
    sub_claims: List[SubClaimResult]


class HateSpeechResponse(BaseModel):
    classification: str
    target: str
    cues: List[str]
    reason: str


class FullPipelineResponse(BaseModel):
    original_text: str
    fact_check: FactCheckResponse
    hate_speech: HateSpeechResponse


@app.get("/api/health")
def health_check():
    """Liveness probe for CI/CD and deployment checks."""
    return {"status": "ok", "service": "FactLens API"}


@app.post("/api/analyze", response_model=FullPipelineResponse)
def analyze_pipeline(payload: AnalyzeRequest):
    """
    End-to-end analysis endpoint:
    1. Coreference resolution: Resolves pronouns to referents.
    2. Claim extraction: Splits sentences and classifies each as Fact or Opinion.
    3. Retrieval: Retrieves evidence passages for checkable claims.
    4. Verification stub: Computes verdict and confidence based on retrieved evidence.
    """
    raw_text = payload.text.strip()
    if not raw_text:
        raise HTTPException(status_code=400, detail="Input text must not be empty.")

    # ---------------------------------------------------------
    # Stage 1: Coreference Resolution
    # ---------------------------------------------------------
    coref_res = resolve(raw_text)
    resolved_full_text = coref_res.resolved_text

    coref_links: list[CorefLink] = []
    if coref_res.clusters:
        for cluster in coref_res.clusters:
            if len(cluster) > 1:
                representative = max(cluster, key=len)
                for mention in cluster:
                    if mention.lower() != representative.lower():
                        coref_links.append(
                            CorefLink(
                                from_mention=mention,
                                to_mention=representative,
                            )
                        )

    # ---------------------------------------------------------
    # Stage 2: Claim Extraction & Fact/Opinion Classification
    # ---------------------------------------------------------
    # Extract claims from the resolved text so downstream modules see self-contained sentences
    classified_sentences = extract_claims(resolved_full_text)

    # ---------------------------------------------------------
    # Stage 3: Evidence Retrieval & Verification
    # ---------------------------------------------------------
    sub_claims: list[SubClaimResult] = []
    fact_scores: list[float] = []

    for item in classified_sentences:
        if not item.is_checkable:
            # Opinion sentence - triaged out of verification
            sub_claims.append(
                SubClaimResult(
                    text=item.text,
                    status="Opinion",
                    reason=item.reason,
                )
            )
        else:
            # Checkable factual claim - execute retrieval
            retrieved = retrieve(item.text, DEFAULT_EVIDENCE_CORPUS, top_k=1)
            top = retrieved[0] if retrieved else None

            # Delegate verification to dedicated verifier module
            ver_res = verify_claim(item.text, top)
            if top:
                fact_scores.append(top.combined_score)

            sub_claims.append(
                SubClaimResult(
                    text=item.text,
                    resolved_text=item.text if item.text != raw_text else None,
                    status="Fact",
                    verdict=ver_res.verdict,
                    confidence=ver_res.confidence,
                    evidence=ver_res.evidence_text,
                    source=ver_res.evidence_source,
                    reason=ver_res.reason,
                    bm25_score=round(top.bm25_score, 4) if top else None,
                    embedding_score=round(top.embedding_score, 4) if top else None,
                )
            )

    # ---------------------------------------------------------
    # Overall Fact-Check Verdict aggregation
    # ---------------------------------------------------------
    all_opinion = bool(sub_claims) and all(c.status == "Opinion" for c in sub_claims)
    if all_opinion:
        overall_verdict = "Not Applicable"
        overall_confidence = None
    else:
        facts = [c for c in sub_claims if c.status == "Fact"]
        if any(f.verdict == "Refuted" for f in facts):
            overall_verdict = "Refuted"
        elif any(f.verdict == "Supported" for f in facts):
            overall_verdict = "Supported"
        else:
            overall_verdict = "Not Enough Evidence"

        confidences = [f.confidence for f in facts if f.confidence is not None]
        overall_confidence = int(sum(confidences) / len(confidences)) if confidences else None

    # ---------------------------------------------------------
    # Hate Speech baseline triage (FYP-2 preview)
    # ---------------------------------------------------------
    lower = raw_text.lower()
    hate_words = ["animals", "vermin", "parasites", "subhuman", "criminals", "should be thrown out", "sent back"]
    matched = [w for w in hate_words if w in lower]
    if matched:
        hate_res = HateSpeechResponse(
            classification="Hate",
            target="Referenced demographic or group",
            cues=matched,
            reason="Contains exclusionary or dehumanizing language generalizing about a group.",
        )
    else:
        hate_res = HateSpeechResponse(
            classification="Normal",
            target="None",
            cues=[],
            reason="No targeted hate speech markers detected in the claim.",
        )

    return FullPipelineResponse(
        original_text=raw_text,
        fact_check=FactCheckResponse(
            overall_verdict=overall_verdict,
            overall_confidence=overall_confidence,
            all_opinion=all_opinion,
            used_retry=False,
            used_wikipedia_fallback=False,
            coref_resolutions=coref_links,
            sub_claims=sub_claims,
        ),
        hate_speech=hate_res,
    )
