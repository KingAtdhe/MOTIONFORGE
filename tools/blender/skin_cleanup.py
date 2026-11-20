"""Remove painted white/pale highlight streaks from the skin in a generated texture (sRGB float arrays, H x W x 3).

The source texture paints glossy highlights as near-white strokes across arms and legs; under real lights they read
as stripes. Skin pixels are found by hue/saturation, the local skin colour is estimated by a masked blur, and pale,
desaturated pixels inside skin areas are replaced by that colour (feathered), keeping the darker muscle shading."""
import numpy as np
from scipy.ndimage import gaussian_filter


def _hsv(rgb):
    mx = rgb.max(-1)
    mn = rgb.min(-1)
    d = mx - mn
    s = np.where(mx > 1e-6, d / np.maximum(mx, 1e-6), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.maximum(d, 1e-6), 0)
    gc = np.where(m, (mx - g) / np.maximum(d, 1e-6), 0)
    bc = np.where(m, (mx - b) / np.maximum(d, 1e-6), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (h / 6.0) % 1.0
    return h, s, mx


def clean(rgb, sigma=None):
    H = rgb.shape[0]
    sigma = sigma or H / 512.0 * 3.0
    h, s, v = _hsv(rgb)
    skin = ((h > 0.015) & (h < 0.11) & (s > 0.42) & (v > 0.30)).astype(np.float32)
    wsum = gaussian_filter(skin, sigma)
    avg = np.stack([gaussian_filter(rgb[..., c] * skin, sigma) for c in range(3)], -1) / np.maximum(wsum, 1e-4)[..., None]
    lum = rgb @ np.array([0.299, 0.587, 0.114])
    alum = avg @ np.array([0.299, 0.587, 0.114])
    near = wsum > 0.15                                   # inside / right next to skin
    pale = (s < 0.55) & (lum > alum * 0.95)             # whitish, desaturated stroke
    bright = lum > alum * 1.22                           # overexposed highlight on skin
    streak = (near & (pale | bright) & (skin < 0.5)).astype(np.float32)
    streak = np.maximum(streak, (near & bright).astype(np.float32))
    a = np.clip(gaussian_filter(streak, 0.8) * 1.6, 0, 1)[..., None]
    out = rgb * (1 - a) + avg * a
    return np.clip(out, 0, 1), float(streak.mean())
