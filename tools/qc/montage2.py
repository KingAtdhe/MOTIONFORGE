import sys, os
from PIL import Image, ImageDraw
src, outp, ids = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
NF = 8; W, H = 240, 300
rows = [(lid, v) for lid in ids for v in range(2)]
S = Image.new("RGB", (NF * W, len(rows) * H), "white"); dr = ImageDraw.Draw(S)
for y, (lid, v) in enumerate(rows):
    for i in range(NF):
        f = os.path.join(src, f"{lid}__{v}_{i}.jpg")
        if os.path.exists(f): S.paste(Image.open(f), (i * W, y * H))
    dr.text((4, y * H + 3), lid + (" side" if v else " 3/4"), fill=(255, 255, 0))
S = S.resize((S.width * 3 // 4, S.height * 3 // 4)); S.save(outp, quality=86)
