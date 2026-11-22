"""Python mirror of the app's TrackingStateEvaluator(FULL_BODY) + rep counters, for fast threshold tuning.
The Kotlin code is the truth; CI runs it on the same fixtures."""
import math, sys
from sig import load
LS,RS,LE,RE,LW,RW,LH,RH,LK,RK,LA,RA=11,12,13,14,15,16,23,24,25,26,27,28
FULL=[LS,RS,LH,RH,LK,RK,LA,RA]
class Tracker:
    def __init__(s, req=FULL, mv=0.6, edge=0.02, stable=5): s.req,s.mv,s.edge,s.stable,s.g=req,mv,edge,stable,0
    def update(s, L):
        if L is None: s.g=0; return "NOPERSON"
        left=[LK,LA]; right=[RK,RA]
        near=left if min(L[i][3] for i in left)>=min(L[i][3] for i in right) else right
        r=[L[i] for i in [LS,RS,LH,RH]+near]
        if any(p[0]<s.edge or p[0]>1-s.edge or p[1]<s.edge or p[1]>1-s.edge for p in r): s.g=0; return "ADJUST"
        if sum(p[3] for p in r)/len(r)<s.mv: s.g=0; return "LOWCONF"
        if any(p[3]<s.mv for p in r): s.g=0; return "OCCLUDED"
        s.g+=1; return "TRACKING" if s.g>=s.stable else "CALIB"
def ang(L,a,b,c,w,h,mv=0.6):
    if min(L[a][3],L[b][3],L[c][3])<mv: return None
    ux,uy=(L[a][0]-L[b][0])*w,(L[a][1]-L[b][1])*h; vx,vy=(L[c][0]-L[b][0])*w,(L[c][1]-L[b][1])*h
    d=math.hypot(ux,uy)*math.hypot(vx,vy)
    return None if d==0 else math.degrees(math.acos(max(-1,min(1,(ux*vx+uy*vy)/d))))
def vis(L,*ix,mv=0.6): return all(L[i][3]>=mv for i in ix)
def mid(L,a,b,w,h): return ((L[a][0]+L[b][0])/2*w,(L[a][1]+L[b][1])/2*h)
def torso_tilt(L,w,h):
    if not vis(L,LS,RS) and not (vis(L,LS,LH) or vis(L,RS,RH)): return None
    s=mid(L,LS,RS,w,h); hp=mid(L,LH,RH,w,h); dy=hp[1]-s[1]
    a=math.degrees(math.atan2(abs(s[0]-hp[0]),dy)); return 180-a if dy<0 else a
def px(L,a,b,w,h): return math.hypot((L[a][0]-L[b][0])*w,(L[a][1]-L[b][1])*h)
def frontal(L,w,h):
    if not vis(L,LS,RS,LH,RH): return None
    t=(px(L,LS,LH,w,h)+px(L,RS,RH,w,h))/2
    return None if t<5 else px(L,LS,RS,w,h)/t
class Cycle:
    def __init__(s, top, bottom, shallow, minrep=700, win=3): s.top,s.bot,s.sh,s.minrep,s.win=top,bottom,shallow,minrep,win; s.count=0; s.phase="U"; s.w=[]; s.events=[]; s.minA=180
    def angle(s,L,w,h): raise NotImplementedError
    def observe(s,L,w,h): pass
    def cues(s): return []
    def start(s): pass
    margin=10; band=8
    def update(s,t,w,h,L,tracking):
        s.t=t
        raw=s.angle(L,w,h) if (tracking and L is not None) else None
        if raw is None: s.phase="U"; s.w=[]; return None
        s.w.append(raw); s.w=s.w[-s.win:]; a=sum(s.w)/len(s.w)
        if s.phase in("D","B"): s.minA=min(s.minA,a)
        if s.phase=="U":
            if a>=s.top: s.phase="T"
        elif s.phase=="T":
            if a<s.top-s.margin: s.phase="D"; s.t0=t; s.minA=a; s.start()
        elif s.phase=="D":
            if a<=s.bot: s.phase="B"; s.tb=t
            elif a>=s.top:
                if s.minA<=s.sh: s.events.append((t,"shallow",round(s.minA)))
                s.phase="T"
        elif s.phase=="B":
            if a>=s.top:
                if t-s.t0>=s.minrep: s.count+=1; s.events.append((t,"rep%d"%s.count,s.cues()))
                s.phase="T"
        if s.phase=="B" and a<=s.bot+s.band: s.observe(L,w,h)
        return a
class Squat(Cycle):
    def __init__(s): super().__init__(160,115,135)
    def start(s): s.fb=s.ki=s.sb=s.lb=0
    def angle(s,L,w,h):
        v=[x for x in (ang(L,LH,LK,LA,w,h),ang(L,RH,RK,RA,w,h)) if x is not None]; return sum(v)/len(v) if v else None
    def observe(s,L,w,h):
        if not vis(L,LS,RS,LH,RH): return
        t=(px(L,LS,LH,w,h)+px(L,RS,RH,w,h))/2
        if t<10: return
        if px(L,LS,RS,w,h)/t>=0.40:
            if not vis(L,LK,RK,LA,RA): return
            an=abs((L[LA][0]-L[RA][0])*w)
            if an<10: return
            s.fb+=1; s.ki+= abs((L[LK][0]-L[RK][0])*w)/an<0.75
        else:
            sx,sy=mid(L,LS,RS,w,h); hx,hy=mid(L,LH,RH,w,h)
            s.sb+=1; s.lb+= math.degrees(math.atan2(abs(sx-hx),hy-sy))>60
    def cues(s):
        c=[]
        if s.fb>=3 and s.ki>=0.6*s.fb: c.append("KNEES_IN")
        if s.sb>=3 and s.lb>=0.6*s.sb: c.append("CHEST_DROP")
        return c
class PushUp(Cycle):
    def __init__(s,knees=False,top=150,bottom=105,shallow=130,tilt=45,fore=0.75,bend=25): super().__init__(top,bottom,shallow); s.knees,s.tilt,s.fore,s.bend=knees,tilt,fore,bend
    def start(s): s.sb=s.sag=s.pike=0
    def inpos(s,L,w,h):
        tl=torso_tilt(L,w,h)
        if tl is None: return False
        pairs=[(a,b) for a,b in ((LS,LW),(RS,RW)) if vis(L,a,b)]
        if not pairs or not all(L[b][1]>L[a][1] for a,b in pairs): return False
        if tl>=s.tilt: return True
        fr=frontal(L,w,h); return fr is not None and fr>=1/s.fore
    def angle(s,L,w,h):
        v=[x for x in (ang(L,LS,LE,LW,w,h),ang(L,RS,RE,RW,w,h)) if x is not None]
        if not v or not s.inpos(L,w,h): return None
        return sum(v)/len(v)
    def observe(s,L,w,h):
        fr=frontal(L,w,h)
        if fr is None or fr>0.45: return
        fa=(LK,RK) if s.knees else (LA,RA)
        left=L[LH][3]+L[fa[0]][3]>=L[RH][3]+L[fa[1]][3]
        sh,hp,e=(LS,LH,fa[0]) if left else (RS,RH,fa[1])
        a=ang(L,sh,hp,e,w,h)
        if a is None: return
        s.sb+=1
        if 180-a>s.bend:
            dx=L[e][0]-L[sh][0]; dx=dx if abs(dx)>1e-6 else 1e-6
            tt=min(1,max(0,(L[hp][0]-L[sh][0])/dx)); ly=L[sh][1]+(L[e][1]-L[sh][1])*tt
            if L[hp][1]>ly: s.sag+=1
            else: s.pike+=1
    def cues(s):
        if s.sb>=3:
            if s.sag>=0.6*s.sb: return ["SAG"]
            if s.pike>=0.6*s.sb: return ["PIKE"]
        return []
class Lunge(Cycle):
    def __init__(s,top=0.92,bottom=0.80,shallow=0.88,upright=50,lean=30,base_ms=5000): super().__init__(top,bottom,shallow); s.up,s.lean,s.bms=upright,lean,base_ms; s.st=[]; s.margin=0.03; s.band=0.03
    def start(s): s.sb=s.lb=0
    def angle(s,L,w,h):
        tl=torso_tilt(L,w,h)
        if tl is None or tl>s.up or not vis(L,LS,RS,LH,RH): return None
        sm=mid(L,LS,RS,w,h); hp=mid(L,LH,RH,w,h); torso=math.hypot(sm[0]-hp[0],sm[1]-hp[1])
        if torso<5: return None
        an=[L[i][1]*h for i in (LA,RA) if L[i][3]>=0.6]
        if not an: return None
        r=(max(an)-hp[1])/torso
        if s.phase in ("U","T"):
            s.st.append((s.t,r)); s.st=[x for x in s.st if s.t-x[0]<=s.bms]
        if not s.st: return None
        b=max(x[1] for x in s.st); return r/b
    def observe(s,L,w,h):
        fr=frontal(L,w,h)
        if fr is None or fr>0.45: return
        tl=torso_tilt(L,w,h)
        if tl is None: return
        s.sb+=1; s.lb+= tl>s.lean
    def cues(s): return ["LEAN"] if s.sb>=3 and s.lb>=0.6*s.sb else []
def run(path, counter, verbose=False):
    tr=Tracker(); states={}; trace=[]
    for t,w,h,L in load(path):
        st=tr.update(L); states[st]=states.get(st,0)+1
        a=counter.update(t,w,h,L,st=="TRACKING")
        trace.append("%s%s"%("--" if a is None else ("%3.0f"%a if a>2 else "%.2f"%a), "" if st=="TRACKING" else st[0].lower()))
    if verbose:
        for i in range(0,len(trace),15): print("   ",i//15," ".join(trace[i:i+15]))
    return counter.count, counter.events, states
class Lunge2:
    """hysteresis peak/valley detector on hip height / standing hip height"""
    def __init__(s,drop=0.12,rise=0.12,upright=50,lean=30,minrep=700):
        s.drop,s.rise,s.up,s.lean,s.minrep=drop,rise,upright,lean,minrep; s.count=0; s.events=[]; s.base=None; s.state="U"; s.peak=None
    def update(s,t,w,h,L,tracking):
        if not tracking or L is None: s.state="U"; return None
        tl=torso_tilt(L,w,h)
        if tl is None or tl>s.up or not vis(L,LS,RS,LH,RH): s.state="U"; return None
        sm=mid(L,LS,RS,w,h); hp=mid(L,LH,RH,w,h); torso=math.hypot(sm[0]-hp[0],sm[1]-hp[1])
        an=[L[i][1]*h for i in (LA,RA) if L[i][3]>=0.6]
        if torso<5 or not an: s.state="U"; return None
        r=(max(an)-hp[1])/torso
        s.base=r if s.base is None else max(s.base,r); x=r/s.base
        if s.state=="U": s.state="T"; s.peak=x; return x
        if s.state=="T":
            s.peak=max(s.peak,x)
            if x<s.peak-s.drop: s.state="D"; s.valley=x; s.t0=t
        elif s.state=="D":
            s.valley=min(s.valley,x)
            if x>s.valley+s.rise:
                if t-s.t0>=s.minrep: s.count+=1; s.events.append((t,"rep%d"%s.count,[]))
                s.state="T"; s.peak=x
        return x

if __name__=="__main__":
    kind=sys.argv[1]
    for p in sys.argv[2:]:
        c={"lunge2":Lunge2,"squat":Squat,"pushup":PushUp,"kpushup":lambda:PushUp(knees=True),"lunge":Lunge}[kind]()
        n,ev,st=run(p,c,verbose="-v" in sys.argv[0:1] or len(sys.argv)==3)
        print(p.split('/')[-1], "count",n, ev, st)
