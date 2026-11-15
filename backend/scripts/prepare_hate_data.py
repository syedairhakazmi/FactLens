"""
Prepare hate-speech datasets for FactLens (Iteration 3).

Every dataset is converted to ONE schema and written as JSONL:
    id, text, label, target, lang, script, source, split
    label  -> "hate" | "offensive" | "normal"      (matches the week plan)
    target -> targeted group(s), "" if none/unknown
    script -> "latin" | "urdu"   (Roman Urdu is "latin" + lang "ur-roman")

Usage (run from the backend/ folder so the Urdu normalizer can be imported):
    python scripts/prepare_hate_data.py hatexplain  --src data/raw/hatexplain.json --split-file data/raw/post_id_divisions.json
    python scripts/prepare_hate_data.py hatecheck   --src data/raw/test_suite_cases.csv
    python scripts/prepare_hate_data.py urdu        --src data/raw/urdu.csv --text-col Tweet --label-col Tag --label-map "0=normal,1=hate" --source adnan_urdu_hate
    # Roman Urdu (RUHSOLD): headerless TSVs with official splits. Task 2 = 5 fine labels
    python scripts/prepare_hate_data.py urdu --no-header --source ruhsold --src "train=data/raw/ruhsold/task_2_train.tsv,test=data/raw/ruhsold/task_2_test.tsv" --label-map "0=offensive,1=normal,2=hate,3=hate,4=offensive"
    python scripts/prepare_hate_data.py report      --src data/hate/hatexplain.jsonl

Output goes to data/hate/<name>.jsonl (change with --out).
"""
import argparse
import csv
import json
import os
import random
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
try:
    from app.retrieval.urdu_preprocessor import normalize_urdu_text
except Exception:  # fallback so the script still runs outside the repo
    def normalize_urdu_text(text):
        return re.sub(r"\s+", " ", text).strip()

URL_RE = re.compile(r"https?://\S+|www\.\S+")
MENTION_RE = re.compile(r"@\w+")
RT_RE = re.compile(r"^\s*RT\b[:\s]*", re.I)
HASHTAG_RE = re.compile(r"#(\w+)")
REPEAT_RE = re.compile(r"(.)\1{3,}")            # sooooo -> sooo
SPACE_RE = re.compile(r"\s+")
URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
LABELS = ("hate", "offensive", "normal")


# ---------- generic cleaning ----------
def script_of(text):
    """'urdu' if most letters are Arabic-script, else 'latin'."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "latin"
    arabic = sum(1 for c in letters if "\u0600" <= c <= "\u06ff" or "\u0750" <= c <= "\u077f")
    return "urdu" if arabic / len(letters) > 0.5 else "latin"


def clean_text(text, urdu=False):
    text = RT_RE.sub("", text or "")
    text = URL_RE.sub(" <url> ", text)
    text = MENTION_RE.sub(" <user> ", text)
    text = HASHTAG_RE.sub(r"\1", text)          # keep the word, drop '#'
    text = REPEAT_RE.sub(r"\1\1\1", text)
    if urdu:
        text = normalize_urdu_text(text).translate(URDU_DIGITS)
    return SPACE_RE.sub(" ", text).strip()


def write_jsonl(rows, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {out_path}")


def dedupe(rows):
    seen, out = set(), []
    for r in rows:
        key = r["text"].lower()
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def stratified_split(rows, seed=42, ratios=(0.8, 0.1, 0.1)):
    """80/10/10 split that keeps label proportions the same in each split."""
    rng = random.Random(seed)
    by_label = {}
    for r in rows:
        by_label.setdefault(r["label"], []).append(r)
    for group in by_label.values():
        rng.shuffle(group)
        n = len(group)
        a, b = int(n * ratios[0]), int(n * (ratios[0] + ratios[1]))
        for i, r in enumerate(group):
            r["split"] = "train" if i < a else ("val" if i < b else "test")
    return rows

def near_dup_groups(texts, threshold=0.9):
    """Group id per text. Texts that are near-copies of each other (char n-gram cosine >= threshold)
    get the same id (connected components), so they can be kept together in one split."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    X = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2).fit_transform(texts)
    parent = list(range(len(texts)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for start in range(0, X.shape[0], 500):
        sim = (X[start:start + 500] @ X.T).tocoo()
        for i, j, v in zip(sim.row, sim.col, sim.data):
            i += start
            if j > i and v >= threshold:
                parent[find(i)] = find(j)
    return [find(i) for i in range(len(texts))]


def group_split(rows, threshold, source, seed=42):
    """Stratified 80/10/10 split where near-duplicate rows ALWAYS land in the same split.
    Groups whose rows disagree on the label are written to a review CSV."""
    gids = near_dup_groups([r["text"] for r in rows], threshold)
    groups = {}
    for r, g in zip(rows, gids):
        r["group"] = f"g{g}"
        groups.setdefault(r["group"], []).append(r)
    units, conflicts = [], []
    for gid, members in groups.items():
        counts = Counter(m["label"] for m in members)
        if len(counts) > 1:
            conflicts.extend(members)
        units.append({"gid": gid, "label": counts.most_common(1)[0][0]})   # majority label
    stratified_split(units, seed=seed)
    split_of = {u["gid"]: u["split"] for u in units}
    for r in rows:
        r["split"] = split_of[r["group"]]
    big = sum(1 for m in groups.values() if len(m) > 1)
    print(f"near-duplicates: {big} groups with >1 row, {len(rows) - len(groups)} extra rows kept together")
    if conflicts:
        path = os.path.join("data", "hate", f"{source}_label_conflicts.csv")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["group", "id", "label", "text"])
            for m in sorted(conflicts, key=lambda m: m["group"]):
                w.writerow([m["group"], m["id"], m["label"], m["text"]])
        print(f"{len(conflicts)} rows in near-duplicate groups with DIFFERENT labels -> {path} (please review)")
    return rows

# ---------- HateXplain ----------
HX_LABELS = {0: "hate", 1: "normal", 2: "offensive"}      # HF label ids
HX_LABELS_STR = {"hatespeech": "hate", "normal": "normal", "offensive": "offensive"}


def _hx_label(x):
    if isinstance(x, int):
        return HX_LABELS[x]
    return HX_LABELS_STR[x]


def convert_hatexplain(src, split_file=None):
    """Accepts the official dataset.json (dict keyed by post id) or a list of HF records."""
    with open(src, encoding="utf-8") as f:
        data = json.load(f)
    items = data.items() if isinstance(data, dict) else ((d.get("id") or d.get("post_id"), d) for d in data)
    divisions = {}
    if split_file:
        with open(split_file, encoding="utf-8") as f:
            for split_name, ids in json.load(f).items():
                for pid in ids:
                    divisions[pid] = {"val": "val"}.get(split_name, split_name)

    rows, dropped_no_majority = [], 0
    for pid, rec in items:
        annotators = rec["annotators"]
        if isinstance(annotators, dict):               # HF columnar form
            labels = [_hx_label(x) for x in annotators["label"]]
            targets = annotators["target"]
        else:                                          # original form: list of dicts
            labels = [_hx_label(a["label"]) for a in annotators]
            targets = [a["target"] for a in annotators]
        counts = Counter(labels).most_common()
        if len(counts) > 1 and counts[0][1] == counts[1][1]:
            dropped_no_majority += 1                   # 3 annotators, 3 different labels
            continue
        label = counts[0][0]
        # targets: keep groups named by >= 2 annotators, never for "normal"
        tcount = Counter(t for ts in targets for t in set(ts) if t and t != "None")
        tlist = sorted(t for t, c in tcount.items() if c >= 2) if label != "normal" else []
        text = clean_text(" ".join(rec["post_tokens"]))
        if len(text.split()) < 2:
            continue
        rows.append({
            "id": str(pid), "text": text, "label": label, "target": "|".join(tlist),
            "lang": "en", "script": "latin", "source": "hatexplain",
            "split": divisions.get(pid, ""),
        })
    print(f"hatexplain: dropped {dropped_no_majority} posts with no annotator majority")
    rows = dedupe(rows)
    if not divisions:
        rows = stratified_split(rows)
    return rows


# ---------- HateCheck (evaluation only) ----------
def convert_hatecheck(src):
    rows = []
    with open(src, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({
                "id": "hatecheck_" + r["case_id"],
                "text": clean_text(r["test_case"]),
                "label": "hate" if r["label_gold"] == "hateful" else "normal",
                "target": r.get("target_ident", "") or "",
                "functionality": r["functionality"],
                "lang": "en", "script": "latin", "source": "hatecheck", "split": "test",
            })
    return rows


# ---------- Urdu / Roman Urdu (csv or xlsx) ----------
def read_table(path, no_header=False):
    """csv / tsv / xlsx -> list of dicts. --no-header files get keys 'text' and 'label'
    (the label is the LAST tab-separated field, so tabs inside the text are safe)."""
    if path.endswith((".xlsx", ".xls")):
        import pandas as pd
        return pd.read_excel(path).to_dict("records")
    if no_header:
        rows = []
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                line = line.rstrip("\n")
                if line:
                    text, _, label = line.rpartition("\t")
                    rows.append({"text": text, "label": label})
        return rows
    delim = "\t" if path.endswith(".tsv") else ","
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delim, quoting=csv.QUOTE_NONE if delim == "\t" else csv.QUOTE_MINIMAL))


def parse_label_map(spec):
    return {k.strip(): v.strip() for k, v in (p.split("=") for p in spec.split(","))}


def parse_sources(spec):
    """'data.csv' -> {'': 'data.csv'};  'train=a.tsv,val=b.tsv,test=c.tsv' -> official splits."""
    if "=" not in spec:
        return {"": spec}
    return {k.strip(): v.strip() for k, v in (p.split("=", 1) for p in spec.split(","))}



def convert_urdu(src, text_col, label_col, label_map, source, min_words=3, no_header=False, near_dup=0.9):
    rows, skipped = [], Counter()
    sources = parse_sources(src)
    records = []
    for split_name, path in sources.items():
        for rec in read_table(path, no_header):
            records.append((split_name, rec))
    for i, (split_name, rec) in enumerate(records):
        raw = str(rec.get(text_col, "") or "")
        raw_label = str(rec.get(label_col, "")).strip()
        if raw_label not in label_map:
            skipped["unmapped label"] += 1
            continue
        script = script_of(raw)
        text = clean_text(raw, urdu=(script == "urdu"))
        if len(text.split()) < min_words:
            skipped["too short"] += 1
            continue
        rows.append({
            "id": f"{source}_{i}", "text": text, "label": label_map[raw_label], "target": "",
            "lang": "ur" if script == "urdu" else "ur-roman", "script": script,
            "source": source, "split": split_name,
        })
    before = len(rows)
    rows = dedupe(rows)          # keeps the FIRST copy, so a train/test leak is removed from test
    skipped["duplicates"] = before - len(rows)
    print("urdu: skipped", dict(skipped))
    if "" not in sources:
        # official splits given: carve a validation set out of train if none was supplied
        if "val" not in sources:
            train = [r for r in rows if r["split"] == "train"]
            carved = stratified_split([dict(r, split="") for r in train], seed=42, ratios=(0.9, 0.1, 0.0))
            ids = {r["id"]: r["split"] for r in carved}
            for r in rows:
                if r["split"] == "train":
                    r["split"] = ids[r["id"]]
        return rows
    if near_dup:
        return group_split(rows, near_dup, source)
    return stratified_split(rows)


# ---------- report ----------
def report(path):
    rows = [json.loads(l) for l in open(path, encoding="utf-8")]
    print(f"{path}: {len(rows)} rows")
    for key in ("label", "split", "script", "lang"):
        print(f"  {key}:", dict(Counter(r[key] for r in rows)))
    tc = Counter(t for r in rows for t in r["target"].split("|") if t)
    if tc:
        print("  top targets:", tc.most_common(10))
    lens = sorted(len(r["text"].split()) for r in rows)
    print(f"  words/text: median {lens[len(lens)//2]}, p95 {lens[int(len(lens)*0.95)]}, max {lens[-1]}")
    bad = [r for r in rows if r["label"] not in LABELS]
    print("  rows with unknown label:", len(bad))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("kind", choices=["hatexplain", "hatecheck", "urdu", "report"])
    p.add_argument("--src", required=True)
    p.add_argument("--out")
    p.add_argument("--split-file")
    p.add_argument("--text-col", default="text")
    p.add_argument("--label-col", default="label")
    p.add_argument("--label-map", default="0=normal,1=hate")
    p.add_argument("--source", default="urdu")
    p.add_argument("--near-dup", type=float, default=0.9,help="similarity (0-1) above which texts count as near-duplicates and stay in one split; 0 = off")
    p.add_argument("--no-header", action="store_true", help="file has no header row: 'text<TAB>label'")
    a = p.parse_args()

    if a.kind == "report":
        return report(a.src)
    if a.kind == "hatexplain":
        rows = convert_hatexplain(a.src, a.split_file)
    elif a.kind == "hatecheck":
        rows = convert_hatecheck(a.src)
    else:
        rows = convert_urdu(a.src, a.text_col, a.label_col, parse_label_map(a.label_map), a.source, no_header=a.no_header, near_dup=a.near_dup)
    out = a.out or os.path.join("data", "hate", (a.source if a.kind == "urdu" else a.kind) + ".jsonl")
    write_jsonl(rows, out)
    report(out)


if __name__ == "__main__":
    main()