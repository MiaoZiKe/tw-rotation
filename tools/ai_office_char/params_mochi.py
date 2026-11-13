# 糰糰（mochi）參數。座標：Blender 慣例，公尺。X 右、Y 向後（臉朝 -Y）、Z 向上；腳底在 Z=0。
# 匯出 glTF 時轉成 Y 向上、臉朝 +Z（與 three.js 與既有角色一致）。
# 其他物種：複製本檔改數字、增減 PARTS／BONES 即可重用 build_char.py。
NAME = 'mochi'

# 橢球部件：c 中心、r 半徑、rot 繞 Y 軸傾角（度，正值＝上端往 +X 倒）、k 與「已合併的部分」平滑聯集的圓角半徑（越大過渡越肥）。
# mirror=True 代表同時生成 X 鏡射的另一半。
BODY = dict(c=(0, 0.01, 0.337), r=(0.445, 0.405, 0.385), pear=0.14)   # pear：下半身加寬比例（梨形，要小：下盤略寬但圓順）
PARTS = [
    # 耳：圓而小，長在頭頂兩側（微向外傾）
    dict(n='ear',  c=(0.272, 0.01, 0.668), r=(0.092, 0.070, 0.088), rot=22, k=0.045, mirror=True),
    # 手：身體兩側清楚凸出的短小手（長軸沿 X，向外下方；露出約身高的 15%），末端圓潤
    dict(n='arm',  c=(0.468, -0.08, 0.19), r=(0.084, 0.068, 0.064), rot=0, k=0.05, mirror=True, axis='arm'),
    # 腳：身體前下方露出一小塊腳掌
    dict(n='leg',  c=(0.150, -0.255, 0.036), r=(0.072, 0.075, 0.038), rot=0, k=0.045, mirror=True),
    dict(n='tail', c=(0.0, 0.385, 0.18), r=(0.062, 0.066, 0.062), rot=0, k=0.045, mirror=False),
]
FLOOR_K = 0.02          # 腳底壓平的圓角

# 骨架：名稱 -> (parent, head, tail)。左右 L=+X。tail 只決定骨頭朝向與蒙皮距離。
def _lr(n, par, h, t):
    out = {}
    for s, side in ((1, 'L'), (-1, 'R')):
        out[f'{n}.{side}'] = (par.replace('@', side) if par else None, (h[0] * s, h[1], h[2]), (t[0] * s, t[1], t[2]))
    return out
BONES = {
    'root':   (None,    (0, 0, 0),        (0, 0, 0.1)),
    'pelvis': ('root',  (0, 0, 0.17),     (0, 0, 0.30)),
    'spine':  ('pelvis',(0, 0, 0.30),     (0, 0, 0.46)),
    'head':   ('spine', (0, 0, 0.46),     (0, 0, 0.74)),
    'tail':   ('pelvis',(0, 0.34, 0.19),  (0, 0.42, 0.185)),
    'tail.tip':('tail', (0, 0.42, 0.185), (0, 0.47, 0.18)),
}
BONES.update(_lr('ear', 'head',   (0.25, 0.0, 0.58), (0.285, 0.0, 0.68)))
BONES.update(_lr('ear.tip', 'ear.@', (0.285, 0.0, 0.68), (0.31, 0.0, 0.75)))
BONES.update(_lr('arm', 'head',  (0.34, -0.07, 0.20), (0.46, -0.08, 0.18)))
BONES.update(_lr('hand', 'arm.@', (0.46, -0.08, 0.18), (0.53, -0.085, 0.16)))
BONES.update(_lr('leg', 'pelvis', (0.15, -0.16, 0.13), (0.15, -0.25, 0.05)))
BONES.update(_lr('foot', 'leg.@', (0.15, -0.25, 0.05), (0.15, -0.315, 0.03)))
# 蒙皮鏈：影響範圍（公尺）。near 內全權，far 外為 0
LIMBS = {
    'ear.L': dict(bones=('ear.L', 'ear.tip.L'), near=0.06, far=0.15, rootn=0.04, rootf=0.12),
    'ear.R': dict(bones=('ear.R', 'ear.tip.R'), near=0.06, far=0.15, rootn=0.04, rootf=0.12),
    'arm.L': dict(bones=('arm.L', 'hand.L'), near=0.06, far=0.11, rootn=0.025, rootf=0.085),
    'arm.R': dict(bones=('arm.R', 'hand.R'), near=0.06, far=0.11, rootn=0.025, rootf=0.085),
    'leg.L': dict(bones=('leg.L', 'foot.L'), near=0.065, far=0.13, rootn=0.05, rootf=0.14),
    'leg.R': dict(bones=('leg.R', 'foot.R'), near=0.065, far=0.13, rootn=0.05, rootf=0.14),
    'tail':  dict(bones=('tail', 'tail.tip'), near=0.05, far=0.12),
}
TORSO = ('pelvis', 'spine', 'head')      # 軀幹由低到高：用 Z 漸層分配
TORSO_Z = (0.085, 0.15)                   # 骨盆→脊椎→頭的過渡中心（糰糰的頭就是身體，臉要整片跟著頭動，所以頭的範圍從很低就開始）
TORSO_W = 0.07                            # 過渡半寬

# 臉：左右眼、鼻、嘴、腮紅位置（X 為正值那一側；Z 高度）。表面點由 SDF 求出。
FACE = dict(eye_x=0.168, eye_z=0.300, nose_z=0.250, mouth_z=0.222, cheek_x=0.25, cheek_z=0.228, brow_z=0.405,
            decal_x=0.345, decal_z0=0.075, decal_z1=0.515, decal_cz=0.295, decal_rz=0.225)
CHEEK_KEY = (0.25, -0.28, 0.228)          # 形態鍵 cheek.L/R 的中心（X 取正側）
LODS = {0: 2700, 1: 950, 2: 420}          # 目標四邊形數（三角面約 2 倍）；LOD0 本體 7000＋臉貼片約 900 ＜ 9000
# 局部顏色（頂點色 RGB 乘數，≤1）：耳內淡粉、肚子較淺、手掌腳掌略粉
TINT = dict(body=(1.0, 1.0, 1.0), belly=(1.0, 1.0, 1.0), pink=(1.0, 0.89, 0.87), palm=(1.0, 1.0, 1.0))
# 局部加密：四肢末端與耳尖的小弧面需要比身體更密的網格，輪廓才不會看出折角（段：起點、終點、半徑；每級是否啟用見 REFINE_LODS）
REFINE = [((0.39, -0.08, 0.185), (0.50, -0.09, 0.15), 0.085), ((-0.39, -0.08, 0.185), (-0.50, -0.09, 0.15), 0.085),
          ((0.15, -0.25, 0.04), (0.15, -0.32, 0.03), 0.07), ((-0.15, -0.25, 0.04), (-0.15, -0.32, 0.03), 0.07),
          ((0.26, 0.0, 0.66), (0.30, 0.0, 0.74), 0.095), ((-0.26, 0.0, 0.66), (-0.30, 0.0, 0.74), 0.095),
          ((0.0, 0.38, 0.18), (0.0, 0.44, 0.18), 0.065)]
REFINE_LODS = (0, 1)

# 配件掛點（表面點由距離場求出）：Z 高度、X 偏移
ANCHOR_PTS = dict(chest=(0, 0.16), bow=(0.17, 0.52), badge=(0.13, 0.17), scarf=(0, 0.11))
