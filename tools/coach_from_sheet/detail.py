"""Turns the owner's painted shading into real surface relief and a light-free colour map.
In:  hull_uv.blend, coach_albedo.png, bake.npz (work dir)
Out: coach_height.png (16-bit), coach_basecolor.png (painted light removed), coach_normal.png (tangent space,
     baked in Blender from a displaced high-res copy -> run detail_bake.py next).
Method (the usual 'shape from painted shading' trick): band-pass the painting's luminance in texture space -> height
(dark creases between muscles become grooves, lit forms become bulges); strength per material (skin strongest,
fabric softer, hair follows the strands). The low-frequency painted light is divided out of the colour so the
renderer's real lights do that job."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

A = np.asarray(Image.open("coach_albedo.png").convert("RGB")).astype(np.float32) / 255     # rows top-down
B = np.load("bake.npz")
cov = (np.linalg.norm(B["nor"][..., :3], axis=2) > 0.5)[::-1]                             # bake rows bottom-up
pos = B["pos"][..., :3][::-1]
RES = A.shape[0]


def nconv(img, sig):
    w = ndi.gaussian_filter(cov.astype(np.float32), sig)
    if img.ndim == 3:
        return np.stack([ndi.gaussian_filter(img[..., c] * cov, sig) for c in range(img.shape[2])], -1) / np.maximum(w, 1e-4)[..., None]
    return ndi.gaussian_filter(img * cov, sig) / np.maximum(w, 1e-4)


L = A @ np.array([0.30, 0.55, 0.15], np.float32)
mx, mn = A.max(2), A.min(2)
sat = (mx - mn) / np.maximum(mx, 1e-4)
skin = cov & (A[..., 0] > 0.45) & (A[..., 0] > A[..., 2] * 1.35) & (sat > 0.25) & (sat < 0.75)
skin = ndi.binary_opening(skin, iterations=1)
hair = cov & (pos[..., 2] > 1.45) & ~skin
fabric = cov & ~skin & ~hair
# ---- clean projection smudges on bare skin (dark red-brown blotches where views were blended) before anything
#      is derived from the paint: inside the body's skin areas, reddish mid-dark pixels that are not skin are
#      replaced from the surrounding skin. Head and near-black straps/ink are left alone.
zone = ndi.binary_closing(skin, iterations=7) & cov & (pos[..., 2] < 1.43)
r_, g_, b_ = A[..., 0], A[..., 1], A[..., 2]
Lr = A @ np.array([0.30, 0.55, 0.15], np.float32)
defect = zone & ~skin & (Lr > 0.10) & (Lr < 0.55) & (r_ > g_ * 1.25) & (r_ > b_ * 1.2)
defect |= zone & skin & (Lr < 0.55 * nconv(Lr * skin, 6.0) / np.maximum(nconv(skin.astype(np.float32), 6.0), 1e-3)) & (r_ > g_ * 1.4)
# arms are bare from the glove cuff to the shoulder: anything there that is clearly darker than the arm's own
# skin, or not skin-coloured, is a projection smudge
PARTS = np.load("parts.npy", allow_pickle=True).item()
_h = np.load("hull.npz"); _PX, _ground, _top = float(_h["px"]), int(_h["ground"]), int(_h["top"])
_ri = np.clip(np.round(_ground - pos[..., 2] / _PX).astype(int) - _top, 0, len(PARTS["armL"]) - 1)
_side = np.where(pos[..., 0] > 0, 1, 0)
_axc = np.where(_side, PARTS["armL"][_ri, 0], PARTS["armR"][_ri, 0])
_axr = np.where(_side, PARTS["armL"][_ri, 1], PARTS["armR"][_ri, 1])
on_arm = ~np.isnan(_axc) & (np.abs(pos[..., 0] - np.nan_to_num(_axc)) < np.nan_to_num(_axr) * 1.15 + 0.004)
arm_zone = cov & ((on_arm & (pos[..., 2] < 1.215)) | (np.abs(pos[..., 0]) > 0.150)) & (pos[..., 2] > 0.985) & (pos[..., 2] < 1.38)
loc = nconv(Lr * skin, 9.0) / np.maximum(nconv(skin.astype(np.float32), 9.0), 1e-3)
defect |= arm_zone & ((Lr < 0.70 * loc) | ~skin)
# upper inner arm / deltoid (above the armpit): only reddish-brown smudges, never the near-black bra straps
upper = cov & on_arm & (pos[..., 2] >= 1.215) & (pos[..., 2] < 1.38) & (np.abs(pos[..., 0]) > 0.095)
defect |= upper & (Lr > 0.14) & ((~skin & (r_ > g_ * 1.2)) | (skin & (Lr < 0.72 * loc)))
zone = zone | arm_zone | upper
defect = ndi.binary_dilation(defect, iterations=2) & zone
good_skin = skin & ~defect
fillc = np.stack([ndi.gaussian_filter(A[..., c] * good_skin, 5.0) for c in range(3)], -1) / np.maximum(ndi.gaussian_filter(good_skin.astype(np.float32), 5.0), 1e-4)[..., None]
A = np.where(defect[..., None], fillc, A)
skin = skin | defect
# painted crease shadows on the arms (inner elbow, armpit) read as bruises once real light is on: lift dark
# skin there toward the local skin tone (relief keeps the crease)
Lr2 = A @ np.array([0.30, 0.55, 0.15], np.float32)
armish = (arm_zone | upper) & skin
armL_med = float(np.median(Lr2[armish])) if armish.sum() > 100 else 0.5
floor_ = np.maximum(0.86 * loc, 0.72 * armL_med)          # never far below the arm's overall skin tone
lift = np.where(armish, np.clip(floor_ / np.maximum(Lr2, 1e-3), 1.0, 1.9), 1.0)
lift = ndi.gaussian_filter(lift, 1.5)
A = np.clip(A * lift[..., None], 0, 1)
# bruise-coloured patches (too little green for skin) on arms / shoulders: recolour to the local skin hue,
# keeping their brightness
armzone2 = cov & (np.abs(pos[..., 0]) > 0.085) & (pos[..., 2] > 0.985) & (pos[..., 2] < 1.40)
sk = armzone2 & skin
Lr3 = A @ np.array([0.30, 0.55, 0.15], np.float32)
ref = np.stack([ndi.gaussian_filter(A[..., c] * sk, 12.0) for c in range(3)], -1) / np.maximum(ndi.gaussian_filter(sk.astype(np.float32), 12.0), 1e-4)[..., None]
refL = ref @ np.array([0.30, 0.55, 0.15], np.float32)
gr = A[..., 1] / np.maximum(A[..., 0], 1e-3)
gr_med = float(np.median(gr[sk])) if sk.sum() > 100 else 0.56
bruise = armzone2 & (A[..., 0] > 0.22) & (gr < gr_med - 0.08) & (Lr3 > 0.12)
glob = np.median(A[sk], axis=0) if sk.sum() > 100 else np.array([0.85, 0.49, 0.33], np.float32)
ref = 0.35 * ref + 0.65 * glob[None, None, :]
refL = ref @ np.array([0.30, 0.55, 0.15], np.float32)
bruise = ndi.binary_dilation(bruise, iterations=2) & armzone2 & (Lr3 > 0.12)
w_ = ndi.gaussian_filter(bruise.astype(np.float32), 1.5)
recol = ref * np.clip(np.maximum(Lr3, 0.75 * refL) / np.maximum(refL, 1e-3), 0.6, 1.3)[..., None]
A = np.clip(A * (1 - w_[..., None]) + recol * w_[..., None], 0, 1)
print("bruise texels", int(bruise.sum()))
print("smudge texels cleaned", int(defect.sum()))
L = A @ np.array([0.30, 0.55, 0.15], np.float32)
wskin = ndi.gaussian_filter(skin.astype(np.float32), 2.0)
whair = ndi.gaussian_filter(hair.astype(np.float32), 2.0)
wfab = np.clip(1 - wskin - whair, 0, 1)

# ---- height: band-pass of luminance (fine creases + muscle masses), clipped so ink lines don't become trenches
fine = nconv(L, 1.2) - nconv(L, 6.0)
mass = nconv(L, 6.0) - nconv(L, 28.0)
fine = np.clip(fine, -0.12, 0.12)
mass = np.clip(mass, -0.20, 0.20)
strand = np.clip(nconv(L, 0.6) - nconv(L, 2.5), -0.10, 0.10)       # hair strands / face creases
face = ndi.gaussian_filter(((pos[..., 2] > 1.43) & skin).astype(np.float32), 2.0)
h = (wskin * (0.55 * fine + 1.0 * mass) + wfab * (0.35 * fine + 0.30 * mass)
     + whair * (0.9 * fine + 1.6 * strand + 0.25 * mass) + face * (0.6 * strand - 0.4 * mass))
h = ndi.gaussian_filter(h, 0.7)
h = np.where(cov, h, 0)
idx = ndi.distance_transform_edt(~cov, return_distances=False, return_indices=True)
h = h[idx[0], idx[1]]
H = np.clip(0.5 + h * 1.6, 0, 1)
Image.fromarray((H * 65535).astype(np.uint16)).save("coach_height.png")

# ---- de-light: divide out the low-frequency painted light, keep about a third of it (painterly look)
low = nconv(L, 22.0)
target = np.zeros_like(L)
for m in (skin, fabric, hair):
    if m.sum():
        target[m] = np.median(L[m])
target = nconv(target, 6.0)
gain = np.clip((target / np.maximum(low, 1e-3)) ** 0.45, 0.70, 1.45)
# painted specular highlights on skin (near-white streaks) are light, not colour: pull them back
hl = wskin * np.clip((L - nconv(L, 3.0) - 0.06) / 0.10, 0, 1)
base = A * gain[..., None]
base = base * (1 - 0.55 * hl[..., None]) + nconv(A, 3.0) * gain[..., None] * (0.55 * hl[..., None])
base = np.clip(base, 0, 1)
base = np.where(cov[..., None], base, A)
Image.fromarray((base * 255 + 0.5).astype(np.uint8)).save("coach_basecolor.png")
# roughness / metal (glTF packs roughness in G, metal in B): skin satin, fabric matte, hair glossier
rough = wskin * 0.48 + wfab * 0.68 + whair * 0.36
rough = rough + 0.06 * np.clip(-fine * 4, 0, 1)          # creases a touch rougher
mr = np.zeros(A.shape, np.float32); mr[..., 1] = np.clip(rough, 0.2, 0.9)
mr[..., 0] = 1.0
Image.fromarray((mr * 255 + 0.5).astype(np.uint8)).save("coach_mr.png")
import json
arm_skin = skin & (pos[..., 2] > 0.95) & (pos[..., 2] < 1.15) & (np.abs(pos[..., 0]) > 0.17)
json.dump({"skin_rgb": [float(v) for v in np.median(base[arm_skin], axis=0)]}, open("coach_skin.json", "w"))
print("skin %.0f%% fabric %.0f%% hair %.0f%%" % (100 * skin.sum() / cov.sum(), 100 * fabric.sum() / cov.sum(), 100 * hair.sum() / cov.sum()),
      "height range", round(float(h.min()), 3), round(float(h.max()), 3))
