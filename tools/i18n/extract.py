"""Collect every English string the app can show: string literals in the Kotlin sources (Kotlin string templates become
{0}, {1}… placeholders) and the text fields of the lesson catalogue. Writes tools/i18n/source.json, the list that
each language's table (app/src/main/assets/i18n/<lang>.json) translates. Run from the repo root."""
import glob, json, re

LIT = re.compile(r'"((?:[^"\\$]|\\.|\$\{[^}]*\}|\$[A-Za-z_][\w.]*|\$)*)"')
TPL = re.compile(r'\$\{[^}]*\}|\$[A-Za-z_]\w*(?:\.\w+)*')
SKIP_FILES = ("/spikes/",)
out = set()


def unescape(s):
    return s.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\').replace('\\$', '$')


for f in sorted(glob.glob("app/src/main/java/**/*.kt", recursive=True)):
    if any(x in f for x in SKIP_FILES):
        continue
    for line in open(f, encoding="utf-8"):
        st = line.strip()
        if st.startswith(("import ", "package ", "//", "*", "/*", "@")) or "Log." in st or "require(" in st or "error(" in st:
            continue
        for m in LIT.finditer(line):
            raw = m.group(1)
            n = [0]

            def ph(_):
                i = n[0]; n[0] += 1
                return "{%d}" % i
            s = unescape(TPL.sub(ph, raw))
            letters = re.sub(r"\{\d+\}", "", s)
            if not re.search(r"[A-Za-z]{2}", letters):
                continue
            if re.fullmatch(r"[a-z0-9_.\-/:]+", s) or re.fullmatch(r"[A-Z0-9_]+", s):   # ids, keys, routes, constants
                continue
            if s.startswith(("eu.", "android.", "http", "mf-", "build-", "plan-")) or "/" in s and " " not in s:
                continue
            if not (" " in s or re.match(r"[A-Z][a-z]", s)):
                continue
            out.add(s)

FIELDS = ("name", "purpose", "space", "safety", "limitations")
for e in json.load(open("data/exercises.json", encoding="utf-8")):
    for k in FIELDS:
        if e.get(k):
            out.add(e[k])
    for k in ("equipment", "instructions", "commonCues"):
        out.update(x for x in e.get(k, []) if x)
    for mm in e.get("commonMistakes", []):
        out.update(x for x in (mm.get("mistake"), mm.get("adjustment")) if x)

src = sorted(out)
json.dump(src, open("tools/i18n/source.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(src), "strings,", sum(len(s) for s in src), "chars")
