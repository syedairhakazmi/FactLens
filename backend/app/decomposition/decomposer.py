import logging
from functools import lru_cache
import spacy

logger = logging.getLogger ("factlens")

_SPLIT_CONJ = {"and", "but", "while", "whereas", "yet"}
_SUBJ_DEPS = {"nsubj", "nsubjpass", "csubj", "csubjpass"}
_COMPLEMENT_DEPS = {
    "dobj", "obj", "attr", "acomp", "prep", "agent", "dative",
    "oprd", "xcomp", "ccomp", "advmod", "npadvmod", "advcl", "prt",
    "auxpass",
}
_MIN_WORDS = 3

@lru_cache (maxsize = 1)
def _get_nlp ():
    # load spacy small english model
    return spacy.load ("en_core_web_sm")

def _text (tokens, sort = True):
    # build clean text from tokens preserving original whitespace
    if sort:
        tokens = sorted (tokens, key = lambda t: t.i)
    out = []
    token_count = len (tokens)
    for idx in range (token_count):
        t = tokens [idx]
        out.append (t.text)
        if idx + 1 < token_count:
            next_t = tokens [idx + 1]
            if next_t.i == t.i + 1:
                out.append (t.whitespace_)
            else:
                out.append (" ")
    joined = "".join (out)
    words = joined.split ()
    return " ".join (words)

def _clean (text):
    # clean leading and trailing punctuation and spaces
    text = text.strip ()
    punctuation_chars = ",;:-.!? "
    while len (text) > 0 and text [-1] in punctuation_chars:
        text = text [:-1].strip ()

    # remove leading conjunction if left behind
    words = text.split ()
    if len (words) > 1:
        first_word = words [0].lower ()
        if first_word in _SPLIT_CONJ or first_word == "or":
            text = " ".join (words [1:])

    while len (text) > 0 and text [-1] in punctuation_chars:
        text = text [:-1].strip ()

    if len (text) == 0:
        return ""

    # capitalize first letter and ensure ending period
    text = text [0].upper () + text [1:]
    if not text.endswith (".") and not text.endswith ("?") and not text.endswith ("!"):
        text = text + "."
    return text

def _is_nonrestrictive (t):
    # check if subtree is set off by a comma or bracket on the left
    left = 999999
    for x in t.subtree:
        if x.i < left:
            left = x.i
    if left > 0:
        prev_token = t.doc [left - 1]
        if prev_token.text == "," or prev_token.text == "(":
            return True
    return False

def _embedded_spans (sent):
    # find appositive and relative clause tokens to pull out
    found = []
    for t in sent:
        if t.dep_ == "appos" and (t.pos_ == "NOUN" or t.pos_ == "PROPN") and _is_nonrestrictive (t):
            found.append (t)
        elif t.dep_ == "relcl" and _is_nonrestrictive (t):
            found.append (t)
    return found

def _embedded_drop (embedded):
    # token indices to remove from the main claim
    drop = set ()
    for t in embedded:
        sub = []
        for x in t.subtree:
            sub.append (x.i)
        sub = sorted (sub)
        for idx in sub:
            drop.add (idx)
        doc = t.doc
        first_idx = sub [0]
        last_idx = sub [-1]
        if first_idx > 0:
            prev_char = doc [first_idx - 1].text
            if prev_char == "," or prev_char == "(":
                drop.add (first_idx - 1)
        if last_idx + 1 < len (doc):
            next_char = doc [last_idx + 1].text
            if next_char == "," or next_char == ")":
                drop.add (last_idx + 1)
    return drop

def _head_phrase (head, drop):
    # extract head phrase tokens excluding dropped embedded tokens
    toks = []
    for t in head.subtree:
        if t.i not in drop:
            toks.append (t)
    return _text (toks)

def _embedded_claims (embedded, drop):
    # extract standalone claims from appositives and relative clauses
    claims = []
    for t in embedded:
        head = t.head
        head_text = _head_phrase (head, drop)
        if len (head_text) == 0:
            continue
        if t.dep_ == "appos":
            if head.tag_ == "NNS" or head.tag_ == "NNPS":
                be = "are"
            else:
                be = "is"
            subtree_toks = []
            for x in t.subtree:
                subtree_toks.append (x)
            sub_text = _text (subtree_toks)
            claim_str = head_text + " " + be + " " + sub_text
            claims.append (_clean (claim_str))
        else:
            relpron = None
            for c in t.children:
                if (c.tag_ == "WDT" or c.tag_ == "WP") and (c.dep_ == "nsubj" or c.dep_ == "nsubjpass"):
                    relpron = c
                    break
            if relpron is None:
                continue
            rest = []
            for x in t.subtree:
                if x.i != relpron.i:
                    rest.append (x)
            claim_str = head_text + " " + _text (rest)
            claims.append (_clean (claim_str))
    return claims

def _conj_children (v):
    # verbs coordinated with v via a splittable conjunction
    out = []
    for c in v.children:
        if c.dep_ == "conj" and (c.pos_ == "VERB" or c.pos_ == "AUX"):
            has_split_cc = False
            for x in c.head.children:
                if x.dep_ == "cc" and x.lower_ in _SPLIT_CONJ:
                    has_split_cc = True
                    break
            if has_split_cc:
                out.append (c)
    return out

def _find_subject (v):
    # find own subject or inherit from ancestor clause
    for c in v.children:
        if c.dep_ in _SUBJ_DEPS:
            return c, False
    anc = v
    while anc.dep_ == "conj":
        anc = anc.head
        for c in anc.children:
            if c.dep_ in _SUBJ_DEPS:
                return c, True
    return None, True

def _clause_claims (root, drop):
    # split coordinated clauses on verbs
    clauses = [root]
    idx = 0
    while idx < len (clauses):
        v = clauses [idx]
        for child in _conj_children (v):
            clauses.append (child)
        idx = idx + 1
    if len (clauses) == 1:
        return None

    claims = []
    for v in clauses:
        subj, inherited = _find_subject (v)
        if subj is None:
            return None

        excluded = set (drop)
        for c in v.children:
            if c.dep_ == "cc":
                excluded.add (c.i)
        for child in _conj_children (v):
            for t in child.subtree:
                excluded.add (t.i)

        subj_idx = set ()
        for t in subj.subtree:
            subj_idx.add (t.i)

        body = []
        for t in v.subtree:
            if t.i not in excluded and t.i not in subj_idx:
                body.append (t)

        # clause must carry something beyond the bare verb
        has_complement = False
        for t in body:
            if t.dep_ in _COMPLEMENT_DEPS:
                has_complement = True
                break
        if not has_complement:
            return None

        if inherited:
            subj_toks = []
            for t in subj.subtree:
                if t.i not in drop:
                    subj_toks.append (t)
            aux = []
            if v.tag_ == "VBN":
                has_aux = False
                for c in v.children:
                    if c.dep_.startswith ("aux"):
                        has_aux = True
                        break
                if not has_aux:
                    for c in subj.head.children:
                        if c.dep_ == "auxpass" or c.dep_ == "aux":
                            aux.append (c)
            parts = []
            subj_text = _text (subj_toks)
            if len (subj_text) > 0:
                parts.append (subj_text)
            aux_text = _text (aux)
            if len (aux_text) > 0:
                parts.append (aux_text)
            body_text = _text (body)
            if len (body_text) > 0:
                parts.append (body_text)
            text = " ".join (parts)
        else:
            toks = []
            for t in v.subtree:
                if t.i not in excluded:
                    toks.append (t)
            text = _text (toks)

        cleaned = _clean (text)
        if len (cleaned.split ()) < _MIN_WORDS:
            return None
        claims.append ((v.i, cleaned))

    claims = sorted (claims, key = lambda item: item [0])
    result = []
    for item in claims:
        result.append (item [1])
    return result

def _decompose_sentence (sent):
    # decompose a single sentence
    embedded = _embedded_spans (sent)
    drop = _embedded_drop (embedded)

    main = _clause_claims (sent.root, drop)
    if main is None:
        toks = []
        for t in sent:
            if t.i not in drop:
                toks.append (t)
        main = [_clean (_text (toks))]

    return main + _embedded_claims (embedded, drop)

def decompose (sentence):
    # split sentence into atomic self-contained sub-claims
    sentence = sentence.strip ()
    if len (sentence) == 0:
        return []
    try:
        nlp = _get_nlp ()
        doc = nlp (sentence)
        claims = []
        for sent in doc.sents:
            for c in _decompose_sentence (sent):
                claims.append (c)

        seen = set ()
        final = []
        for c in claims:
            key = c.lower ().rstrip (".")
            if len (c) > 0 and key not in seen and len (c.split ()) >= _MIN_WORDS:
                seen.add (key)
                final.append (c)
        if len (final) > 0:
            return final
        return [sentence]
    except Exception as exc:
        logger.warning ("Decomposition failed, returning sentence unchanged: %s", exc)
        return [sentence]