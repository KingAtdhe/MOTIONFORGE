"""Check language tables: python3 tools/i18n/check.py [lang ...] (default: all in app/src/main/assets/i18n).
Every source string present with a non-empty translation, the same {n} placeholders, no stray English-only keys."""
import glob, json, os, re, sys

SRC = json.load(open("tools/i18n/source.json", encoding="utf-8"))
PH = re.compile(r"\{\d+\}")
langs = sys.argv[1:] or sorted(os.path.basename(p)[:-5] for p in glob.glob("app/src/main/assets/i18n/*.json"))
bad = 0
for lang in langs:
    t = json.load(open(f"app/src/main/assets/i18n/{lang}.json", encoding="utf-8"))
    missing = [s for s in SRC if not t.get(s, "").strip()]
    ph = [k for k, v in t.items() if sorted(PH.findall(k)) != sorted(PH.findall(v))]
    extra = [k for k in t if k not in SRC]
    nl = [k for k, v in t.items() if k.count("\n") != v.count("\n")]
    print(f"{lang}: {len(t)} entries, missing {len(missing)}, placeholder mismatches {len(ph)}, newline mismatches {len(nl)}, not in source {len(extra)}")
    for k in (missing[:5] + ph[:5] + nl[:3]):
        print("   ", repr(k)[:100])
    bad += len(missing) + len(ph) + len(nl)
sys.exit(1 if bad else 0)
