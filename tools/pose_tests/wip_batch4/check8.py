import sys,os;sys.path.insert(0,'/home/claude/rv');import mirror2 as m
K={"kcrunch":"knee","hkmarch":"knee","revfly":"row","ohtri":"overhead","jjc":"punch","neg_idle_knee":"knee"}
for line in open('/home/claude/rv/queue8.txt'):
    n=line.split('|')[0]
    if not n or not os.path.exists('fx/%s.lm'%n): continue
    k=next(v for p,v in K.items() if n.startswith(p))
    c=m.KINDS[k](); r=m.run('fx/%s.lm'%n,c,"-v" in sys.argv)
    print(n,k,r[0],r[1],getattr(c,'events',''))
