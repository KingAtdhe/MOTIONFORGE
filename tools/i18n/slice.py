"""Print source strings [start, end) as a JSON list (for translating in parts): python3 tools/i18n/slice.py 0 250"""
import json, sys
a, b = int(sys.argv[1]), int(sys.argv[2])
print(json.dumps(json.load(open("tools/i18n/source.json", encoding="utf-8"))[a:b], ensure_ascii=False, indent=0))
