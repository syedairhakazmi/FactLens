"""
Coreference resolution module. Owner: Irha.

Resolves pronouns and other referring expressions ("it", "they", "he")
back to the entity they refer to, so that downstream claim extraction
and decomposition receive self-contained, independently checkable text.

Example:
    Input:  "Ali is a good boy. He is fat."
    Output: "Ali is a good boy. Ali is fat."

Uses fastcoref's FCoref model (the fast, distilled mode), per the team's
decision to prioritize the response-time target over LingMess's higher
accuracy. If evaluation later shows FCoref's accuracy is insufficient,
swap FCoref -> LingMessCoref below, no other code needs to change.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

try:
    from fastcoref import FCoref
except Exception:
    FCoref = None


@dataclass
class CoreferenceResult:
    original_text: str
    resolved_text: str
    clusters: list[list[str]]  # groups of mentions that refer to the same entity


@lru_cache(maxsize=1)
def _get_model() -> FCoref | None:
    """
    Loads the model once per process, not once per request. Coreference
    models are expensive to load, this cache keeps the API responsive
    after the first call.

    Returns None if the pretrained weights can't be fetched (e.g. no
    internet access or fastcoref not installed), so callers can fall
    back gracefully instead of crashing. On a machine with normal
    internet access and weights installed this succeeds and caches.
    """
    if FCoref is None:
        return None
    try:
        return FCoref()
    except Exception:
        return None


def resolve(text: str) -> CoreferenceResult:
    """
    Runs coreference resolution and rewrites the text so every mention
    in a cluster is replaced with that cluster's most specific mention
    (its "representative"), usually the first proper noun mentioned.
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

    # Pick a representative mention per cluster: the longest string mention,
    # since "Ali" is more useful downstream than "he" or "him". This is a
    # simple, defensible heuristic, not a trained component, and is easy
    # to swap for something smarter later without touching callers.
    replacements: list[tuple[int, int, str]] = []
    for str_cluster, span_cluster in zip(clusters, char_clusters):
        representative = max(str_cluster, key=len)
        for (start, end) in span_cluster:
            mention_text = text[start:end]
            if mention_text != representative:
                replacements.append((start, end, representative))

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
