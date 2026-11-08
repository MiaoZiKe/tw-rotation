"""廣達碩畢月薪重算（2026-11-09，回應 legal_review.md 第四節第 1 項：crosscheck 要寫清楚篩選條件並以重算結果更正）。
用法：git show origin/main:site/tc/json/odm.json > /tmp/odm.json && python recalc_salary_1109.py /tmp/odm.json
篩選：職位分組 degree=碩士 且 years=0-2 → 樣本有 base_k（區間取中點）→ in_window → 排除 dup_of → 樣本年資 ≤2 或空白／「—」（D 列＝採用）。
"""
import json, statistics as S, collections as C, sys
d=json.load(open(sys.argv[1]))
q=[x for x in d['companies'] if x['name']=='廣達'][0]
R=[r for r in q['roles'] if r['degree']=='碩士' and r.get('years')=='0-2']
def val(b):
    if isinstance(b,list): return (b[0]+b[1])/2
    return b
rows=[]
for r in R:
    for s in r['samples']:
        if s['base_k'] is None: continue
        rows.append(dict(role=r['role'], years=s['years'], deg=s['degree'], v=val(s['base_k']), raw=s['base_k'], dup=s.get('dup_of'), win=s['in_window'], date=s['date'], site=s['site'], derived=s.get('derived'), cs=s.get('comment_sample')))
def ystr(y):
    try: return float(str(y).replace('年',''))
    except: return None
def report(name, xs):
    v=sorted(x['v'] for x in xs)
    if not v: print(name,0); return
    print(f"{name}: n={len(v)} min={v[0]} max={v[-1]} median={S.median(v)} in58_69={sum(58<=x<=69 for x in v)} "
          f"site={dict(C.Counter(x['site'] for x in xs))} role={dict(C.Counter(x['role'] for x in xs))} year={dict(C.Counter(x['date'][:4] for x in xs))} "
          f"deg={dict(C.Counter(str(x['deg']) for x in xs))} yrs={dict(C.Counter(str(x['years']) for x in xs))}")
report("A 全部有月薪", rows)
nd=[x for x in rows if not x['dup']]
report("B 非重複", nd)
yr=[x for x in nd if (ystr(x['years']) is not None and ystr(x['years'])<=2)]
report("C 非重複＋樣本年資≤2（空白排除）", yr)
yr2=[x for x in nd if (ystr(x['years']) is None or ystr(x['years'])<=2)]
report("D 非重複＋樣本年資≤2或空白", yr2)
for name,xs in (("D",yr2),):
    for x in sorted(xs,key=lambda x:x['v']): print(' ', x['role'], x['years'], x['raw'], x['date'], x['site'], 'dup' if x['dup'] else '', 'derived' if x['derived'] else '', 'comment' if x['cs'] else '')
