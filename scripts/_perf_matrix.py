"""載入效能：多頁 × 多降速 × 多版本交錯量測（呼叫 scripts/_perf.py）。
用法：python scripts/_perf_matrix.py <label>=<site_dir> [<label>=<site_dir> ...] [--cpu 1,4] [--hash h1,h2] [--rep N] [--width W]
多個站交錯跑（A B A B…），降低容器負載漂移對比較的影響。"""
import subprocess, sys, json
from pathlib import Path
PERF = str(Path(__file__).resolve().parent / '_perf.py')
args = sys.argv[1:]
def opt(name, d):
    if name in args:
        i = args.index(name); v = args[i + 1]; del args[i:i + 2]; return v
    return d
hashes = opt('--hash', 'overview,flow,industry/semiconductor,stock/2330').split(',')
cpus = opt('--cpu', '1').split(',')
rep = int(opt('--rep', '1'))
width = opt('--width', '1440')
OUTD = opt('--out', '')
sites = [a.split('=', 1) for a in args]
KEYS = ('fcp_ms', 'boot_done_ms', 'tti_approx_ms', 'tbt_ms', 'longest_ms', 'long_tasks')
for c in cpus:
    for h in hashes:
        t = h.replace('/', '_')
        for r in range(rep):
            for L, SITE in sites:
                tag = f'{L}_c{c}_{t}' + (f'_r{r}' if rep > 1 else '') + (f'_w{width}' if width != '1440' else '')
                p = subprocess.run([sys.executable, PERF, '--site', SITE, '--hash', h, '--cpu', c, '--width', width,
                                    '--tag', tag, '--settle', '8'] + (['--out', OUTD] if OUTD else []), capture_output=True, text=True)
                try:
                    d = json.loads(p.stdout.splitlines()[0])
                    extra = [l for l in p.stdout.splitlines() if l.startswith('script_total')]
                    print(f'{tag:42s} ' + ' '.join(f'{k[:-3]}={d[k]}' for k in KEYS) + ('  ' + extra[0] if extra else ''), flush=True)
                except Exception:
                    print(tag, 'FAILED', (p.stdout + p.stderr)[-800:], flush=True)
