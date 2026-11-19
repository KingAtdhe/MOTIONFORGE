import sys, numpy as np
import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
from PIL import Image
from scipy import ndimage as ndi
pref = sys.argv[1]
d = np.load("./hull.npz"); PX = float(d["px"]); ground = int(d["ground"]); cx = float(d["cx"]); cy = float(d["cy"])
sheet = np.asarray(Image.open(REPO + '/assets/blender/references/workout_coach_owner_sheet.png').convert('RGB'))
VIEWS = {"front": (445, 4), "side": (606, 4), "back": (705, 4)}
outs = []
for k, (ox, oy) in VIEWS.items():
    M = np.load(f"./mask_{k}.npy")
    R = np.asarray(Image.open(f"{pref}_{k}.png").convert("L")) > 30
    n = R.shape[0]
    # render: camera centre at z = H/2 - 0.01, x centre 0 -> pixel n/2
    zc = (1.76 / 2 - 0.01)
    canvas = (sheet[oy:oy + M.shape[0], ox:ox + M.shape[1]] * 0.6).astype(np.uint8)
    rr, cc = np.nonzero(R)
    z = zc + (n / 2 - rr - 0.5) * PX
    h = (cc + 0.5 - n / 2) * PX
    srow = np.round(ground - z / PX).astype(int)
    if k == "front":
        scol = np.round(cx + h / PX).astype(int)
    elif k == "back":
        bc = np.load("./mask_back.npy"); cxb = (np.nonzero(bc[300])[0].min() + np.nonzero(bc[300])[0].max()) / 2 if False else None
        scol = np.round(cx_b + h / PX).astype(int) if False else np.round(np.mean(np.nonzero(M)[1]) + h / PX).astype(int)
    else:
        scol = np.round(cy + h / PX).astype(int)
    ok = (srow >= 0) & (srow < M.shape[0]) & (scol >= 0) & (scol < M.shape[1])
    Rm = np.zeros_like(M); Rm[srow[ok], scol[ok]] = True
    Rm = ndi.binary_closing(Rm, iterations=1)
    edgeM = M ^ ndi.binary_erosion(M)
    edgeR = Rm ^ ndi.binary_erosion(Rm)
    canvas[edgeM] = (0, 255, 0)
    canvas[edgeR] = (255, 0, 255)
    iou = (M & Rm).sum() / (M | Rm).sum()
    print(k, "IoU %.3f" % iou)
    outs.append(Image.fromarray(canvas))
W = sum(o.width for o in outs); c = Image.new("RGB", (W, outs[0].height)); x = 0
for o in outs:
    c.paste(o, (x, 0)); x += o.width
c.resize((c.width * 2, c.height * 2), Image.NEAREST).save(f"{pref}_overlay.png")
