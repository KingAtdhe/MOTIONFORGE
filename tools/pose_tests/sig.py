import sys, math
def load(p):
    out=[]
    for l in open(p):
        s=l.split(); t=int(s[0]); w=int(s[1]); h=int(s[2])
        if s[3]=="none": out.append((t,w,h,None)); continue
        v=list(map(float,s[3:])); out.append((t,w,h,[v[i*5:i*5+5] for i in range(33)]))
    return out
def ang(a,b,c,w,h):
    ux,uy=(a[0]-b[0])*w,(a[1]-b[1])*h; vx,vy=(c[0]-b[0])*w,(c[1]-b[1])*h
    d=math.hypot(ux,uy)*math.hypot(vx,vy)
    return math.degrees(math.acos(max(-1,min(1,(ux*vx+uy*vy)/d)))) if d>0 else None
if __name__=="__main__":
    fr=load(sys.argv[1]); trip=[(23,25,27),(24,26,28)] if len(sys.argv)<3 else [tuple(map(int,x.split('-'))) for x in sys.argv[2].split(',')]
    row=[]
    for t,w,h,L in fr:
        if L is None: row.append(" --- "); continue
        vals=[]
        for a,b,c in trip:
            vis=min(L[a][3],L[b][3],L[c][3]); x=ang(L[a],L[b],L[c],w,h)
            vals.append("%3.0f%s"%(x,"" if vis>=0.6 else "?"))
        row.append("/".join(vals))
    for i in range(0,len(row),15): print(i//15, " ".join(row[i:i+15]))
