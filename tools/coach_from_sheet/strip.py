import sys
from PIL import Image
pref, n, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
ims = [Image.open(f"{pref}_{i}.png").convert("RGB") for i in range(n)]
c = Image.new("RGB", (sum(i.width for i in ims), ims[0].height)); x = 0
for i in ims:
    c.paste(i, (x, 0)); x += i.width
c.save(out)
