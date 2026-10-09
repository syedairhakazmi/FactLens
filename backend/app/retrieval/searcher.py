import os
import json
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
    passage_id: str = ""
    title: str = ""

def _tokenize (text):
    # make text lowercase
    text = text.lower ()

    # remove punctuation symbols using basic python
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

def load_dataset_from_file (file_path):
    # load passages from a jsonl or json dataset file
    if not os.path.exists (file_path):
        return []

    passages = []
    if file_path.endswith (".jsonl"):
        with open (file_path, "r", encoding = "utf-8") as file:
            for line in file:
                line_content = line.strip ()
                if len (line_content) > 0:
                    entry = json.loads (line_content)
                    passages.append (entry)
    elif file_path.endswith (".json"):
        with open (file_path, "r", encoding = "utf-8") as file:
            passages = json.load (file)
    elif file_path.endswith (".csv"):
        import csv
        with open (file_path, "r", encoding = "utf-8") as file:
            reader = csv.DictReader (file)
            for row in reader:
                passages.append (row)

    return passages

def save_dataset_to_file (passages, file_path):
    # save passages to a jsonl dataset file
    folder_path = os.path.dirname (file_path)
    if len (folder_path) > 0:
        os.makedirs (folder_path, exist_ok = True)

    with open (file_path, "w", encoding = "utf-8") as file:
        for item in passages:
            line_str = json.dumps (item)
            file.write (line_str + "\n")

class CorpusIndex:
    # index and search an evidence dataset using hybrid bm25 and embeddings
    def __init__ (self, passages = None, cache_file_path = None):
        self.passages = []
        self.passage_texts = []
        self.passage_sources = []
        self.passage_ids = []
        self.passage_titles = []
        self.tokenized_passages = []
        self.bm25_engine = None
        self.passage_vectors = None
        self.cache_file_path = cache_file_path

        if passages is not None and len (passages) > 0:
            self.build_index (passages)

    def build_index (self, passages):
        self.passages = passages
        self.passage_texts = []
        self.passage_sources = []
        self.passage_ids = []
        self.passage_titles = []
        self.tokenized_passages = []

        for item in passages:
            # handle dictionary records or tuple records
            if isinstance (item, dict):
                passage_text = item.get ("text", "")
                passage_source = item.get ("source", "Local corpus")
                passage_id = item.get ("id", "")
                passage_title = item.get ("title", "")
            else:
                passage_text = item [0]
                passage_source = item [1]
                passage_id = ""
                passage_title = ""

            self.passage_texts.append (passage_text)
            self.passage_sources.append (passage_source)
            self.passage_ids.append (passage_id)
            self.passage_titles.append (passage_title)
            self.tokenized_passages.append (_tokenize (passage_text))

        # build bm25 index
        if len (self.tokenized_passages) > 0:
            self.bm25_engine = BM25Plus (self.tokenized_passages)
        else:
            self.bm25_engine = None

        # load or compute dense vectors
        embedding_model = _get_embedding_model ()
        if embedding_model is not None and len (self.passage_texts) > 0:
            # check if cached vectors file exists on disk
            if self.cache_file_path is not None and os.path.exists (self.cache_file_path):
                try:
                    loaded_vectors = np.load (self.cache_file_path)
                    if len (loaded_vectors) == len (self.passage_texts):
                        self.passage_vectors = loaded_vectors
                    else:
                        self.passage_vectors = None
                except Exception:
                    self.passage_vectors = None

            if self.passage_vectors is None:
                self.passage_vectors = embedding_model.encode (self.passage_texts)
                if self.cache_file_path is not None:
                    try:
                        cache_folder = os.path.dirname (self.cache_file_path)
                        if len (cache_folder) > 0:
                            os.makedirs (cache_folder, exist_ok = True)
                        np.save (self.cache_file_path, self.passage_vectors)
                    except Exception:
                        pass
        else:
            self.passage_vectors = None

    def search (self, query, top_k = 3):
        # hybrid search over the indexed dataset
        total_items = len (self.passage_texts)
        if total_items == 0:
            return []

        # 1. keyword scores from bm25
        if self.bm25_engine is not None:
            query_words = _tokenize (query)
            raw_bm25_scores = np.array (self.bm25_engine.get_scores (query_words))
            normalized_bm25_scores = _min_max_normalize (raw_bm25_scores)
        else:
            raw_bm25_scores = np.zeros (total_items)
            normalized_bm25_scores = np.zeros (total_items)

        # 2. dense meaning scores from embeddings
        embedding_model = _get_embedding_model ()
        if embedding_model is not None and self.passage_vectors is not None:
            query_vector = embedding_model.encode ([query]) [0]

            similarity_scores = []
            for passage_vector in self.passage_vectors:
                dot_product = np.dot (query_vector, passage_vector)
                length_product = np.linalg.norm (query_vector) * np.linalg.norm (passage_vector) + 1e-8
                similarity_scores.append (dot_product / length_product)

            raw_embedding_scores = np.array (similarity_scores)
            normalized_embedding_scores = _min_max_normalize (raw_embedding_scores)
            embedding_weight = RETRIEVAL_WEIGHT_EMBEDDING
        else:
            raw_embedding_scores = np.zeros (total_items)
            normalized_embedding_scores = np.zeros (total_items)
            embedding_weight = 0.0

        # 3. combine scores with 50/50 weighting
        final_scores = embedding_weight * normalized_embedding_scores + (1.0 - embedding_weight) * normalized_bm25_scores

        # 4. pick top k scoring passages
        best_indices = np.argsort (-final_scores) [:top_k]

        top_passages = []
        for best_index in best_indices:
            top_passages.append (
                RetrievedPassage (
                    text = self.passage_texts [best_index],
                    source = self.passage_sources [best_index],
                    bm25_score = float (raw_bm25_scores [best_index]),
                    embedding_score = float (raw_embedding_scores [best_index]),
                    combined_score = float (final_scores [best_index]),
                    passage_id = self.passage_ids [best_index],
                    title = self.passage_titles [best_index],
                )
            )

        return top_passages

_DEFAULT_DATASET_FILE = os.path.join (os.path.dirname (__file__), "..", "..", "data", "corpus.jsonl")
_DEFAULT_CACHE_FILE = os.path.join (os.path.dirname (__file__), "..", "..", "data", "corpus_embeddings.npy")
_GLOBAL_INDEX = None

def get_global_index ():
    # get or initialize global index from the dataset file
    global _GLOBAL_INDEX
    if _GLOBAL_INDEX is None:
        dataset_path = os.path.abspath (_DEFAULT_DATASET_FILE)
        cache_path = os.path.abspath (_DEFAULT_CACHE_FILE)
        loaded_passages = load_dataset_from_file (dataset_path)
        _GLOBAL_INDEX = CorpusIndex (loaded_passages, cache_file_path = cache_path)
    return _GLOBAL_INDEX

def retrieve (query, corpus = None, top_k = 3):
    # retrieve most relevant passages for a query
    if corpus is not None:
        # if a specific corpus is provided, index and search it
        custom_index = CorpusIndex (corpus)
        return custom_index.search (query, top_k = top_k)

    # otherwise use the loaded dataset index
    dataset_index = get_global_index ()
    return dataset_index.search (query, top_k = top_k)

def download_huggingface_dataset (dataset_name = "allenai/scifact", split = "train", max_samples = 100, output_file = None):
    # download sample passages from huggingface datasets into jsonl
    try:
        from datasets import load_dataset
        dataset = load_dataset (dataset_name, split = split)
    except Exception as exc:
        print (f"could not download dataset: {exc}")
        return []

    collected_passages = []
    sample_count = 0
    for row in dataset:
        if sample_count >= max_samples:
            break

        # extract text based on dataset schema
        text = ""
        title = ""
        doc_id = str (sample_count + 1)

        if "abstract" in row:
            if isinstance (row ["abstract"], list):
                text = " ".join (row ["abstract"])
            else:
                text = str (row ["abstract"])
            title = row.get ("title", "")
        elif "text" in row:
            text = row.get ("text", "")
            title = row.get ("title", "")
        elif "claim" in row:
            text = row.get ("claim", "")

        if len (text.strip ()) > 0:
            collected_passages.append ({
                "id": doc_id,
                "title": title,
                "source": dataset_name,
                "text": text.strip (),
            })
            sample_count = sample_count + 1

    if output_file is not None and len (collected_passages) > 0:
        save_dataset_to_file (collected_passages, output_file)

    return collected_passages

if __name__ == "__main__":
    test_query = "The COVID-19 vaccine causes infertility in most patients."
    print (f"Searching dataset for: '{test_query}'\n")

    results = retrieve (test_query, top_k = 3)
    for passage in results:
        print (f"[{passage.combined_score:.3f}] (bm25={passage.bm25_score:.3f}, embed={passage.embedding_score:.3f}) [{passage.source}] {passage.title}")
        print (f"  {passage.text}")
        print ()
