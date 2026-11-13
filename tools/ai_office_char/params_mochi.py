# 糰糰（mochi）參數。座標：Blender 慣例，公尺。X 右、Y 向後（臉朝 -Y）、Z 向上；腳底在 Z=0。
# 匯出 glTF 時轉成 Y 向上、臉朝 +Z（與 three.js 與既有角色一致）。
# 其他物種：複製本檔改數字、增減 PARTS／BONES 即可重用 build_char.py。
NAME = 'mochi'

# 橢球部件：c 中心、r 半徑、rot 繞 Y 軸傾角（度，正值＝上端往 +X 倒）、k 與「已合併的部分」平滑聯集的圓角半徑（越大過渡越肥）。
# mirror=True 代表同時生成 X 鏡射的另一半。
BODY = dict(c=(0, 0.012, 0.378), r=(0.425, 0.40, 0.355), pear=0.15)   # pear：下半身加寬比例（梨形）
PARTS = [
    dict(n='ear',  c=(0.238, 0.01, 0.685), r=(0.118, 0.098, 0.158), rot=26, k=0.065, mirror=True),
    dict(n='arm',  c=(0.400, -0.06, 0.245), r=(0.090, 0.088, 0.105), rot=-24, k=0.09, mirror=True, axis='arm'),
    dict(n='leg',  c=(0.172, -0.095, 0.078), r=(0.112, 0.158, 0.09), rot=0, k=0.07, mirror=True),
    dict(n='tail', c=(0.0, 0.395, 0.215), r=(0.074, 0.082, 0.074), rot=0, k=0.05, mirror=False),
]
FLOOR_K = 0.03          # 腳底壓平的圓角

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
    'tail':   ('pelvis',(0, 0.33, 0.22),  (0, 0.41, 0.21)),
    'tail.tip':('tail', (0, 0.41, 0.21),  (0, 0.47, 0.20)),
}
BONES.update(_lr('ear', 'head',   (0.235, 0.0, 0.57), (0.28, 0.0, 0.67)))
BONES.update(_lr('ear.tip', 'ear.@', (0.28, 0.0, 0.67), (0.32, 0.0, 0.80)))
BONES.update(_lr('arm', 'spine',  (0.34, -0.05, 0.27), (0.45, -0.07, 0.215)))
BONES.update(_lr('hand', 'arm.@', (0.45, -0.07, 0.215), (0.52, -0.08, 0.185)))
BONES.update(_lr('leg', 'pelvis', (0.172, -0.04, 0.15), (0.172, -0.085, 0.05)))
BONES.update(_lr('foot', 'leg.@', (0.172, -0.085, 0.05), (0.172, -0.19, 0.02)))
# 蒙皮鏈：影響範圍（公尺）。near 內全權，far 外為 0
LIMBS = {
    'ear.L': dict(bones=('ear.L', 'ear.tip.L'), near=0.07, far=0.17),
    'ear.R': dict(bones=('ear.R', 'ear.tip.R'), near=0.07, far=0.17),
    'arm.L': dict(bones=('arm.L', 'hand.L'), near=0.07, far=0.15),
    'arm.R': dict(bones=('arm.R', 'hand.R'), near=0.07, far=0.15),
    'leg.L': dict(bones=('leg.L', 'foot.L'), near=0.085, far=0.17),
    'leg.R': dict(bones=('leg.R', 'foot.R'), near=0.085, far=0.17),
    'tail':  dict(bones=('tail', 'tail.tip'), near=0.06, far=0.14),
}
TORSO = ('pelvis', 'spine', 'head')      # 軀幹由低到高：用 Z 漸層分配
TORSO_Z = (0.22, 0.46)                    # 骨盆→脊椎→頭的過渡中心

# 臉：左右眼、鼻、嘴、腮紅位置（X 為正值那一側；Z 高度）。表面點由 SDF 求出。
FACE = dict(eye_x=0.168, eye_z=0.305, eye_r=0.066, nose_z=0.262, mouth_z=0.222, cheek_x=0.265, cheek_z=0.235, brow_z=0.405,
            decal_x=0.30, decal_z0=0.115, decal_z1=0.50)
LODS = {0: 3100, 1: 1000, 2: 300}          # 目標四邊形數（三角面約 2 倍）
