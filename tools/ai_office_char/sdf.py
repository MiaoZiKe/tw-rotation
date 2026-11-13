# 糰糰的距離場（numpy）：橢球平滑聯集。回傳負值＝在內部。
import numpy as np
def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25
def smax(a, b, k): return -smin(-a, -b, k)
def ellipsoid(P, c, r, rot=0.0):
    q = P - np.array(c)
    if rot:
        a = np.radians(rot); ca, sa = np.cos(a), np.sin(a)
        x = ca * q[:, 0] + sa * q[:, 2]; z = -sa * q[:, 0] + ca * q[:, 2]
        q = np.stack([x, q[:, 1], z], 1)
    r = np.array(r)
    k0 = np.linalg.norm(q / r, axis=1); k1 = np.linalg.norm(q / (r * r), axis=1)
    return np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -r.min())
def chain(P, pts, rw, rt, wdir=(1.0, 0.0, 0.0), k=0.03):
    """連續骨鏈（耳、尾、觸手）：沿折線的「錐形橢圓截面管」，截面寬 rw（沿 wdir）、厚 rt，兩端圓頭（軸向半徑＝寬）。
    各段之間用平滑最小值接起來（k），所以折彎處是圓的、不會有摺痕。回傳近似距離（梯度方向正確，數值略偏）。"""
    pts = np.asarray(pts, float); wd = np.asarray(wdir, float); d = None
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]; ab = b - a; L2 = float(ab @ ab); t = np.clip(((P - a) @ ab) / L2, 0, 1)
        C = a + t[:, None] * ab; T = ab / np.sqrt(L2)
        W = wd - T * (wd @ T); W /= np.linalg.norm(W); Nn = np.cross(T, W)
        q = P - C; qa = q @ T; qw = q @ W; qn = q @ Nn
        rwi = rw[i] * (1 - t) + rw[i + 1] * t; rti = rt[i] * (1 - t) + rt[i + 1] * t; rc = rwi
        q0 = np.stack([qw / rwi, qn / rti, qa / rc], 1); q1 = np.stack([qw / rwi ** 2, qn / rti ** 2, qa / rc ** 2], 1)
        k0 = np.linalg.norm(q0, axis=1); k1 = np.linalg.norm(q1, axis=1)
        di = np.where(k1 > 1e-9, k0 * (k0 - 1.0) / np.maximum(k1, 1e-9), -rti)
        d = di if d is None else smin(d, di, k)
    return d

def lathe(P, c, profile, rnd=0.0):
    """旋轉體（凸多邊形截面）：profile＝[(半徑 ρ, 高 z), …] 逆時針、含軸線上的兩點；rnd＝整圈外擴圓角（多邊形要先內縮 rnd）。"""
    q = P - np.array(c); rho = np.hypot(q[:, 0], q[:, 1]); z = q[:, 2]; pr = np.asarray(profile, float); n = len(pr)
    dmin = np.full(len(P), 1e9); inside = np.ones(len(P), bool)
    for i in range(n):
        a = pr[i]; b = pr[(i + 1) % n]; ab = b - a; L2 = ab @ ab
        t = np.clip(((rho - a[0]) * ab[0] + (z - a[1]) * ab[1]) / L2, 0, 1)
        dx = rho - (a[0] + t * ab[0]); dz = z - (a[1] + t * ab[1]); dmin = np.minimum(dmin, np.hypot(dx, dz))
        cr = ab[0] * (z - a[1]) - ab[1] * (rho - a[0]); inside &= cr >= 0
    return np.where(inside, -dmin, dmin) - rnd

def make_sdf(P0):
    B = P0.BODY
    def body(P):
        if B.get('kind') == 'lathe':
            return lathe(P, B['c'], B['profile'], B.get('round', 0.0))
        # 梨形：下半身往外加寬（把 X、Y 在低處除以較大的係數）
        zn = (P[:, 2] - B['c'][2]) / B['r'][2]
        t = np.clip((0.55 - zn) / 1.4, 0, 1); w = 1 + B['pear'] * (t * t * (3 - 2 * t))
        Q = P.copy(); Q[:, 0] = (P[:, 0]) / w; Q[:, 1] = B['c'][1] + (P[:, 1] - B['c'][1]) / (1 + (w - 1) * 0.6)
        return ellipsoid(Q, B['c'], B['r'])
    def sdf(P):
        P = np.asarray(P, float)
        d = body(P)
        for p in P0.PARTS:
            kind = p.get('kind', 'ell'); sides = (1, -1) if p.get('mirror') else (1,)
            for s in sides:
                if kind == 'chain':
                    pts = [(x * s, y, z) for x, y, z in p['pts']]; e = chain(P, pts, p['rw'], p['rt'], p.get('wdir', (1, 0, 0)), p.get('ck', 0.03))
                else:
                    c = (p['c'][0] * s, p['c'][1], p['c'][2]); e = ellipsoid(P, c, p['r'], p.get('rot', 0) * s)
                d = smax(d, -e, p['k']) if p.get('op') == 'sub' else smin(d, e, p['k'])
        return smax(d, -P[:, 2], P0.FLOOR_K)        # 腳底壓平（地面 Z=0）
    return sdf
def grad(sdf, P, e=1e-3):
    g = np.zeros_like(P)
    for i in range(3):
        o = np.zeros(3); o[i] = e
        g[:, i] = (sdf(P + o) - sdf(P - o)) / (2 * e)
    return g
def project(sdf, P, it=6):
    P = P.copy()
    for _ in range(it):
        g = grad(sdf, P); n2 = np.maximum((g * g).sum(1), 1e-9)
        P -= (sdf(P)[:, None]) * g / n2[:, None]
    return P
def ao(sdf, P, N):
    # 解析 SDF 環境遮蔽：沿法線取樣，距離場小於取樣距離代表附近有遮擋
    occ = np.zeros(len(P)); wsum = 0
    for h, w in ((0.015, 1.0), (0.035, 0.8), (0.07, 0.6), (0.12, 0.4)):
        occ += w * np.clip((h - sdf(P + N * h)) / h, 0, 1); wsum += w
    return np.clip(1 - occ / wsum * 1.15, 0, 1)
