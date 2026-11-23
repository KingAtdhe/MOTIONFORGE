import sys, math
from mirror2 import *
def arm_feats(L,w,h,T):
    out={}
    for side,(s,e,wr) in (("L",(LS,LE,LW)),("R",(RS,RE,RW))):
        if not vis(L,s,e,wr): out[side]=None; continue
        el=(L[s][1]*h-L[e][1]*h)/T[2]; wl=(L[s][1]*h-L[wr][1]*h)/T[2]
        ch=px(L,s,e,w,h)+px(L,e,wr,w,h); reach=px(L,s,wr,w,h)/ch if ch>1 else 0
        out[side]=(el,wl,reach)
    return out
f=sys.argv[1]; tr=Tracker(); rows=[]
for t,w,h,L in load(f):
    ok=tr.update(L)=="TRACKING"; T=torso(L,w,h) if L else None
    if not ok or not T: rows.append("  --  "); continue
    a=arm_feats(L,w,h,T)
    rows.append("|".join("%+.1f%+.1f%.1f"%v if v else "  x  " for v in (a["L"],a["R"])))
for i in range(0,len(rows),6): print(i,"  ".join(rows[i:i+6]))
