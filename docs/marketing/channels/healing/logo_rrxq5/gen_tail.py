def avatar_svg(P, sym, k, bg=True):
    b = f'<rect width="1080" height="1080" fill="{P["bg"]}"/>' if bg else ''
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1080" height="1080" viewBox="0 0 1080 1080"><defs>{defs(P)}</defs>{b}<g transform="translate(540 540) scale({k})">{sym}</g></svg>'
def text_w(s, kind, fs, ls):
    f = ImageFont.truetype(FONTS[kind][2], fs); return f.getlength(s) + ls*(len(s)-1)
WH = 420
def wm_svg(P, n, sym, kind, ls, k, sub, bg=True):
    ink = P['ink']; bgr = f'<rect width="{{W}}" height="{WH}" fill="{P["bg"]}"/>' if bg else ''
    fs = 150 if not sub else 134
    ty = 210 if not sub else 170
    symsz = 372
    tw = text_w(NAME, kind, fs, ls); x0 = 60 + symsz + 54; W = int(x0 + tw + 70)
    body = L('sym', f'<g transform="translate({60+symsz/2} 210) scale({k})">{sym}</g>')
    body += L('txt', TX(NAME, kind, fs, x0, ty+.36*fs, ink, ls=ls, bold=3 if kind == 'kai' else 0))
    if sub:
        body += L('sub', TX(SUB, 'sans', 44, x0, 345, ink, ls=7))
    return f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{WH}" viewBox="0 0 {W} {WH}"><defs>{defs(P)}</defs>{bgr.replace("{W}", str(W))}{body}</svg>', W

if __name__ == '__main__':
    import re
    jobs = []; meta = []
    for (n, fo, nm, sty, mean, fn, kind, ls, k, self44, added, tex, simp, rr, xq) in STYLES:
        os.makedirs(fo, exist_ok=True)
        meta.append(dict(n=n, dir=fo, name=nm, style=sty, mean=mean, kind=kind, self44=self44, added=added, texture=tex, simple=simp, rr=rr, xq=xq))
        far1 = FIT.get(str(n), 300); ka = min(420/far1, 1.6); kw = min(172/far1, 1.2)
        meta[-1].update(far1=far1, ka=ka, kw=kw)
        for tag, P in TONES.items():
            sym = fn(P); sv = avatar_svg(P, sym, ka); p = f'{fo}/頭像_1080方_{tag}'; open(p+'.svg', 'w').write(sv)
            jobs.append(dict(n=n, kind='avatar', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            sv = avatar_svg(P, fn(P, True), ka); p = f'{fo}/頭像_簡化小圖版1080方_{tag}'; open(p+'.svg', 'w').write(sv)
            jobs.append(dict(n=n, kind='avatar_s', tag=tag, svg=p+'.svg', png=p+'.png', w=1080, h=1080))
            for sub, suf in ((False, '字標'), (True, '字標含副標')):
                sv, W = wm_svg(P, n, sym, kind, ls, kw, sub); p = f'{fo}/{suf}_{tag}'; open(p+'.svg', 'w').write(sv)
                jobs.append(dict(n=n, kind='wmsub' if sub else 'wm', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH))
                if not TONES[tag].get('mono'):
                    sv, W = wm_svg(P, n, sym, kind, ls, kw, sub, bg=False); p = f'{fo}/{suf}_透明_{tag}'; open(p+'.svg', 'w').write(sv)
                    jobs.append(dict(n=n, kind='wmT', tag=tag, svg=p+'.svg', png=p+'.png', w=W, h=WH, transparent=True))
        P = TONES['奶油晨光']; sym = fn(P)
        open(f'{CHK}/av{n}.svg', 'w').write(avatar_svg(P, sym, ka, bg=False)); open(f'{CHK}/av{n}_1.svg', 'w').write(avatar_svg(P, sym, 1.0, bg=False))
        open(f'{CHK}/avs{n}.svg', 'w').write(avatar_svg(P, fn(P, True), ka, bg=False))
        jobs.append(dict(n=n, kind='chk_av', svg=f'{CHK}/av{n}.svg', png=f'{CHK}/av{n}_all.png', w=1080, h=1080, transparent=True))
        jobs.append(dict(n=n, kind='chk_av1', svg=f'{CHK}/av{n}_1.svg', png=f'{CHK}/av{n}_1.png', w=1080, h=1080, transparent=True))
        jobs.append(dict(n=n, kind='chk_avs', svg=f'{CHK}/avs{n}.svg', png=f'{CHK}/avs{n}_all.png', w=1080, h=1080, transparent=True))
        for lay in sorted(set(re.findall(r'data-layer="(\w+)"', sym))):
            jobs.append(dict(n=n, kind='chk_layer', layer=lay, svg=f'{CHK}/av{n}.svg', png=f'{CHK}/av{n}_{lay}.png', w=1080, h=1080, transparent=True, show=[lay]))
        for sub in (False, True):
            sv, W = wm_svg(P, n, sym, kind, ls, kw, sub, bg=False); open(f'{CHK}/wm{n}{"s" if sub else ""}.svg', 'w').write(sv)
            for lay in ('sym', 'txt', 'sub'):
                if f'data-layer="{lay}"' in sv:
                    jobs.append(dict(n=n, kind='chk_wm', sub=sub, layer=lay, svg=f'{CHK}/wm{n}{"s" if sub else ""}.svg', png=f'{CHK}/wm{n}{"s" if sub else ""}_{lay}.png', w=W, h=WH, transparent=True, show=[lay]))
            jobs.append(dict(n=n, kind='chk_wm', sub=sub, layer='all', svg=f'{CHK}/wm{n}{"s" if sub else ""}.svg', png=f'{CHK}/wm{n}{"s" if sub else ""}_all.png', w=W, h=WH, transparent=True))
    json.dump(dict(jobs=jobs, meta=meta, tones=TONES), open('jobs.json', 'w'), ensure_ascii=False)
    print(len(jobs), 'jobs')
