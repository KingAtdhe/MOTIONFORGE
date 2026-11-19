import numpy as np
import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
from PIL import Image
from scipy import ndimage as ndi
im = np.asarray(Image.open(REPO + '/assets/blender/references/workout_coach_owner_sheet.png').convert('RGB')).astype(float) / 255
VIEWS = {"front": (445, 4, 610, 436), "side": (606, 4, 705, 436), "back": (705, 4, 852, 436)}
def mask_of(box):
    x0, y0, x1, y1 = box
    a = im[y0:y1, x0:x1]
    mx, mn = a.max(2), a.min(2)
    sat = (mx - mn) / np.maximum(mx, 1e-6)
    # background: light, low-saturation, slightly blue
    bg = (mx > 0.70) & (sat < 0.14) & (a[..., 2] >= a[..., 0] - 0.01)
    m = ~bg
    m = ndi.binary_opening(m, iterations=1)
    lab, n = ndi.label(m)
    sizes = ndi.sum(m, lab, range(1, n + 1))
    keep = np.zeros_like(m)
    for i, s in enumerate(sizes):
        if s > 400:
            keep |= lab == i + 1
    keep = ndi.binary_closing(keep, iterations=2)
    filled = ndi.binary_fill_holes(keep)
    # re-open enclosed background pockets (e.g. between arm and waist)
    holes, n = ndi.label(filled & bg)
    for i in range(1, n + 1):
        h = holes == i
        if h.sum() > 25 and np.nonzero(h)[0].mean() < 380:
            filled &= ~ndi.binary_dilation(h, iterations=0) if False else ~h
    return filled
if __name__ == "__main__":
    out = []
    for k, b in VIEWS.items():
        m = mask_of(b)
        np.save(f"mask_{k}.npy", m)
        ys, xs = np.nonzero(m)
        print(k, m.shape, "bbox", xs.min(), xs.max(), ys.min(), ys.max())
        rgb = (im[b[1]:b[3], b[0]:b[2]] * 255).astype(np.uint8).copy()
        rgb[~m] = (rgb[~m] * 0.25 + np.array([0, 160, 255]) * 0.75).astype(np.uint8)
        out.append(Image.fromarray(rgb))
    W = sum(o.width for o in out); c = Image.new("RGB", (W, out[0].height)); x = 0
    for o in out:
        c.paste(o, (x, 0)); x += o.width
    c.resize((c.width * 2, c.height * 2)).save("masks.png")
    # hair: dark, warm, saturated pixels in the upper part of each view (used for the ponytail)
    for k, (ox, oy, _, _) in VIEWS.items():
        M = np.load(f"mask_{k}.npy")
        a = im[oy:oy + M.shape[0], ox:ox + M.shape[1]]
        mx, mn = a.max(2), a.min(2)
        sat = (mx - mn) / np.maximum(mx, 1e-6)
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        hair = (mx < 0.62) & (sat > 0.30) & (r > g) & (g >= b - 0.02) & ((r - b) > 0.08)
        hair &= M & (np.arange(M.shape[0])[:, None] < 170)
        hair = ndi.binary_closing(ndi.binary_opening(hair, iterations=1), iterations=2)
        np.save(f"hair_{k}.npy", hair)
