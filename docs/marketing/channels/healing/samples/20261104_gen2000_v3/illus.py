"""v3 豐富場景插圖（自繪向量，三層：背景／中景／前景）＋可選的簡化線條人物。
座標系 888 寬，內容落在 y=100..440 的「內容帶」；scene_svg 依插圖框高度縮放並置中。
通則：描線 --w-line、圓角端點；每張只有一個主光源（--w-lamp）；人物無五官、無性別特徵、不像任何真人。
人物＝以「外框＋填色」兩道描出的圓管狀肢體（連帽上衣／襯衫），填色用 --w-bg。"""
SW = 3.0
L = LC = LAMP = FNT = ""
def _styles(sw):
    global SW, L, LC, LAMP, FNT
    SW = sw
    b = 'stroke="var(--w-line)" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"' % sw
    L = 'fill="none" ' + b
    LC = 'fill="var(--w-card)" ' + b
    LAMP = 'fill="var(--w-lamp)" ' + b
    FNT = 'fill="none" ' + b + ' opacity=".5"'   # 遠景：同線條但淡

def R(x, y, w, h, rx=0, st=None): return '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" %s/>' % (x, y, w, h, rx, st or L)
def Ln(x1, y1, x2, y2, st=None): return '<line x1="%s" y1="%s" x2="%s" y2="%s" %s/>' % (x1, y1, x2, y2, st or L)
def C(cx, cy, r, st=None): return '<circle cx="%s" cy="%s" r="%s" %s/>' % (cx, cy, r, st or L)
def P(d, st=None): return '<path d="%s" %s/>' % (d, st or L)
def poly(pts, st=None): return '<polygon points="%s" %s/>' % (' '.join('%s,%s' % q for q in pts), st or L)
def glow(cx, cy, r, op):
    return '<g data-g="1" style="filter:blur(24px)"><circle cx="%d" cy="%d" r="%d" fill="url(#gl)" opacity="%s"/></g>' % (cx, cy, r, op)
def steam(x, y, h=40):
    return P('M%s %s q 7 -%s 0 -%s q -7 -%s 0 -%s' % (x, y, h / 4, h / 2, h / 4, h / 2), L.replace('fill="none"', 'fill="none" opacity=".6"'))
def lit(x, y, w, h, op=.5): return '<rect x="%s" y="%s" width="%s" height="%s" fill="var(--w-lamp)" opacity="%s"/>' % (x, y, w, h, op)
def skyline(x0, x1, base, hmin, hmax, seed, density=.35, op=.5, st=None):
    out = []; x = x0; s = seed
    while x < x1:
        s = (s * 1103515245 + 12345) & 0x7fffffff
        w = 34 + s % 30; h = hmin + (s >> 8) % (hmax - hmin); w = min(w, x1 - x)
        out.append(R(x, base - h, w, h, 0, st or FNT))
        for yy in range(int(base - h + 12), int(base - 10), 17):
            for xx in range(int(x + 8), int(x + w - 8), 14):
                s = (s * 1103515245 + 12345) & 0x7fffffff
                if (s % 100) / 100 < density: out.append(lit(xx, yy, 6, 8, op))
        x += w + 4
    return ''.join(out)

# ---------- 人物 ----------
PF = "var(--w-bg)"
def person(tubes, head, extra=""):
    """tubes: [(點列, 寬)]；head: (cx,cy,r)。先畫外框、再畫填色，肢體會融成一個輪廓。"""
    o = f = ""
    for pts, w in tubes:
        d = 'M' + ' L'.join('%s %s' % q for q in pts)
        o += '<path d="%s" fill="none" stroke="var(--w-line)" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"/>' % (d, w + 2 * SW)
        f += '<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-linecap="round" stroke-linejoin="round"/>' % (d, PF, w)
    cx, cy, r = head
    o += '<circle cx="%s" cy="%s" r="%s" fill="var(--w-line)"/>' % (cx, cy, r + SW)
    f += '<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (cx, cy, r, PF)
    return o + f + extra
def hood(cx, cy, r, dirx=0):  # 帽子輪廓：頸後一小段弧線
    return P('M%s %s q %s %s %s %s' % (cx - r * .9 + dirx, cy + r * .9, r * .9, r * .7, r * 1.8, 0))
def phone(x, y, rot=0, w=22, h=36):  # 手機（亮的小矩形）＋小光暈
    return ('<g transform="rotate(%s %s %s)">%s</g>' % (rot, x, y, R(x - w / 2, y - h / 2, w, h, 4, LAMP))) + glow(x, y, 46, ".55")

def p_sit_phone(x, y, face=-1):
    """側面坐在床緣滑手機。(x,y)＝臀部落點；face=-1 朝左。低頭、肩下垂。"""
    f = face
    tubes = [([(x, y - 10), (x + f * -4, y - 62)], 46),                      # 軀幹微彎
             ([(x, y - 14), (x + f * 52, y - 14), (x + f * 56, y + 52)], 22),  # 大腿＋小腿
             ([(x + f * -2, y - 56), (x + f * 22, y - 36), (x + f * 44, y - 56)], 15)]  # 手臂到手機
    return person(tubes, (x + f * 12, y - 92, 19), hood(x + f * 12, y - 92, 19, -f * 6)) + phone(x + f * 50, y - 62, f * 20)
def p_back_stand(x, y, h=170, look=0):
    """背面站立（室內、面向窗）：腳 y，頭頂約 y-h。"""
    hy = y - h + 18
    tubes = [([(x, hy + 40), (x, y - 70)], 56),
             ([(x - 14, y - 76), (x - 14, y - 6)], 22), ([(x + 14, y - 76), (x + 14, y - 6)], 22),
             ([(x - 30, hy + 44), (x - 34, y - 78)], 15), ([(x + 30, hy + 44), (x + 34, y - 78)], 15)]
    return person(tubes, (x + look, hy, 20), hood(x + look, hy, 20))
def p_side_stand(x, y, h=170, f=1):
    hy = y - h + 20
    tubes = [([(x, hy + 40), (x - f * 4, y - 70)], 46),
             ([(x - f * 4, y - 76), (x - f * 6, y - 6)], 22), ([(x + f * 6, y - 76), (x + f * 10, y - 6)], 20),
             ([(x - f * 2, hy + 46), (x + f * 10, y - 96)], 15)]
    return person(tubes, (x + f * 8, hy, 19), hood(x + f * 8, hy, 19, -f * 5))

# ---------- 場景（內容帶 y=100..440） ----------
def sc_home(person_on, dawn):
    o = glow(380, 330, 210, "var(--w-glow)")
    o += Ln(40, 432, 848, 432)
    # 背景：牆上窗（對面大樓幾扇亮著的窗）、月曆
    o += R(70, 130, 190, 200, 6, LC) + skyline(76, 254, 326, 70, 150, 7, .22, .55)
    o += Ln(165, 130, 165, 330) + Ln(70, 230, 260, 230)
    if dawn: o += '<rect x="76" y="136" width="178" height="190" fill="var(--w-lamp)" opacity=".16"/>'
    o += R(310, 148, 64, 74, 3, LC) + ''.join(Ln(318, 170 + k * 14, 366, 170 + k * 14) for k in range(4)) + C(344, 198, 9, L)
    # 中景：小書桌、檯燈、帳單、泡麵、杯子
    o += Ln(250, 336, 500, 336) + Ln(262, 336, 262, 430) + Ln(488, 336, 488, 430)
    o += R(270, 318, 74, 18, 2, LC) + R(280, 304, 74, 14, 2, LC) + Ln(288, 311, 330, 311)
    o += P('M394 336 L402 296 L444 296 L452 336 Z', LC) + Ln(398, 308, 448, 308) + steam(424, 290, 40)
    o += Ln(480, 336, 480, 238, L) + Ln(480, 238, 446, 226) + P('M420 206 L462 206 L452 234 L430 234 Z', LAMP)
    # 床
    o += R(520, 352, 320, 56, 8, LC) + R(520, 316, 22, 116, 5, LC) + R(556, 328, 76, 24, 9, LC) + P('M560 380 Q 650 364 836 382', L)
    o += Ln(540, 408, 540, 430) + Ln(826, 408, 826, 430)
    if person_on: o += p_sit_phone(612, 352)
    # 前景：拖鞋、小地毯
    o += P('M96 436 q 28 -12 54 0', L) + P('M170 436 q 28 -12 54 0', L)
    return o

def sc_dinner(person_on, dawn):
    o = glow(110, 250, 190, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：窗外淡淡煙火、遠景樓
    o += R(700, 130, 150, 170, 6, LC) + skyline(704, 846, 296, 40, 80, 3, .2, .4)
    for (fx, fy) in ((772, 190), (816, 230)):
        for a in range(0, 360, 45):
            import math
            dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
            o += Ln(fx + dx * 8, fy + dy * 8, fx + dx * 20, fy + dy * 20, FNT)
    # 落地燈（主光源）
    o += P('M62 150 L118 150 L130 206 L50 206 Z', LAMP) + Ln(90, 206, 90, 432) + Ln(66, 434, 114, 434)
    # 椅背
    o += R(210, 206, 58, 120, 8, LC) + R(626, 206, 58, 120, 8, LC) + R(392, 190, 96, 136, 10, LC)
    # 人（面向前方，坐中間椅）：軀幹藏在桌後，手放在桌面
    if person_on:
        o += person([([(440, 262), (440, 288)], 76)], (440, 214, 21), P('M418 214 q 22 -26 44 0', L))
    # 桌（正面）：桌板、桌腳、桌布垂邊
    o += R(180, 324, 540, 16, 4, LC) + Ln(214, 340, 214, 434) + Ln(686, 340, 686, 434)
    o += P('M200 340 q 20 24 40 0 q 20 24 40 0', FNT)
    # 桌上：四碗＋筷子、菜盤、茶壺、紅包袋
    for bx in (260, 350, 530, 620):
        o += P('M%d 302 q 28 36 56 0 Z' % (bx - 28), LC)
    o += Ln(506, 298, 556, 304)  # 擱在碗上的筷子
    o += Ln(504, 304, 554, 310)
    o += P('M406 322 q 34 -30 68 0 Z', LC) + Ln(420, 312, 460, 312)
    o += P('M300 312 q 0 -26 24 -26 q 24 0 24 26 Z', LC) + Ln(348, 300, 366, 294) + steam(324, 280, 32)
    o += '<g transform="rotate(-8 668 300)">' + R(654, 268, 40, 56, 3, LC) + Ln(654, 286, 694, 286) + C(674, 294, 5, L) + '</g>'
    if person_on:  # 手放在桌面（放下筷子）
        o += person([([(400, 276), (396, 306), (452, 312)], 14)], (-50, -50, 0)).replace('r="3"', 'r="0"')
        o += Ln(456, 312, 506, 302)
    return o

def sc_deskbills(person_on, dawn):
    o = glow(640, 300, 190, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：牆上便利貼、月曆（圈一個日期）
    for i, (x, y) in enumerate(((120, 150), (186, 160), (150, 214))):
        o += '<g transform="rotate(%d %d %d)">' % ((-4, 3, -2)[i], x, y) + R(x, y, 54, 54, 2, LC) + Ln(x + 10, y + 18, x + 44, y + 18) + Ln(x + 10, y + 30, x + 36, y + 30) + '</g>'
    o += R(330, 140, 120, 100, 4, LC) + ''.join(Ln(340, 170 + k * 16, 440, 170 + k * 16) for k in range(4)) + C(402, 202, 11, L)
    # 椅子（人坐／空）
    o += R(200, 236, 70, 120, 10, LC) + Ln(235, 356, 235, 434) + Ln(205, 436, 265, 436)
    if person_on:
        o += person([([(240, 360), (262, 306)], 52)], (356, 322, 22), P('M338 322 q 20 -26 40 0', L))
    # 桌
    o += R(150, 346, 640, 16, 4, LC) + Ln(180, 362, 180, 434) + Ln(760, 362, 760, 434) + R(620, 362, 120, 70, 4, LC) + Ln(680, 362, 680, 432)
    if person_on:  # 趴著：前臂橫放桌面、頭靠在手臂上
        o += person([([(290, 332), (326, 340), (420, 344)], 22)], (-60, -60, 0)).replace('r="3"', 'r="0"')
    # 桌上：帳單堆、計算機、手機記帳 App、泡麵、檯燈
    o += R(440, 322, 90, 24, 2, LC) + R(450, 306, 90, 18, 2, LC) + Ln(460, 314, 520, 314)
    o += R(560, 296, 66, 50, 6, LC) + ''.join(R(568 + c * 18, 322 + r * 0, 12, 12, 2, L) for r in (0,) for c in range(3)) + R(568, 304, 50, 12, 2, L)
    o += R(640, 266, 42, 78, 8, LAMP) + Ln(650, 322, 650, 336) + Ln(660, 312, 660, 336) + Ln(670, 302, 670, 336, L) + glow(661, 300, 50, ".5")
    o += P('M700 346 L706 312 L744 312 L750 346 Z', LC) + steam(725, 306, 34)
    o += Ln(784, 346, 784, 250) + Ln(784, 250, 750, 232) + P('M722 214 L764 214 L754 240 L732 240 Z', LAMP)
    return o

def sc_window(person_on, dawn):
    o = glow(130, 330, 190, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 大窗（關著）：樓群、窗格、窗鎖
    o += R(200, 90, 560, 290, 4, LC) + skyline(206, 754, 376, 90, 240, 11, .30, .45)
    o += Ln(480, 90, 480, 380) + Ln(200, 235, 760, 235) + R(490, 226, 12, 22, 3, L)
    if dawn: o += '<rect x="206" y="96" width="548" height="120" fill="var(--w-lamp)" opacity=".14"/>'
    o += R(190, 380, 580, 12, 3, LC)
    # 窗簾（左）、窗台盆栽與杯子
    o += P('M60 90 L190 90 L190 430 L60 430 Z', LC) + ''.join(Ln(60 + k * 22, 96, 66 + k * 22, 428, FNT) for k in range(1, 6))
    o += P('M640 380 L650 352 L686 352 L696 380 Z', LC) + P('M668 352 q -14 -26 -2 -40 M668 352 q 14 -22 6 -36', L)
    o += P('M708 380 L712 350 L742 350 L746 380 Z', LC) + steam(727, 346, 28)
    # 左邊矮櫃＋立燈（光源）
    o += P('M100 170 L150 170 L158 214 L92 214 Z', LAMP) + Ln(125, 214, 125, 432) + Ln(104, 434, 146, 434)
    if person_on: o += p_back_stand(470, 432, 176)
    return o

def sc_balcony(person_on, dawn):
    o = glow(130, 250, 190, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：封閉式陽台的整排玻璃窗（遠景樓、細窗格）
    o += R(60, 100, 770, 280, 4, LC)
    for k in range(1, 4): o += Ln(60 + k * 192, 100, 60 + k * 192, 380)
    o += skyline(66, 824, 376, 40, 110, 5, .18, .4)
    o += Ln(60, 240, 830, 240, FNT)
    # 壁燈（光源）
    o += P('M96 132 L146 132 L138 170 L104 170 Z', LAMP)
    # 晾衣架（A 字）＋襯衫、毛巾
    o += Ln(380, 436, 440, 250) + Ln(540, 436, 480, 250) + Ln(440, 250, 480, 250) + Ln(300, 436, 360, 250) + Ln(620, 436, 560, 250) + Ln(360, 250, 560, 250)
    def shirt(cx): return (P('M%d 252 L%d 266 L%d 304 L%d 310 L%d 292 L%d 346 L%d 346 L%d 292 L%d 310 L%d 304 L%d 266 L%d 252 Z' %
                           (cx - 12, cx - 40, cx - 54, cx - 40, cx - 32, cx - 32, cx + 32, cx + 32, cx + 40, cx + 54, cx + 40, cx + 12), LC))
    o += shirt(420) + R(500, 256, 48, 90, 3, LC) + Ln(510, 272, 538, 272, FNT)
    # 右側：洗衣機、洗衣籃
    o += R(680, 300, 130, 130, 8, LC) + C(745, 366, 32, L) + C(745, 366, 18, FNT) + R(694, 312, 40, 10, 3, L)
    o += P('M200 436 L212 380 L290 380 L302 436 Z', LC) + P('M214 380 q 20 -22 40 -8 q 14 -16 34 8', LC)
    if person_on:  # 站在晾衣架旁收衣服，一手伸向襯衫
        x, y = 610, 436
        tubes = [([(x, y - 134), (x, y - 70)], 46), ([(x - 8, y - 76), (x - 10, y - 6)], 22), ([(x + 10, y - 76), (x + 12, y - 6)], 22),
                 ([(x - 14, y - 124), (x - 52, y - 160), (x - 84, y - 168)], 15), ([(x + 14, y - 124), (x + 20, y - 80)], 15)]
        o += person(tubes, (x - 6, y - 170, 19), hood(x - 6, y - 170, 19))
    return o

def sc_bedroom(person_on, dawn):
    o = glow(560, 280, 200, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 天花板吸頂燈（關著，輪廓）與牆角
    o += P('M344 100 q 100 -20 200 0 l -16 18 q -84 -12 -168 0 Z', LC) + Ln(40, 100, 848, 100, FNT)
    # 窗與窗簾（晨光放在窗內）
    o += R(70, 150, 170, 190, 5, LC) + skyline(76, 234, 336, 50, 130, 9, .2, .5) + Ln(155, 150, 155, 340)
    if dawn: o += '<rect x="76" y="156" width="158" height="174" fill="var(--w-lamp)" opacity=".2"/>'
    o += P('M60 140 L100 140 L90 350 L60 350 Z', FNT) + P('M250 140 L210 140 L220 350 L250 350 Z', FNT)
    # 牆上月曆、相框、小書架
    o += R(300, 150, 80, 96, 3, LC) + ''.join(Ln(310, 176 + k * 16, 370, 176 + k * 16) for k in range(4)) + C(352, 224, 9, L)
    o += R(410, 160, 48, 60, 3, LC) + R(470, 172, 40, 36, 3, LC)
    o += Ln(300, 292, 470, 292) + ''.join(R(310 + k * 22, 258 + (k % 2) * 6, 16, 34 - (k % 2) * 6, 2, LC) for k in range(6)) + P('M446 292 q 6 -26 20 -30 q 4 22 -8 30', L)
    # 床、床頭櫃、檯燈、杯子、手機
    o += R(470, 362, 370, 52, 8, LC) + R(470, 306, 22, 128, 5, LC) + R(512, 332, 86, 28, 10, LC) + P('M520 392 Q 660 372 836 394', L)
    o += Ln(490, 414, 490, 434) + Ln(826, 414, 826, 434)
    o += R(396, 372, 70, 62, 4, LC) + Ln(396, 402, 466, 402) + Ln(431, 372, 431, 360) + P('M408 330 L454 330 L446 360 L416 360 Z', LAMP)
    o += P('M376 372 L380 348 L398 348 L402 372 Z', LC) + steam(389, 344, 26)
    if person_on: o += p_sit_phone(660, 362)
    return o

def sc_salary(person_on, dawn):
    o = glow(700, 280, 200, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：牆上便利貼群、月曆、書架
    for i, (x, y, r) in enumerate(((90, 140, -5), (156, 152, 3), (118, 208, -2), (186, 214, 5))):
        o += '<g transform="rotate(%d %d %d)">' % (r, x, y) + R(x, y, 54, 54, 2, LC) + Ln(x + 10, y + 18, x + 44, y + 18) + Ln(x + 10, y + 30, x + 34, y + 30) + '</g>'
    o += R(280, 130, 110, 96, 4, LC) + ''.join(Ln(290, 158 + k * 16, 380, 158 + k * 16) for k in range(4)) + C(344, 194, 10, L)
    o += Ln(50, 292, 240, 292) + ''.join(R(60 + k * 24, 250 + (k % 3) * 6, 18, 42 - (k % 3) * 6, 2, LC) for k in range(7))
    # 椅背
    o += R(386, 250, 116, 120, 12, LC)
    # 人：正面坐著，手托臉頰
    if person_on:
        o += person([([(444, 300), (444, 356)], 84), ([(494, 312), (516, 346), (476, 288)], 17)], (448, 256, 22), P('M426 256 q 22 -28 44 0', L))
    # 桌
    o += R(180, 356, 600, 16, 4, LC) + Ln(210, 372, 210, 434) + Ln(750, 372, 750, 434) + R(560, 372, 160, 62, 4, LC) + Ln(640, 372, 640, 434)
    # 桌上：薪資單、計算機、手機記帳 App、馬克杯、盆栽、筆筒
    o += R(250, 318, 110, 38, 2, LC) + Ln(262, 330, 340, 330) + Ln(262, 342, 320, 342)
    o += R(540, 296, 68, 60, 6, LC) + R(548, 304, 52, 12, 2, L) + ''.join(R(548 + c * 18, 326 + r * 14, 12, 8, 2, L) for r in (0, 1) for c in range(3))
    o += R(620, 306, 44, 50, 8, LAMP) + Ln(630, 342, 630, 330) + Ln(640, 342, 640, 320) + Ln(650, 342, 650, 334) + glow(642, 330, 50, ".5")
    o += P('M300 318 L304 292 L330 292 L334 318 Z', LC) + steam(317, 288, 26)
    o += P('M200 356 L204 330 L232 330 L236 356 Z', LC) + P('M218 330 q -12 -22 -2 -34 M218 330 q 12 -18 6 -30', L)
    o += Ln(740, 356, 740, 262) + Ln(740, 262, 708, 244) + P('M680 226 L724 226 L714 252 L690 252 Z', LAMP)
    return o

def sc_skyline(person_on, dawn):
    o = glow(500, 200, 260, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 大窗：右側遠處高樓群（亮晃晃）、左側近處老公寓的一扇小窗
    o += R(110, 110, 680, 290, 4, LC)
    o += skyline(300, 784, 394, 120, 270, 21, .62, .65)
    o += R(120, 250, 160, 144, 0, FNT) + skyline(122, 278, 394, 50, 110, 4, .1, .4)
    o += R(168, 296, 44, 50, 3, LC) + R(176, 304, 28, 34, 0, '%s' % LAMP.replace('stroke-width="%.2f"' % SW, 'stroke-width="2"'))
    o += Ln(450, 110, 450, 400, FNT) + R(100, 400, 700, 12, 3, LC)
    # 窗台上的杯子
    o += P('M700 400 L704 372 L736 372 L740 400 Z', LC) + steam(718, 368, 26)
    if person_on: o += p_back_stand(380, 436, 170, 4)
    return o

def sc_store(person_on, dawn):
    o = glow(500, 300, 170, "var(--w-glow)")
    o += Ln(40, 436, 848, 436) + Ln(40, 100, 848, 100, FNT)
    # 背景：貨架（上下兩層小商品）、冷藏櫃（玻璃門）
    o += R(60, 120, 250, 210, 4, LC) + Ln(60, 190, 310, 190) + Ln(60, 260, 310, 260)
    for r, y in enumerate((190, 260, 330)):
        for k in range(8): o += R(70 + k * 30, y - 38 + (k % 2) * 4, 22, 38 - (k % 2) * 4, 3, FNT)
    o += R(690, 120, 150, 316, 4, LC) + Ln(765, 120, 765, 436) + ''.join(Ln(700, 180 + k * 60, 830, 180 + k * 60, FNT) for k in range(4))
    # 櫃台、微波爐（亮窗）、便當、飲料
    o += R(330, 346, 340, 16, 4, LC) + R(340, 362, 320, 74, 2, LC)
    o += R(420, 252, 210, 94, 8, LC) + R(436, 266, 120, 66, 4, LAMP) + Ln(574, 264, 574, 334) + C(600, 284, 8, L) + C(600, 312, 8, L)
    o += R(344, 322, 62, 24, 3, LC) + Ln(352, 334, 398, 334) + R(344, 298, 62, 22, 3, FNT)
    if person_on: o += p_side_stand(250, 436, 176, 1)
    return o

def sc_desk(person_on, dawn):
    o = glow(260, 290, 200, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：書架、牆上便利貼板、遠處窗
    o += R(620, 120, 190, 190, 4, LC) + Ln(620, 184, 810, 184) + Ln(620, 248, 810, 248)
    for r, y in enumerate((184, 248, 310)):
        for k in range(6): o += R(630 + k * 28, y - 50 + (k % 3) * 8, 20, 50 - (k % 3) * 8, 2, FNT)
    o += R(70, 130, 200, 120, 4, LC) + ''.join(R(84 + (k % 3) * 62, 144 + (k // 3) * 52, 48, 40, 2, FNT) for k in range(6))
    # 桌、螢幕（履歷）、鍵盤、杯子、盆栽、檯燈
    o += R(190, 360, 560, 16, 4, LC) + Ln(220, 376, 220, 434) + Ln(720, 376, 720, 434)
    o += R(360, 220, 220, 126, 8, LC) + R(374, 234, 192, 98, 3, LAMP) + R(392, 248, 34, 34, 3, L) + Ln(440, 252, 548, 252) + Ln(440, 268, 520, 268) + Ln(392, 298, 540, 298) + Ln(392, 312, 504, 312)
    o += Ln(470, 346, 470, 360) + Ln(440, 360, 500, 360) + R(380, 350, 180, 10, 4, LC)
    o += P('M620 360 L624 332 L652 332 L656 360 Z', LC) + steam(638, 328, 28)
    o += P('M690 360 L696 336 L722 336 L728 360 Z', LC) + P('M709 336 q -14 -26 -2 -40 M709 336 q 14 -22 6 -36', L)
    o += Ln(240, 360, 240, 280) + Ln(240, 280, 276, 262) + P('M258 238 L306 238 L296 266 L268 266 Z', LAMP)
    # 椅背
    o += R(400, 300, 120, 110, 12, LC)
    if person_on:  # 背面坐姿看螢幕，肩下垂、頭微低
        o += person([([(460, 316), (460, 356)], 86), ([(418, 322), (420, 352)], 16), ([(502, 322), (500, 352)], 16)], (460, 280, 22), P('M438 288 q 22 14 44 0', L))
    return o

def sc_mrt(person_on, dawn):
    o = '<g data-g="1" style="filter:blur(24px)"><rect x="140" y="96" width="610" height="260" fill="url(#gl)" opacity="var(--w-glow2)"/></g>'
    # 背景：車窗（流動的燈點）、廣告框、頂部日光燈
    o += R(40, 96, 808, 346, 6)
    o += R(40, 96, 808, 38, 0, LC) + R(300, 104, 290, 20, 6, LAMP)
    for k in range(4):
        x = 70 + k * 200
        o += R(x, 160, 160, 120, 6, LC)
        for j in range(5): o += Ln(x + 14 + (j * 53) % 120, 180 + j * 20, x + 34 + (j * 53) % 120, 180 + j * 20, FNT)
    o += ''.join(R(80 + k * 200, 142, 80, 10, 2, FNT) for k in range(4))
    # 扶手桿（垂直）＋頂部橫桿
    o += Ln(60, 140, 828, 140) + Ln(250, 140, 250, 400) + Ln(650, 140, 650, 400) + Ln(450, 140, 450, 400)
    # 長座椅（含椅背壓線）
    o += R(60, 326, 768, 40, 8, LC) + R(60, 296, 768, 30, 8, LC) + Ln(260, 296, 260, 366, FNT) + Ln(460, 296, 460, 366, FNT) + Ln(660, 296, 660, 366, FNT)
    o += Ln(60, 440, 828, 440)
    if dawn: o += '<rect x="570" y="166" width="150" height="108" fill="var(--w-lamp)" opacity=".15"/>'
    # 人：坐中間，低頭看手機；旁邊放一個包
    if person_on:
        x, y = 350, 330
        tubes = [([(x, y - 12), (x - 2, y - 66)], 50), ([(x - 12, y), (x - 40, y + 4), (x - 38, y + 70)], 22), ([(x + 12, y), (x + 40, y + 4), (x + 38, y + 70)], 22),
                 ([(x - 22, y - 56), (x - 18, y - 22), (x - 2, y - 8)], 14), ([(x + 22, y - 56), (x + 18, y - 22), (x + 2, y - 8)], 14)]
        o += person(tubes, (x, y - 98, 21), P('M%s %s q 20 22 40 0' % (x - 20, y - 98), L)) + phone(x, y - 16, 0, 26, 18)
        o += R(450, 302, 66, 52, 8, LC) + P('M468 302 q 15 -18 30 0', L)
    return o

def sc_morning(person_on, dawn):
    o = glow(700, 220, 300, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：窗（淡淡晨光＋遠景樓）、牆上小相框
    o += R(560, 110, 250, 230, 5, LC) + skyline(566, 804, 336, 40, 110, 13, .2, .5) + Ln(685, 110, 685, 340)
    o += '<rect x="566" y="116" width="238" height="214" fill="var(--w-lamp)" opacity=".24"/>'
    o += R(560, 340, 250, 12, 3, LC) + R(300, 150, 58, 70, 3, LC) + R(376, 164, 46, 40, 3, LC)
    # 桌、筆記本、筆、馬克杯、盆栽、小檯燈
    o += R(250, 350, 300, 14, 4, LC) + Ln(272, 364, 272, 434) + Ln(528, 364, 528, 434)
    o += poly([(330, 350), (344, 328), (440, 328), (454, 350)], LC) + Ln(392, 328, 392, 350) + Ln(352, 336, 384, 336) + Ln(352, 344, 380, 344) + Ln(402, 336, 436, 336)
    o += Ln(462, 346, 500, 336) + P('M486 350 L490 322 L514 322 L518 350 Z', LC) + steam(502, 318, 28)
    o += P('M282 350 L286 326 L308 326 L312 350 Z', LC) + P('M297 326 q -12 -22 -2 -32 M297 326 q 12 -18 6 -30', L)
    # 椅子
    o += R(128, 250, 24, 118, 8, LC) + Ln(152, 372, 236, 372) + Ln(140, 372, 140, 434) + Ln(226, 372, 226, 434)
    if person_on:
        o += person([([(184, 358), (180, 298)], 46), ([(190, 366), (238, 366), (242, 430)], 20), ([(182, 308), (214, 328), (262, 340)], 14)], (196, 266, 19), hood(196, 266, 19, 6))
    return o

def sc_blocks(person_on, dawn):
    o = glow(500, 220, 280, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    o += R(90, 100, 710, 300, 4, LC) + '<rect x="96" y="106" width="698" height="130" fill="var(--w-lamp)" opacity=".2"/>'
    o += skyline(96, 794, 394, 150, 260, 31, .5, .6)
    # 近景：一整棟公寓，格狀窗戶（很多扇亮著）
    o += R(330, 230, 440, 164, 0, LC)
    for r in range(5):
        for c in range(14):
            o += R(344 + c * 30, 246 + r * 30, 18, 20, 0, FNT)
            if (r * 7 + c * 3) % 5 < 3: o += lit(346 + c * 30, 248 + r * 30, 14, 16, .6)
    o += R(80, 400, 730, 12, 3, LC) + P('M690 400 L694 372 L726 372 L730 400 Z', LC) + steam(710, 368, 26)
    if person_on: o += p_back_stand(200, 436, 170, 3)
    return o

def sc_rent(person_on, dawn):
    o = glow(430, 290, 260, "var(--w-glow)")
    o += Ln(40, 436, 848, 436)
    # 背景：牆上月曆（圈日期）、鑰匙掛鉤、窗透進晨光
    o += R(110, 130, 110, 100, 4, LC) + ''.join(Ln(120, 160 + k * 16, 210, 160 + k * 16) for k in range(4)) + C(160, 192, 11, L)
    o += Ln(260, 160, 330, 160) + P('M284 160 l 0 22 q 8 10 16 0 l 0 -22', L)
    o += R(620, 120, 170, 200, 5, LC) + '<rect x="626" y="126" width="158" height="188" fill="var(--w-lamp)" opacity=".2"/>' + Ln(705, 120, 705, 320)
    # 桌、手機（轉帳完成頁）、單據、計算機、杯子
    o += R(260, 350, 340, 14, 4, LC) + Ln(282, 364, 282, 434) + Ln(578, 364, 578, 434)
    o += R(400, 290, 50, 60, 8, LAMP) + Ln(410, 312, 440, 312, L) + P('M414 330 l 8 8 l 16 -16', L) + glow(425, 320, 56, ".5")
    o += R(300, 332, 80, 18, 2, LC) + Ln(308, 341, 366, 341, L) + R(470, 316, 56, 34, 4, LC) + P('M540 350 L544 324 L568 324 L572 350 Z', LC) + steam(556, 320, 26)
    # 椅子
    o += R(190, 250, 24, 118, 8, LC) + Ln(214, 372, 296, 372) + Ln(202, 372, 202, 434) + Ln(286, 372, 286, 434)
    if person_on:
        o += person([([(244, 358), (240, 298)], 46), ([(250, 366), (300, 366), (304, 430)], 20), ([(242, 308), (280, 322), (330, 330)], 14)], (256, 266, 19), hood(256, 266, 19, 6))
    # 前景：落地植物
    o += P('M700 436 L706 390 L750 390 L756 436 Z', LC) + P('M728 390 q -40 -30 -20 -76 M728 390 q 6 -50 40 -64 M728 390 q 34 -12 40 -48', L)
    return o

SCENES = {"morning": sc_morning, "blocks": sc_blocks, "rent": sc_rent, "home": sc_home, "dinner": sc_dinner, "deskbills": sc_deskbills, "window": sc_window, "balcony": sc_balcony,
          "bedroom": sc_bedroom, "salary": sc_salary, "skyline": sc_skyline, "store": sc_store, "desk": sc_desk, "mrt": sc_mrt}

def scene_svg(name, ih, person_on=False, dawn=False):
    k = min(1.0, ih / 360.0)
    _styles(3.0 / k)
    tx = (888 - 888 * k) / 2; ty = (ih - 8) - 440 * k
    inner = SCENES[name](person_on, dawn)
    defs = ('<radialGradient id="gl"><stop offset="0" stop-color="var(--w-lamp)" stop-opacity="1"/><stop offset="1" stop-color="var(--w-lamp)" stop-opacity="0"/></radialGradient>')
    return ('<div data-o="illus" class="illus" style="top:176px;width:888px;height:%dpx"><svg width="888" height="%d" viewBox="0 0 888 %d" '
            'xmlns="http://www.w3.org/2000/svg"><defs>%s</defs><g transform="translate(%.2f %.2f) scale(%.4f)">%s</g></svg></div>' % (ih, ih, ih, defs, tx, ty, k, inner))
