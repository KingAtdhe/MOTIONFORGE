#!/bin/bash
cd "$(dirname "$0")/../../.."
rm -f /tmp/build_f.log /tmp/build_m.log
for c in f m; do h=$([ $c = f ] && echo 1.70 || echo 1.85); (../bpyenv/bin/python tools/blender/build_coach_mesh.py assets/blender/rigged/coach_${c}_tripo_static.glb coach_$c $h --rigged assets/blender/rigged/coach_${c}_tripo.glb --app > /tmp/build_$c.log 2>&1; echo DONE >> /tmp/build_$c.log) & done
wait
grep -h "Traceback\|Error\|authored clips\|over-reach" /tmp/build_f.log /tmp/build_m.log
echo BUILDDONE
