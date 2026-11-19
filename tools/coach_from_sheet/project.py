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
# 4x detail-restored copy of the female half of the sheet (esrgan.py, Real-ESRGAN anime model) if present
import os
HI = None
if os.path.exists("sheet_f_x4.png"):
    HI = np.asarray(Image.open("sheet_f_x4.png").convert("RGB")).astype(np.float32) / 255
    HI_OX, HI_OY, HI_S = 440, 0, 4.0
    print("using 4x source", HI.shape)

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
if HI is not None:
    ox, oy = VIEWS["front"]
    big = np.zeros(HI.shape[:2], bool)
    rr2, cc2 = np.nonzero(logo)
    for dy in range(4):
        for dx in range(4):
            big[np.clip((rr2 + oy - HI_OY) * 4 + dy, 0, HI.shape[0] - 1), np.clip((cc2 + ox - HI_OX) * 4 + dx, 0, HI.shape[1] - 1)] = True
    big = ndi.binary_dilation(big, iterations=6)
    idx2 = ndi.distance_transform_edt(big, return_distances=False, return_indices=True)
    HI[big] = HI[idx2[0][big], idx2[1][big]]
    HI[big] = ndi.uniform_filter(HI, size=(9, 9, 1))[big]

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

# smooth the warp vertically so rows with a different interval count don't jump
bm_ok = ~np.isnan(back_map)
bm_f = np.where(bm_ok, back_map, 0.0)
num = ndi.gaussian_filter1d(bm_f, 3.0, axis=0); den = ndi.gaussian_filter1d(bm_ok.astype(np.float32), 3.0, axis=0)
back_map = np.where(bm_ok & (den > 0.3), num / np.maximum(den, 1e-6), np.nan).astype(np.float32)


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
half_band = np.maximum(np.nan_to_num(arm_yr) * 1.3, np.where(P[:, 2] < 1.0, 0.04, 0.0)) + 0.008
band_lo = cy - (np.nan_to_num(arm_yc) + half_band) / PX
band_hi = cy - (np.nan_to_num(arm_yc) - half_band) / PX
in_band = has_arm & (side_col >= band_lo) & (side_col <= band_hi)
side_block = in_band & ~is_arm
# head: the side painting holds the face profile; on the head use it only for the back/side hair
zf = P[:, 2] / 1.70
head_face = (zf > 0.845) & (P[:, 1] < -0.062)           # face zone of the sculpted head (front paint only)
# the side painting has a headset mic along the jaw: the lower side of the face takes front paint / fill instead
mic_zone = (P[:, 2] > 1.43) & (P[:, 2] < 1.53) & (P[:, 1] < -0.015)
side_block |= head_face | mic_zone
print("side-blocked texels", side_block.sum())

acc = np.zeros((len(P), 3), np.float32); wsum = np.zeros(len(P), np.float32)
acc2 = np.zeros((len(P), 3), np.float32); w2 = np.zeros(len(P), np.float32)
for name, dirv, rows, cols in views:
    col, ok = sample(img[name], rows, cols)
    if HI is not None:
        ox, oy = VIEWS[name]
        col2, ok2 = sample(HI, (rows + oy - HI_OY + 0.5) * HI_S - 0.5, (cols + ox - HI_OX + 0.5) * HI_S - 0.5)
        col = np.where(ok2[:, None], col2, col)
    msk = ndi.binary_erosion(M[name], iterations=2 if name == "side" else 4)
    inm = np.zeros(len(P), bool)
    ii = np.clip(np.round(rows).astype(int), 0, msk.shape[0] - 1); jj = np.clip(np.round(np.nan_to_num(cols, nan=-1)).astype(int), 0, msk.shape[1] - 1)
    inm = ok & msk[ii, jj]
    facing = np.clip(N @ dirv, 0, 1)
    vis = visibility(dirv, rows, cols)
    w = facing ** 3 * vis * inm * (1.0 if name != "side" else 0.8)
    if name == "side":
        # bare arms: never take dark fabric from where the painted arm and our arm disagree
        redish = (col[:, 0] > 0.45) & (col[:, 1] < 0.30) & ((col[:, 0] - col[:, 1]) > 0.30)
        w = w * ~(is_arm & (P[:, 2] > 0.97) & ((col.max(1) < 0.38) | redish))
        is_tail = (P[:, 2] > 1.05) & (np.abs(P[:, 0]) < 0.08) & (P[:, 1] > np.nan_to_num(PARTS["torso"][ri_all, 2] + PARTS["torso"][ri_all, 3], nan=9) - 0.005)
        hairlike = (col.max(1) < 0.62) & ((col[:, 0] - col[:, 2]) > 0.06)
        w = w * ~(is_tail & ~hairlike)
    # never paint with background showing through loose hair strands
    cmx, cmn = col.max(1), col.min(1)
    w = w * ~((cmx > 0.70) & ((cmx - cmn) / np.maximum(cmx, 1e-6) < 0.16))
    if name == "front":
        w = np.where(head_face, facing ** 0.8 * vis * inm, w)
        # under the jaw the front painting only has the jaw's ink outline: leave it to the neck fill
        w = w * ~(mic_zone & (facing < 0.6))     # jaw sides: the painting there is hair edge / jaw ink line
        w = w * ~((P[:, 2] > 1.40) & (P[:, 2] < 1.47) & (N[:, 2] < -0.30) & (P[:, 1] > -0.072))
    if name == "side":
        w = w * ~side_block

    acc += col * w[:, None]; wsum += w
    w_ = facing ** 3 * inm + 1e-4 * ok
    acc2 += col * w_[:, None]; w2 += w_
good = wsum > 0.05
color = acc / np.maximum(wsum, 1e-6)[:, None]
# jaw sides and under the jaw: no view paints them cleanly (hair edge, jaw ink line, headset mic), so they get the
# neck's own skin tone with a soft shadow toward the jaw instead of a fill from dark neighbours
neck_ref = good & (P[:, 2] > 1.40) & (P[:, 2] < 1.43) & (P[:, 1] < -0.02) & (np.abs(P[:, 0]) < 0.025)
skin_tone = np.median(color[neck_ref], axis=0) if neck_ref.sum() > 20 else np.array([0.80, 0.52, 0.36])
jaw_zone = (P[:, 2] > 1.415) & (P[:, 2] < 1.50) & (np.abs(P[:, 0]) > 0.018) & (P[:, 1] > -0.085) & (P[:, 1] < 0.03)
jaw_zone &= ~good | (color.max(1) < 0.50)          # only where there is no paint or the paint is ink / hair
shade_k = np.clip(1.0 - 0.22 * np.clip((P[:, 2] - 1.415) / 0.05, 0, 1), 0.75, 1.0)
color[jaw_zone] = skin_tone * shade_k[jaw_zone, None]
good = good | jaw_zone
print("jaw texels", jaw_zone.sum(), "skin", np.round(skin_tone, 2))
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
# soften the filled areas so they read as smooth shading rather than streaks (only filled texels change)
sm = np.stack([ndi.gaussian_filter(tex[..., c] * cov, 3.0) for c in range(3)], -1) / np.maximum(ndi.gaussian_filter(cov.astype(np.float32), 3.0), 1e-6)[..., None]
tex[fill] = sm[fill]
# soften the replaced jaw patch edges into their surroundings
jz = np.zeros((RES, RES), bool); jj = np.zeros(len(P), bool); jj[:] = jaw_zone; jz[cov] = jj
ring = ndi.binary_dilation(jz, iterations=6) & cov
sm2 = np.stack([ndi.gaussian_filter(tex[..., c] * cov, 4.0) for c in range(3)], -1) / np.maximum(ndi.gaussian_filter(cov.astype(np.float32), 4.0), 1e-6)[..., None]
tex[ring] = sm2[ring]
# bleed colour past UV island borders (avoids dark seams after mip-mapping)
idx = ndi.distance_transform_edt(~cov, return_distances=False, return_indices=True)
tex = tex[idx[0], idx[1]]
out = (np.clip(tex, 0, 1) * 255).astype(np.uint8)[::-1]      # Blender image rows are bottom-up
Image.fromarray(out).save("coach_albedo.png")
print("texels", cov.sum(), "low-weight", (wsum < 0.02).sum())
