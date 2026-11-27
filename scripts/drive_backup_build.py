"""規範備份彙整檔產生器（Andy 11-26：規範要同步到 Google 雲端硬碟）。
用法：python scripts/drive_backup_build.py <輸出資料夾> [ai-mp4 路徑]
依 docs/SYSTEM_PLAYBOOK.md 各區串接 tw-rotation 規範檔；依 docs/drive_backup_manifest.json 的 ai-mp4 分支串 CLAUDE.md、docs/**/*.md、.github/workflows/*.yml。
輸出每份的 sha256，跟 manifest 比對，印出有變的檔名。"""
import re, os, sys, json, hashlib, subprocess
O = sys.argv[1]; MP4 = sys.argv[2] if len(sys.argv) > 2 else '/home/user/ai-mp4'
os.makedirs(O, exist_ok=True)
pb = open('docs/SYSTEM_PLAYBOOK.md', encoding='utf-8').read()
man = json.load(open('docs/drive_backup_manifest.json', encoding='utf-8'))
out = {'00_總索引_SYSTEM_PLAYBOOK.md': pb}
for s in re.split(r'\n(?=## )', pb):
    m = re.match(r'## ([A-H](?:-\d)?)\. ([^（\n]+)', s)
    if not m: continue
    paths = sorted(set(p for p in re.findall(r'`([^`\s]+\.(?:md|yaml|yml|json|txt|tsv|mjs|py))`', s) if os.path.isfile(p)))
    t = [f"# {m.group(1)}. {m.group(2).strip()}（{len(paths)} 份，tw-rotation main）\n"]
    for p in paths:
        t.append(f"\n\n---\n\n# 檔案：{p}\n\n" + open(p, encoding='utf-8', errors='replace').read())
    out[f"{m.group(1)}_{m.group(2).strip()}.md"] = ''.join(t)
for name, v in man['files'].items():
    b = v.get('branch')
    if not b: continue
    subprocess.run(['git', '-C', MP4, 'fetch', '-q', '--depth', '1', '--filter=blob:limit=1m', 'origin', b], timeout=300)
    ls = subprocess.run(['git', '-C', MP4, 'ls-tree', '-r', '--name-only', 'FETCH_HEAD'], capture_output=True, text=True).stdout.split()
    t = [f"# ai-mp4 分支 {b} 的規範文件\n"]
    for p in ls:
        if re.match(r'^(CLAUDE\.md|docs/.*\.md|\.github/workflows/.*\.yml)$', p):
            c = subprocess.run(['git', '-C', MP4, 'show', f'FETCH_HEAD:{p}'], capture_output=True, text=True, errors='replace').stdout
            t.append(f"\n\n---\n\n# 檔案：{p}\n\n{c}")
    out[name] = ''.join(t)
for name, txt in out.items():
    fn = os.path.join(O, name); open(fn, 'w', encoding='utf-8').write(txt)
    h = hashlib.sha256(open(fn, 'rb').read()).hexdigest()
    old = man['files'].get(name, {})
    flag = 'NEW' if not old else ('CHANGED' if old.get('sha256') != h else 'same')
    print(flag, h, fn, old.get('id', ''), sep='|')
