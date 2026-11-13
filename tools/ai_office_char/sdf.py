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
def make_sdf(P0):
    B = P0.BODY
    def sdf(P):
        P = np.asarray(P, float)
        # 梨形：下半身往外加寬（把 X、Y 在低處除以較大的係數）
        zn = (P[:, 2] - B['c'][2]) / B['r'][2]
        t = np.clip((0.55 - zn) / 1.4, 0, 1); w = 1 + B['pear'] * (t * t * (3 - 2 * t))
        Q = P.copy(); Q[:, 0] = (P[:, 0]) / w; Q[:, 1] = B['c'][1] + (P[:, 1] - B['c'][1]) / (1 + (w - 1) * 0.6)
        d = ellipsoid(Q, B['c'], B['r'])
        for p in P0.PARTS:
            sides = (1, -1) if p.get('mirror') else (1,)
            for s in sides:
                c = (p['c'][0] * s, p['c'][1], p['c'][2]); rot = p.get('rot', 0) * s
                d = smin(d, ellipsoid(P, c, p['r'], rot), p['k'])
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
