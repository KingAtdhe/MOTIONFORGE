import sys, os, json
from PIL import Image, ImageDraw
src, outdir, view = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = json.load(open("data/exercises.json")); L = d if isinstance(d, list) else d["exercises"]
ids = [e["id"] for e in L]
os.makedirs(outdir, exist_ok=True)
W, H = 180, 225
for p in range(0, len(ids), 8):
    chunk = ids[p:p + 8]
    S = Image.new("RGB", (8 * W, len(chunk) * H), "white"); dr = ImageDraw.Draw(S)
    for y, lid in enumerate(chunk):
        for i in range(8):
            f = os.path.join(src, f"{lid}__{view}_{i}.jpg")
            if os.path.exists(f): S.paste(Image.open(f).resize((W, H)), (i * W, y * H))
        dr.rectangle((0, y * H, 8 * W, y * H + 14), fill=(0, 0, 0)); dr.text((4, y * H + 2), f"{p + y}: {lid}", fill=(255, 255, 0))
    S.save(os.path.join(outdir, f"p{p // 8:02d}.jpg"), quality=82)
print("pages", (len(ids) + 7) // 8)
