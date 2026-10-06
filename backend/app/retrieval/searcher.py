import string
from dataclasses import dataclass
from functools import lru_cache
import numpy as np
from rank_bm25 import BM25Plus

RETRIEVAL_WEIGHT_EMBEDDING = 0.5

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

def _tokenize (text):
    # make text lowercase
    text = text.lower ()

    # remove punctuation symbols
    for symbol in string.punctuation:
        text = text.replace (symbol, " ")

    # split by spaces to get words
    words = text.split ()

    # remove useless small words like is the in
    clean_words = []
    for word in words:
        if word not in _STOPWORDS:
            clean_words.append (word)

    return clean_words

@lru_cache (maxsize = 1)
def _get_embedding_model ():
    # load embedding model
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer ("all-MiniLM-L6-v2")
    except Exception:
        return None

def _min_max_normalize (scores):
    # scale scores between 0 and 1
    min_value = scores.min ()
    max_value = scores.max ()
    if max_value == min_value:
        return np.zeros_like (scores)
    return (scores - min_value) / (max_value - min_value)

def retrieve (query, corpus, top_k = 3):
    # search through the corpus to find best passages
    if len (corpus) == 0:
        return []

    passage_texts = []
    passage_sources = []
    for text_item, source_item in corpus:
        passage_texts.append (text_item)
        passage_sources.append (source_item)

    # 1. keyword matching with bm25
    tokenized_passages = []
    for passage_text in passage_texts:
        tokenized_passages.append (_tokenize (passage_text))

    bm25_engine = BM25Plus (tokenized_passages)
    query_words = _tokenize (query)
    raw_bm25_scores = np.array (bm25_engine.get_scores (query_words))
    normalized_bm25_scores = _min_max_normalize (raw_bm25_scores)

    # 2. meaning matching with embeddings
    embedding_model = _get_embedding_model ()
    if embedding_model is not None:
        query_vector = embedding_model.encode ([query]) [0]
        passage_vectors = embedding_model.encode (passage_texts)

        similarity_scores = []
        for passage_vector in passage_vectors:
            dot_product = np.dot (query_vector, passage_vector)
            length_product = np.linalg.norm (query_vector) * np.linalg.norm (passage_vector) + 1e-8
            similarity_scores.append (dot_product / length_product)

        raw_embedding_scores = np.array (similarity_scores)
        normalized_embedding_scores = _min_max_normalize (raw_embedding_scores)
        embedding_weight = RETRIEVAL_WEIGHT_EMBEDDING
    else:
        raw_embedding_scores = np.zeros_like (raw_bm25_scores)
        normalized_embedding_scores = raw_embedding_scores
        embedding_weight = 0.0

    # 3. combine keyword and meaning scores
    final_scores = embedding_weight * normalized_embedding_scores + (1.0 - embedding_weight) * normalized_bm25_scores

    # 4. pick the top scoring passages
    best_indices = np.argsort (-final_scores) [:top_k]

    top_passages = []
    for best_index in best_indices:
        top_passages.append (
            RetrievedPassage (
                text = passage_texts [best_index],
                source = passage_sources [best_index],
                bm25_score = float (raw_bm25_scores [best_index]),
                embedding_score = float (raw_embedding_scores [best_index]),
                combined_score = float (final_scores [best_index]),
            )
        )

    return top_passages

if __name__ == "__main__":
    sample_corpus = [
        ("The Eiffel Tower, located in Paris, France, was completed in 1889 for the World's Fair.", "sample-wiki"),
        ("Clinical trials found no statistically significant link between the vaccine and fertility outcomes.", "sample-scifact"),
        ("The vaccine received regulatory approval after completing three phases of clinical trials.", "sample-fever"),
        ("Paris is the capital city of France and home to several major landmarks.", "sample-wiki"),
    ]

    sample_query = "The vaccine causes infertility in most patients."
    found_results = retrieve (sample_query, sample_corpus, top_k = 2)

    print (f"QUERY: {sample_query}\n")
    for item in found_results:
        print (f"[{item.combined_score:.3f}] (bm25={item.bm25_score:.3f}, embed={item.embedding_score:.3f}) {item.source}")
        print (f"  {item.text}")
        print ()
