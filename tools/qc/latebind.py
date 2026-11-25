"""Finds closures (def / lambda) created inside a loop that read a variable the loop changes without binding it as a
default argument: they run later (when the rig solves the frame) and see the loop's LAST value, not the one of their
own frame. Usage: python3 tools/qc/latebind.py tools/blender/*.py"""
import ast, sys


class V(ast.NodeVisitor):
    def __init__(self, fn):
        self.fn, self.loops, self.hits = fn, [], []

    def assigned(self, node):
        names = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                names.add(n.id)
        return names

    def visit_For(self, node):
        changing = (self.assigned(node.target) if hasattr(node, "target") else set()) | set().union(*[self.assigned(s) for s in node.body])
        self.loops.append(changing)
        self.generic_visit(node)
        self.loops.pop()

    visit_While = visit_For

    def check(self, node, args):
        if not self.loops:
            return
        changing = set().union(*self.loops)
        bound = {a.arg for a in args.args + args.kwonlyargs}
        used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
        local = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
        bad = sorted((used & changing) - bound - local)
        if bad:
            self.hits.append((node.lineno, getattr(node, "name", "lambda"), bad))

    def visit_FunctionDef(self, node):
        self.check(node, node.args)
        saved, self.loops = self.loops, []        # loops inside the closure itself are its own business
        self.generic_visit(node)
        self.loops = saved

    def visit_Lambda(self, node):
        self.check(node, node.args)
        self.generic_visit(node)


found = 0
for fn in sys.argv[1:]:
    v = V(fn)
    v.visit(ast.parse(open(fn).read()))
    for ln, name, bad in v.hits:
        print(f"{fn}:{ln} {name} reads loop variables {bad}")
        found += 1
sys.exit(1 if found else 0)
