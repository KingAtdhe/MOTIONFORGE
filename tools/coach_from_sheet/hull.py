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
HAIR_F = np.load("hair_front.npy")


def face_half_width(r):
    """Half width of the bare face (no hair strands) on front row r, or None."""
    skin = F[r] & ~ndi.binary_dilation(HAIR_F[r], iterations=1)
    for a, b in intervals(skin):
        if a <= cx <= b:
            return (b - a + 1) / 2 * PX
    return None
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
                fw = face_half_width(r)
                if Z(r) < 1.555 and fw is not None:              # jaw / cheeks: bare-face width, not hair
                    xr = float(np.clip(fw + 0.006, 0.040, 0.080))
                yr = min((yb - yf) / 2, max(xr, 0.072) * 1.18)
                P["torso"][i] = (xc, xr, yf + yr, yr, 2.0)
                head_back = yf + 2 * yr
            elif r < armpit:                                     # shoulders: torso + deltoids
                t = np.clip((armpit - r) * PX / (Z(chin) - Z(armpit)), 0, 1)
                yb2 = min(yb, (back_ref if back_ref is not None else yb) + 0.012)
                txr = min(xr, CH * (1 - 0.32 * t ** 1.6))
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
# head: an explicit sculpt (skull, face planes, jaw, chin, cheekbones, brow, nose, lips, ears, hair cap) placed
# on the landmarks measured on the sheet (brows 1.575, eyes 1.555, nose tip 1.515, mouth 1.485, chin 1.445 m);
# the outline-derived head oval above the neck is replaced by it.
HEAD = [  # centre (x, y, z), radii (x, y, z)
    ((0, -0.025, 1.585), (0.071, 0.091, 0.086)),      # cranium
    ((0, -0.058, 1.515), (0.053, 0.056, 0.066)),      # face mass
    ((0.029, -0.056, 1.476), (0.024, 0.036, 0.026)), ((-0.029, -0.056, 1.476), (0.024, 0.036, 0.026)),   # jaw
    ((0, -0.081, 1.463), (0.018, 0.015, 0.016)),      # chin
    ((0, -0.040, 1.468), (0.038, 0.042, 0.026)),      # under the jaw, into the neck
    ((0.040, -0.074, 1.537), (0.018, 0.014, 0.014)), ((-0.040, -0.074, 1.537), (0.018, 0.014, 0.014)),  # cheekbones
    ((0.026, -0.099, 1.578), (0.026, 0.009, 0.010)), ((-0.026, -0.099, 1.578), (0.026, 0.009, 0.010)),  # brow
    ((0, -0.107, 1.545), (0.0075, 0.011, 0.024)),     # nose bridge
    ((0, -0.116, 1.515), (0.0105, 0.010, 0.0095)),    # nose tip
    ((0.0095, -0.110, 1.511), (0.0068, 0.0065, 0.006)), ((-0.0095, -0.110, 1.511), (0.0068, 0.0065, 0.006)),
    ((0, -0.101, 1.487), (0.018, 0.009, 0.010)),      # lips
    ((0.071, -0.015, 1.535), (0.009, 0.015, 0.024)), ((-0.071, -0.015, 1.535), (0.009, 0.015, 0.024)),  # ears
    ((0, 0.020, 1.678), (0.034, 0.030, 0.024)),       # hair gathered at the crown
]
NECK = ((0, -0.015), 0.043, 1.395, 1.52)
TRAPS = [((s_ * 0.025, 0.005, 1.445), (s_ * 0.125, 0.000, 1.375), 0.034) for s_ in (-1, 1)]


def capsule(a, b, r):
    a, b = np.array(a), np.array(b)
    return a, b, r
for kz, z in enumerate(zs):
    if z < NECK[2] - 0.01:
        continue
    f = vol[:, :, kz]
    if z > CHIN_Z + 0.008:                               # drop the outline oval: the sculpted head takes over
        i = int(np.argmin(np.abs(zrow - z)))
        f = np.full(X.shape, -1.0, np.float32)
        if not np.isnan(P["hair"][i][0]):
            xc, xr, yc, yr, n = P["hair"][i]
            f = np.maximum(f, 1.0 - (np.abs((X - xc) / xr) ** n + np.abs((Y - yc) / yr) ** n) ** (1 / n))
    if z < NECK[3]:
        f = np.maximum(f, 1.0 - np.sqrt((X - NECK[0][0]) ** 2 + (Y - NECK[0][1]) ** 2) / NECK[1])
    for a, b, r in TRAPS:
        a, b = np.array(a), np.array(b)
        ab = b - a
        # closest point on the segment for every (X, Y) at this z
        t = ((X - a[0]) * ab[0] + (Y - a[1]) * ab[1] + (z - a[2]) * ab[2]) / ab.dot(ab)
        t = np.clip(t, 0, 1)
        dx, dy, dz_ = X - (a[0] + t * ab[0]), Y - (a[1] + t * ab[1]), z - (a[2] + t * ab[2])
        f = np.maximum(f, 1.0 - np.sqrt(dx * dx + dy * dy + dz_ * dz_) / r)
    for (cx_, cy_, cz_), (rx, ry, rz) in HEAD:
        dz = (z - cz_) / rz
        if abs(dz) < 1:
            f = np.maximum(f, 1.0 - np.sqrt(((X - cx_) / rx) ** 2 + ((Y - cy_) / ry) ** 2 + dz ** 2))
    # hair cap: skull + ~1 cm, behind the hairline (forehead stays bare), with locks framing the face down the sides
    dz = (z - 1.595) / 0.097
    if abs(dz) < 1:
        cap = 1.0 - np.sqrt((X / 0.081) ** 2 + ((Y + 0.022) / 0.101) ** 2 + dz ** 2)
        keep = (Y > -0.062) | (z > 1.638) | ((np.abs(X) > 0.058) & (z > 1.525))
        f = np.maximum(f, np.where(keep, cap, -1.0))
    vol[:, :, kz] = f
vs = ndi.gaussian_filter(vol, sigma=(1.0, 1.0, 1.6))
wide = ndi.gaussian_filter(vol, sigma=(2.6, 2.6, 2.6))
wz = np.clip(1 - np.abs(zs - 1.36) / 0.10, 0, 1)[None, None, :]        # shoulder / neck band
mid = ndi.gaussian_filter(vol, sigma=(1.7, 1.7, 1.7))
wh = np.clip((zs - 1.44) / 0.02, 0, 1)[None, None, :]                    # head: blend the sculpt forms
vol = vs * (1 - wz) + wide * wz
vol = vol * (1 - wh) + mid * wh
verts, faces, _, _ = measure.marching_cubes(vol, level=0.0, spacing=(VOX, VOX, VOX))
verts += np.array([xs[0], ys[0], zs[0]])
np.savez("hull.npz", verts=verts.astype(np.float32), faces=faces.astype(np.int32), px=PX, cx=cx, cy=cy, top=top, ground=ground,
         crotch=Z(crotch), armpit=Z(armpit), neck=Z(neck_r))
np.save("parts.npy", {k: v for k, v in P.items()}, allow_pickle=True)
print("verts", len(verts), "bbox", verts.min(0).round(3), verts.max(0).round(3))
