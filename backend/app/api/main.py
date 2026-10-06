from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.claims.detector import extract_claims
from app.coreference.resolver import resolve
from app.retrieval.searcher import retrieve
from app.verification.verifier import verify_claim

app = FastAPI (title = "FactLens API", version = "1.0.0")

app.add_middleware (
    CORSMiddleware,
    allow_origins = ["*"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

DEFAULT_EVIDENCE_CORPUS = [
    (
        "Clinical trials and observational studies of over 1.2 million individuals confirm that "
        "the COVID-19 vaccine does not cause infertility or pregnancy complications.",
        "Local corpus",
    ),
    (
        "The COVID-19 vaccine received official emergency use authorization and subsequent full regulatory approval "
        "following Phase 3 multinational randomized clinical trials.",
        "Local corpus",
    ),
    (
        "Water boils at 100 degrees Celsius (212 degrees Fahrenheit) at standard atmospheric pressure at sea level.",
        "Local corpus",
    ),
    (
        "Antibiotics are medicines that fight bacterial infections in people and animals. "
        "They do not work against viral infections such as colds or flu.",
        "Local corpus",
    ),
    (
        "The Eiffel Tower is a wrought-iron lattice tower on the Champ de Mars in Paris, France. "
        "It was constructed from 1887 to 1889 as the entrance to the 1889 World's Fair.",
        "Local corpus",
    ),
    (
        "Paris is the capital and most populous city of France, with an estimated population of over 2.1 million residents within city limits.",
        "Local corpus",
    ),
    (
        "The Great Wall of China is a series of fortifications that were built across the historical northern borders of ancient Chinese states.",
        "Local corpus",
    ),
    (
        "Apple announced the iPhone 15 series in September 2023, introducing an aerospace-grade titanium design and USB-C connectivity.",
        "Local corpus",
    ),
    (
        "Graphene is a single layer of carbon atoms arranged in a two-dimensional honeycomb lattice with exceptional electrical and thermal conductivity.",
        "Local corpus",
    ),
    (
        "Python is a high-level, general-purpose programming language developed by Guido van Rossum and first released in 1991.",
        "Local corpus",
    ),
]

class AnalyzeRequest (BaseModel):
    text: str

class CorefLink (BaseModel):
    from_mention: str
    to_mention: str

class SubClaimResult (BaseModel):
    text: str
    resolved_text: Optional [str] = None
    status: str
    verdict: Optional [str] = None
    confidence: Optional [int] = None
    evidence: Optional [str] = None
    source: Optional [str] = None
    reason: Optional [str] = None
    bm25_score: Optional [float] = None
    embedding_score: Optional [float] = None

class FactCheckResponse (BaseModel):
    overall_verdict: str
    overall_confidence: Optional [int] = None
    all_opinion: bool
    used_retry: bool = False
    used_wikipedia_fallback: bool = False
    coref_resolutions: list [CorefLink]
    sub_claims: list [SubClaimResult]

class HateSpeechResponse (BaseModel):
    classification: str
    target: str
    cues: list [str]
    reason: str

class FullPipelineResponse (BaseModel):
    original_text: str
    fact_check: FactCheckResponse
    hate_speech: HateSpeechResponse

@app.get ("/api/health")
def health_check ():
    return {"status": "ok", "service": "FactLens API"}

@app.post ("/api/analyze", response_model = FullPipelineResponse)
def analyze_pipeline (payload: AnalyzeRequest):
    raw_text = payload.text.strip ()
    if len (raw_text) == 0:
        raise HTTPException (status_code = 400, detail = "Input text must not be empty.")

    # 1. coreference resolution
    coreference_result = resolve (raw_text)
    resolved_full_text = coreference_result.resolved_text

    coreference_links = []
    if coreference_result.clusters:
        for cluster in coreference_result.clusters:
            if len (cluster) > 1:
                representative_word = max (cluster, key = len)
                for mention in cluster:
                    if mention.lower () != representative_word.lower ():
                        coreference_links.append (
                            CorefLink (
                                from_mention = mention,
                                to_mention = representative_word,
                            )
                        )

    # 2. extract claims
    classified_sentences = extract_claims (resolved_full_text)

    # 3. retrieve evidence and verify claims
    sub_claims = []
    for classified_item in classified_sentences:
        if not classified_item.is_checkable:
            sub_claims.append (
                SubClaimResult (
                    text = classified_item.text,
                    status = "Opinion",
                    reason = classified_item.reason,
                )
            )
        else:
            found_passages = retrieve (classified_item.text, DEFAULT_EVIDENCE_CORPUS, top_k = 1)
            top_passage = None
            if len (found_passages) > 0:
                top_passage = found_passages [0]

            verification_result = verify_claim (classified_item.text, top_passage)

            resolved_value = None
            if classified_item.text != raw_text:
                resolved_value = classified_item.text

            bm25_value = None
            embedding_value = None
            if top_passage is not None:
                bm25_value = round (top_passage.bm25_score, 4)
                embedding_value = round (top_passage.embedding_score, 4)

            sub_claims.append (
                SubClaimResult (
                    text = classified_item.text,
                    resolved_text = resolved_value,
                    status = "Fact",
                    verdict = verification_result.verdict,
                    confidence = verification_result.confidence,
                    evidence = verification_result.evidence_text,
                    source = verification_result.evidence_source,
                    reason = verification_result.reason,
                    bm25_score = bm25_value,
                    embedding_score = embedding_value,
                )
            )

    # 4. aggregate verdict
    factual_claims = []
    opinion_claims = []
    for claim_item in sub_claims:
        if claim_item.status == "Fact":
            factual_claims.append (claim_item)
        elif claim_item.status == "Opinion":
            opinion_claims.append (claim_item)

    if len (factual_claims) == 0 and len (sub_claims) > 0:
        all_opinion = True
        overall_verdict = "Not Applicable"
        overall_confidence = None
    else:
        all_opinion = False
        has_refuted = False
        has_supported = False
        confidence_scores = []

        for fact_claim in factual_claims:
            if fact_claim.verdict == "Refuted":
                has_refuted = True
            elif fact_claim.verdict == "Supported":
                has_supported = True
            if fact_claim.confidence is not None:
                confidence_scores.append (fact_claim.confidence)

        if has_refuted:
            overall_verdict = "Refuted"
        elif has_supported:
            overall_verdict = "Supported"
        else:
            overall_verdict = "Not Enough Evidence"

        if len (confidence_scores) > 0:
            overall_confidence = int (sum (confidence_scores) / len (confidence_scores))
        else:
            overall_confidence = None

    # 5. hate speech check
    lower_text = raw_text.lower ()
    hate_keywords = ["animals", "vermin", "parasites", "subhuman", "criminals", "should be thrown out", "sent back"]
    matched_words = []
    for word in hate_keywords:
        if word in lower_text:
            matched_words.append (word)

    if len (matched_words) > 0:
        hate_response = HateSpeechResponse (
            classification = "Hate",
            target = "Referenced demographic or group",
            cues = matched_words,
            reason = "Contains exclusionary or dehumanizing language generalizing about a group.",
        )
    else:
        hate_response = HateSpeechResponse (
            classification = "Normal",
            target = "None",
            cues = [],
            reason = "No targeted hate speech markers detected in the claim.",
        )

    return FullPipelineResponse (
        original_text = raw_text,
        fact_check = FactCheckResponse (
            overall_verdict = overall_verdict,
            overall_confidence = overall_confidence,
            all_opinion = all_opinion,
            used_retry = False,
            used_wikipedia_fallback = False,
            coref_resolutions = coreference_links,
            sub_claims = sub_claims,
        ),
        hate_speech = hate_response,
    )
