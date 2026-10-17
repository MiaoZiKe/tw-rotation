"""比比／科技素材索引：不搬移原檔，批准狀態不從外觀或自然語句推定。"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageSequence

FIELDS = {'pose': ['pose', '姿勢'], 'expression': ['expression', '表情'],
          'orientation': ['orientation', '視線', '角度'], 'prop': ['prop', '道具'],
          'scene': ['scene', '情境', '主持功能', '可用用途'], 'tags': ['tags', '搜尋標籤']}
SYNONYMS = [('趴', '趴著', 'lie', 'prone'), ('放大鏡', 'magnifier'),
            ('晶片', 'chip'), ('晶圓', 'wafer'), ('好奇', 'curious'),
            ('思考', 'think', 'thinking'), ('指向', '指示', 'point', 'pointer'),
            ('揮手', 'wave'), ('右', 'right'), ('左', 'left'), ('正面', 'front'),
            ('側面', 'side'), ('介紹', 'explain', 'intro'), ('驚嘆', 'wow')]

def flatten(value):
    if isinstance(value, dict):
        return ' '.join(flatten(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(flatten(v) for v in value)
    return str(value or '')

def image_info(path):
    result = {'path': path.as_posix(), 'exists': path.is_file()}
    if not path.is_file():
        return result
    result.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    try:
        with Image.open(path) as im:
            result.update(dimensions=list(im.size), format=im.format, frames=getattr(im, 'n_frames', 1))
            durations, extrema = [], []
            for frame in ImageSequence.Iterator(im):
                # 實測每格 alpha；RGBA 模式本身不代表確有透明像素。
                extrema.append(frame.convert('RGBA').getchannel('A').getextrema())
                durations.append(frame.info.get('duration', im.info.get('duration', 0)))
            result['alpha_extrema'] = [min(v[0] for v in extrema), max(v[1] for v in extrema)]
            result['has_transparent_pixels'] = result['alpha_extrema'][0] < 255
            result['duration_ms'] = sum(durations) if result['frames'] > 1 else None
            result['fps'] = round(1000 * len(durations) / sum(durations), 3) if result['frames'] > 1 and sum(durations) else None
    except Exception as exc:
        result['inspection_error'] = str(exc)
    return result

def status_of(manifest):
    # 只接受機器可讀的明確核可與證據；「檢查通過、待確認」不等於 approved。
    status = manifest.get('status', manifest.get('qa_status', 'review'))
    if status == 'approved' and not manifest.get('approval_evidence'):
        return 'review'
    return status if status in {'approved', 'review', 'visual_checked', 'rejected'} else 'review'

def scan(root):
    entries, warnings = [], []
    for path in sorted((root / 'docs/social_assets').rglob('manifest.json')):
        try:
            raw = json.loads(path.read_text(encoding='utf-8-sig'))
            fields = {k: ' '.join(flatten(raw.get(a)) for a in aliases) for k, aliases in FIELDS.items()}
            filename = raw.get('file', raw.get('檔案'))
            files = raw.get('files', [filename] if filename else [])
            inspected = []
            for f in files:
                f = f.get('path', f.get('file', '')) if isinstance(f, dict) else f
                candidate = Path(f)
                candidate = candidate if candidate.is_absolute() else path.parent / candidate
                inspected.append(image_info(candidate))
            entries.append({'asset_id': raw.get('asset_id', path.parent.name),
                            'name': raw.get('中文名稱', raw.get('name', path.parent.name)),
                            'version': raw.get('version', raw.get('版本', 'unknown')),
                            'status': status_of(raw), 'rights': raw.get('rights', raw.get('權利狀態', 'unknown')),
                            'category': raw.get('category', 'author_unverified'), 'fields': fields,
                            'manifest': path.relative_to(root).as_posix(), 'files': inspected})
        except Exception as exc:
            warnings.append({'manifest': str(path), 'error': str(exc)})
    # 遠端快照是有證據的索引，並非本機已下載／逐檔已檢查。
    snapshot = root / 'output/2026-10-17_asml-outlook/catalog_snapshot.json'
    if snapshot.exists():
        saved = json.loads(snapshot.read_text(encoding='utf-8-sig'))
        entries.extend(saved.get('remote_entries', []))
    return {'schema_version': 1, 'entries': entries, 'warnings': warnings}

def terms(query):
    tokens = re.findall(r'[a-z0-9_]+|[\u3400-\u9fff]+', query.lower())
    result = []
    for token in tokens:
        expanded = {token}
        for group in SYNONYMS:
            if any(x in token or token in x for x in group):
                expanded.update(group)
        result.append(expanded)
    return result

def search(catalog, query='', include_review=False, filters=None):
    matches = []
    for entry in catalog['entries']:
        status = entry['status']
        if status == 'rejected' or (status != 'approved' and not include_review):
            continue
        if filters and any(not any(t in entry['fields'].get(k, '').lower() for t in group)
                           for k, value in filters.items() for group in terms(value)):
            continue
        haystack = flatten([entry.get('asset_id'), entry.get('name'), entry['fields']]).lower()
        groups = terms(query)
        hits = sum(any(token in haystack for token in group) for group in groups)
        if groups and not hits:
            continue
        matches.append({**entry, 'score': round(100 * hits / len(groups), 1) if groups else 100,
                        'selectable': status == 'approved'})
    return sorted(matches, key=lambda e: (-e['score'], e['asset_id']))

def self_test():
    demo = {'entries': [{'asset_id': str(i), 'status': status, 'fields': {'pose': '趴姿', 'prop': '放大鏡'}}
                        for i, status in enumerate(['approved', 'review', 'visual_checked', 'rejected'])]}
    assert len(search(demo, 'prone magnifier')) == 1
    assert len(search(demo, 'prone', True)) == 3
    assert all(x['status'] != 'rejected' for x in search(demo, '', True))
    assert not status_of({'status': 'approved'}) == 'approved'
    assert status_of({'status': 'approved', 'approval_evidence': 'Andy 明確核可紀錄'}) == 'approved'
    assert not search(demo, filters={'prop': 'wafer'})
    print('通過：批准門檻、拒用隔離、中英同義詞、欄位篩選。')

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['scan', 'search', 'self-test'])
    parser.add_argument('query', nargs='?', default='')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out', type=Path)
    parser.add_argument('--include-review', action='store_true')
    for field in FIELDS:
        parser.add_argument('--' + field)
    args = parser.parse_args()
    if args.command == 'self-test':
        self_test()
        return
    result = scan(args.root)
    if args.command == 'search':
        result = search(result, args.query, args.include_review, {k: getattr(args, k) for k in FIELDS if getattr(args, k)})
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(content, encoding='utf-8')
    else:
        print(content)

if __name__ == '__main__':
    main()
