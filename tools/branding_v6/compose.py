"""MOTIONFORGE icon & launch screen v6, step 2: compose the app's icon, themed icon, splash icon, launch art and the
Play Store icon from the cut-outs (tools/branding_v6/prepare.py), and write them into the app's resources.

Icon: her portrait and his (mirrored, so the pair flexes outwards) in front of a timing-yellow disc on black, inside
the adaptive icon's 66 dp safe zone. Launch art: both full-body front double-biceps poses side by side.
Usage: python tools/branding_v6/compose.py <work_dir>   (run from the repo root)
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

work = sys.argv[1]
RES = 'app/src/main/res'
YELLOW = (255, 214, 10, 255)

def load(name, fade=0.0, rfade=0.0, mirror=False):
    a = Image.open(os.path.join(work, name + '_cut.png')).convert('RGBA')
    al = np.asarray(a.split()[3]).astype(float)
    h, w = al.shape
    if fade:      # the portrait's cut-off bottom fades into the black
        n = int(h * fade); g = np.ones(h); g[-n:] = np.linspace(1, 0, n) ** 1.4; al *= g[:, None]
    if rfade:     # his portrait is cut off at the right edge of the sheet's panel
        n = int(w * rfade); g = np.ones(w); g[-n:] = np.linspace(1, 0, n) ** 1.3; al *= g[None, :]
    a.putalpha(Image.fromarray(al.astype('uint8')))
    return ImageOps.mirror(a) if mirror else a

M_BUST = load('m_bust', 0.25, 0.14, mirror=True)
F_BUST = load('f_bust', 0.25)
M_FRONT = load('m_front'); F_FRONT = load('f_front')

def fit(a, h):
    s = h / a.height
    out = a.resize((max(1, round(a.width * s)), max(1, round(a.height * s))), Image.LANCZOS)
    return out.filter(ImageFilter.UnsharpMask(radius=max(0.6, h / 900), percent=45, threshold=2)) if s < 1 else out

def duo(S, disc=True, alpha_only=False):
    """The pair on the full 108 dp canvas (S px). The whole group is drawn at G of its layout size around the
    middle, which keeps both heads, both raised fists and the disc inside the central 66 dp safe zone."""
    G = 0.73
    c = Image.new('RGBA', (S, S), (0, 0, 0, 0 if alpha_only else 255))
    def X(u): return S * (0.485 + (u - 0.5) * G)
    def Yy(v): return S * (0.47 + (v - 0.47) * G)
    if disc and not alpha_only:
        r = S * 0.215 * G
        d = Image.new('RGBA', (S, S)); ImageDraw.Draw(d).ellipse((X(0.5) - r, Yy(0.405) - r, X(0.5) + r, Yy(0.405) + r), fill=YELLOW)
        c.alpha_composite(d)
    m = fit(M_BUST, round(S * 0.49 * G)); f = fit(F_BUST, round(S * 0.46 * G))
    c.alpha_composite(m, (round(X(0.52) - m.width * 0.16), round(Yy(0.27))))
    c.alpha_composite(f, (round(X(0.52) - f.width * 0.90), round(Yy(0.30))))
    return c

def launch_art(S):
    c = Image.new('RGBA', (S, S), (0, 0, 0, 255))
    m = fit(M_FRONT, round(S * 0.74)); f = fit(F_FRONT, round(S * 0.70))
    c.alpha_composite(f, (round(S * 0.5 - f.width * 0.97), round(S * 0.5 - f.height / 2 + S * 0.02)))
    c.alpha_composite(m, (round(S * 0.5 - m.width * 0.03), round(S * 0.5 - m.height / 2)))
    return c

def save_webp(img, path, lossless=False, q=95):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, 'WEBP', lossless=lossless, quality=q, method=6)

DENS = {'mdpi': 1, 'hdpi': 1.5, 'xhdpi': 2, 'xxhdpi': 3, 'xxxhdpi': 4}
for d, k in DENS.items():
    S = round(108 * k)
    save_webp(duo(S).convert('RGB'), f'{RES}/mipmap-{d}/ic_launcher_foreground.webp', q=96)
    # themed icon (Android 13+): the system tints this one-colour shape; only its alpha counts
    mono = duo(S, alpha_only=True)
    a = mono.split()[3].point(lambda v: min(255, v * 2))
    save_webp(Image.merge('RGBA', (Image.new('L', (S, S), 255),) * 3 + (a,)), f'{RES}/mipmap-{d}/ic_launcher_monochrome.webp', lossless=True)
# Android 12+ launch icon without an icon background: 288 dp canvas, content inside the central 192 dp circle
for d, k in (('xhdpi', 2), ('xxhdpi', 3), ('xxxhdpi', 4)):
    save_webp(duo(round(288 * k)).convert('RGB'), f'{RES}/drawable-{d}/splash_icon.webp', q=96)
# the app's own launch art (shown for about a second after the system launch screen)
save_webp(launch_art(1440).convert('RGB'), f'{RES}/drawable-nodpi/launch_duo.webp', q=94)
# Google Play listing icon, 512 x 512, full square (Play applies its own mask)
os.makedirs('assets/branding', exist_ok=True)
duo(512).convert('RGB').save('assets/branding/icon_512.png', optimize=True)
duo(1024).convert('RGB').save('assets/branding/v6/icon_1024.png', optimize=True)
print('done')
