"""
Evidence retrieval module. Owner: Irha.

Combines two scoring methods per candidate evidence passage:

1. BM25 (rank_bm25), pure keyword overlap. Fast, needs no pretrained
   weights, works immediately offline.
2. Sentence embedding cosine similarity (sentence-transformers), a
   meaning-based score that catches paraphrases BM25 misses. Needs a
   pretrained model downloaded from Hugging Face on first run.

Both scores are min-max normalized to [0, 1] within the current query's
candidate set (not globally), since BM25's raw scores and cosine
similarity live on incomparable scales. They're then combined as a
weighted sum. RETRIEVAL_WEIGHT below controls that split, tune it once
real evaluation data (FEVER / FEVEROUS / SciFact) is wired in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Plus

# Weight given to the embedding score vs. BM25. 0.5 = equal weight.
# This is a tunable hyperparameter, not a fixed design decision, treat
# it as something the evaluation plan (Slide 14) should actually sweep.
RETRIEVAL_WEIGHT_EMBEDDING = 0.5

# A minimal stopword list. Without this, BM25's IDF weighting can be
# thrown off badly on small corpora, a word like "in" can look
# statistically "rare" and therefore "important" just because only one
# passage happens to contain it, even though it's meaningless. This
# matters less on the real, large FEVER-scale corpus, but it's cheap,
# standard practice, and worth keeping regardless of corpus size.
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "of", "and", "or", "but", "with",
    "this", "that", "these", "those", "it", "its", "as", "by", "from",
}


@dataclass
class RetrievedPassage:
    text: str
    source: str
    bm25_score: float
    embedding_score: float
    combined_score: float


def _tokenize(text: str) -> list[str]:
    # Lowercase, strip punctuation, and drop stopwords, so "patients."
    # matches "patients", and common words don't distort BM25's IDF
    # weighting on small corpora. See _STOPWORDS above.
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in tokens if t not in _STOPWORDS]


@lru_cache(maxsize=1)
def _get_embedding_model():
    """
    Returns None if the pretrained model can't be downloaded (e.g. no
    internet access), so callers can fall back to BM25-only ranking
    instead of crashing. On a normal machine with internet access this
    always succeeds, downloading once and caching locally afterward.
    """
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _min_max_normalize(scores: np.ndarray) -> np.ndarray:
    if scores.max() == scores.min():
        return np.zeros_like(scores)
    return (scores - scores.min()) / (scores.max() - scores.min())


def retrieve(
    query: str,
    corpus: list[tuple[str, str]],  # list of (passage_text, source_name)
    top_k: int = 3,
) -> list[RetrievedPassage]:
    """
    Ranks every passage in `corpus` against `query` and returns the
    top_k highest-scoring ones, each carrying its BM25 score, embedding
    score, and the combined score that determined its rank.
    """
    if not corpus:
        return []

    passages = [text for text, _ in corpus]
    sources = [source for _, source in corpus]

    # --- BM25 half ---
    tokenized_corpus = [_tokenize(p) for p in passages]

    # BM25Plus, not BM25Okapi, deliberately. The plain Okapi IDF formula
    # can hit zero or go negative for any term appearing in half or more
    # of the corpus, verified this directly on our sample data, "vaccine"
    # got an IDF of exactly 0.0 despite being the most relevant word in
    # the query, because it appeared in 2 of our 4 sample passages.
    # BM25Plus adds a smoothing delta specifically to prevent this. This
    # matters less on the real, large corpus, but costs nothing to fix
    # now and avoids the same failure mode resurfacing on any query whose
    # key terms happen to be common within whatever subset gets searched.
    bm25 = BM25Plus(tokenized_corpus)
    bm25_raw = np.array(bm25.get_scores(_tokenize(query)))
    bm25_norm = _min_max_normalize(bm25_raw)

    # --- Embedding half ---
    model = _get_embedding_model()
    if model is not None:
        query_vec = model.encode([query])[0]
        passage_vecs = model.encode(passages)
        # cosine similarity between the query vector and every passage vector
        embed_raw = np.array([
            np.dot(query_vec, p) / (np.linalg.norm(query_vec) * np.linalg.norm(p) + 1e-8)
            for p in passage_vecs
        ])
        embed_norm = _min_max_normalize(embed_raw)
        weight = RETRIEVAL_WEIGHT_EMBEDDING
    else:
        # Offline fallback: embedding model unavailable, fall back to
        # BM25-only ranking rather than crashing. NOT the real intended
        # behavior, only triggers without internet access.
        embed_raw = np.zeros_like(bm25_raw)
        embed_norm = embed_raw
        weight = 0.0

    combined = weight * embed_norm + (1 - weight) * bm25_norm

    ranked_indices = np.argsort(-combined)[:top_k]
    return [
        RetrievedPassage(
            text=passages[i],
            source=sources[i],
            bm25_score=float(bm25_raw[i]),
            embedding_score=float(embed_raw[i]),
            combined_score=float(combined[i]),
        )
        for i in ranked_indices
    ]


if __name__ == "__main__":
    # Tiny sample corpus standing in for FEVER/FEVEROUS/SciFact until the
    # real datasets are wired in. Swap `sample_corpus` for a real loader
    # once download infrastructure exists, everything else stays the same.
    sample_corpus = [
        ("The Eiffel Tower, located in Paris, France, was completed in 1889 for the World's Fair.", "sample-wiki"),
        ("Clinical trials found no statistically significant link between the vaccine and fertility outcomes.", "sample-scifact"),
        ("The vaccine received regulatory approval after completing three phases of clinical trials.", "sample-fever"),
        ("Paris is the capital city of France and home to several major landmarks.", "sample-wiki"),
    ]

    query = "The vaccine causes infertility in most patients."
    results = retrieve(query, sample_corpus, top_k=2)

    print(f"QUERY: {query}\n")
    for r in results:
        print(f"[{r.combined_score:.3f}] (bm25={r.bm25_score:.3f}, embed={r.embedding_score:.3f}) {r.source}")
        print(f"  {r.text}")
        print()
