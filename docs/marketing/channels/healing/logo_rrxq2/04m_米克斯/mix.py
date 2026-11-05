# 04 貓睡陽光 → 米克斯版（2026-11-05 Andy：「幫我改成米克斯」，參考照片：虎斑＋白的米克斯小貓）
# 花色：白底（臉中線白鼻樑、白口鼻、白胸、白腳）＋灰棕虎斑（頭頂、眼周、背、尾）＋深色斑紋＋粉鼻＋黑尾尖
# A 打盹版：保留原本蜷在陽光裡的姿勢；B 歪頭版：照片那種坐著歪頭看你
import sys, os, json
sys.path.insert(0, os.path.abspath('..'))
os.chdir(os.path.abspath('..')); import gen; os.chdir(os.path.dirname(os.path.abspath(__file__)))
TONES, L, lightfill, defs = gen.TONES, gen.L, gen.lightfill, gen.defs
def cols(P):
    if P.get('mono'):
        return dict(w=P['bg'], tb=P['ink'], st=P['bg'], pk=P['bg'], tip=P['ink'], ol=P['ink'], eye=P['ink'])
    dark = P['bg'] == '#1E1A16'
    return dict(w='#FFFDF8', tb='#A8896B', st='#5C4636', pk='#EE9E98', tip='#2E2925', ol=('#FFF6E5' if dark else '#3A3A3A'), eye='#2E2925')
HEAD = 'M -102 -18 A 98 86 0 0 0 94 -18 A 98 86 0 0 0 -102 -18 Z'
def sA(P):
    c = cols(P); ol = c['ol']
    patch = f'<polygon points="-170,128 290,128 224,268 -246,268" fill="{lightfill(P)}"/>'
    shape = ('<ellipse cx="0" cy="124" rx="178" ry="98"/><ellipse cx="-4" cy="-18" rx="98" ry="86"/>'
             '<polygon points="-92,-62 -84,-168 -18,-92"/><polygon points="80,-62 72,-168 6,-92"/>')
    tail_d = 'M 176 168 C 262 170 286 84 238 38'
    tail = (f'<path d="{tail_d}" fill="none" stroke="{ol}" stroke-width="62" stroke-linecap="round"/>'
            f'<path d="{tail_d}" fill="none" stroke="{c["tb"]}" stroke-width="42" stroke-linecap="round"/>'
            f'<path d="{tail_d}" fill="none" stroke="{c["st"]}" stroke-width="42" stroke-dasharray="0 34 14 300"/>'
            f'<path d="M 252 70 C 254 58 248 46 238 38" fill="none" stroke="{c["tip"]}" stroke-width="42" stroke-linecap="round"/>')
    bodyS = '<ellipse cx="0" cy="124" rx="178" ry="98"/>'
    headS = '<ellipse cx="-4" cy="-18" rx="98" ry="86"/><polygon points="-92,-62 -84,-168 -18,-92"/><polygon points="80,-62 72,-168 6,-92"/>'
    def base(S): return (f'<g fill="{ol}" stroke="{ol}" stroke-width="40" stroke-linejoin="round">{S}</g>'
                         f'<g fill="{c["w"]}" stroke="{c["w"]}" stroke-width="18" stroke-linejoin="round">{S}</g>')
    cp = ('<clipPath id="cmb"><ellipse cx="0" cy="124" rx="187" ry="107"/></clipPath>'
          '<clipPath id="cmh"><ellipse cx="-4" cy="-18" rx="107" ry="95"/><polygon points="-101,-62 -92,-180 -10,-86"/><polygon points="89,-62 80,-180 -2,-86"/></clipPath>')
    back = (f'<g clip-path="url(#cmb)"><ellipse cx="70" cy="40" rx="170" ry="80" fill="{c["tb"]}"/>'
            f'<path d="M 110 40 q 12 24 0 50 M 160 50 q 12 22 2 44 M 200 66 q 8 18 0 36" fill="none" stroke="{c["st"]}" stroke-width="13" stroke-linecap="round"/></g>')
    headtab = (f'<g clip-path="url(#cmh)">'
           f'<path d="M -200 -200 L 200 -200 L 200 6 Q 120 30 60 4 L 10 -70 L -18 -70 L -66 4 Q -130 30 -200 6 Z" fill="{c["tb"]}"/>'
           f'<path d="M -60 -110 l 10 26 M -36 -116 l 6 30 M 26 -116 l -6 30 M 50 -110 l -10 26" stroke="{c["st"]}" stroke-width="10" stroke-linecap="round"/></g>')
    tab = ''
    base = base(bodyS) + back + base(headS) + headtab
    ears = f'<polygon points="-80,-80 -78,-138 -38,-96" fill="{c["pk"]}"/><polygon points="68,-80 66,-138 26,-96" fill="{c["pk"]}"/>'
    face = (f'<path d="M -70 -14 q 22 20 44 0 M 18 -14 q 22 20 44 0" fill="none" stroke="{c["w"]}" stroke-width="21" stroke-linecap="round"/>'
            f'<path d="M -70 -14 q 22 20 44 0 M 18 -14 q 22 20 44 0" fill="none" stroke="{c["eye"]}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M -16 10 L 8 10 L -4 24 Z" fill="{c["pk"]}" stroke="{c["pk"]}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M -20 32 q 8 8 16 0 q 8 8 16 0" fill="none" stroke="{c["eye"]}" stroke-width="6" stroke-linecap="round"/>')
    paws = f'<ellipse cx="-110" cy="206" rx="34" ry="18" fill="{c["w"]}" stroke="{ol}" stroke-width="9"/><ellipse cx="-50" cy="210" rx="34" ry="18" fill="{c["w"]}" stroke="{ol}" stroke-width="9"/>'
    return f'<defs>{cp}</defs>' + L('b', patch) + L('a', tail + base + tab + ears + face + paws)
def sB(P):
    c = cols(P); ol = c['ol']
    patch = f'<polygon points="-210,150 250,150 196,272 -264,272" fill="{lightfill(P)}"/>'
    # 身體（坐姿）＋尾巴
    body = 'M -96 220 C -120 120 -84 40 -40 20 L 40 20 C 84 40 120 120 96 220 Z'
    tail_d = 'M 92 210 C 170 214 214 180 206 120'
    tail = (f'<path d="{tail_d}" fill="none" stroke="{ol}" stroke-width="54" stroke-linecap="round"/>'
            f'<path d="{tail_d}" fill="none" stroke="{c["tb"]}" stroke-width="34" stroke-linecap="round"/>'
            f'<path d="{tail_d}" fill="none" stroke="{c["st"]}" stroke-width="34" stroke-dasharray="0 40 12 300"/>'
            f'<path d="M 210 150 C 211 140 209 128 206 120" fill="none" stroke="{c["tip"]}" stroke-width="34" stroke-linecap="round"/>')
    bodyg = (f'<path d="{body}" fill="{c["w"]}" stroke="{ol}" stroke-width="12" stroke-linejoin="round"/>'
             f'<path d="M -96 220 C -120 120 -84 40 -40 20 L -20 20 C -60 70 -70 150 -50 220 Z" fill="{c["tb"]}" stroke="{ol}" stroke-width="12" stroke-linejoin="round"/>'
             f'<path d="M 96 220 C 120 120 84 40 40 20 L 20 20 C 60 70 70 150 50 220 Z" fill="{c["tb"]}" stroke="{ol}" stroke-width="12" stroke-linejoin="round"/>'
             f'<ellipse cx="-34" cy="222" rx="30" ry="18" fill="{c["w"]}" stroke="{ol}" stroke-width="10"/><ellipse cx="34" cy="222" rx="30" ry="18" fill="{c["w"]}" stroke="{ol}" stroke-width="10"/>')
    # 頭（往右歪 14 度）
    hs = ('<ellipse cx="0" cy="-60" rx="112" ry="96"/>'
          '<polygon points="-104,-96 -112,-214 -30,-146"/><polygon points="104,-96 112,-214 30,-146"/>')
    cp = f'<clipPath id="cmB">{hs}</clipPath>'
    head = (f'<g fill="{c["w"]}" stroke="{ol}" stroke-width="12" stroke-linejoin="round">{hs}</g>'
            f'<g clip-path="url(#cmB)">'
            f'<path d="M -220 -260 L 220 -260 L 220 -40 Q 150 -20 70 -50 L 14 -128 L -14 -128 L -70 -50 Q -150 -20 -220 -40 Z" fill="{c["tb"]}"/>'
            f'<path d="M -64 -150 l 10 28 M -36 -156 l 6 30 M 36 -156 l -6 30 M 64 -150 l -10 28" stroke="{c["st"]}" stroke-width="10" stroke-linecap="round"/>'
            f'</g>'
            f'<g fill="none" stroke="{ol}" stroke-width="12" stroke-linejoin="round">{hs}</g>'
            f'<polygon points="-92,-112 -98,-180 -48,-140" fill="{c["pk"]}"/><polygon points="92,-112 98,-180 48,-140" fill="{c["pk"]}"/>'
            f'<circle cx="-46" cy="-62" r="31" fill="{c["w"]}"/><circle cx="46" cy="-62" r="31" fill="{c["w"]}"/>'
            f'<circle cx="-46" cy="-62" r="24" fill="{c["eye"]}"/><circle cx="46" cy="-62" r="24" fill="{c["eye"]}"/>'
            f'<circle cx="-38" cy="-72" r="8" fill="{c["w"]}"/><circle cx="54" cy="-72" r="8" fill="{c["w"]}"/>'
            f'<path d="M -14 -26 L 14 -26 L 0 -10 Z" fill="{c["pk"]}" stroke="{c["pk"]}" stroke-width="6" stroke-linejoin="round"/>'
            f'<path d="M -20 0 q 10 10 20 0 q 10 10 20 0" fill="none" stroke="{c["eye"]}" stroke-width="7" stroke-linecap="round"/>')
    return f'<defs>{cp}</defs>' + L('b', patch) + L('a', tail + bodyg + f'<g transform="rotate(14 0 0)">{head}</g>')
VAR = [('A', 'A_米克斯打盹', sA), ('B', 'B_米克斯歪頭', sB)]
