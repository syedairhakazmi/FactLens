"""
Make the prepared hate-speech JSONL files fully bilingual (English + Urdu).

Input : a JSONL file written by prepare_hate_data.py
Output: same rows plus these extra fields
    label_en, label_ur            bilingual labels (always filled)
    target_en, target_ur          bilingual target groups (Urdu falls back to English if not in the table)
    text_en, text_ur              the text in BOTH languages (needs --translate)
    text_original_lang            which side is the human-written original ("en", "ur" or "ur-roman")
    translation_model             model used for the machine-translated side
    quality_flag                  "" or a warning, e.g. "roman_urdu_source_unreliable"

The ORIGINAL `text` column is never changed. Treat it as gold. Translated text is machine output
and must not be used for evaluation without a human check.

Usage (run from backend/):
    # 1) labels only, instant, no model needed
    python scripts/make_bilingual.py --src data/hate/hs_urdu_clean.jsonl

    # 2) add translations. ALWAYS try a small run first
    python scripts/make_bilingual.py --src data/hate/hs_urdu_clean.jsonl --translate --limit 20
    # 3) full run (resumes automatically if interrupted)
    python scripts/make_bilingual.py --src data/hate/hs_urdu_clean.jsonl --translate

Needs for --translate:  pip install transformers sentencepiece torch
"""
import argparse
import json
import os
import re

LABELS = {
    "hate":      {"en": "hate",      "ur": "نفرت انگیز"},
    "offensive": {"en": "offensive", "ur": "توہین آمیز"},
    "normal":    {"en": "normal",    "ur": "عام"},
}

# Target groups used by HateXplain and HateCheck. Anything not listed keeps its English name in
# target_ur and is reported at the end, so you can add it here. Please have a native speaker
# check these Urdu terms.
TARGETS_UR = {
    "African": "افریقی", "Arab": "عرب", "Asian": "ایشیائی", "Caucasian": "سفید فام",
    "Hispanic": "ہسپانوی", "Buddhism": "بدھ مت", "Christian": "مسیحی", "Hindu": "ہندو",
    "Islam": "اسلام", "Jewish": "یہودی", "Men": "مرد", "Women": "خواتین",
    "Homosexual": "ہم جنس پرست", "Refugee": "پناہ گزین", "Disability": "معذور افراد",
    "Economic": "معاشی طبقہ", "Indigenous": "مقامی باشندے", "Other": "دیگر",
    "Nonreligious": "غیر مذہبی",
    "Indian": "بھارتی",
    # HateCheck
    "women": "خواتین", "gay people": "ہم جنس پرست افراد", "disabled people": "معذور افراد",
    "Muslims": "مسلمان", "black people": "سیاہ فام لوگ", "trans people": "ٹرانس جینڈر افراد",
    "immigrants": "تارکینِ وطن",
}

# NLLB-200 language codes
NLLB = {"en": "eng_Latn", "ur": "urd_Arab"}


class NLLBTranslator:
    """Loads facebook/nllb-200-distilled-600M once; translates batches in either direction."""

    def __init__(self, model_name="facebook/nllb-200-distilled-600M", device=None, batch_size=16):
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        self.torch = torch
        self.model_name = model_name
        self.batch_size = batch_size
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"loading {model_name} on {self.device} ...")
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(self.device).eval()

    def translate(self, texts, src, tgt):
        self.tok.src_lang = NLLB[src]
        out = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            enc = self.tok(batch, return_tensors="pt", padding=True, truncation=True,
                           max_length=128).to(self.device)
            with self.torch.no_grad():
                gen = self.model.generate(**enc, forced_bos_token_id=self.tok.convert_tokens_to_ids(NLLB[tgt]),
                                          max_new_tokens=160, num_beams=4)
            out.extend(self.tok.batch_decode(gen, skip_special_tokens=True))
        return out


def add_labels(row, missing_targets):
    lab = LABELS[row["label"]]
    row["label_en"], row["label_ur"] = lab["en"], lab["ur"]
    targets = [t for t in row.get("target", "").split("|") if t]
    row["target_en"] = "|".join(targets)
    ur = []
    for t in targets:
        if t not in TARGETS_UR:
            missing_targets.add(t)
        ur.append(TARGETS_UR.get(t, t))
    row["target_ur"] = "|".join(ur)
    return row


def add_translations(rows, translator):
    """Fills text_en / text_ur for rows. Original text is copied into its own language column."""
    todo = {"en": [], "ur": []}          # direction groups: source language -> rows
    for r in rows:
        r["text_original_lang"] = r["lang"]
        r["quality_flag"] = ""
        r["translation_model"] = translator.model_name
        if r["lang"] == "en":
            r["text_en"], r["text_ur"] = r["text"], None
            todo["en"].append(r)
        elif r["lang"] == "ur":
            r["text_ur"], r["text_en"] = r["text"], None
            todo["ur"].append(r)
        else:                            # ur-roman: NLLB has no Roman Urdu, so quality is unreliable
            r["text_ur"], r["text_en"] = None, None
            r["quality_flag"] = "roman_urdu_source_unreliable"
            todo["ur"].append(r)
    for src, tgt, field in (("en", "ur", "text_ur"), ("ur", "en", "text_en")):
        group = todo[src]
        if group:
            # <user>/<url> placeholders confuse translation models, so they are removed from the input
            inputs = [re.sub(r"\s*<(?:user|url)>\s*", " ", r["text"]).strip() or r["text"] for r in group]
            results = translator.translate(inputs, src, tgt)
            for r, t in zip(group, results):
                r[field] = t
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", required=True)
    p.add_argument("--out")
    p.add_argument("--translate", action="store_true")
    p.add_argument("--limit", type=int, help="only process the first N rows (smoke test)")
    p.add_argument("--chunk", type=int, default=200, help="rows per checkpoint")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--model", default="facebook/nllb-200-distilled-600M")
    a = p.parse_args()

    out_path = a.out or a.src.replace(".jsonl", "_bilingual.jsonl")
    rows = [json.loads(l) for l in open(a.src, encoding="utf-8")]
    if a.limit:
        rows = rows[:a.limit]

    done = set()
    if a.translate and os.path.exists(out_path):          # resume after interruption
        old = [json.loads(l) for l in open(out_path, encoding="utf-8")]
        kept = [r for r in old if "translation_model" in r]     # drop rows from a labels-only run
        with open(out_path, "w", encoding="utf-8") as f:
            for r in kept:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        done = {r["id"] for r in kept}
        print(f"resuming: {len(done)} translated rows already in {out_path}")
    elif os.path.exists(out_path):
        os.remove(out_path)

    missing = set()
    rows = [add_labels(r, missing) for r in rows if r["id"] not in done]
    translator = NLLBTranslator(a.model, batch_size=a.batch_size) if a.translate else None

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as f:
        for i in range(0, len(rows), a.chunk):
            chunk = rows[i:i + a.chunk]
            if translator:
                add_translations(chunk, translator)
            for r in chunk:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            print(f"  {min(i + a.chunk, len(rows))}/{len(rows)} rows written")
    print(f"done -> {out_path}")
    if missing:
        print("targets with no Urdu term yet (add to TARGETS_UR):", sorted(missing))


if __name__ == "__main__":
    main()