"""Python mirror of ExcursionCounting.kt (tuning only; CI runs the Kotlin)."""
import math, sys
from sig import load
from mirror import Tracker, vis, mid, torso_tilt, px, LS,RS,LE,RE,LW,RW,LH,RH,LK,RK,LA,RA
LFI,RFI=31,32
def torso(L,w,h):
    if not vis(L,LS,RS,LH,RH): return None
    s=mid(L,LS,RS,w,h); hp=mid(L,LH,RH,w,h); n=math.hypot(s[0]-hp[0],s[1]-hp[1])
    return None if n<5 else (s,hp,n)
def tilt(s,hp):
    dy=hp[1]-s[1]; a=math.degrees(math.atan2(abs(s[0]-hp[0]),abs(dy))); return 180-a if dy<0 else a
class Exc:
    def __init__(s,d,travel,ret=0.8,minrep=700,win=3): s.d,s.tr,s.ret,s.minrep,s.win=d,travel,ret,minrep,win; s.count=0; s.ph="U"; s.w=[]; s.events=[]
    def update(s,t,w,h,L,ok):
        raw=s.sig(L,w,h) if ok and L else None
        if raw is None: s.ph="U"; s.w=[]; return None
        s.w.append(raw); s.w=s.w[-s.win:]; v=sum(s.w)/len(s.w); x=s.d*v
        if s.ph=="U": s.ph="T"; s.rest=x
        elif s.ph=="T":
            s.rest=min(s.rest,x)
            if x>s.rest+s.tr: s.ph="B"; s.ext=x; s.t0=t
        else:
            s.ext=max(s.ext,x)
            if x<s.ext-s.ret*s.tr:
                if t-s.t0>=s.minrep: s.count+=1; s.events.append(t)
                s.ph="T"; s.rest=x
        return v
class ArmLift(Exc):
    def __init__(s,tr,maxtilt=40): super().__init__(1,tr); s.mt=maxtilt
    def sig(s,L,w,h):
        T=torso(L,w,h)
        if not T or tilt(T[0],T[1])>s.mt: return None
        v=[(L[a][1]*h-L[c][1]*h)/T[2] for a,b,c in ((LS,LE,LW),(RS,RE,RW)) if vis(L,a,c)]
        return sum(v)/len(v) if v else None
class Row(Exc):
    def __init__(s,tr=0.22,mt=20): super().__init__(1,tr); s.mt=mt; s.st=0
    def sig(s,L,w,h):
        T=torso(L,w,h)
        if not T: return None
        s.st=max(s.st,T[2]); p=max(tilt(T[0],T[1]),math.degrees(math.acos(min(1,T[2]/s.st))))
        if p<s.mt: return None
        v=[(T[1][1]-L[c][1]*h)/T[2] for c in (LW,RW) if L[c][3]>=0.6]
        return sum(v)/len(v) if v else None
class Band(Exc):
    def __init__(s,tr=0.6,mf=0.45): super().__init__(1,tr); s.mf=mf
    def sig(s,L,w,h):
        T=torso(L,w,h)
        if not T: return None
        sw=px(L,LS,RS,w,h)
        if sw/T[2]<s.mf or not vis(L,LW,RW): return None
        return abs((L[LW][0]-L[RW][0])*w)/sw
class Hinge(Exc):
    def __init__(s,tr=30): super().__init__(1,tr); s.st=0
    def sig(s,L,w,h):
        T=torso(L,w,h)
        if not T: return None
        s.st=max(s.st,T[2]); return max(tilt(T[0],T[1]),math.degrees(math.acos(min(1,T[2]/s.st))))
class Bridge(Exc):
    def __init__(s,tr=20): super().__init__(1,tr)
    def sig(s,L,w,h):
        left=L[LH][3]+L[LK][3]>=L[RH][3]+L[RK][3]
        a,b,c=(LS,LH,LK) if left else (RS,RH,RK)
        if not vis(L,a,b,c): return None
        T=torso(L,w,h)
        if not T or tilt(T[0],T[1])<50: return None
        ux,uy=(L[a][0]-L[b][0])*w,(L[a][1]-L[b][1])*h; vx,vy=(L[c][0]-L[b][0])*w,(L[c][1]-L[b][1])*h
        d=math.hypot(ux,uy)*math.hypot(vx,vy)
        return math.degrees(math.acos(max(-1,min(1,(ux*vx+uy*vy)/d)))) if d>1 else None
class Calf(Exc):
    def __init__(s,tr=0.07): super().__init__(1,tr)
    def sig(s,L,w,h):
        T=torso(L,w,h)
        if not T or tilt(T[0],T[1])>30: return None
        v=[((L[t][1]-L[a][1])*h)/max(1,px(L,k,a,w,h)) for k,a,t in ((LK,LA,LFI),(RK,RA,RFI)) if vis(L,k,a,t)]
        return sum(v)/len(v) if v else None
KINDS={"curl":lambda:ArmLift(0.45),"press":lambda:ArmLift(0.45),"lateral":lambda:ArmLift(0.40),"stepjack":lambda:ArmLift(0.9),
       "row":Row,"band":Band,"hinge":Hinge,"bridge":Bridge,"calf":Calf}
def run(path,c,verbose=False):
    tr=Tracker(); trace=[]; st={}
    for t,w,h,L in load(path):
        s_=tr.update(L); st[s_]=st.get(s_,0)+1
        v=c.update(t,w,h,L,s_=="TRACKING"); trace.append("--" if v is None else "%.2f"%v)
    if verbose:
        for i in range(0,len(trace),15): print("  ",i//15," ".join(trace[i:i+15]))
    return c.count,st
if __name__=="__main__":
    k=sys.argv[1]
    for p in sys.argv[2:]:
        n,st=run(p,KINDS[k](),verbose="-v" in sys.argv); 
        if p!="-v": print(p.split('/')[-1],k,"count",n,st)
