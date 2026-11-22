"""Compose motion-study plates from the frames rendered by tools/blender/render_studies.py.

Usage: python tools/compose_studies.py <frames_dir> <out_dir>
For each lesson: <out_dir>/<id>.webp   one black plate, earlier exposures fading in, the key position sharp (600x750)
                 <out_dir>/<id>_strip.webp   four frames of the movement side by side (contact sheet row, 640x200)
"""
import glob, os, re, sys
import numpy as np
from PIL import Image

src, out = sys.argv[1:3]
os.makedirs(out, exist_ok=True)
ids = sorted({re.sub(r"_\d+\.png$", "", os.path.basename(p)) for p in glob.glob(os.path.join(src, "*_0.png"))})
for lid in ids:
    frames = [Image.open(p).convert("RGBA") for p in sorted(glob.glob(os.path.join(src, f"{lid}_[0-9].png")), key=lambda p: int(p[-5]))]
    n = len(frames)
    W, H = frames[0].size
    acc = np.zeros((H, W, 3))
    for i, f in enumerate(frames[:-1]):
        a = np.asarray(f).astype(float) / 255
        w = 0.18 + 0.42 * (i / max(1, n - 2)) ** 1.5          # older exposures fainter
        acc = 1 - (1 - acc) * (1 - a[..., :3] * a[..., 3:4] * w)  # screen blend, like light adding up on a plate
    plate = Image.fromarray((acc * 255).astype("uint8")).convert("RGBA")
    plate.alpha_composite(frames[-1])                              # the key position, sharp and in full colour
    plate.convert("RGB").save(os.path.join(out, f"{lid}.webp"), quality=78, method=6)
    pick = [frames[round(i * (n - 1) / 3)] for i in range(4)]
    cw, ch = 160, 200
    strip = Image.new("RGB", (cw * 4, ch), (0, 0, 0))
    for i, f in enumerate(pick):
        bg = Image.new("RGBA", f.size, (0, 0, 0, 255)); bg.alpha_composite(f)
        # crop the frame to the cell's aspect around its centre
        fw, fh = bg.size; tw = int(fh * cw / ch)
        bg = bg.crop(((fw - tw) // 2, 0, (fw + tw) // 2, fh)).resize((cw, ch), Image.LANCZOS)
        strip.paste(bg.convert("RGB"), (i * cw, 0))
    strip.save(os.path.join(out, f"{lid}_strip.webp"), quality=74, method=6)
    print("composed", lid)
