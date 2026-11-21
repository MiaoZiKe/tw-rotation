"""用 ast 精準改某一鏡的 sub／idle 字串（只動指定鏡）。"""
import ast, sys

def apply(path, table):
    src = open(path, encoding="utf8").read()
    tree = ast.parse(src)
    lines = src.split("\n")
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln.encode("utf8")) + 1)
    b = src.encode("utf8")

    def pos(l, c):
        return offs[l - 1] + c
    reps = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("feat", "featv", "featp") and n.args and isinstance(n.args[0], ast.Constant):
            sid = n.args[0].value
            if sid in table:
                sub, idle = table[sid]
                si = 7 if n.func.id == "featp" else 6
                a = n.args[si]
                reps.append((pos(a.lineno, a.col_offset), pos(a.end_lineno, a.end_col_offset), repr(sub)))
                kw = next((k for k in n.keywords if k.arg == "idle"), None)
                if kw is not None:
                    v = kw.value
                    reps.append((pos(v.lineno, v.col_offset), pos(v.end_lineno, v.end_col_offset), repr(idle)))
                else:
                    last = n.keywords[-1].value if n.keywords else n.args[-1]
                    e = pos(last.end_lineno, last.end_col_offset)
                    reps.append((e, e, f", idle={idle!r}"))
    for s_, e_, t in sorted(reps, reverse=True):
        b = b[:s_] + t.encode("utf8") + b[e_:]
    open(path, "w", encoding="utf8").write(b.decode("utf8"))
    print(path, len(table), "鏡")


def add_kw(path, table):
    """table: {sid: 'main=[(...)]' 這種 kwarg 原始碼字串}"""
    src = open(path, encoding="utf8").read()
    tree = ast.parse(src)
    lines = src.split("\n")
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln.encode("utf8")) + 1)
    b = src.encode("utf8")
    reps = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("feat", "featv", "featp") and n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value in table:
            kws = table[n.args[0].value]
            last = n.keywords[-1].value if n.keywords else n.args[-1]
            e = offs[last.end_lineno - 1] + last.end_col_offset
            reps.append((e, f", {kws}"))
    for e, t in sorted(reps, reverse=True):
        b = b[:e] + t.encode("utf8") + b[e:]
    open(path, "w", encoding="utf8").write(b.decode("utf8"))


def replace_stmt(path, sid, newcode):
    """把 S.append(feat*("sid", ...)) 整個敘述換成 newcode（縮排 4 格；可多行）。"""
    src = open(path, encoding="utf8").read()
    tree = ast.parse(src)
    lines = src.split("\n")
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln.encode("utf8")) + 1)
    b = src.encode("utf8")
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and getattr(n.value.func, "attr", "") == "append":
            c = n.value.args[0] if n.value.args else None
            if isinstance(c, ast.Call) and c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == sid:
                s_ = offs[n.lineno - 1]
                e_ = offs[n.end_lineno - 1] + n.end_col_offset
                b = b[:s_] + newcode.encode("utf8") + b[e_:]
                open(path, "w", encoding="utf8").write(b.decode("utf8"))
                return True
    raise KeyError(sid)


def insert_after(path, sid, newcode):
    src = open(path, encoding="utf8").read()
    tree = ast.parse(src)
    lines = src.split("\n")
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln.encode("utf8")) + 1)
    b = src.encode("utf8")
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and getattr(n.value.func, "attr", "") == "append":
            c = n.value.args[0] if n.value.args else None
            if isinstance(c, ast.Call) and c.args and isinstance(c.args[0], ast.Constant) and c.args[0].value == sid:
                e_ = offs[n.end_lineno - 1] + n.end_col_offset
                b = b[:e_] + ("\n" + newcode).encode("utf8") + b[e_:]
                open(path, "w", encoding="utf8").write(b.decode("utf8"))
                return True
    raise KeyError(sid)
