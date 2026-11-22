import json
G = json.load(open('/tmp/icon4/glyphs.json'))
R = 'app/src/main/res'
S, TX, BASE = 0.044660, 23.595, 69.35
SQ = (75.1, BASE - 6.0, 6.0)
HDR = '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n    android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">\n'
def m(color):
    return f'''    <group android:translateX="{TX}" android:translateY="{BASE}" android:scaleX="{S}" android:scaleY="{S}">
        <path android:pathData="{G["m"]}" android:fillColor="{color}" />
    </group>\n'''
def sq(color, named=False):
    x, y, a = SQ
    p = f'<path android:pathData="M{x},{y} h{a} v{a} h-{a} z" android:fillColor="{color}" />'
    if named:
        return f'''    <group android:name="dot" android:pivotX="{x + a/2:.2f}" android:pivotY="{y + a:.2f}">
        {p}
    </group>\n'''
    return '    ' + p + '\n'
open(f'{R}/drawable/ic_launcher_foreground.xml', 'w').write('<?xml version="1.0" encoding="utf-8"?>\n<!-- MOTIONFORGE mark: a heavy extra-wide "M" (Archivo, wdth 125 / wght 900, as outlines) and the chalk-blue square the app\n     uses to mark lessons. Source: assets/branding/icon.svg (tools/branding_icon.py) -->\n' + HDR + m("#FFFFFFFF") + sq("#FF9CC4FF") + '</vector>\n')
open(f'{R}/drawable/ic_launcher_monochrome.xml', 'w').write('<?xml version="1.0" encoding="utf-8"?>\n<!-- Single-colour layer for Android 13+ themed icons -->\n' + HDR + m("#FF000000") + sq("#FF000000") + '</vector>\n')
open(f'{R}/drawable/ic_launcher_background.xml', 'w').write('<?xml version="1.0" encoding="utf-8"?>\n' + HDR + '    <path android:pathData="M0,0h108v108h-108z" android:fillColor="#FF000000" />\n</vector>\n')
anim = ('<?xml version="1.0" encoding="utf-8"?>\n'
 '<!-- Launch icon for Android 12+: one moment only — the square lands beside the M (about 0.6 s). -->\n'
 '<animated-vector xmlns:android="http://schemas.android.com/apk/res/android"\n    xmlns:aapt="http://schemas.android.com/aapt">\n'
 '    <aapt:attr name="android:drawable">\n        <vector android:width="108dp" android:height="108dp" android:viewportWidth="108" android:viewportHeight="108">\n'
 + m("#FFFFFFFF").replace('\n    ', '\n            ').replace('    <group', '            <group', 1)
 + sq("#FF9CC4FF", True).replace('\n    ', '\n            ').replace('    <group', '            <group', 1)
 + '        </vector>\n    </aapt:attr>\n' + '''    <target android:name="dot">
        <aapt:attr name="android:animation">
            <set>
                <objectAnimator android:propertyName="translateY" android:valueFrom="-16" android:valueTo="0" android:startOffset="120"
                    android:duration="420" android:interpolator="@android:interpolator/bounce" />
                <objectAnimator android:propertyName="scaleY" android:valueFrom="1.25" android:valueTo="1" android:startOffset="120"
                    android:duration="420" android:interpolator="@android:interpolator/decelerate_quad" />
            </set>
        </aapt:attr>
    </target>
</animated-vector>
''')
open(f'{R}/drawable/splash_icon_animated.xml', 'w').write(anim)
x0, y0, x1, y1 = G["wb"]
ws = 172.0 / (x1 - x0)
tx = 14.0 - ws * x0
ty = 40.0 + ws * G["wcap"] / 2
open(f'{R}/drawable/splash_branding.xml', 'w').write(f'''<?xml version="1.0" encoding="utf-8"?>
<!-- MOTIONFORGE wordmark (Archivo, wdth 125 / wght 800, as outlines), under the launch icon on Android 12+ -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="200dp" android:height="80dp" android:viewportWidth="200" android:viewportHeight="80">
    <group android:translateX="{tx:.3f}" android:translateY="{ty:.3f}" android:scaleX="{ws:.6f}" android:scaleY="{ws:.6f}">
        <path android:pathData="{G["w"]}" android:fillColor="#FFFFFFFF" />
    </group>
</vector>
''')
import cairosvg
cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="320" viewBox="0 0 200 80"><rect width="200" height="80" fill="#000"/><g transform="translate({tx:.3f} {ty:.3f}) scale({ws:.6f})"><path d="{G["w"]}" fill="#fff"/></g></svg>'.encode(), write_to='/tmp/icon4/wordmark.png')
open('/tmp/icon4/wordmark.svg','w').write(f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="320" viewBox="0 0 200 80"><rect width="200" height="80" fill="#000"/><g transform="translate({tx:.3f} {ty:.3f}) scale({ws:.6f})"><path d="{G["w"]}" fill="#fff"/></g></svg>')
print("ok")
