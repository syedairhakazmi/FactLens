"""
Claim decomposition (baseline, rule-based).

Splits a sentence containing more than one fact into independent,
self-contained sub-claims, using spaCy's dependency parse (the same
en_core_web_sm model detector.py already loads).

Patterns handled:
  1. Coordinated verbs / clauses ("and", "but", "while", "whereas", "yet")
       "The vaccine was approved last week, and it causes infertility."
       "Obama was born in Hawaii and served as president."
     -> one claim per verb; a missing subject is inherited from the
        first clause.
  2. Non-restrictive appositives (comma-bracketed)
       "Paris, the capital of France, hosts the Eiffel Tower."
     -> "Paris is the capital of France." + "Paris hosts the Eiffel Tower."
  3. Non-restrictive subject relative clauses (comma-bracketed)
       "The Eiffel Tower, which was built in 1889, is in Paris."
     -> "The Eiffel Tower was built in 1889." + "The Eiffel Tower is in Paris."

Deliberately NOT split (too error-prone for a baseline):
  - "or" (a disjunction is not two independent facts)
  - coordinated nouns ("physics and chemistry")
  - restrictive relative clauses ("the man who stole the car")
  - reported speech ("He said that A and B")

Safety net: any sentence that doesn't match a pattern, or whose split
would produce a fragment, is returned unchanged, so this stage can
never lose a claim.

Public API:  decompose(sentence: str) -> list[str]
"""

from __future__ import annotations

import logging
from functools import lru_cache

import spacy
from spacy.tokens import Span, Token

import re

logger = logging.getLogger("factlens")

_SPLIT_CONJ = {"and", "but", "while", "whereas", "yet"}
_SUBJ_DEPS = {"nsubj", "nsubjpass", "csubj", "csubjpass"}
# A clause needs at least one of these to be a meaningful claim on its own
# (guards against "He bought and sold stocks" -> "He bought.")
_COMPLEMENT_DEPS = {
    "dobj", "obj", "attr", "acomp", "prep", "agent", "dative",
    "oprd", "xcomp", "ccomp", "advmod", "npadvmod", "advcl", "prt",
    "auxpass",
}
_MIN_WORDS = 3


@lru_cache(maxsize=1)
def _get_nlp():
    return spacy.load("en_core_web_sm")


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------

def _text(tokens: list[Token], sort: bool = True) -> str:
    """Rebuild a string from tokens, keeping original spacing where tokens
    were adjacent and inserting a space where tokens were removed between."""
    if sort:
        tokens = sorted(tokens, key=lambda t: t.i)
    out = []
    for n, t in enumerate(tokens):
        out.append(t.text)
        if n + 1 < len(tokens):
            out.append(t.whitespace_ if tokens[n + 1].i == t.i + 1 else " ")
    return " ".join("".join(out).split())


def _clean(text: str) -> str:
    """Trim stray punctuation/conjunctions, capitalise, end with a period."""
    text = text.strip(" ,;:-")
    while True:
        prev = text
        text = re.sub(r"[,;:-]+\s*\.?$", "", text).strip()
        text = text.strip(" ,;:-.!?")
        if text == prev:
            break
    first, _, rest = text.partition(" ")
    if rest and first.lower() in _SPLIT_CONJ | {"or"}:
        text = rest
    text = text.strip(" ,;:-.!?")
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text


def _idx(tokens) -> set[int]:
    return {t.i for t in tokens}


# ---------------------------------------------------------------------------
# embedded material: appositives + relative clauses
# ---------------------------------------------------------------------------

def _is_nonrestrictive(t: Token) -> bool:
    """True if the subtree of t is set off by a comma / bracket on the left."""
    left = min(x.i for x in t.subtree)
    return left > 0 and t.doc[left - 1].text in {",", "("}


def _embedded_spans(sent: Span) -> list[Token]:
    """Appositive / relative-clause heads we will pull out of the sentence."""
    found = []
    for t in sent:
        if t.dep_ == "appos" and t.pos_ in {"NOUN", "PROPN"} and _is_nonrestrictive(t):
            found.append(t)
        elif t.dep_ == "relcl" and _is_nonrestrictive(t):
            found.append(t)
    return found


def _embedded_drop(embedded: list[Token]) -> set[int]:
    """Token indices to remove from the main claim (phrase + bracketing commas)."""
    drop: set[int] = set()
    for t in embedded:
        sub = sorted(x.i for x in t.subtree)
        drop |= set(sub)
        doc = t.doc
        if doc[sub[0] - 1].text in {",", "("}:
            drop.add(sub[0] - 1)
        if sub[-1] + 1 < len(doc) and doc[sub[-1] + 1].text in {",", ")"}:
            drop.add(sub[-1] + 1)
    return drop


def _head_phrase(head: Token, drop: set[int]) -> str:
    return _text([t for t in head.subtree if t.i not in drop])


def _embedded_claims(embedded: list[Token], drop: set[int]) -> list[str]:
    claims = []
    for t in embedded:
        head = t.head
        head_text = _head_phrase(head, drop)
        if not head_text:
            continue
        if t.dep_ == "appos":
            be = "are" if head.tag_ in {"NNS", "NNPS"} else "is"
            claims.append(_clean(f"{head_text} {be} {_text(list(t.subtree))}"))
        else:  # relcl: only subject relatives (who / which / that)
            relpron = next(
                (c for c in t.children
                 if c.tag_ in {"WDT", "WP"} and c.dep_ in {"nsubj", "nsubjpass"}),
                None,
            )
            if relpron is None:
                continue
            rest = [x for x in t.subtree if x.i != relpron.i]
            claims.append(_clean(f"{head_text} {_text(rest)}"))
    return claims


# ---------------------------------------------------------------------------
# coordinated clauses
# ---------------------------------------------------------------------------

def _conj_children(v: Token) -> list[Token]:
    """Verbs coordinated with v via a splittable conjunction."""
    out = []
    for c in v.children:
        if c.dep_ == "conj" and c.pos_ in {"VERB", "AUX"}:
            ccs = [x.lower_ for x in c.head.children if x.dep_ == "cc"]
            if any(w in _SPLIT_CONJ for w in ccs):
                out.append(c)
    return out


def _find_subject(v: Token) -> tuple[Token | None, bool]:
    """Own subject if present, otherwise inherited from a parent clause."""
    own = next((c for c in v.children if c.dep_ in _SUBJ_DEPS), None)
    if own is not None:
        return own, False
    anc = v
    while anc.dep_ == "conj":
        anc = anc.head
        s = next((c for c in anc.children if c.dep_ in _SUBJ_DEPS), None)
        if s is not None:
            return s, True
    return None, True


def _clause_claims(root: Token, drop: set[int]) -> list[str] | None:
    """
    Split the main clause on coordinated verbs.
    Returns None when there is nothing to split or a clause can't stand alone.
    """
    clauses = [root]
    for v in clauses:                      # list grows while iterating (BFS)
        clauses.extend(_conj_children(v))
    if len(clauses) == 1:
        return None

    claims = []
    for v in clauses:
        subj, inherited = _find_subject(v)
        if subj is None:
            return None

        excluded = set(drop)
        for c in v.children:
            if c.dep_ == "cc":
                excluded.add(c.i)
        for child in _conj_children(v):
            excluded |= _idx(child.subtree)

        subj_idx = _idx(subj.subtree)
        body = [t for t in v.subtree if t.i not in excluded and t.i not in subj_idx]

        # clause must carry something beyond the bare verb
        if not any(t.dep_ in _COMPLEMENT_DEPS for t in body):
            return None

        if inherited:
            subj_toks = [t for t in subj.subtree if t.i not in drop]
            # "was created by X and released in 1991" -> keep the passive aux
            aux = []
            if v.tag_ == "VBN" and not any(c.dep_.startswith("aux") for c in v.children):
                aux = [c for c in subj.head.children if c.dep_ in {"auxpass", "aux"}]
            text = " ".join(filter(None, [_text(subj_toks), _text(aux), _text(body)]))
        else:
            text = _text([t for t in v.subtree if t.i not in excluded])

        cleaned = _clean(text)
        if len(cleaned.split()) < _MIN_WORDS:
            return None
        claims.append((v.i, cleaned))

    return [c for _, c in sorted(claims)]


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def _decompose_sentence(sent: Span) -> list[str]:
    embedded = _embedded_spans(sent)
    drop = _embedded_drop(embedded)

    main = _clause_claims(sent.root, drop)
    if main is None:
        # no verb split: the main claim is the sentence minus embedded phrases
        main = [_clean(_text([t for t in sent if t.i not in drop]))]

    return main + _embedded_claims(embedded, drop)


def decompose(sentence: str) -> list[str]:
    """
    Split `sentence` into atomic, self-contained sub-claims.
    Always returns at least one claim; falls back to [sentence].
    """
    sentence = sentence.strip()
    if not sentence:
        return []
    try:
        doc = _get_nlp()(sentence)
        claims: list[str] = []
        for sent in doc.sents:
            claims.extend(_decompose_sentence(sent))

        seen, final = set(), []
        for c in claims:
            key = c.lower().rstrip(".")
            if c and key not in seen and len(c.split()) >= _MIN_WORDS:
                seen.add(key)
                final.append(c)
        return final or [sentence]
    except Exception as exc:  # never break the pipeline
        logger.warning("Decomposition failed, returning sentence unchanged: %s", exc)
        return [sentence]