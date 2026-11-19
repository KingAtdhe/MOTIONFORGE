"""Projects the owner's painted front / side / back views onto the baked surface texels -> coach_albedo.png"""
import numpy as np
import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", ".."))
from PIL import Image
from scipy import ndimage as ndi

d = np.load("hull.npz"); PX = float(d["px"]); ground = int(d["ground"]); cx = float(d["cx"]); cy = float(d["cy"])
B = np.load("bake.npz"); pos = B["pos"][..., :3]; nor = B["nor"][..., :3]
RES = pos.shape[0]
nl = np.linalg.norm(nor, axis=2)
cov = nl > 0.5
nor = nor / np.maximum(nl[..., None], 1e-6)
P = pos[cov]; N = nor[cov]
sheet = np.asarray(Image.open(REPO + '/assets/blender/references/workout_coach_owner_sheet.png').convert('RGB')).astype(np.float32) / 255
VIEWS = {"front": (445, 4), "side": (606, 4), "back": (705, 4)}
M = {k: np.load(f"mask_{k}.npy") for k in VIEWS}
img = {k: sheet[oy:oy + M[k].shape[0], ox:ox + M[k].shape[1]].copy() for k, (ox, oy) in VIEWS.items()}

# --- remove the chest logo from the front view (bright marks on the bra), fill from surrounding fabric
f = img["front"]
H_, W_ = f.shape[:2]
rr, cc = np.mgrid[0:H_, 0:W_]
bra = (rr > 95) & (rr < 130) & (np.abs(cc - cx) < 16)
logo = bra & (f.max(2) > 0.55) & ((f.max(2) - f.min(2)) < 0.25)
logo = ndi.binary_dilation(logo, iterations=2)
idx = ndi.distance_transform_edt(logo, return_distances=False, return_indices=True)
f[logo] = f[idx[0][logo], idx[1][logo]]
f[logo] = ndi.uniform_filter(f, size=(5, 5, 1))[logo]
print("logo px", logo.sum())

# --- back view: per-row piecewise-linear warp so its outline matches the (mirrored) front outline
def intervals(row):
    dd = np.diff(np.concatenate([[0], row.astype(int), [0]]))
    return list(zip(np.nonzero(dd == 1)[0], np.nonzero(dd == -1)[0] - 1))
Fm, Bm = M["front"], M["back"]
back_map = np.full(Fm.shape, np.nan, np.float32)   # for each front-frame (row, col): back image col
for r in range(Fm.shape[0]):
    fi = intervals(Fm[r]); bi = intervals(Bm[r]) if r < Bm.shape[0] else []
    if not fi or not bi:
        continue
    # model x (front frame) -> mirrored; the back image sees -x on its right
    fx = sorted([(cx - (b + 0.5 - cx), cx - (a - 0.5 - cx)) for a, b in fi])   # mirrored front intervals (in front-col units)
    bx = [(a - 0.5, b + 0.5) for a, b in bi]
    if len(fx) == len(bx):
        src = np.array([v for t in fx for v in t]); dst = np.array([v for t in bx for v in t])
    else:
        src = np.array([fx[0][0], fx[-1][1]]); dst = np.array([bx[0][0], bx[-1][1]])
    cols = np.arange(Fm.shape[1], dtype=np.float32)
    mir = 2 * cx - cols                       # mirrored front col for each front col
    back_map[r] = np.interp(mir, src, dst, left=np.nan, right=np.nan)

def sample(im, rows, cols):
    out = np.zeros((len(rows), 3), np.float32)
    ok = (rows >= 0) & (rows <= im.shape[0] - 1) & (cols >= 0) & (cols <= im.shape[1] - 1) & ~np.isnan(cols)
    for ch in range(3):
        out[ok, ch] = ndi.map_coordinates(im[..., ch], [rows[ok], cols[ok]], order=1, mode="nearest")
    return out, ok

row = ground - P[:, 2] / PX
views = []
# front: camera at -Y
views.append(("front", np.array([0, -1, 0]), row, cx + P[:, 0] / PX))
# back: warp via back_map
bc = np.full(len(P), np.nan, np.float32)
ri = np.clip(np.round(row).astype(int), 0, Fm.shape[0] - 1)
fc = cx + P[:, 0] / PX
ci0 = np.clip(np.floor(fc).astype(int), 0, Fm.shape[1] - 2)
t = np.clip(fc - ci0, 0, 1)
bc = back_map[ri, ci0] * (1 - t) + back_map[ri, ci0 + 1] * t
views.append(("back", np.array([0, 1, 0]), row, bc))
# sides: same painting for both sides (body is near symmetric); image right = -Y
views.append(("side", np.array([1, 0, 0]), row, cy - P[:, 1] / PX))
views.append(("side", np.array([-1, 0, 0]), row, cy - P[:, 1] / PX))

def visibility(dirv, rows, cols):
    """Z-buffer over the texel points themselves at sheet-pixel resolution x2."""
    s = 2.0
    depth = P @ dirv                    # larger = closer to the camera
    ok = ~np.isnan(cols)
    gi = np.round(rows * s).astype(int); gj = np.round(np.nan_to_num(cols, nan=-9) * s).astype(int)
    key = gi * 100000 + gj
    zb = {}
    order = np.argsort(-depth)
    best = np.full(len(P), -np.inf, np.float32)
    # max depth per cell via pandas-free groupby
    uk, inv = np.unique(key[ok], return_inverse=True)
    mx = np.full(len(uk), -np.inf, np.float32)
    np.maximum.at(mx, inv, depth[ok])
    best[ok] = mx[inv]
    return ok & (depth >= best - 0.012)

# --- where the arm covers the body in the side painting, those pixels must only paint the arm itself
PARTS = np.load("parts.npy", allow_pickle=True).item()
top = int(d["top"])
ri_all = np.clip(np.round(row).astype(int) - top, 0, len(PARTS["armL"]) - 1)
arm_xc = np.where(P[:, 0] > 0, PARTS["armL"][ri_all, 0], PARTS["armR"][ri_all, 0])
arm_xr = np.where(P[:, 0] > 0, PARTS["armL"][ri_all, 1], PARTS["armR"][ri_all, 1])
arm_yc = np.nanmean([PARTS["armL"][:, 2], PARTS["armR"][:, 2]], axis=0)[ri_all]
arm_yr = np.nanmean([PARTS["armL"][:, 3], PARTS["armR"][:, 3]], axis=0)[ri_all]
has_arm = ~np.isnan(arm_xc) & ~np.isnan(arm_yc)
is_arm = has_arm & (np.abs(P[:, 0] - np.nan_to_num(arm_xc)) < np.nan_to_num(arm_xr) * 1.0 + 0.004)
# side-image column band covered by the arm at this row
side_col = cy - P[:, 1] / PX
band_lo = cy - (np.nan_to_num(arm_yc) + np.nan_to_num(arm_yr) * 1.3 + 0.008) / PX
band_hi = cy - (np.nan_to_num(arm_yc) - np.nan_to_num(arm_yr) * 1.3 - 0.008) / PX
in_band = has_arm & (side_col >= band_lo) & (side_col <= band_hi)
side_block = in_band & ~is_arm
# head: the side painting holds the face profile; on the head use it only for the back/side hair
zf = P[:, 2] / 1.70
head_front_y = PARTS["torso"][ri_all, 2] - PARTS["torso"][ri_all, 3]
head_face = (zf > 0.845) & (P[:, 1] < head_front_y + 0.085)
side_block |= head_face
print("side-blocked texels", side_block.sum())

acc = np.zeros((len(P), 3), np.float32); wsum = np.zeros(len(P), np.float32)
acc2 = np.zeros((len(P), 3), np.float32); w2 = np.zeros(len(P), np.float32)
for name, dirv, rows, cols in views:
    col, ok = sample(img[name], rows, cols)
    msk = ndi.binary_erosion(M[name], iterations=2)
    inm = np.zeros(len(P), bool)
    ii = np.clip(np.round(rows).astype(int), 0, msk.shape[0] - 1); jj = np.clip(np.round(np.nan_to_num(cols, nan=-1)).astype(int), 0, msk.shape[1] - 1)
    inm = ok & msk[ii, jj]
    facing = np.clip(N @ dirv, 0, 1)
    vis = visibility(dirv, rows, cols)
    w = facing ** 3 * vis * inm * (1.0 if name != "side" else 0.8)
    # never paint with background showing through loose hair strands
    cmx, cmn = col.max(1), col.min(1)
    w = w * ~((cmx > 0.70) & ((cmx - cmn) / np.maximum(cmx, 1e-6) < 0.16))
    if name == "front":
        w = np.where(head_face, facing ** 0.8 * vis * inm, w)
    if name == "side":
        w = w * ~side_block

    acc += col * w[:, None]; wsum += w
    w_ = facing ** 3 * inm + 1e-4 * ok
    acc2 += col * w_[:, None]; w2 += w_
good = wsum > 0.05
color = acc / np.maximum(wsum, 1e-6)[:, None]
tex = np.zeros((RES, RES, 3), np.float32)
valid = np.zeros((RES, RES), bool)
tex[cov] = color
vv = np.zeros(len(P), bool); vv[:] = good
valid[cov] = vv
# fill texels no painting saw cleanly by diffusing from their good neighbours (normalised convolution)
fill = cov & ~valid
print("texels to fill", fill.sum())
cur = tex * valid[..., None]; wv = valid.astype(np.float32)
for sig in (2, 4, 8, 16, 32, 64):
    num = np.stack([ndi.gaussian_filter(cur[..., c], sig) for c in range(3)], -1)
    den = ndi.gaussian_filter(wv, sig)
    newv = fill & (den > 1e-3) & (wv == 0)
    tex[newv] = num[newv] / den[newv, None]
    cur[newv] = tex[newv]; wv[newv] = 1.0
    if not (fill & (wv == 0)).any():
        break
# bleed colour past UV island borders (avoids dark seams after mip-mapping)
idx = ndi.distance_transform_edt(~cov, return_distances=False, return_indices=True)
tex = tex[idx[0], idx[1]]
out = (np.clip(tex, 0, 1) * 255).astype(np.uint8)[::-1]      # Blender image rows are bottom-up
Image.fromarray(out).save("coach_albedo.png")
print("texels", cov.sum(), "low-weight", (wsum < 0.02).sum())
