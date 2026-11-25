#!/bin/bash
cd "$(dirname "$0")/../../.."
(../bpyenv/bin/python tools/qc/rigscan.py -- coach_f > /tmp/rs_f.log 2>&1) & ../bpyenv/bin/python tools/qc/rigscan.py -- coach_m > /tmp/rs_m.log 2>&1; wait
grep -h "Traceback\|Error" /tmp/rs_f.log /tmp/rs_m.log | head -3
python3 - <<'PY'
import json
for c in "fm":
    d=json.load(open(f"/tmp/rigscan_coach_{c}.json"))
    rows=sorted(((v["jerk"],k,v["at"],v["stretch"]) for k,v in d.items()), reverse=True)
    print(c, len(rows), ">400:", sum(r[0]>400 for r in rows), ">300:", sum(r[0]>300 for r in rows), "stretch>0.997:", [(k,v["stretch"]) for k,v in d.items() if v["stretch"]>0.997])
    for r in rows[:18]: print("  ", r)
PY
