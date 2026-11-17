"""Turn a translated .jsonl into a readable .txt you can open in VS Code.
Usage (from backend/):  python scripts/view_translations.py data/hate/test_ur.jsonl
Writes data/hate/test_ur.txt next to it."""
import json
import sys

src = sys.argv[1]
rows = [json.loads(line) for line in open(src, encoding="utf-8")]
blocks = []
for r in rows:
    blocks.append(
        f"[{r['label']}] {r['id']}  flag={r.get('quality_flag', '')}\n"
        f"ORIGINAL ({r['lang']}): {r['text']}\n"
        f"ENGLISH: {r.get('text_en')}\n"
        f"URDU   : {r.get('text_ur')}"
    )
out = src.replace(".jsonl", ".txt")
open(out, "w", encoding="utf-8").write("\n\n".join(blocks))
print("wrote", out)