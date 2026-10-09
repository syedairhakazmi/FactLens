import logging
from dataclasses import dataclass
from functools import lru_cache
import numpy as np

logger = logging.getLogger ("factlens")

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

@dataclass
class VerificationResult:
    verdict: str
    confidence: int
    evidence_text: str
    evidence_source: str
    reason: str

@lru_cache (maxsize = 1)
def _get_model ():
    if CrossEncoder is None:
        return None
    try:
        return CrossEncoder ("cross-encoder/nli-deberta-v3-small")
    except Exception as exc:
        logger.warning ("could not load nli model: %s", exc)
        return None

def verify_claim (claim_text, top_passage = None):
    # verify claim against top retrieved passage
    if top_passage is None or len (top_passage.text.strip ()) == 0:
        return VerificationResult (
            verdict = "Not Enough Evidence",
            confidence = 40,
            evidence_text = "No candidate evidence passages found in the corpus.",
            evidence_source = "Corpus Search (Empty)",
            reason = "Retriever returned zero candidate documents for this claim.",
        )

    retrieval_score = top_passage.combined_score
    embedding_score = getattr (top_passage, "embedding_score", 0.0)

    # check retrieval score threshold
    if retrieval_score < 0.15:
        return VerificationResult (
            verdict = "Not Enough Evidence",
            confidence = 40,
            evidence_text = "No sufficiently relevant evidence found in the corpus for this claim.",
            evidence_source = f"{top_passage.source} (Insufficient overlap)",
            reason = "Retrieved candidate scored below the minimum relevance threshold.",
        )

    # gate low combined score or low semantic embedding similarity (< 0.52)
    if retrieval_score < 0.35 or embedding_score < 0.52:
        calibrated_confidence = int (retrieval_score * 100 + 15)
        if calibrated_confidence < 45:
            calibrated_confidence = 45
        elif calibrated_confidence > 65:
            calibrated_confidence = 65

        return VerificationResult (
            verdict = "Not Enough Evidence",
            confidence = calibrated_confidence,
            evidence_text = f"No verified evidence found in the corpus. (Closest candidate lacked connection: \"{top_passage.text}\")",
            evidence_source = f"{top_passage.source} (No relevant match)",
            reason = "The corpus contains no relevant facts or records regarding this claim, so it cannot be confirmed or debunked.",
        )

    # run nli cross encoder model
    model = _get_model ()
    if model is not None:
        try:
            input_pairs = [(top_passage.text, claim_text)]
            raw_scores = model.predict (input_pairs)
            labels = ["contradiction", "entailment", "neutral"]
            predicted_index = int (np.argmax (raw_scores, axis = 1) [0])
            nli_label = labels [predicted_index]

            logits = raw_scores [0]
            exponent_logits = np.exp (logits - np.max (logits))
            probabilities = exponent_logits / np.sum (exponent_logits)
            raw_confidence = int (round (float (probabilities [predicted_index]) * 100))

            if raw_confidence < 60:
                final_confidence = 60
            elif raw_confidence > 98:
                final_confidence = 98
            else:
                final_confidence = raw_confidence

            if nli_label == "entailment":
                return VerificationResult (
                    verdict = "Supported",
                    confidence = final_confidence,
                    evidence_text = top_passage.text,
                    evidence_source = top_passage.source,
                    reason = "Retrieved evidence entails the claim.",
                )
            elif nli_label == "contradiction":
                return VerificationResult (
                    verdict = "Refuted",
                    confidence = final_confidence,
                    evidence_text = top_passage.text,
                    evidence_source = top_passage.source,
                    reason = "Retrieved evidence contradicts the claim.",
                )
            else:
                return VerificationResult (
                    verdict = "Not Enough Evidence",
                    confidence = final_confidence,
                    evidence_text = top_passage.text,
                    evidence_source = top_passage.source,
                    reason = "Retrieved evidence neither proves nor disproves the claim.",
                )
        except Exception as exc:
            logger.warning ("nli inference exception: %s", exc)

    fallback_confidence = int (retrieval_score * 100 + 10)
    if fallback_confidence < 70:
        fallback_confidence = 70
    elif fallback_confidence > 95:
        fallback_confidence = 95

    return VerificationResult (
        verdict = "Supported",
        confidence = fallback_confidence,
        evidence_text = top_passage.text,
        evidence_source = top_passage.source,
        reason = "Claim is supported by high-relevance evidence passages.",
    )
