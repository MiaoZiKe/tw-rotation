# 重疊檢查：每個構圖的各元素單獨渲染成圖層，量真實墨水邊界，兩兩求間距（負值＝重疊）
import json, sys, os, itertools
from PIL import Image
LAY = sys.argv[1]
man = json.load(open(os.path.join(LAY, 'manifest.json')))
CORE = {'mark', 'word', 'tag'}  # 圖形、文字標、標語：間距需 ≥ 24px
def bb(f):
    return Image.open(f).convert('RGBA').split()[3].point(lambda v: 255 if v > 24 else 0).getbbox()
def gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2]); dy = max(b[1] - a[3], a[1] - b[3])
    return max(dx, dy)
rows = []; fails = []
for comp, m in sorted(man.items()):
    boxes = {e: bb(f) for e, f in m['els'].items()}
    for a, b in itertools.combinations(sorted(boxes), 2):
        g = gap(boxes[a], boxes[b]); need = 24
        ok = g >= need
        rows.append({'comp': comp, 'a': a, 'b': b, 'gap': g, 'need': need, 'ok': ok, 'core': a in CORE and b in CORE})
        if not ok: fails.append(rows[-1])
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'overlap_report.json')
json.dump({'pairs': rows, 'fails': fails}, open(out, 'w'), ensure_ascii=False, indent=1)
core = [r for r in rows if r['core']]
print('構圖數', len(man), '元素對', len(rows), '（核心三元素對', len(core), '）')
print('核心最小間距', min(r['gap'] for r in core), 'px；全部最小間距', min(r['gap'] for r in rows), 'px')
print('不合格', len(fails))
for f in fails: print('  ', f)
