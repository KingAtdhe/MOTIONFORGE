import sys, os
from PIL import Image, ImageDraw
src, outp, view, ids = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4].split(",")
W, H = 180, 225
S = Image.new("RGB", (8 * W, len(ids) * H), "white"); dr = ImageDraw.Draw(S)
for y, lid in enumerate(ids):
    for i in range(8):
        f = os.path.join(src, f"{lid}__{view}_{i}.jpg")
        if os.path.exists(f): S.paste(Image.open(f).resize((W, H)), (i * W, y * H))
    dr.rectangle((0, y * H, 8 * W, y * H + 14), fill=(0, 0, 0)); dr.text((4, y * H + 2), lid + " side", fill=(255, 255, 0))
S.save(outp, quality=82)
