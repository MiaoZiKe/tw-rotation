# 布布（pudding）：雞蛋布丁。平頂梯形（旋轉體、側面微鼓）＋焦糖圓唇（蓋在頂面邊緣、前右側垂下兩滴）＋頂面小凹窩給櫻桃坐。
# 沒有手、沒有耳；底部只露兩小塊腳尖（讓腳步規劃有東西可以落地）。座標：Blender 慣例（Y 向後＝臉朝 -Y），腳底 Z=0。
# 交界（k）：焦糖圓唇 0.025、兩滴焦糖 0.04、腳尖 0.04、凹窩 0.02。
import numpy as np
NAME = 'pudding'
GRID = dict(x=(-0.46, 0.46), y=(-0.46, 0.46), z=(-0.04, 0.62), h=0.007)
GRAD_Y = (0.0, 0.42)
VOXEL = 0.0075
BODY = dict(kind='lathe', c=(0.0, 0.0, 0.0), profile=[(0.0, 0.04), (0.255, 0.04), (0.300, 0.10), (0.285, 0.20), (0.250, 0.32), (0.205, 0.405), (0.0, 0.405)], round=0.04, r=(0.34, 0.34, 0.45), pear=0.0)
PARTS = [
    dict(n='lip', c=(0.0, 0.0, 0.408), r=(0.262, 0.262, 0.046), k=0.025),
    dict(n='drip', c=(0.15, -0.14, 0.352), r=(0.052, 0.042, 0.082), k=0.04),
    dict(n='drip', c=(-0.20, 0.10, 0.37), r=(0.046, 0.040, 0.06), k=0.04),
    dict(n='dent', op='sub', c=(0.03, 0.0, 0.462), r=(0.068, 0.068, 0.034), k=0.02),
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
    'head': ('spine', (0, 0, 0.27), (0, 0, 0.45)), 'tail': ('pelvis', (0, 0.1, 0.14), (0, 0.16, 0.14)), 'tail.tip': ('tail', (0, 0.16, 0.14), (0, 0.2, 0.14)),
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
BREATH_Z = (0.05, 0.12, 0.40, 0.30)
FACE = dict(eye_x=0.098, eye_z=0.262, nose_z=0.21, mouth_z=0.190, cheek_x=0.172, cheek_z=0.190, brow_z=0.325, eyeK=0.80,
            decal_x=0.215, decal_z0=0.06, decal_z1=0.385, decal_cz=0.225, decal_rz=0.17)
CHEEK_KEY = (0.172, -0.24, 0.19)
ANCHOR_PTS = dict(chest=(0, 0.12), bow=(-0.14, 0.375), badge=(0.14, 0.12))
LODS = {0: 2600, 1: 900, 2: 380}
REFINE = [((0.10, -0.2, 0.05), (0.10, -0.24, 0.03), 0.06), ((-0.10, -0.2, 0.05), (-0.10, -0.24, 0.03), 0.06)]
REFINE_LODS = (0, 1)
TINT_PATCHES = []
ZONE = dict(name='cap', y0=0.375, y1=0.395)
def zone_mask(P, N):
    """焦糖區：圓唇（z>0.39）＋前右、後左兩滴（高斯範圍）。輸出 0..1，存在本體 UV 的 U。"""
    t = np.clip((P[:, 2] - 0.385) / 0.02, 0, 1); m = t * t * (3 - 2 * t)
    for c, r in (((0.15, -0.14, 0.352), (0.075, 0.062, 0.10)), ((-0.20, 0.10, 0.37), (0.068, 0.06, 0.085))):
        g = np.exp(-np.sum(((P - np.array(c)) / np.array(r)) ** 2, 1)); gg = np.clip((g - 0.28) / 0.25, 0, 1); m = np.maximum(m, gg * gg * (3 - 2 * gg))
    return m
