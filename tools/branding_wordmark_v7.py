"""Wordmark v7: CORZA in Barlow Semi Condensed Bold, as vector outlines (white on the black plate).

Five wide-spaced capitals, cap height 26 dp, centred in the 200x80 dp box the launch screen and LaunchIntro use.
Usage: python3 tools/branding_wordmark_v7.py app/src/main/res/font/barlow_semicond_bold.ttf app/src/main/res/drawable/splash_branding.xml
"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

WORD, TRACK, CAP_DP = "CORZA", 0.16, 26.0
font = TTFont(sys.argv[1]); gs = font.getGlyphSet(); cmap = font.getBestCmap(); upm = font["head"].unitsPerEm
x = 0; cmds = []; bp = BoundsPen(gs)
for ch in WORD:
    g = cmap[ord(ch)]
    pen = SVGPathPen(gs); gs[g].draw(TransformPen(pen, (1, 0, 0, -1, x, 0))); cmds.append(pen.getCommands())
    gs[g].draw(TransformPen(bp, (1, 0, 0, 1, x, 0)))
    x += gs[g].width + TRACK * upm
x0, y0, x1, y1 = bp.bounds
cap = font["OS/2"].sCapHeight
ws = CAP_DP / cap
tx = 100.0 - ws * (x0 + x1) / 2; ty = 40.0 + ws * cap / 2
assert ws * (x1 - x0) < 190, "wordmark wider than its box"
open(sys.argv[2], "w").write(f'''<?xml version="1.0" encoding="utf-8"?>
<!-- CORZA wordmark v7 (Barlow Semi Condensed Bold, as outlines), under the launch icon on Android 12+ and in the launch intro -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="200dp" android:height="80dp" android:viewportWidth="200" android:viewportHeight="80">
    <group android:translateX="{tx:.3f}" android:translateY="{ty:.3f}" android:scaleX="{ws:.6f}" android:scaleY="{ws:.6f}">
        <path android:pathData="{" ".join(cmds)}" android:fillColor="#FFFFFFFF" />
    </group>
</vector>
''')
print(f"ok width={ws*(x1-x0):.1f}dp")
