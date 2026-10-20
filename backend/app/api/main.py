from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.claims.detector import extract_claims
from app.coreference.resolver import resolve
from app.decomposition import decompose
from app.retrieval.searcher import retrieve
from app.verification.verifier import verify_claim
from app.translation.translator import is_urdu, translate_ur_to_en, translate_en_to_ur, get_urdu_verdict, get_urdu_reason

app = FastAPI (
    title = "FactLens API",
    description = "Bilingual Automated Fact-Checking and Contextual Harm Detection Pipeline",
    version = "1.0.0",
)

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
    (
        "Tokyo is the capital and most populous prefecture of Japan.",
        "Local corpus",
    ),
    (
        "Python is a genus of constricting snakes in the Pythonidae family native to the tropics and subtropics of the Eastern Hemisphere.",
        "Local corpus",
    ),
    (
        "Cairo is the capital and largest city of Egypt.",
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
    text_ur: Optional [str] = None
    resolved_text: Optional [str] = None
    status: str
    status_ur: Optional [str] = None
    verdict: Optional [str] = None
    verdict_ur: Optional [str] = None
    confidence: Optional [int] = None
    evidence: Optional [str] = None
    evidence_ur: Optional [str] = None
    source: Optional [str] = None
    reason: Optional [str] = None
    reason_ur: Optional [str] = None
    bm25_score: Optional [float] = None
    embedding_score: Optional [float] = None

class FactCheckResponse (BaseModel):
    overall_verdict: str
    overall_verdict_ur: Optional [str] = None
    overall_confidence: Optional [int] = None
    all_opinion: bool
    language: str = "en"
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
    original_text_en: Optional [str] = None
    language: str = "en"
    fact_check: FactCheckResponse
    hate_speech: HateSpeechResponse

@app.get ("/api/health")
def health_check ():
    return {
        "status": "ok",
        "service": "FactLens API",
        "version": "1.0.0",
        "milestone": "Mid-1 Evaluation",
    }

@app.post ("/api/analyze", response_model = FullPipelineResponse)
def analyze_pipeline (payload: AnalyzeRequest):
    raw_text = payload.text.strip ()
    if len (raw_text) == 0:
        raise HTTPException (status_code = 400, detail = "Input text must not be empty.")
    if len (raw_text) > 50000:
        raise HTTPException (status_code = 413, detail = "Input text exceeds maximum allowed length.")

    # language detection and translation
    input_is_urdu = is_urdu (raw_text)
    if input_is_urdu:
        input_language = "ur"
        text_for_pipeline = translate_ur_to_en (raw_text)
        original_text_en = text_for_pipeline
    else:
        input_language = "en"
        text_for_pipeline = raw_text
        original_text_en = None

    # 1. coreference resolution
    coreference_result = resolve (text_for_pipeline)
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
    raw_sentences = extract_claims (text_for_pipeline)
    classified_sentences = extract_claims (resolved_full_text)

    # 3. retrieve evidence and verify claims
    sub_claims = []
    sentence_index = 0
    for classified_item in classified_sentences:
        raw_sentence_text = classified_item.text
        if sentence_index < len (raw_sentences):
            raw_sentence_text = raw_sentences [sentence_index].text
        sentence_index = sentence_index + 1

        is_coref_modified = False
        if raw_sentence_text.strip () != classified_item.text.strip ():
            is_coref_modified = True

        if not classified_item.is_checkable:
            category_label = getattr (classified_item, "category", "Non-Checkable")
            sub_text_ur = None
            status_ur_val = None
            reason_ur_val = None
            if input_is_urdu:
                sub_text_ur = translate_en_to_ur (raw_sentence_text)
                status_ur_val = get_urdu_verdict (category_label)
                reason_ur_val = get_urdu_reason (classified_item.reason)
            sub_claims.append (
                SubClaimResult (
                    text = raw_sentence_text,
                    text_ur = sub_text_ur,
                    status = category_label,
                    status_ur = status_ur_val,
                    reason = classified_item.reason,
                    reason_ur = reason_ur_val,
                )
            )
        else:
            atomic_claims = decompose (classified_item.text)
            for atomic_claim in atomic_claims:
                found_passages = retrieve (atomic_claim, top_k = 1)
                top_passage = None
                if len (found_passages) > 0:
                    top_passage = found_passages [0]

                if input_is_urdu and (top_passage is None or top_passage.combined_score < 0.25):
                    urdu_passages = retrieve (raw_text, top_k = 1, lang = "ur")
                    if len (urdu_passages) > 0 and urdu_passages [0].combined_score > 0.05:
                        top_passage = urdu_passages [0]

                verification_result = verify_claim (atomic_claim, top_passage)

                claim_display_text = atomic_claim
                resolved_value = None
                if is_coref_modified:
                    claim_display_text = raw_sentence_text
                    resolved_value = atomic_claim

                bm25_value = None
                embedding_value = None
                if top_passage is not None:
                    bm25_value = round (top_passage.bm25_score, 4)
                    embedding_value = round (top_passage.embedding_score, 4)

                sub_text_ur = None
                verdict_ur_val = None
                status_ur_val = None
                reason_ur_val = None
                evidence_ur_val = None
                if input_is_urdu:
                    sub_text_ur = translate_en_to_ur (claim_display_text)
                    verdict_ur_val = get_urdu_verdict (verification_result.verdict)
                    status_ur_val = get_urdu_verdict ("Fact")
                    reason_ur_val = get_urdu_reason (verification_result.reason)
                    if verification_result.evidence_text is not None:
                        evidence_ur_val = translate_en_to_ur (verification_result.evidence_text)

                sub_claims.append (
                    SubClaimResult (
                        text = claim_display_text,
                        text_ur = sub_text_ur,
                        resolved_text = resolved_value,
                        status = "Fact",
                        status_ur = status_ur_val,
                        verdict = verification_result.verdict,
                        verdict_ur = verdict_ur_val,
                        confidence = verification_result.confidence,
                        evidence = verification_result.evidence_text,
                        evidence_ur = evidence_ur_val,
                        source = verification_result.evidence_source,
                        reason = verification_result.reason,
                        reason_ur = reason_ur_val,
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
        supported_count = 0
        refuted_count = 0
        nee_count = 0
        confidence_scores = []

        for fact_claim in factual_claims:
            if fact_claim.verdict == "Supported":
                supported_count = supported_count + 1
            elif fact_claim.verdict == "Refuted":
                refuted_count = refuted_count + 1
            else:
                nee_count = nee_count + 1
            if fact_claim.confidence is not None:
                confidence_scores.append (fact_claim.confidence)

        total_claims = len (factual_claims)
        if supported_count == total_claims and total_claims > 0:
            overall_verdict = "Supported"
        elif refuted_count == total_claims and total_claims > 0:
            overall_verdict = "Refuted"
        elif nee_count == total_claims and total_claims > 0:
            overall_verdict = "Not Enough Evidence"
        else:
            overall_verdict = "Mixed"

        if len (confidence_scores) > 0:
            overall_confidence = int (sum (confidence_scores) / len (confidence_scores))
        else:
            overall_confidence = None

    overall_verdict_ur = None
    if input_is_urdu:
        overall_verdict_ur = get_urdu_verdict (overall_verdict)

    # 5. hate speech check
    lower_text = text_for_pipeline.lower ()
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
        original_text_en = original_text_en,
        language = input_language,
        fact_check = FactCheckResponse (
            overall_verdict = overall_verdict,
            overall_verdict_ur = overall_verdict_ur,
            overall_confidence = overall_confidence,
            all_opinion = all_opinion,
            language = input_language,
            used_retry = False,
            used_wikipedia_fallback = False,
            coref_resolutions = coreference_links,
            sub_claims = sub_claims,
        ),
        hate_speech = hate_response,
    )
