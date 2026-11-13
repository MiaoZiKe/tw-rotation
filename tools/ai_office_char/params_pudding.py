# 布布（pudding）：雞蛋布丁。平頂梯形（旋轉體、側面微鼓）＋焦糖圓唇（蓋在頂面邊緣、前右側垂下兩滴）＋頂面小凹窩給櫻桃坐。
# 沒有手、沒有耳；底部只露兩小塊腳尖（讓腳步規劃有東西可以落地）。座標：Blender 慣例（Y 向後＝臉朝 -Y），腳底 Z=0。
# 交界（k）：焦糖圓唇 0.025、兩滴焦糖 0.04、腳尖 0.04、凹窩 0.02。
import numpy as np
NAME = 'pudding'
GRID = dict(x=(-0.46, 0.46), y=(-0.46, 0.46), z=(-0.04, 0.62), h=0.007)
GRAD_Y = (0.0, 0.42)
VOXEL = 0.0075
# 側面用平滑曲線取樣（下緣外鼓、上段拋物線內收），不是幾段直線，輪廓才不會有折角
_low = [(0.255 + 0.045 * np.sin(np.pi * t / 2), 0.04 + 0.08 * t) for t in np.linspace(0, 1, 7)]
_up = [(0.30 - 0.98 * (z - 0.12) ** 2, z) for z in np.linspace(0.12, 0.47, 26)[1:]]
BODY = dict(kind='lathe', c=(0.0, 0.0, 0.0), profile=[(0.0, 0.04)] + _low + _up + [(0.0, 0.47)], round=0.04, r=(0.34, 0.34, 0.5), pear=0.0)
PARTS = [
    dict(n='lip', c=(0.0, 0.0, 0.468), r=(0.246, 0.246, 0.046), k=0.025),
    # 焦糖從圓唇邊緣自然垂下幾道（長短不一）
    dict(n='drip', c=(0.17, -0.14, 0.395), r=(0.05, 0.04, 0.095), k=0.04),
    dict(n='drip', c=(-0.02, -0.235, 0.43), r=(0.045, 0.036, 0.06), k=0.04),
    dict(n='drip', c=(-0.2, 0.12, 0.415), r=(0.045, 0.038, 0.08), k=0.04),
    dict(n='drip', c=(0.22, 0.1, 0.44), r=(0.04, 0.034, 0.05), k=0.04),
    # 白色鮮奶油小丘（頂面中央），櫻桃坐在上面
    dict(n='cream', c=(0.0, 0.0, 0.512), r=(0.15, 0.15, 0.052), k=0.03),
    dict(n='foot', c=(0.10, -0.205, 0.03), r=(0.052, 0.062, 0.032), k=0.04, mirror=True),
]
FLOOR_K = 0.02
def _lr(n, par, h, t):
    out = {}
    for s, side in ((1, 'L'), (-1, 'R')):
        out[f'{n}.{side}'] = (par.replace('@', side) if par else None, (h[0] * s, h[1], h[2]), (t[0] * s, t[1], t[2]))
    return out
BONES = {
    'root': (None, (0, 0, 0), (0, 0, 0.1)), 'pelvis': ('root', (0, 0, 0.10), (0, 0, 0.18)), 'spine': ('pelvis', (0, 0, 0.18), (0, 0, 0.27)),
    'head': ('spine', (0, 0, 0.27), (0, 0, 0.5)), 'tail': ('pelvis', (0, 0.1, 0.14), (0, 0.16, 0.14)), 'tail.tip': ('tail', (0, 0.16, 0.14), (0, 0.2, 0.14)),
}
BONES.update(_lr('ear', 'head', (0.06, 0.0, 0.40), (0.07, 0.0, 0.43)))
BONES.update(_lr('ear.tip', 'ear.@', (0.07, 0.0, 0.43), (0.08, 0.0, 0.45)))
BONES.update(_lr('arm', 'head', (0.12, -0.05, 0.2), (0.16, -0.06, 0.2)))
BONES.update(_lr('hand', 'arm.@', (0.16, -0.06, 0.2), (0.19, -0.065, 0.2)))
BONES.update(_lr('leg', 'pelvis', (0.10, -0.14, 0.17), (0.10, -0.20, 0.05)))
BONES.update(_lr('foot', 'leg.@', (0.10, -0.20, 0.05), (0.10, -0.245, 0.03)))
LIMBS = {
    'leg.L': dict(bones=('leg.L', 'foot.L'), near=0.05, far=0.1, rootn=0.04, rootf=0.11),
    'leg.R': dict(bones=('leg.R', 'foot.R'), near=0.05, far=0.1, rootn=0.04, rootf=0.11),
}
TORSO = ('pelvis', 'spine', 'head'); TORSO_Z = (0.05, 0.10); TORSO_W = 0.05
BREATH_Z = (0.05, 0.12, 0.45, 0.35)
FACE = dict(eye_x=0.098, eye_z=0.295, nose_z=0.24, mouth_z=0.215, cheek_x=0.172, cheek_z=0.215, brow_z=0.365, eyeK=0.80,
            decal_x=0.215, decal_z0=0.07, decal_z1=0.44, decal_cz=0.255, decal_rz=0.2)
CHEEK_KEY = (0.172, -0.24, 0.215)
ANCHOR_PTS = dict(chest=(0, 0.13), bow=(-0.14, 0.42), badge=(0.14, 0.13))
CHERRY = (0.0, 0.595, 0.0)
AO_SMOOTH = 3
ZONE_SMOOTH = 3
LODS = {0: 3500, 1: 1100, 2: 380}
REFINE = [((0.10, -0.2, 0.05), (0.10, -0.24, 0.03), 0.06), ((-0.10, -0.2, 0.05), (-0.10, -0.24, 0.03), 0.06)]
REFINE_LODS = (0, 1)
TINT_PATCHES = []
ZONE = dict(name='cap')
def zone_mask(P, N):
    """焦糖區：圓唇（z>0.44）＋四道垂下的滴（高斯範圍）→ UV.u"""
    t = np.clip((P[:, 2] - 0.435) / 0.02, 0, 1); m = t * t * (3 - 2 * t)
    for c, r in (((0.17, -0.14, 0.395), (0.07, 0.058, 0.115)), ((-0.02, -0.235, 0.43), (0.062, 0.05, 0.08)), ((-0.2, 0.12, 0.415), (0.062, 0.055, 0.1)), ((0.22, 0.1, 0.44), (0.055, 0.05, 0.07))):
        g = np.exp(-np.sum(((P - np.array(c)) / np.array(r)) ** 2, 1)); gg = np.clip((g - 0.28) / 0.25, 0, 1); m = np.maximum(m, gg * gg * (3 - 2 * gg))
    m = m * (1 - zone_mask2(P, N))
    return m
def zone_mask2(P, N):
    """奶油區：頂面中央的白色小丘 → UV.v"""
    d = np.hypot(P[:, 0], P[:, 1]); t = np.clip((P[:, 2] - 0.49) / 0.02, 0, 1) * np.clip((0.15 - d) / 0.025, 0, 1); return t * t * (3 - 2 * t)
FINAL_SMOOTH = 8
