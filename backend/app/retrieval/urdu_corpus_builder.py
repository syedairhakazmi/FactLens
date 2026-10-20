import os
import csv
import json
import re
import pandas as pd
from app.retrieval.urdu_preprocessor import normalize_urdu_text

def chunk_text (text, max_words = 120, overlap = 20):
    words = text.split ()
    if len (words) <= max_words:
        return [text]

    chunks = []
    step = max_words - overlap
    i = 0
    while i < len (words):
        chunk_words = words [i : i + max_words]
        if len (chunk_words) >= 15:
            chunks.append (" ".join (chunk_words))
        i = i + step
    return chunks

def load_urdu_news_augmented (dataset_folder, max_passages = 2000):
    passages = []
    news_dir = os.path.join (dataset_folder, "Urdu-News-Augmented-Dataset", "extracted", "Urdu News Augmented Dataset", "3.Corpus_Mixed")
    if not os.path.exists (news_dir):
        news_dir = os.path.join (dataset_folder, "Urdu-News-Augmented-Dataset", "extracted", "Urdu News Augmented Dataset", "1.Corpus")

    if not os.path.exists (news_dir):
        return passages

    for root, _, files in os.walk (news_dir):
        for f in files:
            if f.endswith (".txt"):
                file_path = os.path.join (root, f)
                try:
                    with open (file_path, "r", encoding = "utf-8", errors = "ignore") as fp:
                        raw = fp.read ().strip ()
                    normalized = normalize_urdu_text (raw)
                    if len (normalized) > 30:
                        is_fake = False
                        if ".fake" in f.lower () or "fake" in root.lower ():
                            is_fake = True
                        label_tag = "Real"
                        if is_fake:
                            label_tag = "Fake"
                        chunks = chunk_text (normalized, max_words = 120)
                        chunk_idx = 0
                        for chunk in chunks:
                            passages.append ({
                                "id": "una_" + os.path.splitext (f) [0] + "_" + str (chunk_idx),
                                "title": "Urdu News (" + label_tag + ") - " + f,
                                "source": "Urdu-News-Augmented (Maaz Amjad)",
                                "text": chunk,
                            })
                            chunk_idx = chunk_idx + 1
                            if len (passages) >= max_passages:
                                return passages
                except Exception:
                    continue
    return passages

def load_urdufactcheck (dataset_folder, max_passages = 5000):
    passages = []
    ufc_base = os.path.join (dataset_folder, "UrduFactCheck", "datasets", "raw")
    if not os.path.exists (ufc_base):
        return passages

    # 1. Claims: bingcheck data_full.jsonl
    bing_path = os.path.join (ufc_base, "claims", "bingcheck", "data_full.jsonl")
    if not os.path.exists (bing_path):
        bing_path = os.path.join (ufc_base, "claims", "bingcheck", "bingcheck.jsonl")
    if os.path.exists (bing_path):
        with open (bing_path, "r", encoding = "utf-8", errors = "ignore") as fp:
            line_idx = 0
            for line in fp:
                line = line.strip ()
                if len (line) > 0:
                    try:
                        entry = json.loads (line)
                        claim_text = normalize_urdu_text (entry.get ("claim", ""))
                        label = entry.get ("label", "Verified")
                        if len (claim_text) > 15:
                            passages.append ({
                                "id": "ufc_bing_" + str (line_idx),
                                "title": "UrduFactCheck Claim (" + str (label) + ")",
                                "source": "UrduFactCheck (MBZUAI)",
                                "text": claim_text,
                            })
                    except Exception:
                        pass
                line_idx = line_idx + 1

    # 2. Claims: factcheckbench
    fcb_path = os.path.join (ufc_base, "claims", "factcheckbench", "claim_factuality.jsonl")
    if os.path.exists (fcb_path):
        with open (fcb_path, "r", encoding = "utf-8", errors = "ignore") as fp:
            line_idx = 0
            for line in fp:
                line = line.strip ()
                if len (line) > 0:
                    try:
                        entry = json.loads (line)
                        claim_text = normalize_urdu_text (entry.get ("claim", ""))
                        revised = normalize_urdu_text (entry.get ("revised_claim", ""))
                        full_text = claim_text
                        if len (revised) > 0 and revised != claim_text:
                            full_text = claim_text + " (تصحیح: " + revised + ")"
                        if len (full_text) > 15:
                            passages.append ({
                                "id": "ufc_fcb_" + str (line_idx),
                                "title": "FactCheckBench (" + str (entry.get ("label", "")) + ")",
                                "source": "UrduFactCheck (MBZUAI)",
                                "text": full_text,
                            })
                    except Exception:
                        pass
                line_idx = line_idx + 1

    # 3. QA: simpleqa
    sq_path = os.path.join (ufc_base, "qa", "simpleqa", "simpleqa.json")
    if os.path.exists (sq_path):
        try:
            with open (sq_path, "r", encoding = "utf-8", errors = "ignore") as fp:
                sq_data = json.load (fp)
            idx = 0
            for item in sq_data:
                q = normalize_urdu_text (item.get ("question", ""))
                a = normalize_urdu_text (item.get ("answer", ""))
                if len (q) > 0 and len (a) > 0:
                    fact_statement = q + " جواب: " + a
                    item_id = str (item.get ("id", idx))
                    passages.append ({
                        "id": "ufc_sq_" + str (idx),
                        "title": "SimpleQA Fact #" + item_id,
                        "source": "UrduFactCheck (SimpleQA)",
                        "text": fact_statement,
                    })
                idx = idx + 1
        except Exception:
            pass

    # 4. QA: freshqa
    fq_path = os.path.join (ufc_base, "qa", "freshqa", "freshqa.json")
    if os.path.exists (fq_path):
        try:
            with open (fq_path, "r", encoding = "utf-8", errors = "ignore") as fp:
                fq_data = json.load (fp)
            idx = 0
            for item in fq_data:
                q = normalize_urdu_text (item.get ("question", ""))
                ans = normalize_urdu_text (item.get ("answer_0", ""))
                if len (q) > 0 and len (ans) > 0:
                    fact_type = str (item.get ("fact_type", "General"))
                    passages.append ({
                        "id": "ufc_fq_" + str (idx),
                        "title": "FreshQA Fact - " + fact_type,
                        "source": "UrduFactCheck (FreshQA)",
                        "text": q + " جواب: " + ans,
                    })
                idx = idx + 1
        except Exception:
            pass

    return passages [:max_passages]

def load_ulnc_corpus (dataset_folder, max_passages = 5000):
    passages = []
    ulnc_base = os.path.join (dataset_folder, "Urdu-Large-language-dataset")
    if not os.path.exists (ulnc_base):
        return passages

    # 1. Notri-Fact_Real_Unreal_Urdu_NEWS.xlsx
    notri_path = os.path.join (ulnc_base, "Notri-Fact_Real_Unreal_Urdu_NEWS.xlsx")
    if os.path.exists (notri_path):
        try:
            df = pd.read_excel (notri_path)
            row_idx = 0
            for _, row in df.iterrows ():
                headline = normalize_urdu_text (str (row.get ("Headline", "")))
                body = normalize_urdu_text (str (row.get ("News_Text", "")))
                category = str (row.get ("Category", "News"))
                label = str (row.get ("Label", ""))

                combined = body
                if len (headline) > 0 and headline != body:
                    combined = headline + ". " + body
                if len (combined) > 30:
                    chunks = chunk_text (combined, max_words = 120)
                    c_idx = 0
                    for chunk in chunks [:2]:
                        title_str = "ULNC " + category + " (" + label + ")"
                        if len (headline) > 0:
                            title_str = headline [:60]
                        passages.append ({
                            "id": "ulnc_notri_" + str (row_idx) + "_" + str (c_idx),
                            "title": title_str,
                            "source": "Urdu-Large-language-dataset (ULNC)",
                            "text": chunk,
                        })
                        c_idx = c_idx + 1
                        if len (passages) >= max_passages:
                            return passages
                row_idx = row_idx + 1
        except Exception:
            pass

    # 2. Labeled_Urdu_News.xlsx
    labeled_path = os.path.join (ulnc_base, "Labeled_Urdu_News.xlsx")
    if os.path.exists (labeled_path) and len (passages) < max_passages:
        try:
            df_lab = pd.read_excel (labeled_path)
            row_idx = 0
            for _, row in df_lab.iterrows ():
                news_txt = normalize_urdu_text (str (row.get ("news", "")))
                label = str (row.get ("label", ""))
                if len (news_txt) > 30:
                    chunks = chunk_text (news_txt, max_words = 120)
                    c_idx = 0
                    for chunk in chunks [:1]:
                        passages.append ({
                            "id": "ulnc_lab_" + str (row_idx) + "_" + str (c_idx),
                            "title": "ULNC Labeled News (" + label + ")",
                            "source": "Urdu-Large-language-dataset (ULNC)",
                            "text": chunk,
                        })
                        c_idx = c_idx + 1
                        if len (passages) >= max_passages:
                            return passages
                row_idx = row_idx + 1
        except Exception:
            pass

    return passages [:max_passages]

def load_ax_to_grind_corpus (dataset_folder, max_passages = 5000):
    passages = []
    ax_csv = os.path.join (dataset_folder, "Ax-to-Grind-Urdu", "Combined .csv")
    if not os.path.exists (ax_csv):
        ax_csv = os.path.join (dataset_folder, "Urdu-Large-language-dataset", "Ax-to-Grind-Urdu-Dataset.csv")

    if not os.path.exists (ax_csv):
        return passages

    try:
        with open (ax_csv, "r", encoding = "utf-8", errors = "ignore") as fp:
            reader = csv.reader (fp)
            next (reader, None)
            idx = 0
            for row in reader:
                if len (row) >= 2:
                    news_item = normalize_urdu_text (row [1])
                    label = "News"
                    if len (row) > 2:
                        label = row [2]
                    if len (news_item) > 30:
                        chunks = chunk_text (news_item, max_words = 120)
                        c_idx = 0
                        for chunk in chunks [:2]:
                            passages.append ({
                                "id": "ax_urdu_" + str (idx) + "_" + str (c_idx),
                                "title": "Ax-to-Grind Urdu (" + label + ")",
                                "source": "Ax-to-Grind-Urdu",
                                "text": chunk,
                            })
                            c_idx = c_idx + 1
                            if len (passages) >= max_passages:
                                return passages
                idx = idx + 1
    except Exception:
        pass

    return passages [:max_passages]

def synthesize_urdu_corpus (dataset_folder, output_file):
    una_passages = load_urdu_news_augmented (dataset_folder, max_passages = 2500)
    ufc_passages = load_urdufactcheck (dataset_folder, max_passages = 5500)
    ulnc_passages = load_ulnc_corpus (dataset_folder, max_passages = 4000)
    ax_passages = load_ax_to_grind_corpus (dataset_folder, max_passages = 4000)

    combined = una_passages + ufc_passages + ulnc_passages + ax_passages
    seen = set ()
    unique_passages = []
    for p in combined:
        text_key = re.sub (r"\s+", "", p ["text"]) [:80]
        if len (text_key) > 0 and text_key not in seen:
            seen.add (text_key)
            unique_passages.append (p)

    out_folder = os.path.dirname (output_file)
    if len (out_folder) > 0:
        os.makedirs (out_folder, exist_ok = True)

    with open (output_file, "w", encoding = "utf-8") as fp:
        for item in unique_passages:
            line_str = json.dumps (item, ensure_ascii = False)
            fp.write (line_str + "\n")

    return unique_passages

if __name__ == "__main__":
    base_datasets = r"d:\Desktop\FYP\Mid 1\urdu_datasets"
    output_path = r"d:\Desktop\FYP\Mid 1\factlens_repo_starter\backend\data\corpus_urdu.jsonl"
    synthesize_urdu_corpus (base_datasets, output_path)
