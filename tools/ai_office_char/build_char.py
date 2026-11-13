"""AI Office 角色建模腳本（Blender Python，bpy 5.3）。

流程：參數化 SDF（橢球平滑聯集，四肢是「捏出來」的凸起）→ Marching Cubes → 體素重網格清拓樸 →
QuadriFlow 重拓撲成四邊形 → 投影回距離場 → 解析 AO 頂點色 → 程序化蒙皮權重 → 骨架 → 形態鍵 → 臉貼片 → GLB。

用法：  python build_char.py params_mochi  <輸出資料夾>  [--lod 0,1,2]
說明與環境安裝見 README.md。
"""
import sys, os, json, time, importlib, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bpy, bmesh
from skimage import measure
import sdf as S

def parse():
    a = sys.argv[1:]
    mod = a[0]; out = a[1]; lods = [0, 1, 2]
    if '--lod' in a: lods = [int(x) for x in a[a.index('--lod') + 1].split(',')]
    return mod, out, lods

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

# ───────────────────────── 網格
def marching(sdf, P0=None):
    g = getattr(P0, 'GRID', None) or dict(x=(-0.68, 0.68), y=(-0.55, 0.58), z=(-0.04, 0.88), h=0.008); h = g['h']
    xs = np.arange(g['x'][0], g['x'][1], h); ys = np.arange(g['y'][0], g['y'][1], h); zs = np.arange(g['z'][0], g['z'][1], h)
    G = np.stack(np.meshgrid(xs, ys, zs, indexing='ij'), -1).reshape(-1, 3)
    v = sdf(G).reshape(len(xs), len(ys), len(zs))
    vv, ff, _, _ = measure.marching_cubes(v, 1e-5, spacing=(h, h, h)); vv += np.array([xs[0], ys[0], zs[0]])
    return vv, ff, h

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def quad_mesh(vv, ff, h, quads, seed=3, P0=None):
    me = bpy.data.meshes.new('src'); me.from_pydata(vv.tolist(), [], ff.tolist()); me.update()
    bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=h * 0.1); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('Body', me); bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; ob.select_set(True)
    # QuadriFlow 對體素網格很挑（偶爾回「needs to be manifold」）：失敗就換體素大小重做，最多試幾輪
    v0 = getattr(P0, 'VOXEL', 0.007); tries = [(v0 * f, sm) for f in (1.0, 1.43, 0.79, 1.21, 1.79, 0.93, 1.07, 0.7) for sm in (0, 3)]; r = None
    for vs, sm in tries:
        ob.data.remesh_voxel_size = vs; bpy.ops.object.voxel_remesh()
        if sm:
            bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            for _ in range(sm - 1): bmesh.ops.smooth_vert(bm, verts=bm.verts, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
            bm.to_mesh(ob.data); bm.free()
        try: r = bpy.ops.object.quadriflow_remesh(mode='FACES', target_faces=quads, use_mesh_symmetry=getattr(P0, 'SYMMETRY', True), smooth_normals=True, seed=seed)
        except RuntimeError: r = None
        if r == {'FINISHED'}: print('quadriflow ok at voxel', round(vs, 4), 'smooth', sm); break
    assert r == {'FINISHED'}, 'quadriflow failed'
    return ob

def refine(ob, P0):
    """把四肢末端、耳尖附近的面再切一刀（之後整體會貼回距離場，所以新點直接落在解析曲面上）"""
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table(); edges = set()
    for f in bm.faces:
        c = np.array(f.calc_center_median())
        for a, b, r in getattr(P0, 'REFINE', []):
            d, _ = seg_dist(c[None], a, b)
            if d[0] < r: edges.update(f.edges); break
    bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1, use_grid_fill=True, use_single_edge=False)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    return ob

def verts(ob): return np.array([tuple(v.co) for v in ob.data.vertices])
def set_verts(ob, P):
    ob.data.vertices.foreach_set('co', P.reshape(-1)); ob.data.update()
def adjacency(ob):
    n = len(ob.data.vertices); E = np.array([tuple(e.vertices) for e in ob.data.edges])
    return n, E
def lap_smooth(P, n, E, it=1, lam=0.5):
    for _ in range(it):
        acc = np.zeros_like(P); cnt = np.zeros(n)
        np.add.at(acc, E[:, 0], P[E[:, 1]]); np.add.at(acc, E[:, 1], P[E[:, 0]]); np.add.at(cnt, E[:, 0], 1); np.add.at(cnt, E[:, 1], 1)
        P = P + lam * (acc / np.maximum(cnt, 1)[:, None] - P)
    return P
def vnormals(ob):
    ob.data.calc_normals() if hasattr(ob.data, 'calc_normals') else None
    return np.array([tuple(v.normal) for v in ob.data.vertices])

# ───────────────────────── 蒙皮
def seg_dist(P, a, b):
    a = np.array(a); b = np.array(b); ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1), t

def skin_weights(P, P0, n, E):
    names = list(P0.BONES.keys()); idx = {k: i for i, k in enumerate(names)}
    W = np.zeros((len(P), len(names)))
    fsum = np.zeros(len(P)); z = P[:, 2]
    for key, L in P0.LIMBS.items():
        b1, b2 = L['bones']; h1, t1 = P0.BONES[b1][1], P0.BONES[b1][2]; t2 = P0.BONES[b2][2]
        d1, u1 = seg_dist(P, h1, t1); d2, u2 = seg_dist(P, t1, t2)
        d = np.minimum(d1, d2); f = 1 - sstep(L['near'], L['far'], d)
        root = np.linalg.norm(P - np.array(h1), axis=1)
        f = f * sstep(L.get('rootn', 0.05), L.get('rootf', 0.17), root)      # 根部漸入：內凹過渡區跟著身體動
        # 沿鏈位置 0..2
        tc = np.where(d1 <= d2, u1, 1 + u2)
        w2 = sstep(0.6, 1.5, tc)
        W[:, idx[b1]] += f * (1 - w2); W[:, idx[b2]] += f * w2; fsum += f
    fsum = np.clip(fsum, 0, 1)
    rest = 1 - fsum
    a, b = P0.TORSO_Z
    w_ = getattr(P0, 'TORSO_W', 0.09); t1_ = sstep(a - w_, a + w_, z); t2_ = sstep(b - w_, b + w_, z)
    W[:, idx['pelvis']] += rest * (1 - t1_); W[:, idx['spine']] += rest * t1_ * (1 - t2_); W[:, idx['head']] += rest * t1_ * t2_
    # 平滑權重，再取前四名
    for _ in range(3):
        Wn = lap_smooth(W, n, E, 1, 0.5); W = Wn
    top = np.argsort(-W, 1)[:, :4]; M = np.zeros_like(W)
    np.put_along_axis(M, top, np.take_along_axis(W, top, 1), 1)
    M /= np.maximum(M.sum(1, keepdims=True), 1e-9)
    return names, M, fsum

def apply_weights(ob, names, M, ids=None):
    vgs = [ob.vertex_groups.new(name=nm) for nm in names]
    for i in range(M.shape[0]):
        for j in np.nonzero(M[i] > 1e-4)[0]:
            vgs[j].add([i], float(M[i, j]), 'REPLACE')

# ───────────────────────── 形態鍵（座標 P、法線 N 的純函式，所以任何 LOD 都一致）
def shape_deltas(P, N, fsum, P0):
    D = {}
    z = P[:, 2]; x = P[:, 0]; y = P[:, 1]
    cy = P0.BODY['c'][1]
    def sc(sx, sy, sz, zc=0.0):
        Q = P.copy(); Q[:, 0] = x * sx; Q[:, 1] = cy + (y - cy) * sy; Q[:, 2] = zc + (z - zc) * sz; return Q - P
    D['squash'] = sc(1.10, 1.10, 0.80)
    D['stretch'] = sc(0.935, 0.935, 1.15)
    low = sstep(0.55, 0.0, z)
    d = sc(1.17, 1.17, 0.70); d[:, 0] *= (0.5 + 0.5 * low); d[:, 1] *= (0.5 + 0.5 * low); D['land'] = d
    D['plump'] = sc(1.07, 1.07, 0.975)
    bz = getattr(P0, 'BREATH_Z', (0.08, 0.2, 0.62, 0.45))
    torso = (1 - fsum) * sstep(bz[0], bz[1], z) * sstep(bz[2], bz[3], z)
    D['breath'] = N * (0.0125 * torso)[:, None]
    for s, nm in ((1, 'L'), (-1, 'R')):
        ck = P0.CHEEK_KEY; cc = np.array([s * ck[0], ck[1], ck[2]]); g = np.exp(-np.sum((P - cc) ** 2, 1) / 0.095 ** 2)
        D[f'cheek.{nm}'] = N * (0.024 * g)[:, None]
    return D

def add_shapes(ob, D):
    ob.shape_key_add(name='Basis')
    for k, d in D.items():
        sk = ob.shape_key_add(name=k, from_mix=False); P = np.array([tuple(v.co) for v in ob.data.vertices])
        sk.data.foreach_set('co', (P + d).reshape(-1)); sk.value = 0.0

# ───────────────────────── 局部顏色（頂點色 RGB 乘數，≤1）
def local_tint(P, N, P0):
    if getattr(P0, 'TINT_PATCHES', None) is not None: return patch_tint(P, N, P0)
    T = P0.TINT; n = len(P); col = np.tile(np.array(T['body']), (n, 1))
    front = sstep(0.05, 0.5, -N[:, 1])
    # 肚子較淺：身體前下方一塊柔邊橢圓
    bm = np.exp(-((P[:, 0] / 0.17) ** 2 + ((P[:, 2] - 0.135) / 0.105) ** 2)) * front
    col = col + (np.array(T['belly']) - col) * bm[:, None]
    # 耳內淡粉
    for p in P0.PARTS:
        if p['n'] != 'ear': continue
        for s_ in (1, -1):
            c = np.array([p['c'][0] * s_, p['c'][1], p['c'][2]])
            m = np.exp(-(((P[:, 0] - c[0]) / 0.085) ** 4 + ((P[:, 2] - c[2] - 0.01) / 0.085) ** 4)) * sstep(-0.1, 0.4, -N[:, 1]) * sstep(0.56, 0.62, P[:, 2])
            col = col + (np.array(T['pink']) - col) * (0.92 * m)[:, None]
    # 手掌、腳掌略粉（取骨架末端附近；手是外側末端、腳是底面與前端）
    for s_ in (1, -1):
        for bn, rad, k in (('hand', 0.075, 0.9), ('foot', 0.07, 0.8)):
            t = np.array(P0.BONES[f'{bn}.{"L" if s_ > 0 else "R"}'][2]); h = np.array(P0.BONES[f'{bn}.{"L" if s_ > 0 else "R"}'][1])
            c = (t * 0.7 + h * 0.3)
            m = np.exp(-np.sum((P - c) ** 2, 1) / rad ** 2)
            col = col + (np.array(T['palm']) - col) * (k * m)[:, None]
    return np.clip(col, 0, 1)

def patch_tint(P, N, P0):
    """通用局部顏色：每個補丁＝橢球範圍內的顏色乘數（c 中心、r 半徑、color、k 強度、mirror、face＝只作用在朝前的面）。"""
    col = np.ones((len(P), 3))
    for t in P0.TINT_PATCHES:
        for s_ in ((1, -1) if t.get('mirror') else (1,)):
            c = np.array([t['c'][0] * s_, t['c'][1], t['c'][2]]); r = np.array(t['r'])
            m = np.exp(-np.sum(((P - c) / r) ** 4, 1)) * t.get('k', 1.0)
            if t.get('face'): m = m * sstep(0.05, 0.5, -N[:, 1])
            col = col + (np.array(t['color']) - col) * m[:, None]
    return np.clip(col, 0, 1)

def set_custom_normals(ob, N):
    try:
        ob.data.normals_split_custom_set_from_vertices([tuple(v) for v in N])
    except Exception as e:
        print('custom normals failed:', e)

# ───────────────────────── 骨架
def make_armature(P0):
    arm = bpy.data.armatures.new('Rig'); ao = bpy.data.objects.new('Rig', arm); bpy.context.scene.collection.objects.link(ao)
    bpy.context.view_layer.objects.active = ao; ao.select_set(True); bpy.ops.object.mode_set(mode='EDIT')
    for nm, (par, h, t) in P0.BONES.items():
        b = arm.edit_bones.new(nm); b.head = h; b.tail = t
    for nm, (par, h, t) in P0.BONES.items():
        if par:
            b = arm.edit_bones[nm]; b.parent = arm.edit_bones[par]
            if (np.array(arm.edit_bones[par].tail) - np.array(h)).any() == 0: b.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    return ao

def bind(ob, ao):
    ob.parent = ao
    m = ob.modifiers.new('Armature', 'ARMATURE'); m.object = ao

# ───────────────────────── 臉貼片與錨點
def surface_point(sdf, x, z, y0=-0.8, y1=0.0):
    lo, hi = y0, y1
    for _ in range(40):
        mid = (lo + hi) / 2
        if sdf(np.array([[x, mid, z]]))[0] > 0: lo = mid
        else: hi = mid
    p = np.array([[x, (lo + hi) / 2, z]]); g = S.grad(sdf, p)[0]; return p[0], g / np.linalg.norm(g)

def make_decal(ob, P0, sdf):
    F = P0.FACE; bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
    keep = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.y < 0 and (c.x / F['decal_x']) ** 2 + ((c.z - F['decal_cz']) / F['decal_rz']) ** 2 < 1.0 and f.normal.y < -0.2: keep.append(f)
    kv = set(v for f in keep for v in f.verts)
    nb = bmesh.new(); mp = {}
    for v in kv: mp[v] = nb.verts.new(v.co)
    for f in keep: nb.faces.new([mp[v] for v in f.verts])
    me = bpy.data.meshes.new('FaceDecal'); nb.to_mesh(me); nb.free(); bm.free()
    d = bpy.data.objects.new('FaceDecal', me); bpy.context.scene.collection.objects.link(d)
    P = verts(d); Q = S.project(sdf, P, 2); G = S.grad(sdf, Q); G /= np.linalg.norm(G, axis=1)[:, None]
    set_verts(d, Q + G * 0.0012)
    uv = me.uv_layers.new(name='UV0')
    for poly in me.polygons:
        for li in poly.loop_indices:
            p = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((p.x + F['decal_x']) / (2 * F['decal_x']), (p.z - F['decal_z0']) / (F['decal_z1'] - F['decal_z0']))
    for p in me.polygons: p.use_smooth = True
    return d

def anchors(sdf, P0):
    F = P0.FACE; A = {}
    def put(name, x, z, off=0.0):
        p, n = surface_point(sdf, x, z); A[name] = dict(p=list(map(float, p)), n=list(map(float, n)))
    for s, nm in ((1, 'L'), (-1, 'R')):
        put(f'eye.{nm}', s * F['eye_x'], F['eye_z']); put(f'cheek.{nm}', s * F['cheek_x'], F['cheek_z']); put(f'brow.{nm}', s * F['eye_x'], F['brow_z'])
    put('nose', 0, F['nose_z']); put('mouth', 0, F['mouth_z'])
    # 配件掛點：頂、胸
    p, n = surface_point(sdf, 0.0, 0.0, -0.7, 0.0)
    top = np.array([[0.0, P0.BODY['c'][1], 1.0]]);
    lo, hi = 0.3, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if sdf(np.array([[0, P0.BODY['c'][1], mid]]))[0] > 0: hi = mid
        else: lo = mid
    A['hat'] = dict(p=[0, P0.BODY['c'][1], lo], n=[0, 0, 1])
    for nm, (ax, az) in getattr(P0, 'ANCHOR_PTS', dict(chest=(0, 0.16), bow=(0.17, 0.52))).items(): put(nm, ax, az)
    # 腳底接觸（左右腳中心）：Z=0 平面的接地足印
    fh = P0.BONES['foot.L'][2]
    A['foot.L'] = dict(p=[fh[0], fh[1], 0.0], n=[0, 0, 1]); A['foot.R'] = dict(p=[-fh[0], fh[1], 0.0], n=[0, 0, 1])
    return A

def to_gltf(v): return [float(v[0]), float(v[2]), float(-v[1])]

# ───────────────────────── 主流程
def build_lod(P0, lod, quads, cache, out_dir):
    clear(); vv, ff, h, sdf = cache
    ob = quad_mesh(vv, ff, h, quads, P0=P0)
    if lod in P0.REFINE_LODS: refine(ob, P0)
    P = verts(ob); n, E = adjacency(ob)
    # 重拓撲後先把四邊形邊長整平（切線平滑）再貼回距離場：輪廓是解析曲面，格點分佈均勻，頂點法線才不會抖
    for _ in range(4):
        P = lap_smooth(P, n, E, 2, 0.5); P = S.project(sdf, P, 6)
    P = S.project(sdf, P, 8); set_verts(ob, P)
    bpy.ops.object.shade_smooth()
    N = S.grad(sdf, P); N /= np.linalg.norm(N, axis=1)[:, None]
    set_custom_normals(ob, N)
    names, M, fsum = skin_weights(P, P0, n, E)
    apply_weights(ob, names, M)
    # AO 頂點色
    ao = S.ao(sdf, P, N)
    ca = ob.data.color_attributes.new(name='AO', type='FLOAT_COLOR', domain='POINT')
    tint = local_tint(P, N, P0)            # RGB＝局部顏色乘數；A＝AO（執行期 setAOStrength 依材質調強度，再合成成 RGB）
    col = np.concatenate([tint, ao[:, None]], 1); ca.data.foreach_set('color', col.reshape(-1))
    if hasattr(P0, 'zone_mask'):
        zm = np.clip(P0.zone_mask(P, N), 0, 1); uvl = ob.data.uv_layers.new(name='UV0')
        for poly in ob.data.polygons:
            for li in poly.loop_indices: uvl.data[li].uv = (float(zm[ob.data.loops[li].vertex_index]), 0.5)
    arm = make_armature(P0); bind(ob, arm)
    D = shape_deltas(P, N, fsum, P0); add_shapes(ob, D)
    if lod >= 2: join_eye_dots(ob, sdf, P0, names, arm)
    objs = [ob]
    mat = bpy.data.materials.new('fur'); mat.use_nodes = True; ob.data.materials.append(mat)
    decal = None
    if lod <= 1:
        decal = make_decal(ob, P0, sdf)
        Pd = verts(decal); nd, Ed = adjacency(decal); Nd = S.grad(sdf, Pd); Nd /= np.linalg.norm(Nd, axis=1)[:, None]
        set_custom_normals(decal, Nd)
        # 臉貼片的權重與形態鍵：用與身體相同的函式
        _, Md, fd = skin_weights(Pd, P0, nd, Ed) if False else (None, None, None)
        names2, Md, fd = skin_weights_pointwise(Pd, P0)
        apply_weights(decal, names2, Md); bind(decal, arm)
        add_shapes(decal, shape_deltas(Pd, Nd, fd, P0))
        m2 = bpy.data.materials.new('face'); m2.use_nodes = True; decal.data.materials.append(m2)
        objs.append(decal)
    # 輸出
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs + [arm]: o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    path = os.path.join(out_dir, f'{P0.NAME}_lod{lod}.glb')
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_animations=False, export_skins=True, export_morph=True,
              export_morph_normal=False, export_yup=True, export_apply=False, export_materials='EXPORT')
    try:
        bpy.ops.export_scene.gltf(export_vertex_color='ACTIVE', **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    info = dict(lod=lod, verts=len(ob.data.vertices), quads=len(ob.data.polygons), tris=tris, bytes=os.path.getsize(path),
                decal_tris=(sum(len(p.vertices) - 2 for p in decal.data.polygons) if decal else 0))
    print('LOD', info); return info

def join_eye_dots(ob, sdf, P0, names, arm):
    """最遠一級（LOD2）沒有臉貼片與眼球：在本體上併入兩個深色小橢球當眼睛（同權重＝跟頭、同形態鍵、頂點色全暗），零額外繪製呼叫"""
    F = P0.FACE; pieces = []
    for s_, nm in ((1, 'L'), (-1, 'R')):
        p, n = surface_point(sdf, s_ * F['eye_x'], F['eye_z'] - 0.004)
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        z = n / np.linalg.norm(n); x = np.cross([0, 0, 1.0], z); x /= np.linalg.norm(x); y = np.cross(z, x)
        for v in bm.verts:
            c = np.array(v.co); v.co = tuple(p + x * c[0] * 0.034 * F.get('eyeK', 1) + y * c[1] * 0.043 * F.get('eyeK', 1) + z * (c[2] * 0.016 - 0.004))
        me = bpy.data.meshes.new('dot' + nm); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new('Dot' + nm, me); bpy.context.scene.collection.objects.link(o)
        pieces.append(o)
    for o in pieces:
        P = verts(o); N = np.array([tuple(v.normal) for v in o.data.vertices])
        n_ = len(P); idx = {k: i for i, k in enumerate(names)}
        for nm in names: o.vertex_groups.new(name=nm)
        for i in range(n_): o.vertex_groups[idx['head']].add([i], 1.0, 'REPLACE')
        ca = o.data.color_attributes.new(name='AO', type='FLOAT_COLOR', domain='POINT')
        ca.data.foreach_set('color', np.tile([0.09, 0.07, 0.07, 1.0], (n_, 1)).reshape(-1))
        o.shape_key_add(name='Basis'); D = shape_deltas(P, N, np.zeros(n_), P0)
        for k, d in D.items():
            sk = o.shape_key_add(name=k, from_mix=False); sk.data.foreach_set('co', (P + d).reshape(-1))
        for p_ in o.data.polygons: p_.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT')
    for o in pieces: o.select_set(True)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.join()

def skin_weights_pointwise(P, P0):
    """臉貼片沒有自己的鄰接，用最近身體頂點太麻煩：直接用同一組公式（不做網格平滑，貼片全在軀幹，差異可忽略）"""
    class _E: pass
    n = len(P); E = np.zeros((0, 2), int)
    names, M, f = skin_weights(P, P0, n, E)
    return names, M, f

def meta_only(P0, out):
    """只重算錨點並併進既有的 <name>.json（不動 GLB）：新增配件掛點時用。"""
    sdf = S.make_sdf(P0); A = anchors(sdf, P0); path = os.path.join(out, f'{P0.NAME}.json'); meta = json.load(open(path))
    meta['anchors'] = {k: dict(p=to_gltf(v['p']), n=to_gltf(v['n'])) for k, v in A.items()}; json.dump(meta, open(path, 'w'), ensure_ascii=False, indent=1); print('anchors updated', len(A))

def main():
    mod, out, lods = parse(); P0 = importlib.import_module(mod); os.makedirs(out, exist_ok=True)
    if '--meta' in sys.argv: return meta_only(P0, out)
    t0 = time.time(); sdf = S.make_sdf(P0); vv, ff, h = marching(sdf, P0); print('marching', len(vv), round(time.time() - t0, 1), 's')
    cache = (vv, ff, h, sdf); infos = []
    for lod in lods: infos.append(build_lod(P0, lod, P0.LODS[lod], cache, out))
    A = anchors(sdf, P0)
    meta = dict(name=P0.NAME, units='m', up='Y', front='+Z', lods=infos, bones={k: dict(parent=v[0], head=to_gltf(v[1]), tail=to_gltf(v[2])) for k, v in P0.BONES.items()},
                anchors={k: dict(p=to_gltf(v['p']), n=to_gltf(v['n'])) for k, v in A.items()},
                face=dict(P0.FACE), shapes=['squash', 'stretch', 'land', 'plump', 'breath', 'cheek.L', 'cheek.R'],
                decal=dict(x=P0.FACE['decal_x'], z0=P0.FACE['decal_z0'], z1=P0.FACE['decal_z1']),
                bodyCy=P0.BODY['c'][1], gradY=list(getattr(P0, 'GRAD_Y', (-0.025, 0.585))), zone=getattr(P0, 'ZONE', None),
                noNose=True)
    json.dump(meta, open(os.path.join(out, f'{P0.NAME}.json'), 'w'), ensure_ascii=False, indent=1)
    print('done', round(time.time() - t0, 1), 's')

main()
