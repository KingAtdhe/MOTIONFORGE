import sys, glob
from PIL import Image, ImageDraw
fs = sorted(glob.glob(sys.argv[2])); ims = [Image.open(f) for f in fs]
cols = int(sys.argv[3]) if len(sys.argv) > 3 else len(ims); rows = (len(ims) + cols - 1) // cols
S = Image.new("RGB", (cols * 360, rows * 450), "white"); d = ImageDraw.Draw(S)
for i, (f, im) in enumerate(zip(fs, ims)):
    S.paste(im, ((i % cols) * 360, (i // cols) * 450)); d.text(((i % cols) * 360 + 4, (i // cols) * 450 + 4), f.split("/")[-1], fill=(255, 255, 0))
S.save(sys.argv[1], quality=85)
