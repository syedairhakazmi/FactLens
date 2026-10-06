"""
Coreference resolution module. Owner: Irha.

Resolves pronouns and other referring expressions ("it", "they", "he")
back to the entity they refer to, so that downstream claim extraction
and decomposition receive self-contained, independently checkable text.

Example:
    Input:  "Ali is a good boy. He is fat."
    Output: "Ali is a good boy. Ali is fat."

Uses fastcoref's LingMessCoref model, which is generally more accurate than
the distilled FCoref model for resolving referring expressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import spacy
from spacy.tokens import Doc, Span, Token

try:
    from fastcoref import LingMessCoref
    from fastcoref.coref_models import modeling_lingmess
    from transformers import AutoModel as _AutoModel

    class _EagerAutoModel:
        """
        LingMess is built on Longformer, which doesn't support the SDPA
        attention implementation newer transformers versions use by
        default, loading crashes with a ValueError. Without this patch
        _get_model() swallows that error and resolve() silently returns
        the input unchanged. Forcing "eager" attention avoids the crash.
        """

        @staticmethod
        def from_config(config, **kwargs):
            kwargs.setdefault("attn_implementation", "eager")
            return _AutoModel.from_config(config, **kwargs)

    modeling_lingmess.AutoModel = _EagerAutoModel
except Exception:
    LingMessCoref = None

@dataclass
class CoreferenceResult:
    original_text: str
    resolved_text: str
    clusters: list[list[str]]  # groups of mentions that refer to the same entity


# ---------------------------------------------------------------------------
# Rewriting rules
# ---------------------------------------------------------------------------
# The coreference model only tells us WHICH mentions belong together. Turning
# that into readable, self-contained text is done here, using spaCy's grammar
# analysis rather than hand-written word lists, so the rules generalize to any
# input instead of only the pronouns/phrasings someone thought to list:
#
#   Rule 1  Representative = the first mention whose head word is a proper
#           noun ("SpaceX", "Barack Obama"), else the first mention containing
#           a proper noun, else the first non-pronoun mention. Clusters made of
#           only pronouns are left untouched, there's nothing to resolve to.
#   Rule 2  Only personal pronouns are replaced. Names and descriptive phrases
#           ("The company", "the organization") are left as the author wrote
#           them.
#   Rule 3  Pronoun form is respected:
#             plain       he / she / it / they / him / them  -> "Obama"
#             possessive  his / its / their / her(book) / hers -> "Obama's"
#             reflexive   himself / itself / themselves      -> unchanged
#   Rule 4  Capitalization: capitalize at sentence start, and lowercase a
#           leading determiner mid-sentence ("and The vaccine" -> "and the
#           vaccine").

# Entity types that count as "names" when choosing a representative.
# DATE / CARDINAL / PERCENT etc. are deliberately excluded.
_NAME_ENTITY_TYPES = {
    "PERSON", "ORG", "GPE", "LOC", "NORP", "FAC",
    "PRODUCT", "EVENT", "WORK_OF_ART", "LAW",
}


@lru_cache(maxsize=1)
def _get_nlp():
    return spacy.load("en_core_web_sm")


def _to_span(doc: Doc, start: int, end: int) -> Span | None:
    """Map the model's character offsets onto spaCy tokens."""
    return doc.char_span(start, end, alignment_mode="expand")


def _is_pronoun(span: Span) -> bool:
    """Any standalone pronoun, never eligible to be a representative."""
    return len(span) == 1 and (span[0].pos_ == "PRON" or span[0].tag_ in ("PRP", "PRP$"))


def _is_personal_pronoun(span: Span) -> bool:
    """
    Personal pronouns (he, her, its, they...) are the only mentions that get
    replaced. Demonstratives like "this"/"that" are excluded: they often
    refer to whole events or ideas, and substituting a noun phrase for them
    tends to produce wrong or unreadable sentences.
    """
    return len(span) == 1 and span[0].tag_ in ("PRP", "PRP$")


def _pronoun_form(token: Token) -> str:
    morph = token.morph
    if "Yes" in morph.get("Reflex") or token.lower_.endswith(("self", "selves")):
        return "reflexive"
    # PRP$ = possessive determiner ("his car", "her car"); Poss=Yes also
    # covers independent possessives ("the car is hers").
    if token.tag_ == "PRP$" or "Yes" in morph.get("Poss"):
        return "possessive"
    return "plain"


def _is_name(token: Token) -> bool:
    return token.pos_ == "PROPN" or token.ent_type_ in _NAME_ENTITY_TYPES


def _clean_representative(span: Span) -> Span:
    """Drop trailing possessive markers / punctuation: "Obama's" -> "Obama"."""
    end = span.end
    while end > span.start + 1 and (span.doc[end - 1].tag_ == "POS" or span.doc[end - 1].is_punct):
        end -= 1
    return span.doc[span.start:end]


def _choose_representative(mentions: list[Span]) -> Span | None:
    """Rule 1. `mentions` must be in order of appearance."""
    candidates = [m for m in mentions if not _is_pronoun(m)]
    if not candidates:
        return None
    for prefer in (
        lambda m: _is_name(m.root),               # head word is a name: "Barack Obama"
        lambda m: any(_is_name(t) for t in m),    # contains a name: "the Paris office"
        lambda m: True,                           # any descriptive phrase: "the new vaccine"
    ):
        for m in candidates:
            if prefer(m):
                return _clean_representative(m)
    return None


def _make_possessive(text: str, rep: Span) -> str:
    last = rep[-1]
    # Plural nouns ending in "s" take a bare apostrophe: "the scientists'".
    if last.tag_ in ("NNS", "NNPS") and text.endswith("s"):
        return text + "'"
    return text + "'s"


def _match_case(text: str, rep: Span, pronoun: Token) -> str:
    """Rule 4."""
    if not text:
        return text
    if pronoun.is_sent_start:
        return text[0].upper() + text[1:]
    if rep[0].pos_ == "DET" and text[0].isupper():
        return text[0].lower() + text[1:]
    return text


def _render(pronoun: Token, rep: Span, rep_text: str) -> str | None:
    """Rule 3: the replacement string for one pronoun, or None to leave it."""
    form = _pronoun_form(pronoun)
    if form == "reflexive":
        return None
    new = _make_possessive(rep_text, rep) if form == "possessive" else rep_text
    return _match_case(new, rep, pronoun)


@lru_cache(maxsize=1)
def _get_model() -> LingMessCoref | None:
    """
    Loads the model once per process, not once per request. Coreference
    models are expensive to load, this cache keeps the API responsive
    after the first call.

    Returns None if the pretrained weights can't be fetched (e.g. no
    internet access or fastcoref is not installed), so callers can fall
    back gracefully instead of crashing. On a machine with normal
    internet access and weights installed this succeeds and caches.
    """
    if LingMessCoref is None:
        return None
    try:
        return LingMessCoref()
    except Exception:
        return None


def resolve(text: str) -> CoreferenceResult:
    """
    Runs LingMess coreference resolution and rewrites the text so every
    personal pronoun is replaced with its cluster's representative,
    following Rules 1-4 described above.
    """
    model = _get_model()

    if model is None:
        # Offline fallback, NOT the real coreference logic. Only triggers
        # when the pretrained model can't be downloaded, e.g. a sandboxed
        # environment with no internet access. On a normal machine this
        # branch never runs. Kept here so the rest of the pipeline can
        # still be exercised end to end without the real model present.
        return CoreferenceResult(original_text=text, resolved_text=text, clusters=[])

    prediction = model.predict(texts=[text])[0]

    clusters = prediction.get_clusters(as_strings=True)
    char_clusters = prediction.get_clusters(as_strings=False)

    if not clusters:
        return CoreferenceResult(original_text=text, resolved_text=text, clusters=[])

    doc = _get_nlp()(text)

    # Step 1: per cluster, pick a representative (Rule 1) and collect the
    # personal pronouns that should point at it (Rule 2).
    reps: dict[int, Span] = {}
    pronouns: list[tuple[Token, int]] = []  # (pronoun token, cluster index)
    for ci, span_cluster in enumerate(char_clusters):
        mentions = [
            s for s in (_to_span(doc, start, end) for start, end in sorted(span_cluster))
            if s is not None
        ]
        rep = _choose_representative(mentions)
        if rep is None:
            continue
        reps[ci] = rep
        pronouns.extend((m[0], ci) for m in mentions if _is_personal_pronoun(m))

    # Step 2: a representative can itself contain a pronoun from another
    # cluster, e.g. "it" -> "his project". Resolve those inner pronouns one
    # level deep so the substituted text is self-contained ("John's project").
    rep_text: dict[int, str] = {}
    for ci, rep in reps.items():
        inner = sorted(
            ((tok, other) for tok, other in pronouns
             if other != ci and rep.start <= tok.i < rep.end),
            key=lambda p: p[0].idx,
            reverse=True,
        )
        piece = rep.text
        for tok, other in inner:
            new = _render(tok, reps[other], reps[other].text)
            if new is None:
                continue
            offset = tok.idx - rep.start_char
            piece = piece[:offset] + new + piece[offset + len(tok.text):]
        rep_text[ci] = piece

    # Step 3: build the replacements (Rules 3 and 4).
    replacements: list[tuple[int, int, str]] = []
    for tok, ci in pronouns:
        new = _render(tok, reps[ci], rep_text[ci])
        if new is not None:
            replacements.append((tok.idx, tok.idx + len(tok.text), new))

    # Apply replacements right-to-left so earlier character offsets stay valid.
    resolved = text
    for start, end, replacement in sorted(replacements, key=lambda r: r[0], reverse=True):
        resolved = resolved[:start] + replacement + resolved[end:]

    return CoreferenceResult(original_text=text, resolved_text=resolved, clusters=clusters)


if __name__ == "__main__":
    # Quick manual check: run `python -m app.coreference.resolver` from
    # backend/ to sanity-check the module on its own before wiring it in.
    samples = [
        "Ali is a good boy. He is fat.",
        "The Eiffel Tower was completed in 1889. It is located in Paris.",
        "The new vaccine was approved last week, and it causes infertility in most patients.",
    ]
    for s in samples:
        result = resolve(s)
        print(f"IN:  {result.original_text}")
        print(f"OUT: {result.resolved_text}")
        print()
