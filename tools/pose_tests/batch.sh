#!/bin/bash
# usage: batch.sh name coach view seq [fault] [env assignments, e.g. "RV_CAMH=0.4 RV_FLIP=1"]
cd /home/claude/MOTIONFORGE
n=$1; c=$2; v=$3; s=$4; export RV_FAULT=$5
for kv in $6; do export "$kv"; done
mkdir -p /home/claude/rv/fx
[ -f /home/claude/rv/fx/$n.lm ] && exit 0
rm -rf /tmp/rv_$n
RV_SAMPLES=${RV_SAMPLES:-5} ../bpyenv/bin/python /home/claude/rv/render_video.py app/src/main/assets/models/$c.glb /tmp/rv_$n $v "$s" 15 > /tmp/rv_$n.log 2>&1 || { echo "FAIL render $n"; exit 1; }
if [ "$RV_FLIP" = "1" ]; then python3 -c "
import glob; from PIL import Image, ImageOps
for f in glob.glob('/tmp/rv_$n/f*.jpg'): ImageOps.mirror(Image.open(f)).save(f, quality=88)"; fi
if [ -n "$RV_LIGHT" ]; then python3 -c "
# a phone brightening a dim room: low contrast, grain, slight softness
import glob, random; import numpy as np; from PIL import Image, ImageFilter
rng = np.random.default_rng(3)
for f in glob.glob('/tmp/rv_$n/f*.jpg'):
    a = np.asarray(Image.open(f)).astype(np.float32)
    a = (a - a.mean()) * 0.6 + a.mean() * 1.15 + rng.normal(0, 16, a.shape)
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7)).save(f, quality=80)"; fi
python3 /home/claude/rv/landmarks.py /tmp/rv_$n /home/claude/rv/fx/$n.lm 2>/dev/null | grep LM
echo "$n|$c|$v|$s|$5|$6" >> /home/claude/rv/fx/index.txt
