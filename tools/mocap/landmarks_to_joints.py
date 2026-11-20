"""Offline tooling: turn MediaPipe world landmarks (video_pose.py output) into the joint-position format of
assets/mocap (P: frames x joints x 3, metres, Blender Z-up, CMU joint names, 30 fps) so the existing retarget
(tools/blender/mocap_retarget.py) can drive the coach rig with it.

Usage: python landmarks_to_joints.py IN.npz OUT.npz [--first F] [--last F] [--sigma S]
Untracked / low-visibility frames are interpolated from neighbours; positions are resampled to 30 fps and
smoothed (Gaussian; --speed / --reverse retime it, sigma in output frames; depth gets 1.5x, it is the noisiest axis for a single camera)."""
import argparse
import numpy as np
from scipy.ndimage import gaussian_filter1d

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--first", type=int, default=0); ap.add_argument("--last", type=int, default=-1)
ap.add_argument("--sigma", type=float, default=1.6)
ap.add_argument("--min-vis", type=float, default=0.35)
ap.add_argument("--speed", type=float, default=1.0, help="playback speed (0.5 = half speed, slowed to a lesson tempo)")
ap.add_argument("--reverse", action="store_true", help="play backwards (e.g. a lowering phase reused for rising)")
a = ap.parse_args()
d = np.load(a.inp)
W, vis, ok, fps = d["world"].astype(np.float64), d["vis"], d["ok"], float(d["fps"])
last = len(W) - 1 if a.last < 0 else a.last
W, vis, ok = W[a.first:last + 1], vis[a.first:last + 1], ok[a.first:last + 1]
F = len(W)
# MediaPipe world: x right, y down, z away from camera  ->  Blender: X = x, Y = z, Z = -y (right-handed, Z up)
P = np.stack([W[..., 0], W[..., 2], -W[..., 1]], -1)
# drop unreliable samples per landmark and interpolate them in time
t = np.arange(F)
for j in range(33):
    good = ok & (vis[:, j] >= a.min_vis)
    if good.sum() >= 2 and not good.all():
        for c in range(3):
            P[~good, j, c] = np.interp(t[~good], t[good], P[good, j, c])
# resample to 30 fps
n_out = max(2, int(round((F - 1) * 30.0 / fps / a.speed)) + 1)
to = np.linspace(0, F - 1, n_out)
P = np.stack([np.stack([np.interp(to, t, P[:, j, c]) for c in range(3)], -1) for j in range(33)], 1)
P[..., 0] = gaussian_filter1d(P[..., 0], a.sigma, axis=0, mode="nearest")
P[..., 2] = gaussian_filter1d(P[..., 2], a.sigma, axis=0, mode="nearest")
P[..., 1] = gaussian_filter1d(P[..., 1], a.sigma * 1.5, axis=0, mode="nearest")

# MediaPipe world landmarks are hip-centred, so the body never drops. Give it its real height: per frame, move
# everything so the lowest foot point (heels, ankles, toes) sits on the floor (Z = 0).
low = P[:, [27, 28, 29, 30, 31, 32], 2].min(1)
P[..., 2] -= gaussian_filter1d(low, a.sigma, mode="nearest")[:, None]

L = lambda i: P[:, i]
mid = lambda i, k: (P[:, i] + P[:, k]) * 0.5
hips, neck = mid(23, 24), mid(11, 12)
J = {
    "Hips": hips, "Spine": hips + (neck - hips) * 0.3, "Spine1": hips + (neck - hips) * 0.65, "Neck1": neck,
    "Head": mid(7, 8),
    "LeftShoulder": neck, "LeftArm": L(11), "LeftForeArm": L(13), "LeftHand": L(15), "LeftFingerBase": mid(17, 19),
    "RightShoulder": neck, "RightArm": L(12), "RightForeArm": L(14), "RightHand": L(16), "RightFingerBase": mid(18, 20),
    "LeftUpLeg": L(23), "LeftLeg": L(25), "LeftFoot": L(27), "LeftToeBase": L(31),
    "RightUpLeg": L(24), "RightLeg": L(26), "RightFoot": L(28), "RightToeBase": L(32),
}
names = list(J)
out = np.stack([J[n] for n in names], 1).astype(np.float32)
if a.reverse:
    out = out[::-1].copy()
np.savez_compressed(a.out, P=out, names=np.array(names))
print(a.out, out.shape, "from", F, "frames at", round(fps, 2), "fps")
