"""S1～S9 無人場景插圖（自繪向量）。座標系 888x460（對應插圖區 888x460），全部走 CSS 變數。
通則：描線 3px --w-line、圓角端點；內部不填或填 --w-card；每張只有一個光源（--w-lamp）。
glow(cx,cy,r,op) 畫模糊光暈；光源實體用 fill=var(--w-lamp)。"""
L = 'fill="none" stroke="var(--w-line)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"'
LC = 'fill="var(--w-card)" stroke="var(--w-line)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"'
LAMP = 'fill="var(--w-lamp)" stroke="var(--w-line)" stroke-width="3" stroke-linejoin="round"'

def glow(cx, cy, r, op, gid):
    return ('<g data-g="1" style="filter:blur(24px)"><circle cx="%d" cy="%d" r="%d" fill="url(#%s)" opacity="%s"/></g>' % (cx, cy, r, gid, op))

def defs(gid):
    return ('<radialGradient id="%s"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/>'
            '<stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>' % gid)

def S1():  # 租屋小套房一盞燈＋帳單
    return (glow(170, 330, 200, "var(--w-glow)", "g1") +
      '<line x1="40" y1="380" x2="860" y2="380" %s/>' % L +
      # 矮床
      '<rect x="440" y="326" width="320" height="54" rx="6" %s/><rect x="440" y="296" width="22" height="84" rx="4" %s/>'
      '<rect x="476" y="304" width="72" height="22" rx="8" %s/>' % (LC, LC, LC) +
      # 落地燈
      '<path d="M142 170 L198 170 L212 226 L128 226 Z" %s/><line x1="170" y1="226" x2="170" y2="378" %s/>'
      '<line x1="142" y1="380" x2="198" y2="380" %s/>' % (LAMP, L, L) +
      # 小凳與帳單
      '<line x1="262" y1="340" x2="352" y2="340" %s/><line x1="272" y1="340" x2="272" y2="380" %s/><line x1="342" y1="340" x2="342" y2="380" %s/>' % (L, L, L) +
      '<rect x="270" y="318" width="64" height="22" rx="2" %s/><line x1="280" y1="327" x2="316" y2="327" %s/><line x1="280" y1="334" x2="302" y2="334" %s/>' % (LC, L, L))

def S2():  # 末班捷運空車廂（透視：兩側座位與窗、遠端門、天花板日光燈；無月台、無軌道、無吊環）
    def side(sign, t0, t1, f0, f1):
        # sign=1 左牆、-1 右牆；t 為深度 0（近）~1（遠）；f 為高度比例（0 天花板~1 地板）
        def pt(t, f):
            x = 30 + 300 * t if sign == 1 else 858 - 300 * t
            c = 90 + 80 * t; fl = 360 - 70 * t
            return (round(x, 1), round(c + (fl - c) * f, 1))
        p = [pt(t0, f0), pt(t1, f0), pt(t1, f1), pt(t0, f1)]
        return ' '.join('%s,%s' % q for q in p)
    out = '<defs><linearGradient id="gb" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></linearGradient></defs>'
    out += '<polygon data-g="1" points="344,100 544,100 700,350 188,350" fill="url(#gb)" opacity="var(--w-glow2)" style="filter:blur(24px)"/>'
    out += '<rect x="30" y="90" width="828" height="270" %s/>' % L
    out += '<rect x="330" y="170" width="228" height="120" %s/><rect x="400" y="190" width="88" height="70" %s/>' % (L, L)
    out += '<line x1="30" y1="90" x2="330" y2="170" %s/><line x1="858" y1="90" x2="558" y2="170" %s/>' % (L, L)
    out += '<line x1="30" y1="360" x2="330" y2="290" %s/><line x1="858" y1="360" x2="558" y2="290" %s/>' % (L, L)
    for sg in (1, -1):
        out += '<polygon points="%s" %s/>' % (side(sg, .12, .88, .2, .5), L)
        out += '<polygon points="%s" %s/>' % (side(sg, .06, .94, .66, .86), LC)
    out += '<polygon points="394,104 494,104 474,150 414,150" %s/>' % LAMP
    return out

def S3():  # 便利商店微波便當
    return (glow(360, 260, 200, "var(--w-glow)", "g3") +
      '<line x1="60" y1="360" x2="860" y2="360" %s/>' % L +
      '<rect x="200" y="160" width="420" height="200" rx="12" %s/>' % LC +
      '<rect x="228" y="188" width="270" height="144" rx="8" %s/>' % LAMP +
      '<line x1="528" y1="170" x2="528" y2="350" %s/>' % L +
      ''.join('<circle cx="574" cy="%d" r="12" %s/>' % (y, L) for y in (210, 258, 306)) +
      '<rect x="660" y="292" width="160" height="68" rx="10" %s/><line x1="740" y1="298" x2="740" y2="356" %s/>' % (LC, L) +
      '<rect x="676" y="276" width="128" height="16" rx="6" %s/>' % LC)

def S4():  # 桌上帳單與薪資單＋計算機＋檯燈
    def paper(x, y, rot):
        return ('<g transform="rotate(%d %d %d)"><rect x="%d" y="%d" width="190" height="170" rx="3" %s/>%s</g>' %
                (rot, x + 95, y + 85, x, y, LC, "".join('<line x1="%d" y1="%d" x2="%d" y2="%d" %s/>' % (x + 24, y + 40 + k * 30, x + 120 - k * 14, y + 40 + k * 30, L) for k in range(3))))
    keys = "".join('<rect x="%d" y="%d" width="22" height="18" rx="4" %s/>' % (636 + c * 36, 304 + r * 26, L) for r in range(3) for c in range(3))
    return ('<defs><linearGradient id="gc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/>'
      '<stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></linearGradient></defs>' +
      '<polygon data-g="1" points="690,150 740,150 560,396 250,396" fill="url(#gc)" opacity="var(--w-glow2)" style="filter:blur(24px)"/>' +
      '<line x1="60" y1="384" x2="860" y2="384" %s/>' % L +
      paper(180, 210, -6) + paper(250, 200, 3) + paper(330, 214, -2) +
      '<rect x="620" y="244" width="140" height="140" rx="10" %s/><rect x="636" y="260" width="108" height="30" rx="4" %s/>' % (LC, L) + keys +
      '<line x1="812" y1="384" x2="812" y2="190" %s/><line x1="790" y1="384" x2="834" y2="384" %s/>' % (L, L) +
      '<line x1="812" y1="190" x2="730" y2="150" %s/><path d="M668 130 L752 130 L736 172 L684 172 Z" %s/>' % (L, LAMP))

def S5():  # 手機上的房仲 App
    return (glow(450, 230, 190, "var(--w-glow)", "g5") +
      '<rect x="340" y="40" width="220" height="360" rx="26" %s/><rect x="356" y="76" width="188" height="290" rx="10" %s/>' % (LC, LAMP) +
      '<rect x="372" y="92" width="76" height="58" rx="8" %s/>' % L +
      ''.join('<line x1="372" y1="%d" x2="%d" y2="%d" %s/>' % (y, x, y, L) for y, x in ((176, 520), (212, 500), (248, 520))))

def S6():  # 陽台晾衣（室內看向落地玻璃門）
    pre = '<defs><linearGradient id="gd6" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0.2"/></linearGradient></defs>'
    def shirt(cx):
        return ('<path d="M%d 238 L%d 256 L%d 300 L%d 308 L%d 286 L%d 346 L%d 346 L%d 286 L%d 308 L%d 300 L%d 256 L%d 238" %s/>'
                % (cx - 14, cx - 50, cx - 70, cx - 52, cx - 40, cx - 40, cx + 40, cx + 40, cx + 52, cx + 70, cx + 50, cx + 14, LC) +
                '<path d="M%d 238 Q%d 224 %d 238" %s/>' % (cx - 10, cx, cx + 10, L))
    return (pre + '<polygon data-g="1" points="110,380 490,380 560,446 10,446" fill="var(--w-lamp)" opacity="var(--w-glow2)" style="filter:blur(24px)"/>' +
      '<rect x="100" y="60" width="400" height="320" fill="url(#gd6)" opacity="0.16"/>' +
      '<rect x="100" y="60" width="400" height="320" %s/><rect x="114" y="74" width="172" height="292" %s/><rect x="314" y="74" width="172" height="292" %s/>' % (L, L, L) +
      '<line x1="150" y1="330" x2="236" y2="112" %s opacity="0.55"/><line x1="176" y1="330" x2="262" y2="112" %s opacity="0.55"/>' % (L, L) +
      '<line x1="350" y1="330" x2="436" y2="112" %s opacity="0.55"/><line x1="376" y1="330" x2="462" y2="112" %s opacity="0.55"/>' % (L, L) +
      '<line x1="300" y1="60" x2="300" y2="380" %s/><line x1="292" y1="200" x2="292" y2="236" %s/><line x1="308" y1="200" x2="308" y2="236" %s/>' % (L, L, L) +
      '<line x1="40" y1="380" x2="860" y2="380" %s/>' % L +
      '<line x1="580" y1="226" x2="860" y2="226" %s/>' % L +
      '<path d="M594 226 L568 380 M846 226 L872 380 M594 226 L632 380 M846 226 L808 380" %s/>' % L +
      shirt(650) + shirt(790))

def S7():  # 天花板吸頂燈（由下往上看）
    return (glow(444, 210, 200, "var(--w-glow)", "g7") +
      '<rect x="80" y="40" width="728" height="390" rx="4" %s/><rect x="200" y="100" width="488" height="270" %s/>' % (L, L) +
      '<line x1="80" y1="40" x2="200" y2="100" %s/><line x1="808" y1="40" x2="688" y2="100" %s/>' % (L, L) +
      '<line x1="80" y1="430" x2="200" y2="370" %s/><line x1="808" y1="430" x2="688" y2="370" %s/>' % (L, L) +
      '<rect x="324" y="180" width="240" height="60" rx="6" %s/>' % LAMP)

def S8():  # 沒有人坐的書桌（椅子推進桌下）
    return (glow(580, 240, 200, "var(--w-glow)", "g8") +
      '<line x1="40" y1="410" x2="860" y2="410" %s/>' % L +
      '<rect x="140" y="304" width="660" height="16" rx="4" %s/>' % LC +
      '<line x1="170" y1="320" x2="170" y2="408" %s/><line x1="770" y1="320" x2="770" y2="408" %s/>' % (L, L) +
      '<rect x="236" y="214" width="118" height="92" rx="14" %s/><line x1="272" y1="226" x2="272" y2="294" %s/><line x1="295" y1="226" x2="295" y2="294" %s/><line x1="318" y1="226" x2="318" y2="294" %s/><line x1="258" y1="320" x2="258" y2="400" %s/><line x1="332" y1="320" x2="332" y2="400" %s/>' % (LC, L, L, L, L, L) +
      '<path d="M470 302 L690 302 L676 312 L484 312 Z" %s/><rect x="484" y="186" width="200" height="116" rx="8" %s/><rect x="498" y="200" width="172" height="88" rx="3" %s/><line x1="514" y1="222" x2="620" y2="222" stroke="var(--w-card)" stroke-width="3" stroke-linecap="round"/><line x1="514" y1="244" x2="590" y2="244" stroke="var(--w-card)" stroke-width="3" stroke-linecap="round"/>' % (LC, LC, LAMP))

def S9():  # 電腦上開著的履歷表
    return (glow(440, 210, 200, "var(--w-glow)", "g9") +
      '<rect x="250" y="70" width="380" height="250" rx="10" %s/><rect x="272" y="90" width="336" height="210" rx="4" %s/>' % (LC, LAMP) +
      '<rect x="292" y="112" width="68" height="68" rx="4" %s/>' % L +
      ''.join('<line x1="380" y1="%d" x2="%d" y2="%d" %s/>' % (y, x, y, L) for y, x in ((122, 580), (146, 556), (170, 570))) +
      ''.join('<line x1="292" y1="%d" x2="%d" y2="%d" %s/>' % (y, x, y, L) for y, x in ((210, 560), (240, 520))) +
      '<path d="M210 320 L670 320 L690 346 L190 346 Z" %s/>' % LC)

SCENES = {"S1": S1, "S2": S2, "S3": S3, "S4": S4, "S5": S5, "S6": S6, "S7": S7, "S8": S8, "S9": S9}

def scene_svg(name, ih, crop):
    x0, y0, s = crop if crop else (0, 0, 1)
    vb = "%s %s %s %s" % (x0, y0, round(888 / s, 2), round(ih / s, 2))
    inner = SCENES[name]()
    # 漸層 defs 共用（每個場景自帶 id；光暈用的 g? 在這裡統一補上）
    gds = "".join(defs(g) for g in ("g1", "g3", "g5", "g7", "g8", "g9"))
    return ('<div data-o="illus" class="illus" style="top:176px;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="%s" preserveAspectRatio="xMinYMax meet" '
            'xmlns="http://www.w3.org/2000/svg"><defs>%s</defs>%s</svg></div>' % (ih, ih, vb, gds, inner))
