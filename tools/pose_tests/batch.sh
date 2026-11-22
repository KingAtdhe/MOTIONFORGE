#!/bin/bash
# usage: batch.sh name coach view seq   (renders + extracts landmarks to /home/claude/rv/fx/name.lm)
cd /home/claude/MOTIONFORGE
n=$1; c=$2; v=$3; s=$4
mkdir -p /home/claude/rv/fx
[ -f /home/claude/rv/fx/$n.lm ] && exit 0
rm -rf /tmp/rv_$n
RV_SAMPLES=${RV_SAMPLES:-5} ../bpyenv/bin/python /home/claude/rv/render_video.py app/src/main/assets/models/$c.glb /tmp/rv_$n $v "$s" 15 > /tmp/rv_$n.log 2>&1 || { echo "FAIL render $n"; exit 1; }
python3 /home/claude/rv/landmarks.py /tmp/rv_$n /home/claude/rv/fx/$n.lm 2>/dev/null | grep LM
echo "$n|$c|$v|$s" >> /home/claude/rv/fx/index.txt
