"""Coach body volume from the sheet's front + side silhouettes.
Per sheet row the front outline is split into parts (torso/head, shoulders, arms, legs); each part gets a
superelliptic cross-section whose depth comes from the side outline. Part parameters are smoothed along the
height before the volume is built, then a surface is extracted with marching cubes -> hull.npz."""
import numpy as np
from scipy import ndimage as ndi
from skimage import measure

F, S = np.load("mask_front.npy"), np.load("mask_side.npy")
H = 1.70
top = min(np.nonzero(F)[0].min(), np.nonzero(S)[0].min())
ground = max(np.nonzero(F)[0].max(), np.nonzero(S)[0].max())
PX = H / (ground - top)


def intervals(row):
    d = np.diff(np.concatenate([[0], row.astype(int), [0]]))
    return list(zip(np.nonzero(d == 1)[0], np.nonzero(d == -1)[0] - 1))


Z = lambda r: (ground - r) * PX
waist = [r for r in range(top, ground) if 0.98 < Z(r) < 1.12]
cx = np.median([(a + b) / 2 for r in waist for a, b in [max(intervals(F[r]), key=lambda t: t[1] - t[0])]])
c = int(round(cx))
crotch = next(r for r in range(ground, top, -1) if F[r, c] and Z(r) > 0.5)
cy = np.mean(max(intervals(S[crotch - int(0.05 / PX)]), key=lambda t: t[1] - t[0]))
armpit = next(r + 1 for r in range(crotch - 1, top, -1) if len(intervals(F[r])) < 3)
_ta = next(t for t in intervals(F[armpit + 2]) if t[0] <= cx <= t[1])
CH = (_ta[1] - _ta[0] + 1) / 2 * PX
CHIN_Z = 1.435                                  # measured on the sheet (chin line of the front view)
neck_r = chin = int(round(ground - CHIN_Z / PX))
print("px %.5f cx %.1f cy %.1f crotch %.3f armpit %.3f neck %.3f" % (PX, cx, cy, Z(crotch), Z(armpit), Z(neck_r)))

HAIR_S = np.load("hair_side.npy")
HB = np.load("hair_back.npy")
_lab, _n = ndi.label(HB)
HB = _lab == (np.argmax(ndi.sum(HB, _lab, range(1, _n + 1))) + 1)

rows = np.arange(top, ground + 1)
N = len(rows)
P = {k: np.full((N, 5), np.nan) for k in ("torso", "armL", "armR", "legL", "legR", "delL", "delR", "hair")}  # xc xr yc yr n


def side_main(r):
    iv = intervals(S[r])
    return min(iv, key=lambda t: 0 if t[0] <= cy <= t[1] else min(abs(t[0] - cy), abs(t[1] - cy)))


def ym(col):  # side-image column -> metres (+Y = behind)
    return -(col - cy) * PX


SIDE = {}
back_ref = max(ym(side_main(r)[0] - 0.5) for r in range(armpit, armpit + int(0.10 / PX)))
for i, r in enumerate(rows):
    fiv = intervals(F[r])
    if not fiv or not intervals(S[r]):
        continue
    sm = side_main(r)
    yf, yb = ym(sm[1] + 0.5), ym(sm[0] - 0.5)
    zf = Z(r) / H
    below = r >= crotch
    legs = sorted(fiv, key=lambda t: abs((t[0] + t[1]) / 2 - cx))[:2] if below else []
    for a, b in fiv:
        x0, x1 = (a - 0.5 - cx) * PX, (b + 0.5 - cx) * PX
        xc, xr = (x0 + x1) / 2, (x1 - x0) / 2
        if not below and a <= cx <= b:
            if r < chin:                                         # head + neck: drop the ponytail mass behind
                yr = min((yb - yf) / 2, xr * 1.18)
                P["torso"][i] = (xc, xr, yf + yr, yr, 2.0)
                head_back = yf + 2 * yr
            elif r < armpit:                                     # shoulders: torso + deltoids
                t = np.clip((armpit - r) * PX / (Z(chin) - Z(armpit)), 0, 1)
                yb2 = min(yb, (back_ref if back_ref is not None else yb) + 0.012)
                txr = min(xr, CH * (1 - 0.55 * t ** 1.6))
                P["torso"][i] = (0.0, txr, (yf + yb2) / 2, (yb2 - yf) / 2, 2.3)
                for key, edge in (("armR", x0), ("armL", x1)):
                    inner = np.sign(edge) * txr * 0.70
                    axr = abs(edge - inner) / 2
                    if axr > 0.015:
                        P[key][i] = ((edge + inner) / 2, axr, (yf + yb2) / 2, min(axr * 0.88, (yb2 - yf) / 2), 2.0)
            else:
                P["torso"][i] = (xc, xr, (yf + yb) / 2, (yb - yf) / 2, 2.3 if zf > 0.45 else 2.1)
                SIDE[i] = (yf, yb, xr)
        elif below and (a, b) in legs:
            key = "legL" if xc > 0 else "legR"
            # both legs share the side outline; split it so each leg is no deeper than it is wide x 1.35
            yr = min((yb - yf) / 2, xr * 1.35) if zf > 0.07 else (yb - yf) / 2
            P[key][i] = (xc, xr, (yf + yb) / 2, yr, 2.1)
        else:
            key = "armL" if xc > 0 else "armR"
            if not np.isnan(P[key][i][0]):                       # keep the wider piece
                if P[key][i][1] > xr:
                    continue
            ref = P["torso"][i][2] if not np.isnan(P["torso"][i][2]) else (yf + yb) / 2
            P[key][i] = (xc, xr, ref if not below else (yf + yb) / 2 - 0.0, xr * 0.92, 2.0)
    # ponytail / hair behind the head and upper back
    if zf > 0.74:
        cols = np.nonzero(S[r] & (HAIR_S[r] | (np.arange(S.shape[1]) < sm[0])))[0]
        yc_ = ym(cols)
        lim = head_back if r < chin else yb
        beh = yc_[yc_ > lim - 0.01]
        if len(beh) > 2:
            hc = np.nonzero(HB[r])[0]
            wx = (hc.max() - hc.min() + 1) * PX / 2 if len(hc) > 3 else 0.03
            wx = float(np.clip(wx * 0.85, 0.02, 0.07))
            P["hair"][i] = (0.0, wx, (beh.min() + beh.max()) / 2, max((beh.max() - beh.min()) / 2, 0.012), 2.0)


def smooth(a, sig):
    out = a.copy()
    ok = ~np.isnan(a[:, 0])
    if ok.sum() < 3:
        return out
    lab, n = ndi.label(ok)
    for j in range(1, n + 1):
        idx = np.nonzero(lab == j)[0]
        for k in range(4):
            out[idx, k] = ndi.gaussian_filter1d(a[idx, k], sig, mode="nearest")
    return out


# ponytail: bridge gaps in the hair detection so it is one continuous lock
hk = P["hair"]
okh = np.nonzero(~np.isnan(hk[:, 0]))[0]
if len(okh) > 4:
    span = np.arange(okh.min(), okh.max() + 1)
    for k in range(5):
        hk[span, k] = np.interp(span, okh, hk[okh, k])
for k in P:
    P[k] = smooth(P[k], 4.0 if k == "hair" else (2.2 if k == "torso" else 1.6))
# head rows: stronger smoothing of width (loose hair strands in the front outline)
hr = (rows < chin) & ~np.isnan(P["torso"][:, 0])
for k in range(4):
    col = P["torso"][:, k].copy()
    okc = ~np.isnan(col)
    col[~okc] = np.interp(np.nonzero(~okc)[0], np.nonzero(okc)[0], col[okc])
    P["torso"][hr, k] = ndi.gaussian_filter1d(col, 4.0, mode="nearest")[hr]

# head: centre it and cap the width (the front outline includes loose strands framing the face)
for i, r in enumerate(rows):
    if r < chin and not np.isnan(P["torso"][i][0]):
        P["torso"][i][0] = 0.0
        P["torso"][i][1] = min(P["torso"][i][1], 0.080)
# round the top of the head (the smoothing above would otherwise leave a flat cut)
zt = Z(top)
for i, r in enumerate(rows):
    h = zt - Z(r)
    if h < 0.075 and not np.isnan(P["torso"][i][0]):
        k = np.sqrt(max(0.0, 1 - ((0.075 - h) / 0.075) ** 2))
        P["torso"][i][1] *= max(k, 0.05)
        P["torso"][i][3] *= max(k, 0.05)
# anatomy lobes: the side outline's forward bulge at the chest is two breasts (not a wider ribcage), and its
# backward bulge at the hips is two glutes; carve the torso back to a smooth line and add paired lobes there
BUST = {}; GLUTE = {}
zs_side = sorted((Z(rows[i]), i) for i in SIDE)
def _line(z0, z1, k):
    i0 = min(SIDE, key=lambda i: abs(Z(rows[i]) - z0)); i1 = min(SIDE, key=lambda i: abs(Z(rows[i]) - z1))
    a, b = SIDE[i0][k], SIDE[i1][k]
    return lambda z: a + (b - a) * (z - z0) / (z1 - z0)
back_line = _line(0.80, 1.06, 1)
# bust: measured on the side outline (underbust ~1.18 m, apex ~1.25 m, upper chest falls back above 1.32 m)
ap_i = max((i for i in SIDE if 1.19 < Z(rows[i]) < 1.31), key=lambda i: -SIDE[i][0])
APEX_Z, APEX_Y = 1.245, SIDE[ap_i][0]
ub_i = min(SIDE, key=lambda i: abs(Z(rows[i]) - 1.175))
rib = lambda z: SIDE[ub_i][0] + (z - 1.175) * 0.16          # ribcage front line under the bust
for i, (yf, yb, xr) in SIDE.items():
    z = Z(rows[i])
    if 1.18 < z < 1.31 and yf < rib(z):
        cut = rib(z) - yf
        P["torso"][i][2] += cut / 2; P["torso"][i][3] -= cut / 2
    if 0.80 < z < 1.06:
        bump = yb - back_line(z)
        if bump > 0.004:
            P["torso"][i][2] -= bump / 2; P["torso"][i][3] -= bump / 2
            GLUTE[i] = (yb, bump, xr)
print("bust apex z %.3f y %.3f" % (APEX_Z, APEX_Y), "glute rows", len(GLUTE))
VOX = 0.004
xs = np.arange(-0.40, 0.40, VOX)
ys = np.arange(-0.26, 0.26, VOX)
zs = np.arange(-0.01, H + 0.02, VOX)
X, Y = np.meshgrid(xs, ys, indexing="ij")
vol = np.full((len(xs), len(ys), len(zs)), -1.0, np.float32)
zrow = Z(rows)
for kz, z in enumerate(zs):
    i = int(np.argmin(np.abs(zrow - z)))
    if abs(zrow[i] - z) > PX:
        continue
    f = np.full(X.shape, -1.0, np.float32)
    dz = (z - APEX_Z) / 0.074
    if abs(dz) < 1:
        ry = 0.058
        for sx in (-1, 1):
            f = np.maximum(f, 1.0 - np.sqrt(((X - sx * 0.058) / 0.064) ** 2 + ((Y - (APEX_Y + ry)) / ry) ** 2 + dz ** 2))
    if i in GLUTE:
        yb_, bump, xr_ = GLUTE[i]
        lr = 0.06 + bump * 0.6
        for sx in (-1, 1):
            f = np.maximum(f, 1.0 - np.sqrt(((X - sx * xr_ * 0.48) / (xr_ * 0.55)) ** 2 + ((Y - (yb_ - lr)) / lr) ** 2))
    for k, arr in P.items():
        xc, xr, yc, yr, n = arr[i]
        if np.isnan(xc) or xr <= 0 or yr <= 0:
            continue
        f = np.maximum(f, 1.0 - (np.abs((X - xc) / xr) ** n + np.abs((Y - yc) / yr) ** n) ** (1 / n))
    vol[:, :, kz] = f
vol = ndi.gaussian_filter(vol, sigma=(1.0, 1.0, 1.6))
verts, faces, _, _ = measure.marching_cubes(vol, level=0.0, spacing=(VOX, VOX, VOX))
verts += np.array([xs[0], ys[0], zs[0]])
np.savez("hull.npz", verts=verts.astype(np.float32), faces=faces.astype(np.int32), px=PX, cx=cx, cy=cy, top=top, ground=ground,
         crotch=Z(crotch), armpit=Z(armpit), neck=Z(neck_r))
np.save("parts.npy", {k: v for k, v in P.items()}, allow_pickle=True)
print("verts", len(verts), "bbox", verts.min(0).round(3), verts.max(0).round(3))
