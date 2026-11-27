"""Merge translated parts: python3 tools/i18n/merge.py <lang>. Reads tools/i18n/parts/<lang>/*.json (objects English ->
translation), keeps only source strings, writes app/src/main/assets/i18n/<lang>.json sorted by source order."""
import glob, json, sys

lang = sys.argv[1]
SRC = json.load(open("tools/i18n/source.json", encoding="utf-8"))
t = {}
for p in sorted(glob.glob(f"tools/i18n/parts/{lang}/*.json")):
    t.update(json.load(open(p, encoding="utf-8")))
out = {s: t[s] for s in SRC if s in t and str(t[s]).strip()}
json.dump(out, open(f"app/src/main/assets/i18n/{lang}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(lang, len(out), "of", len(SRC))
