#!/bin/bash
cd "$(dirname "$0")/../../.."
for c in f m; do
  G=assets/blender/exports/coach_$c.glb
  ../bpyenv/bin/python tools/qc/audit2.py -- $G /tmp/audit_$c.json "$(cat tools/qc/joins.json)" > /tmp/audit_$c.log 2>&1
  ../bpyenv/bin/python tools/qc/natural.py $G > /tmp/natural_$c.log 2>&1
  ../bpyenv/bin/python tools/qc/clip_int.py $G > /tmp/clipint_$c.log 2>&1
  ALL=$(python3 -c "import json;print(','.join(json.load(open('app/src/main/assets/models/coach_$c.clips.json'))['clips'][i]['name'] for i in range(len(json.load(open('app/src/main/assets/models/coach_$c.clips.json'))['clips']))))")
  ../bpyenv/bin/python tools/qc/jerk.py $G $ALL > /tmp/jerk_$c.log 2>&1
done
echo QCDONE
