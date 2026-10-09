from dataclasses import dataclass
from functools import lru_cache
import spacy

try:
    from fastcoref import LingMessCoref
    from fastcoref.coref_models import modeling_lingmess
    from transformers import AutoModel as _AutoModel

    class _EagerAutoModel:
        @staticmethod
        def from_config (config, **kwargs):
            kwargs.setdefault ("attn_implementation", "eager")
            return _AutoModel.from_config (config, **kwargs)

    modeling_lingmess.AutoModel = _EagerAutoModel
except Exception:
    LingMessCoref = None

@dataclass
class CoreferenceResult:
    original_text: str
    resolved_text: str
    clusters: list

_NAME_ENTITY_TYPES = {
    "PERSON", "ORG", "GPE", "LOC", "NORP", "FAC",
    "PRODUCT", "EVENT", "WORK_OF_ART", "LAW",
}

@lru_cache (maxsize = 1)
def _get_nlp ():
    return spacy.load ("en_core_web_sm")

def _to_span (doc, start, end):
    return doc.char_span (start, end, alignment_mode = "expand")

def _is_pronoun (span):
    if len (span) == 1:
        if span [0].pos_ == "PRON" or span [0].tag_ in ("PRP", "PRP$"):
            return True
    return False

def _is_personal_pronoun (span):
    if len (span) == 1:
        if span [0].tag_ in ("PRP", "PRP$"):
            return True
    return False

def _pronoun_form (token):
    morph = token.morph
    if "Yes" in morph.get ("Reflex") or token.lower_.endswith (("self", "selves")):
        return "reflexive"
    if token.tag_ == "PRP$" or "Yes" in morph.get ("Poss"):
        return "possessive"
    return "plain"

def _is_name (token):
    if token.pos_ == "PROPN" or token.ent_type_ in _NAME_ENTITY_TYPES:
        return True
    return False

def _clean_representative (span):
    end = span.end
    while end > span.start + 1:
        last_token = span.doc [end - 1]
        if last_token.tag_ == "POS" or last_token.is_punct:
            end = end - 1
        else:
            break
    return span.doc [span.start:end]

def _choose_representative (mentions):
    candidates = []
    for mention in mentions:
        if not _is_pronoun (mention):
            candidates.append (mention)

    if len (candidates) == 0:
        return None

    for mention in candidates:
        if _is_name (mention.root):
            return _clean_representative (mention)

    for mention in candidates:
        has_name = False
        for token in mention:
            if _is_name (token):
                has_name = True
                break
        if has_name:
            return _clean_representative (mention)

    return _clean_representative (candidates [0])

def _make_possessive (text, representative):
    last_token = representative [-1]
    if last_token.tag_ in ("NNS", "NNPS") and text.endswith ("s"):
        return text + "'"
    return text + "'s"

def _match_case (text, representative, pronoun):
    if len (text) == 0:
        return text
    if pronoun.is_sent_start:
        return text [0].upper () + text [1:]
    if representative [0].pos_ == "DET" and text [0].isupper ():
        return text [0].lower () + text [1:]
    return text

def _render (pronoun, representative, representative_text):
    form = _pronoun_form (pronoun)
    if form == "reflexive":
        return None
    if form == "possessive":
        new_text = _make_possessive (representative_text, representative)
    else:
        new_text = representative_text
    return _match_case (new_text, representative, pronoun)

@lru_cache (maxsize = 1)
def _get_model ():
    if LingMessCoref is None:
        return None
    try:
        return LingMessCoref ()
    except Exception:
        return None

_PRONOUN_TOKENS = {
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "they", "them", "their", "theirs", "themselves",
    "we", "us", "our", "ours", "ourselves",
    "i", "me", "my", "mine", "myself",
    "you", "your", "yours", "yourself", "yourselves",
}

def _has_candidate_pronouns (text):
    # check if text contains any personal pronoun candidates
    words = []
    current = []
    for ch in text.lower ():
        if ch.isalnum ():
            current.append (ch)
        else:
            if len (current) > 0:
                words.append ("".join (current))
                current = []
    if len (current) > 0:
        words.append ("".join (current))

    for word in words:
        if word in _PRONOUN_TOKENS:
            return True
    return False

def resolve (text):
    # run coreference resolution on input text
    if not _has_candidate_pronouns (text):
        return CoreferenceResult (original_text = text, resolved_text = text, clusters = [])

    model = _get_model ()
    if model is None:
        return CoreferenceResult (original_text = text, resolved_text = text, clusters = [])

    prediction = model.predict (texts = [text]) [0]
    clusters = prediction.get_clusters (as_strings = True)
    char_clusters = prediction.get_clusters (as_strings = False)

    if len (clusters) == 0:
        return CoreferenceResult (original_text = text, resolved_text = text, clusters = [])

    nlp = _get_nlp ()
    doc = nlp (text)

    # pick main name for each cluster
    cluster_representatives = {}
    pronouns_to_replace = []

    cluster_index = 0
    for span_cluster in char_clusters:
        sorted_spans = sorted (span_cluster)
        mentions = []
        for start, end in sorted_spans:
            span = _to_span (doc, start, end)
            if span is not None:
                mentions.append (span)

        representative = _choose_representative (mentions)
        if representative is not None:
            cluster_representatives [cluster_index] = representative
            for mention in mentions:
                if _is_personal_pronoun (mention):
                    pronouns_to_replace.append ((mention [0], cluster_index))

        cluster_index = cluster_index + 1

    # handle pronouns that appear inside representatives
    representative_texts = {}
    for cluster_id, representative in cluster_representatives.items ():
        inner_pronouns = []
        for token, other_cluster_id in pronouns_to_replace:
            if other_cluster_id != cluster_id and representative.start <= token.i < representative.end:
                inner_pronouns.append ((token, other_cluster_id))

        inner_pronouns.sort (key = lambda item: item [0].idx, reverse = True)

        current_text = representative.text
        for token, other_cluster_id in inner_pronouns:
            other_rep = cluster_representatives [other_cluster_id]
            replacement_word = _render (token, other_rep, other_rep.text)
            if replacement_word is not None:
                offset = token.idx - representative.start_char
                current_text = current_text [:offset] + replacement_word + current_text [offset + len (token.text):]

        representative_texts [cluster_id] = current_text

    # replace pronouns from right to left to keep text positions correct
    replacements = []
    for token, cluster_id in pronouns_to_replace:
        target_representative = cluster_representatives [cluster_id]
        replacement_word = _render (token, target_representative, representative_texts [cluster_id])
        if replacement_word is not None:
            start_pos = token.idx
            end_pos = token.idx + len (token.text)
            replacements.append ((start_pos, end_pos, replacement_word))

    replacements.sort (key = lambda item: item [0], reverse = True)
    resolved_text = text
    for start_pos, end_pos, replacement_word in replacements:
        resolved_text = resolved_text [:start_pos] + replacement_word + resolved_text [end_pos:]

    return CoreferenceResult (original_text = text, resolved_text = resolved_text, clusters = clusters)

if __name__ == "__main__":
    samples = [
        "Ali is a good boy. He is fat.",
        "The Eiffel Tower was completed in 1889. It is located in Paris.",
        "The new vaccine was approved last week, and it causes infertility in most patients.",
    ]
    for sample in samples:
        result = resolve (sample)
        print (f"IN:  {result.original_text}")
        print (f"OUT: {result.resolved_text}")
        print ()
