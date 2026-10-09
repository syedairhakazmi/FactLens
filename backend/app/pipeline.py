import logging
from dataclasses import dataclass, field

from app.coreference.resolver import resolve, CoreferenceResult
from app.claims.detector import extract_claims, ClassifiedSentence, _get_nlp
from app.retrieval.searcher import retrieve, RetrievedPassage
from app.verification.verifier import verify_claim, VerificationResult

logger = logging.getLogger ("factlens")

def _is_independent_clause (text):
    # checks if a text snippet contains both a subject and a verb predicate
    nlp = _get_nlp ()
    doc = nlp (text)
    has_subject = False
    has_predicate = False
    for token in doc:
        if "subj" in token.dep_:
            has_subject = True
        if token.pos_ in ("VERB", "AUX"):
            has_predicate = True
    return has_subject and has_predicate

def _decompose (sentence):
    # split compound sentences containing coordinating conjunctions into atomic sub-claims
    conjunctions = [", and ", ", but ", "; "]
    pieces = [sentence]
    for conj in conjunctions:
        next_pieces = []
        for piece in pieces:
            if conj in piece:
                for part in piece.split (conj):
                    cleaned_part = part.strip ()
                    if len (cleaned_part) > 0:
                        next_pieces.append (cleaned_part)
            else:
                next_pieces.append (piece)
        pieces = next_pieces

    clause_pieces = []
    for piece in pieces:
        if ", " in piece:
            comma_parts = piece.split (", ")
            all_clauses = True
            for cp in comma_parts:
                if not _is_independent_clause (cp):
                    all_clauses = False
                    break
            if all_clauses:
                for cp in comma_parts:
                    cleaned_cp = cp.strip ()
                    if len (cleaned_cp) > 0:
                        clause_pieces.append (cleaned_cp)
            else:
                clause_pieces.append (piece)
        else:
            clause_pieces.append (piece)

    results = []
    for piece in clause_pieces:
        text = piece.strip ()
        if len (text) > 0:
            if not text.endswith (".") and not text.endswith ("?") and not text.endswith ("!"):
                text = text + "."
            text = text [0].upper () + text [1:]
            results.append (text)

    if len (results) == 0:
        return [sentence]
    return results

@dataclass
class ClaimResult:
    original_sentence: str
    decomposed_text: str
    status: str
    reason: str
    retrieval: RetrievedPassage | None = None
    verification: VerificationResult | None = None

@dataclass
class PipelineResult:
    input_text: str
    coreference: CoreferenceResult
    claims: list = field (default_factory = list)
    overall_verdict: str = "Not Applicable"
    overall_confidence: int | None = None
    all_opinion: bool = False

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
        "Paris is the capital and most populous city of France, with an estimated population "
        "of over 2.1 million residents within city limits.",
        "Local corpus",
    ),
    (
        "The Great Wall of China is a series of fortifications that were built across "
        "the historical northern borders of ancient Chinese states.",
        "Local corpus",
    ),
    (
        "Apple announced the iPhone 15 series in September 2023, introducing an "
        "aerospace-grade titanium design and USB-C connectivity.",
        "Local corpus",
    ),
    (
        "Graphene is a single layer of carbon atoms arranged in a two-dimensional honeycomb "
        "lattice with exceptional electrical and thermal conductivity.",
        "Local corpus",
    ),
    (
        "Python is a high-level, general-purpose programming language developed by "
        "Guido van Rossum and first released in 1991.",
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

def run_pipeline (text, corpus = None, top_k = 1):
    # execute pipeline stages in order (uses real datasets when corpus is None)
    result = PipelineResult (input_text = text, coreference = None)

    # 1. coreference resolution
    coreference_result = resolve (text)
    result.coreference = coreference_result
    resolved_text = coreference_result.resolved_text

    # 2. claim extraction and opinion check
    classified_sentences = extract_claims (resolved_text)

    claim_cache = {}

    for classified_item in classified_sentences:
        if not classified_item.is_checkable:
            result.claims.append (
                ClaimResult (
                    original_sentence = classified_item.text,
                    decomposed_text = classified_item.text,
                    status = "Opinion",
                    reason = classified_item.reason,
                )
            )
            continue

        # 3. claim decomposition
        sub_claims = _decompose (classified_item.text)

        for sub_claim in sub_claims:
            if sub_claim in claim_cache:
                top_passage, verification_result = claim_cache [sub_claim]
            else:
                # 4. evidence retrieval
                found_passages = retrieve (sub_claim, corpus, top_k = top_k)
                top_passage = None
                if len (found_passages) > 0:
                    top_passage = found_passages [0]

                # 5. verification
                verification_result = verify_claim (sub_claim, top_passage)
                claim_cache [sub_claim] = (top_passage, verification_result)

            result.claims.append (
                ClaimResult (
                    original_sentence = classified_item.text,
                    decomposed_text = sub_claim,
                    status = "Fact",
                    reason = classified_item.reason,
                    retrieval = top_passage,
                    verification = verification_result,
                )
            )

    # aggregate final verdict
    factual_claims = []
    for claim_item in result.claims:
        if claim_item.status == "Fact":
            factual_claims.append (claim_item)

    if len (factual_claims) == 0 and len (result.claims) > 0:
        result.all_opinion = True
    else:
        result.all_opinion = False

    if result.all_opinion or len (factual_claims) == 0:
        result.overall_verdict = "Not Applicable"
        result.overall_confidence = None
    else:
        all_supported = True
        has_refuted = False
        has_supported = False
        confidence_scores = []

        for fact_claim in factual_claims:
            if fact_claim.verification is not None:
                if fact_claim.verification.verdict == "Refuted":
                    has_refuted = True
                    all_supported = False
                elif fact_claim.verification.verdict == "Supported":
                    has_supported = True
                else:
                    all_supported = False
                if fact_claim.verification.confidence is not None:
                    confidence_scores.append (fact_claim.verification.confidence)

        if has_refuted:
            result.overall_verdict = "Refuted"
        elif all_supported and has_supported:
            result.overall_verdict = "Supported"
        else:
            result.overall_verdict = "Not Enough Evidence"

        if len (confidence_scores) > 0:
            result.overall_confidence = int (sum (confidence_scores) / len (confidence_scores))
        else:
            result.overall_confidence = None

    return result

def _print_result (pipeline_result):
    print ("=" * 72)
    print (f"INPUT:    {pipeline_result.input_text}")
    print (f"RESOLVED: {pipeline_result.coreference.resolved_text}")
    if pipeline_result.coreference.clusters:
        print (f"CLUSTERS: {pipeline_result.coreference.clusters}")
    print ("-" * 72)

    claim_index = 1
    for claim_item in pipeline_result.claims:
        print (f"\n  Claim {claim_index}: {claim_item.decomposed_text}")
        print (f"    Status : {claim_item.status}")
        print (f"    Reason : {claim_item.reason}")
        if claim_item.status == "Fact" and claim_item.verification:
            ver = claim_item.verification
            print (f"    Verdict: {ver.verdict} ({ver.confidence}%)")
            print (f"    Evidence: {ver.evidence_text[:100]}...")
            print (f"    Source : {ver.evidence_source}")
        if claim_item.status == "Opinion":
            print ("    -> Skipped retrieval and verification (opinion)")
        claim_index = claim_index + 1

    print ()
    print (f"  OVERALL VERDICT   : {pipeline_result.overall_verdict}")
    print (f"  OVERALL CONFIDENCE: {pipeline_result.overall_confidence}")
    print (f"  ALL OPINION?      : {pipeline_result.all_opinion}")
    print ("=" * 72)

if __name__ == "__main__":
    logging.basicConfig (level = logging.INFO, format = "%(message)s")

    samples = [
        "Ali is a good boy. He is fat.",
        "The new vaccine was approved last week, and it causes infertility in most patients.",
        "I think the president did a great job this year.",
        "Water boils at 100 degrees Celsius at sea level. The Eiffel Tower was built in 1889.",
        "This woman is evil.",
    ]

    for sample in samples:
        res = run_pipeline (sample)
        _print_result (res)
        print ()
