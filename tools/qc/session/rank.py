import re, json, sys
lim = int(sys.argv[1]) if len(sys.argv) > 1 else 30
for c in 'fm':
    rows=[]
    for l in open(f'/tmp/jerk_{c}.log'):
        m=re.match(r"^(\S+) \[\((\d+), '(\w+)', np\.int64\((\d+)\)\)", l.strip())
        if m: rows.append((int(m.group(2)), m.group(1), m.group(3), int(m.group(4))))
    rows.sort(reverse=True)
    print(c, len(rows), "clips; >400:", sum(r[0]>400 for r in rows), " >250:", sum(r[0]>250 for r in rows), " median:", sorted(r[0] for r in rows)[len(rows)//2])
    for r in rows[:lim]: print("  ", r)
