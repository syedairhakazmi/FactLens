"""
Quick quality check for a labelled text dataset (xlsx / csv).
Usage (from backend/):
    python scripts/check_dataset.py data/raw/hs_urdu.xlsx            # text = col 1, label = col 2
    python scripts/check_dataset.py data/raw/hs_urdu.xlsx 0.9         # near-duplicate threshold
Prints: size, columns, label counts, exact duplicates, NEAR-duplicates (same text with small edits),
and how many near-duplicate pairs have DIFFERENT labels.
"""
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

path = sys.argv[1]
thr = float(sys.argv[2]) if len(sys.argv) > 2 else 0.9
df = pd.read_excel(path) if path.endswith(("xlsx", "xls")) else pd.read_csv(path)
text, label = df.columns[0], df.columns[1]
df[text] = df[text].astype(str)
print("rows:", len(df), "| columns:", df.columns.tolist())
print(df[label].value_counts().to_string())
print("exact duplicate texts:", df[text].duplicated().sum())

X = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2).fit_transform(df[text])
pairs = []
for s in range(0, X.shape[0], 500):
    sim = (X[s:s + 500] @ X.T).tocoo()
    for i, j, v in zip(sim.row, sim.col, sim.data):
        i += s
        if j > i and v >= thr:
            pairs.append((i, j, v))
rows_in_pairs = {k for p in pairs for k in p[:2]}
diff = [p for p in pairs if df[label].iloc[p[0]] != df[label].iloc[p[1]]]
print(f"near-duplicate pairs (cosine >= {thr}):", len(pairs), "| rows involved:", len(rows_in_pairs))
print("  ...of which have DIFFERENT labels:", len(diff))
for i, j, v in pairs[:5]:
    print(f"  excel rows {i+2} & {j+2}  sim={v:.2f}  labels {df[label].iloc[i]}/{df[label].iloc[j]}")