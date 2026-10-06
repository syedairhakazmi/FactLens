import pytest
from app.coreference import resolver

class FakePrediction:
    def __init__ (self, clusters, spans):
        self._clusters = clusters
        self._spans = spans

    def get_clusters (self, as_strings):
        if as_strings:
            return self._clusters
        return self._spans

class FakeLingMess:
    def __init__ (self, prediction):
        self.prediction = prediction

    def predict (self, texts):
        return [self.prediction]

def _mention_spans (text, clusters):
    spans = []
    cursors = {}
    for cluster in clusters:
        cluster_spans = []
        for mention in cluster:
            start_pos = text.index (mention, cursors.get (mention, 0))
            end_pos = start_pos + len (mention)
            cluster_spans.append ((start_pos, end_pos))
            cursors [mention] = end_pos
        spans.append (cluster_spans)
    return spans

@pytest.mark.parametrize (
    ("text", "clusters", "expected"),
    [
        (
            "The cat sat on the mat. It was very old. It had been in the family for years.",
            [["The cat", "It", "It"]],
            "The cat sat on the mat. The cat was very old. The cat had been in the family for years.",
        ),
        (
            "Barack Obama served as president. He gave a speech. His words moved him.",
            [["Barack Obama", "He", "His", "him"]],
            "Barack Obama served as president. Barack Obama gave a speech. Barack Obama's words moved Barack Obama.",
        ),
        (
            "Mary told John that he could handle it himself.",
            [["John", "he", "himself"]],
            "Mary told John that John could handle it himself.",
        ),
        (
            "The company hired a CEO. She was confident.",
            [["The company", "She"]],
            "The company hired a CEO. The company was confident.",
        ),
        (
            "The scientists published their paper. They claimed it was conclusive.",
            [["The scientists", "their", "They"], ["paper", "it"]],
            "The scientists published the scientists' paper. The scientists claimed paper was conclusive.",
        ),
    ],
)
def test_lingmess_cluster_replacements (monkeypatch, text, clusters, expected):
    spans = _mention_spans (text, clusters)
    monkeypatch.setattr (
        resolver,
        "_get_model",
        lambda: FakeLingMess (FakePrediction (clusters, spans)),
    )

    result = resolver.resolve (text)

    assert result.resolved_text == expected
    assert result.clusters == clusters
