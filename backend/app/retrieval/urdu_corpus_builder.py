import os
import csv
import json
import re
import pandas as pd
from app.retrieval.urdu_preprocessor import normalize_urdu_text

def chunk_text(text: str, max_words: int = 120, overlap: int = 20) -> list[str]:
    """
    Split longer text into passage-sized chunks with slight overlap for optimal retrieval.
    """
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    step = max_words - overlap
    for i in range(0, len(words), step):
        chunk_words = words[i : i + max_words]
        if len(chunk_words) >= 15:  # skip tiny trailing fragments
            chunks.append(" ".join(chunk_words))
    return chunks

def load_urdu_news_augmented(dataset_folder: str, max_passages: int = 2000) -> list[dict]:
    """
    Load articles from Dr. Maaz Amjad's Urdu-News-Augmented-Dataset (BBC Urdu, Jang, Express).
    """
    passages = []
    news_dir = os.path.join(dataset_folder, "Urdu-News-Augmented-Dataset", "extracted", "Urdu News Augmented Dataset", "3.Corpus_Mixed")
    if not os.path.exists(news_dir):
        # fallback to 1.Corpus if Corpus_Mixed not found
        news_dir = os.path.join(dataset_folder, "Urdu-News-Augmented-Dataset", "extracted", "Urdu News Augmented Dataset", "1.Corpus")

    if not os.path.exists(news_dir):
        return passages

    for root, _, files in os.walk(news_dir):
        for f in files:
            if f.endswith(".txt"):
                file_path = os.path.join(root, f)
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
                        raw = fp.read().strip()
                    normalized = normalize_urdu_text(raw)
                    if len(normalized) > 30:
                        is_fake = ".fake" in f.lower() or "fake" in root.lower()
                        label_tag = "Fake" if is_fake else "Real"
                        chunks = chunk_text(normalized, max_words=120)
                        for idx, chunk in enumerate(chunks):
                            passages.append({
                                "id": f"una_{os.path.splitext(f)[0]}_{idx}",
                                "title": f"Urdu News ({label_tag}) - {f}",
                                "source": "Urdu-News-Augmented (Maaz Amjad)",
                                "text": chunk,
                            })
                            if len(passages) >= max_passages:
                                return passages
                except Exception:
                    continue
    return passages

def load_urdufactcheck(dataset_folder: str, max_passages: int = 5000) -> list[dict]:
    """
    Load claims and QA pairs from MBZUAI UrduFactCheck (bingcheck, factcheckbench, simpleqa, freshqa).
    """
    passages = []
    ufc_base = os.path.join(dataset_folder, "UrduFactCheck", "datasets", "raw")
    if not os.path.exists(ufc_base):
        return passages

    # 1. Claims: bingcheck data_full.jsonl
    bing_path = os.path.join(ufc_base, "claims", "bingcheck", "data_full.jsonl")
    if not os.path.exists(bing_path):
        bing_path = os.path.join(ufc_base, "claims", "bingcheck", "bingcheck.jsonl")
    if os.path.exists(bing_path):
        with open(bing_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line_idx, line in enumerate(fp):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    claim_text = normalize_urdu_text(entry.get("claim", ""))
                    label = entry.get("label", "Verified")
                    if len(claim_text) > 15:
                        passages.append({
                            "id": f"ufc_bing_{line_idx}",
                            "title": f"UrduFactCheck Claim ({label})",
                            "source": "UrduFactCheck (MBZUAI)",
                            "text": claim_text,
                        })
                except Exception:
                    continue

    # 2. Claims: factcheckbench
    fcb_path = os.path.join(ufc_base, "claims", "factcheckbench", "claim_factuality.jsonl")
    if os.path.exists(fcb_path):
        with open(fcb_path, "r", encoding="utf-8", errors="ignore") as fp:
            for line_idx, line in enumerate(fp):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    claim_text = normalize_urdu_text(entry.get("claim", ""))
                    revised = normalize_urdu_text(entry.get("revised_claim", ""))
                    full_text = claim_text
                    if revised and revised != claim_text:
                        full_text = f"{claim_text} (تصحیح: {revised})"
                    if len(full_text) > 15:
                        passages.append({
                            "id": f"ufc_fcb_{line_idx}",
                            "title": f"FactCheckBench ({entry.get('label', '')})",
                            "source": "UrduFactCheck (MBZUAI)",
                            "text": full_text,
                        })
                except Exception:
                    continue

    # 3. QA: simpleqa
    sq_path = os.path.join(ufc_base, "qa", "simpleqa", "simpleqa.json")
    if os.path.exists(sq_path):
        try:
            with open(sq_path, "r", encoding="utf-8", errors="ignore") as fp:
                sq_data = json.load(fp)
            for idx, item in enumerate(sq_data):
                q = normalize_urdu_text(item.get("question", ""))
                a = normalize_urdu_text(item.get("answer", ""))
                if q and a:
                    fact_statement = f"{q} جواب: {a}"
                    passages.append({
                        "id": f"ufc_sq_{idx}",
                        "title": f"SimpleQA Fact #{item.get('id', idx)}",
                        "source": "UrduFactCheck (SimpleQA)",
                        "text": fact_statement,
                    })
        except Exception:
            pass

    # 4. QA: freshqa
    fq_path = os.path.join(ufc_base, "qa", "freshqa", "freshqa.json")
    if os.path.exists(fq_path):
        try:
            with open(fq_path, "r", encoding="utf-8", errors="ignore") as fp:
                fq_data = json.load(fp)
            for idx, item in enumerate(fq_data):
                q = normalize_urdu_text(item.get("question", ""))
                ans = normalize_urdu_text(item.get("answer_0", ""))
                if q and ans:
                    passages.append({
                        "id": f"ufc_fq_{idx}",
                        "title": f"FreshQA Fact - {item.get('fact_type', 'General')}",
                        "source": "UrduFactCheck (FreshQA)",
                        "text": f"{q} جواب: {ans}",
                    })
        except Exception:
            pass

    return passages[:max_passages]

def load_ulnc_corpus(dataset_folder: str, max_passages: int = 5000) -> list[dict]:
    """
    Load broad news and topical knowledge from Urdu-Large-language-dataset (Notri-Fact & Labeled_Urdu_News).
    """
    passages = []
    ulnc_base = os.path.join(dataset_folder, "Urdu-Large-language-dataset")
    if not os.path.exists(ulnc_base):
        return passages

    # 1. Notri-Fact_Real_Unreal_Urdu_NEWS.xlsx
    notri_path = os.path.join(ulnc_base, "Notri-Fact_Real_Unreal_Urdu_NEWS.xlsx")
    if os.path.exists(notri_path):
        try:
            df = pd.read_excel(notri_path)
            for idx, row in df.iterrows():
                headline = normalize_urdu_text(str(row.get("Headline", "")))
                body = normalize_urdu_text(str(row.get("News_Text", "")))
                category = str(row.get("Category", "News"))
                label = str(row.get("Label", ""))

                combined = f"{headline}. {body}" if headline and headline != body else body
                if len(combined) > 30:
                    chunks = chunk_text(combined, max_words=120)
                    for c_idx, chunk in enumerate(chunks[:2]):  # take first 2 chunks
                        passages.append({
                            "id": f"ulnc_notri_{idx}_{c_idx}",
                            "title": headline[:60] if headline else f"ULNC {category} ({label})",
                            "source": "Urdu-Large-language-dataset (ULNC)",
                            "text": chunk,
                        })
                        if len(passages) >= max_passages:
                            return passages
        except Exception as e:
            print(f"Error reading Notri-Fact: {e}")

    # 2. Labeled_Urdu_News.xlsx
    labeled_path = os.path.join(ulnc_base, "Labeled_Urdu_News.xlsx")
    if os.path.exists(labeled_path) and len(passages) < max_passages:
        try:
            df_lab = pd.read_excel(labeled_path)
            for idx, row in df_lab.iterrows():
                news_txt = normalize_urdu_text(str(row.get("news", "")))
                label = str(row.get("label", ""))
                if len(news_txt) > 30:
                    chunks = chunk_text(news_txt, max_words=120)
                    for c_idx, chunk in enumerate(chunks[:1]):
                        passages.append({
                            "id": f"ulnc_lab_{idx}_{c_idx}",
                            "title": f"ULNC Labeled News ({label})",
                            "source": "Urdu-Large-language-dataset (ULNC)",
                            "text": chunk,
                        })
                        if len(passages) >= max_passages:
                            return passages
        except Exception as e:
            print(f"Error reading Labeled_Urdu_News: {e}")

    return passages[:max_passages]

def load_ax_to_grind_corpus(dataset_folder: str, max_passages: int = 5000) -> list[dict]:
    """
    Load verified articles across 15 domains from Ax-to-Grind-Urdu dataset.
    """
    passages = []
    ax_csv = os.path.join(dataset_folder, "Ax-to-Grind-Urdu", "Combined .csv")
    if not os.path.exists(ax_csv):
        ax_csv = os.path.join(dataset_folder, "Urdu-Large-language-dataset", "Ax-to-Grind-Urdu-Dataset.csv")

    if not os.path.exists(ax_csv):
        return passages

    try:
        with open(ax_csv, "r", encoding="utf-8", errors="ignore") as fp:
            reader = csv.reader(fp)
            header = next(reader, None)
            for idx, row in enumerate(reader):
                if len(row) >= 2:
                    news_item = normalize_urdu_text(row[1])
                    label = row[2] if len(row) > 2 else "News"
                    if len(news_item) > 30:
                        chunks = chunk_text(news_item, max_words=120)
                        for c_idx, chunk in enumerate(chunks[:2]):
                            passages.append({
                                "id": f"ax_urdu_{idx}_{c_idx}",
                                "title": f"Ax-to-Grind Urdu ({label})",
                                "source": "Ax-to-Grind-Urdu",
                                "text": chunk,
                            })
                            if len(passages) >= max_passages:
                                return passages
    except Exception as e:
        print(f"Error reading Ax-to-Grind: {e}")

    return passages[:max_passages]

def synthesize_urdu_corpus(
    dataset_folder: str,
    output_file: str,
    target_count: int = 13500,
) -> list[dict]:
    """
    Synthesize and balance a 13,500+ passage Urdu knowledge corpus from all 4 datasets.
    Deduplicates and cleans passages.
    """
    print(f"Synthesizing Urdu corpus from: {dataset_folder}")

    # Allocate target quotas across the 4 sources
    una_passages = load_urdu_news_augmented(dataset_folder, max_passages=2500)
    print(f"  [1/4] Urdu-News-Augmented-Dataset: {len(una_passages)} passages loaded.")

    ufc_passages = load_urdufactcheck(dataset_folder, max_passages=5500)
    print(f"  [2/4] UrduFactCheck: {len(ufc_passages)} passages loaded.")

    ulnc_passages = load_ulnc_corpus(dataset_folder, max_passages=4000)
    print(f"  [3/4] Urdu-Large-language-dataset: {len(ulnc_passages)} passages loaded.")

    ax_passages = load_ax_to_grind_corpus(dataset_folder, max_passages=4000)
    print(f"  [4/4] Ax-to-Grind-Urdu: {len(ax_passages)} passages loaded.")

    combined = una_passages + ufc_passages + ulnc_passages + ax_passages
    print(f"  Total raw passages collected: {len(combined)}")

    # Deduplication
    seen = set()
    unique_passages = []
    for p in combined:
        # compute simple character sequence key
        text_key = re.sub(r"\s+", "", p["text"])[:80]
        if text_key and text_key not in seen:
            seen.add(text_key)
            unique_passages.append(p)

    print(f"  Total unique deduplicated Urdu passages: {len(unique_passages)}")

    # Save to jsonl
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as fp:
        for item in unique_passages:
            fp.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"  Saved {len(unique_passages)} passages to: {output_file}")
    return unique_passages

if __name__ == "__main__":
    base_datasets = r"d:\Desktop\FYP\Mid 1\urdu_datasets"
    output_path = r"d:\Desktop\FYP\Mid 1\factlens_repo_starter\backend\data\corpus_urdu.jsonl"
    synthesize_urdu_corpus(base_datasets, output_path)
