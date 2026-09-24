"""蓝色大肥鱼 — chibi maid whale girl, sculpted with signed distance fields for a soft figure look.

References (EP1 1.7s / 19.7s / 31.7s, EP2 32.2s): ~2.2 heads tall, big fluffy navy->sky-blue wavy
hair with an ahoge, white ruffled maid headdress with light-blue bows, navy whale-fin ears with white
fluff, navy maid dress, white apron with a whale emblem, layered white petticoat, white frilled
socks, glossy navy Mary Janes, and a thick navy whale tail with a pale belly and upright fluke.
"""
import math
import os

import bpy  # noqa: F401
import numpy as np

from .. import core, face as F, sdf, shapes as S

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', 'textures', 'face_bluefish.png'))


def lin(h):
    return np.array(core.hexc(h)[:3], dtype=np.float32)


C = dict(
    skin=lin('#fcdcca'), blush=lin('#f7b2aa'), sock=lin('#f6f7fc'),
    hair_root=lin('#1c2b64'), hair_mid=lin('#264693'), hair_tip=lin('#5a9fe6'),
    dress=lin('#1b2551'), dress_band=lin('#27377a'), gold=lin('#e2b24c'),
    white=lin('#f7f8fd'), fin=lin('#1d2b62'), tail_top=lin('#1d2e67'), tail_under=lin('#d2dcf0'),
    shoe=lin('#1b2349'), bow=lin('#5a9bee'), bow_white=lin('#f4f7ff'), silver=lin('#e3e7f1'),
)

HC = np.array([0.0, 0.0, 0.665], dtype=np.float32)   # head center
HR = np.array([0.152, 0.146, 0.152], dtype=np.float32)
EYE_Z = 0.628


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=np.float32) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def head_dir(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)], dtype=np.float32)


def head_pt(az, el, off=0.0):
    d = head_dir(az, el)
    r = 1.0 / math.sqrt((d[0] / HR[0]) ** 2 + (d[1] / HR[1]) ** 2 + (d[2] / HR[2]) ** 2)
    return HC + d * (r + off)


def ruffle(field, center, radius, n, size, col, theta=None, phase=0.0, k=None, tilt=0.0):
    """Gathered ruffle around a horizontal circle: overlapping flattened ellipsoids."""
    rad, hei, tang = size
    t0, t1 = theta if theta else (0, 2 * math.pi)
    for i in range(n):
        a = t0 + (t1 - t0) * (i / n if theta is None else i / max(n - 1, 1)) + phase
        p = (center[0] + radius * math.cos(a), center[1] + radius * math.sin(a), center[2])
        field.add(sdf.ellipsoid(p, (rad, tang, hei), rot=(0, tilt, math.degrees(a))), col, k=k if k is not None else rad * 0.9)


def ring(center, radius, n, r, axis_z=True, phase=0.0, squash_y=1.0, theta=None, z_wave=0.0):
    """Points around a horizontal circle (for scalloped frills made of spheres)."""
    pts = []
    t0, t1 = theta if theta else (0, 2 * math.pi)
    full = theta is None
    for i in range(n):
        a = t0 + (t1 - t0) * (i / n if full else i / max(n - 1, 1)) + phase
        pts.append(np.array([center[0] + radius * math.cos(a), center[1] + radius * math.sin(a) * squash_y,
                             center[2] + z_wave * math.sin(3 * a)], dtype=np.float32))
    return pts


def add_bow(field, center, size, facing, col, knot_col=None, tails=True, roll=0.0):
    """Ribbon bow: two flat looped ribbons, a knot and two tails, facing `facing`."""
    f = np.asarray(facing, dtype=np.float32)
    f /= np.linalg.norm(f)
    up = np.array([0, 0, 1.0], dtype=np.float32)
    right = np.cross(f, up)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0, 0], dtype=np.float32)
    right /= np.linalg.norm(right)
    up = np.cross(right, f)
    c, s_ = math.cos(roll), math.sin(roll)
    right, up = right * c + up * s_, up * c - right * s_
    C0 = np.asarray(center, dtype=np.float32)
    w = size * 0.2
    t = size * 0.055
    for side in (-1, 1):
        loop = [C0 + right * side * size * x + up * size * y - f * size * z for x, y, z in
                [(0.08, 0.06, 0.0), (0.45, 0.36, 0.05), (0.9, 0.3, 0.08), (0.98, -0.02, 0.08), (0.8, -0.3, 0.06), (0.4, -0.24, 0.03), (0.08, -0.04, 0.0)]]
        field.ribbon(loop, [w * 0.6, w, w * 1.1, w * 1.1, w * 1.1, w, w * 0.6], t, col, k=size * 0.06, up=f, inner_k=0.002)
        if tails:
            tail = [C0 + right * side * size * x + up * size * y for x, y in [(0.08, -0.1), (0.22, -0.5), (0.36, -0.92)]]
            field.ribbon(tail, [w * 0.7, w * 0.85, w * 0.95], t, col, k=size * 0.05, up=f, inner_k=0.002)
    field.add(sdf.ellipsoid(C0 + f * size * 0.04, (size * 0.16, size * 0.13, size * 0.17)), knot_col if knot_col is not None else col, k=size * 0.06)


def _frame_rot(x, y, z, tilt=0.0):
    """Euler (degrees) that maps local x,y,z axes onto the given world directions (approx via matrix->euler)."""
    from mathutils import Matrix
    x = x / np.linalg.norm(x)
    zz = np.cross(x, y)
    zz /= np.linalg.norm(zz)
    yy = np.cross(zz, x)
    M = Matrix(((x[0], yy[0], zz[0]), (x[1], yy[1], zz[1]), (x[2], yy[2], zz[2])))
    e = M.to_euler('XYZ')
    return (math.degrees(e.x), math.degrees(e.y) + tilt, math.degrees(e.z))


# ----------------------------------------------------------------------------- mesh realization

def realize(field, name, mat, voxel=0.0025, target=None, post=None, cav=0.35, cav_dist=0.008):
    V, Fc, Col = field.mesh(voxel)
    o = core.mesh_from_arrays(name, V, Fc, colors=Col, mat=mat)
    me = o.data
    N = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get('normal', N)
    N = N.reshape(-1, 3)
    if cav:
        Col = Col * sdf.cavity(field.grid, V.astype(np.float32), N, dist=cav_dist, strength=cav)[:, None]
    if post:
        Col = post(V, N, Col)
    core.paint(o, lambda co, c=Col: c)
    tris = core.tri_count(o)
    if target and tris > target:
        core.add_modifier(o, 'DECIMATE', ratio=target / tris, use_collapse_triangulate=True)
        core.apply_modifiers(o)
    o.data.shade_smooth()
    return o


# ----------------------------------------------------------------------------- sculpt

def hair_shell(axis_y=0.03, z_top=0.72, z_bot=0.36, phi_max=math.radians(112)):
    """Thick bell-shaped mass behind/around the body that the locks sit on (no see-through gaps).
    It wraps round the sides outside the arms, like the voluminous hair in the reference."""
    def r_in(z):
        return np.interp(z, [0.24, 0.45, 0.58, 0.66, 0.74], [0.2, 0.19, 0.16, 0.12, 0.08])

    def r_out(z, phi):
        base = np.interp(z, [0.3, 0.4, 0.5, 0.58, 0.64, 0.7, 0.76], [0.245, 0.245, 0.235, 0.215, 0.19, 0.16, 0.12])
        edge = np.clip((np.abs(phi) - (phi_max - 0.5)) / 0.5, 0, 1)
        return base + 0.012 * np.sin(10 * phi + 14 * z) - 0.07 * edge ** 2

    def f(P):
        x, y, z = P[..., 0], P[..., 1] - axis_y, P[..., 2]
        rho = np.sqrt(x * x + y * y)
        phi = np.arctan2(x, y)
        dr = np.maximum(r_in(z) - rho, rho - r_out(z, phi))
        zb = z_bot + 0.02 * np.cos(10 * phi + 0.5) + 0.03 * (np.abs(phi) / phi_max) ** 2
        dz = np.maximum(zb - z, z - z_top)
        q = np.stack([np.maximum(dr, 0), np.maximum(dz, 0)], axis=-1)
        d = np.minimum(np.maximum(dr, dz), 0) + _n2(q)
        return np.maximum(d, (np.abs(phi) - phi_max) * rho) - 0.006
    return f, (np.array([-0.32, -0.3, z_bot - 0.05], dtype=np.float32), np.array([0.32, 0.34, z_top + 0.03], dtype=np.float32))


def _n2(q):
    return np.sqrt(np.einsum('...i,...i->...', q, q))


def sculpt_hair():
    """Smooth sculpted base (scalp volume + hidden filler behind the back); visible locks are swept."""
    H = sdf.Field('hair')
    col = C['hair_mid']
    H.add(sdf.ellipsoid(HC + np.array([0, 0.016, 0.02]), HR + np.array([0.028, 0.03, 0.026])), col, k=0.01)
    H.carve(sdf.ellipsoid(np.array([0, -0.21, 0.59]), (0.122, 0.14, 0.118)), k=0.022)
    H.add(hair_shell(), col, k=0.05)
    ah = [(0.0, 0.03, 0.845), (0.004, 0.012, 0.905), (0.0, -0.032, 0.95), (-0.004, -0.074, 0.94), (-0.002, -0.082, 0.91)]
    H.tube([np.array(p, dtype=np.float32) for p in ah], [0.01, 0.009, 0.008, 0.006, 0.003], col, k=0.004)
    return H


LENS = None


def lock(path, w, th_ratio=0.42, n=30, up=(0, 0, 1), root=0.75, tip_start=0.72):
    """A swept anime hair lock: lens cross-section (thin edges), full body, sharp tapered tip."""
    global LENS
    if LENS is None:
        a = np.linspace(0, 2 * np.pi, 12, endpoint=False)
        LENS = np.stack([np.cos(a), np.sin(a) * (0.35 + 0.65 * np.abs(np.sin(a)))], axis=1)

    def wf(s):
        s = np.asarray(s, dtype=float)
        g = root + (1 - root) * np.clip(s / 0.2, 0, 1)
        t = np.clip((s - tip_start) / (1 - tip_start), 0, 1)
        return w * g * (1 - t ** 1.6) + 2e-4
    return S.sweep(path, n=n, profile=LENS, width=wf, thick=lambda s: wf(s) * th_ratio, up=up, tip1=True, cap0=True)


def hair_locks():
    geos = []
    rng = np.random.default_rng(21)
    # bangs: crisp locks from the crown down to the eyelids, covering the forehead
    bangs = [(-84, -90, 8, 0.03), (-70, -76, 12, 0.032), (-56, -61, 5, 0.034), (-42, -45, 11, 0.034), (-28, -30, 3, 0.034),
             (-14, -14, 9, 0.032), (-3, -1, -2, 0.026), (8, 10, 8, 0.032), (21, 24, 2, 0.034), (35, 40, 10, 0.034),
             (49, 55, 4, 0.034), (63, 69, 11, 0.032), (77, 83, 6, 0.03), (90, 94, 10, 0.028)]
    for azr, azt, elt, w in bangs:
        pts = [head_pt(azr + (azt - azr) * t ** 1.3, 66 + (elt - 66) * t ** 0.8, off=0.026 + 0.01 * math.sin(math.pi * t) - 0.008 * t)
               for t in np.linspace(0, 1, 6)]
        tip = pts[-1] + head_dir(azt, elt - 30) * 0.016 - head_dir(azt, elt) * 0.006
        geos.append(lock(pts + [tip], w, 0.42, n=20, up=head_dir(azr, 55), root=0.9, tip_start=0.62))
    # side hair: frames the face and falls in front of the shoulders in soft waves
    for side in (-1, 1):
        for k, (azr, zend, xo, yo, w) in enumerate([(62, 0.41, -0.012, -0.004, 0.028), (78, 0.37, 0.03, 0.02, 0.034), (94, 0.35, 0.07, 0.05, 0.038)]):
            p = [head_pt(side * azr, 38, 0.024), head_pt(side * (azr + 2), 8, 0.03), head_pt(side * (azr + 4), -20, 0.032)]
            b = p[-1]
            p += [np.array([side * (0.19 + xo), b[1] + yo * 0.5 - 0.004, 0.535]), np.array([side * (0.218 + xo), b[1] + yo, 0.48]),
                  np.array([side * (0.203 + xo), b[1] + yo, 0.43]), np.array([side * (0.23 + xo), b[1] + yo, zend + 0.02]),
                  np.array([side * (0.214 + xo), b[1] + yo - 0.008, zend])]
            geos.append(lock(p, w, 0.45, n=34, up=head_dir(side * azr, 10), tip_start=0.78))
    # long wavy back locks, two layers; the outer layer makes the silhouette
    for layer, (az_list, spread0, wbase) in enumerate([(np.linspace(118, 242, 9), -0.02, 0.05),
                                                       (list(np.linspace(112, 248, 13)) + [s * a for s in (-1, 1) for a in (94, 104)], 0.0, 0.044)]):
        for i, az in enumerate(az_list):
            azr = az % 360
            side = math.sin(math.radians(azr))
            sidek = 1.0 if (azr < 108 or azr > 252) else 0.0
            pts = [head_pt(azr, el, off=-0.004 + layer * 0.004 + 0.028 * (22 - el) / 22) for el in (22, 11, 0)]
            base = pts[-1]
            radial = np.array([base[0], base[1] - 0.03, 0.0], dtype=np.float32)
            radial /= np.linalg.norm(radial)
            tangent = np.cross(np.array([0, 0, 1.0], dtype=np.float32), radial)
            z_end = 0.24 + 0.05 * abs(side) + rng.uniform(-0.02, 0.02) + layer * 0.0
            zs = np.linspace(base[2] - 0.045, z_end, 9)
            ph = 1.2 * i + rng.uniform(0, 0.8) + layer * 0.9
            amp = 0.026 + rng.uniform(0, 0.012)
            r0 = float(np.linalg.norm(base[:2] - np.array([0, 0.03])))
            for kk, z in enumerate(zs):
                t = (kk + 1) / len(zs)
                spread = float(np.interp(z, [0.24, 0.32, 0.42, 0.52, 0.6], [0.315, 0.3, 0.278, 0.255, 0.232])) + spread0 + layer * 0.012
                rho = max(spread + sidek * 0.035 * t, r0 + 0.004 * kk) + 0.01 * math.cos(ph + t * 8.0)
                q = np.array([0, 0.03, 0], dtype=np.float32) + radial * rho + tangent * amp * math.sin(ph + t * 8.0)
                q[2] = z
                pts.append(q)
            last = pts[-1]
            curl = 1 if (i + layer) % 2 else -1
            pts.append(last + tangent * 0.02 * curl + radial * 0.016 + np.array([0, 0, 0.004], dtype=np.float32))
            pts.append(last + tangent * 0.03 * curl + radial * 0.03 + np.array([0, 0, 0.02], dtype=np.float32))
            w = wbase + rng.uniform(-0.004, 0.006)
            geos.append(lock(pts, w, 0.4, n=34, up=radial, root=0.25, tip_start=0.78))
    return geos


def hair_post(V, N, col):
    z = V[:, 2]
    a = smoothstep(0.66, 0.46, z)[:, None]
    b = smoothstep(0.47, 0.27, z)[:, None]
    c = C['hair_root'] * (1 - a) + C['hair_mid'] * a
    c = c * (1 - b) + C['hair_tip'] * b
    # keep cavity darkening from the sculpt
    shade = col / np.maximum(C['hair_mid'], 1e-4)
    return c * np.clip(shade.mean(axis=1, keepdims=True), 0.3, 1.0)


def sculpt_skin():
    K = sdf.Field('skin')
    sk = C['skin']
    K.add(sdf.ellipsoid(HC, HR), sk, k=0.0)
    for s in (-1, 1):   # round, full cheeks
        K.add(sdf.sphere((s * 0.064, -0.074, 0.588), 0.07), sk, k=0.05)
    K.add(sdf.sphere((0, -0.088, 0.55), 0.036), sk, k=0.05)   # small soft chin
    K.add(sdf.round_cone((0, 0.004, 0.47), (0, 0.006, 0.56), 0.03, 0.028), sk, k=0.01)  # neck
    for s in (-1, 1):
        x = s * 0.047
        K.add(sdf.round_cone((x, 0.0, 0.29), (x * 1.02, -0.004, 0.16), 0.037, 0.033), sk, k=0.004)
        K.add(sdf.round_cone((x * 1.02, -0.004, 0.16), (x * 1.03, 0.0, 0.075), 0.033, 0.029), sk, k=0.012)
        K.paint(sdf.ellipsoid((x * 1.03, 0.0, 0.07), (0.05, 0.05, 0.035)), C['sock'], k=0.004)   # socks
        # mitten hands (arms are slightly bent forward, hands near the skirt sides)
        hc = np.array([s * 0.14, -0.05, 0.325], dtype=np.float32)
        K.add(sdf.ellipsoid(hc, (0.021, 0.019, 0.026), rot=(15, s * 20, 0)), sk, k=0.0)
        K.add(sdf.ellipsoid(hc + np.array([-s * 0.013, -0.012, 0.006], dtype=np.float32), (0.008, 0.008, 0.012), rot=(20, 0, s * 20)), sk, k=0.006)
    return K


def sculpt_dress():
    D = sdf.Field('dress')
    dc = C['dress']
    torso = [(0, 0.36), (0.066, 0.36), (0.073, 0.40), (0.072, 0.44), (0.066, 0.475), (0.05, 0.498), (0.03, 0.51), (0, 0.51)]
    D.parts = {'body': [], 'sleeve.L': [], 'sleeve.R': []}
    tor = sdf.lathe(torso, squash_y=0.82)
    D.parts['body'].append(tor[0])
    D.add(tor, dc, k=0.0)

    def folds(th, z):
        t = np.clip((0.40 - z) / 0.2, 0, 1)
        return 1 + (0.03 * np.sin(th * 9) + 0.012 * np.sin(th * 4 + 1)) * t ** 1.3
    skirt = [(0, 0.405), (0.074, 0.405), (0.1, 0.385), (0.135, 0.34), (0.162, 0.29), (0.178, 0.245), (0.184, 0.21), (0.176, 0.198), (0, 0.198)]
    sk = sdf.lathe(skirt, mod=folds)
    D.parts['body'].append(sk[0])
    D.add(sk, dc, k=0.012)
    D.paint(sdf.lathe([(0, 0.19), (0.3, 0.19), (0.3, 0.232), (0, 0.232)]), C['dress_band'], k=0.004)
    D.paint(sdf.torus((0, 0, 0.236), 0.176, 0.0025), C['gold'], k=0.0015)
    # puffy sleeves, arms relaxed and a little forward
    for s in (-1, 1):
        sh = np.array([s * 0.066, 0.0, 0.482], dtype=np.float32)
        el = np.array([s * 0.112, -0.022, 0.405], dtype=np.float32)
        wr = np.array([s * 0.132, -0.042, 0.35], dtype=np.float32)
        a1 = sdf.round_cone(sh, el, 0.037, 0.028)
        a2 = sdf.round_cone(el, wr, 0.027, 0.03)
        D.parts['sleeve.L' if s > 0 else 'sleeve.R'] += [a1[0], a2[0]]
        D.add(a1, dc, k=0.014)
        D.add(a2, dc, k=0.006)
    # neck bow (navy) with a silver button
    add_bow(D, (0, -0.064, 0.49), 0.03, (0, -1, 0), dc, knot_col=C['silver'])
    return D


def sculpt_white():
    """Returns (body, limbs, head) fields: kept apart so parts on different bones never fuse."""
    Wf = sdf.Field('white')
    Wl = sdf.Field('white_limbs')
    Wh = sdf.Field('white_head')
    wc = C['white']
    down = lambda P, T: np.array([P[0] * 0.25, P[1] * 0.25, -1.0])
    out_h = lambda P, T: np.array([P[0], P[1], 0.0])
    # collar: gathered frill around the neck, falling outward
    sdf.frill(Wf, [np.array((0.046 * math.cos(a), 0.046 * math.sin(a) * 0.9, 0.508), dtype=np.float32) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)],
              0.026, 0.004, 13, 0.004, wc, lambda P, T: np.array([P[0], P[1], -0.6]), closed=True, k=0.006)
    # apron bib with frilled edges
    Wf.add(sdf.rounded_box((0, -0.052, 0.442), (0.046, 0.012, 0.044), 0.01), wc, k=0.0)
    for sd in (-1, 1):
        path = [np.array((sd * 0.047, -0.058 + 0.012 * (z - 0.4), z), dtype=np.float32) for z in np.linspace(0.4, 0.495, 5)]
        sdf.frill(Wf, path, 0.022, 0.0035, 5, 0.003, wc, lambda P, T, sd=sd: np.array([sd * 1.0, 0.25, 0.0]), k=0.006)
    # apron panel over the skirt front, with a gathered hem frill
    apron_prof = [(0.075, 0.405), (0.103, 0.382), (0.138, 0.336), (0.158, 0.296), (0.165, 0.28), (0.172, 0.28),
                  (0.165, 0.296), (0.145, 0.336), (0.11, 0.382), (0.082, 0.405)]
    wedge = (-math.pi / 2 - 0.95, -math.pi / 2 + 0.95)
    Wf.add(sdf.lathe(apron_prof, theta=wedge, mod=lambda th, z: 1 + (0.03 * np.sin(th * 9)) * np.clip((0.40 - z) / 0.2, 0, 1) ** 1.3), wc, k=0.0)
    hem = [np.array((0.172 * math.cos(a), 0.172 * math.sin(a), 0.284), dtype=np.float32) for a in np.linspace(wedge[0] - 0.05, wedge[1] + 0.05, 12)]
    sdf.frill(Wf, hem, 0.034, 0.004, 12, 0.006, wc, lambda P, T: np.array([P[0] * 0.5, P[1] * 0.5, -1.0]), k=0.008)
    for sd in (-1, 1):
        a = -math.pi / 2 + sd * 0.95
        path = [np.array((r * math.cos(a) * 1.04, r * math.sin(a) * 1.04, z), dtype=np.float32) for r, z in apron_prof[:5]]
        sdf.frill(Wf, path, 0.02, 0.0035, 5, 0.004, wc, lambda P, T, a=a, sd=sd: np.array([-math.sin(a) * sd, math.cos(a) * sd, 0.0]), k=0.006)
    # layered petticoat: two gathered frills below the skirt hem
    ring1 = [np.array((0.183 * math.cos(a), 0.183 * math.sin(a), 0.212), dtype=np.float32) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    sdf.frill(Wf, ring1, 0.05, 0.005, 28, 0.009, wc, lambda P, T: np.array([P[0] * 0.35, P[1] * 0.35, -1.0]), closed=True, k=0.01)
    ring2 = [np.array((0.172 * math.cos(a), 0.172 * math.sin(a), 0.178), dtype=np.float32) for a in np.linspace(0, 2 * math.pi, 24, endpoint=False)]
    sdf.frill(Wf, ring2, 0.036, 0.0045, 30, 0.008, wc, lambda P, T: np.array([P[0] * 0.45, P[1] * 0.45, -1.0]), closed=True, k=0.01)
    # cuffs and sock frills
    for sd in (-1, 1):
        wr = np.array([sd * 0.134, -0.044, 0.346], dtype=np.float32)
        cuff = [wr + np.array((0.03 * math.cos(a), 0.024 * math.sin(a), 0.004 * math.sin(a)), dtype=np.float32) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
        sdf.frill(Wl, cuff, 0.018, 0.0035, 9, 0.004, wc, lambda P, T, wr=wr: (P - wr) * np.array([1, 1, 0]) + np.array([0, 0, -0.012]), closed=True, k=0.006)
        sock = [np.array((sd * 0.048 + 0.03 * math.cos(a), 0.03 * math.sin(a), 0.108), dtype=np.float32) for a in np.linspace(0, 2 * math.pi, 10, endpoint=False)]
        sdf.frill(Wl, sock, 0.02, 0.0035, 10, 0.004, wc, lambda P, T, sd=sd: np.array([P[0] - sd * 0.048, P[1], 0.9]), closed=True, k=0.006)
    # maid headdress: band + gathered lace arching over the crown (tilted forward)
    tilt = math.radians(24)
    arc = []
    for t in np.linspace(-1, 1, 21):
        a = t * math.radians(98)
        d = np.array([math.sin(a), -math.sin(tilt) * math.cos(a), math.cos(a) * math.cos(tilt)], dtype=np.float32)
        r = 1.0 / math.sqrt((d[0] / (HR[0] + 0.046)) ** 2 + (d[1] / (HR[1] + 0.046)) ** 2 + (d[2] / (HR[2] + 0.04)) ** 2)
        arc.append(HC + np.array([0, 0.016, 0.02], dtype=np.float32) + d * r)
    Wh.ribbon(arc, 0.012, 0.006, wc, k=0.004, up=np.array([0, -math.cos(tilt), -math.sin(tilt)], dtype=np.float32))
    sdf.frill(Wh, arc, 0.042, 0.004, 20, 0.007, wc, lambda P, T: P - HC, k=0.006)
    # apron sash bow at the back
    add_bow(Wf, (0, 0.085, 0.395), 0.045, (0, 1, 0), wc)
    return Wf, Wl, Wh


def sculpt_fins():
    Fi = sdf.Field('fins')
    outline = [(0.0, 0.034), (0.05, 0.05), (0.1, 0.046), (0.142, 0.03), (0.168, 0.006), (0.162, -0.016),
               (0.12, -0.03), (0.07, -0.038), (0.026, -0.042), (0.0, -0.038)]
    fluff = [(0.004, -0.036), (0.05, -0.042), (0.1, -0.036), (0.145, -0.02), (0.165, -0.004),
             (0.14, -0.006), (0.1, -0.014), (0.05, -0.016), (0.006, -0.012)]
    for s in (-1, 1):
        o = np.array([s * 0.165, -0.006, 0.64], dtype=np.float32)
        u = np.array([s * 1.0, 0.18, -0.24], dtype=np.float32)
        v = np.array([0.0, 0.05, 1.0], dtype=np.float32)
        Fi.add(sdf.slab(outline, 0.024, o, u, v, round_r=0.009), C['fin'], k=0.0)
        uu = u / np.linalg.norm(u)
        n = np.cross(uu, v / np.linalg.norm(v))
        Fi.add(sdf.slab(fluff, 0.02, o - n * 0.002 + np.array([0, 0, -0.004], dtype=np.float32), u, v, round_r=0.009), C['white'], k=0.006)
    return Fi


TAIL_PATH = [(0.0, 0.066, 0.33), (0.08, 0.14, 0.26), (0.18, 0.165, 0.19), (0.28, 0.135, 0.15), (0.36, 0.085, 0.15), (0.42, 0.045, 0.18)]


def sculpt_tail():
    T = sdf.Field('tail')
    pts = [np.array(p, dtype=np.float32) for p in TAIL_PATH]
    T.tube(pts, [0.07, 0.064, 0.052, 0.04, 0.028, 0.019], C['tail_top'], k=0.0)
    end = pts[-1]
    d = end - pts[-2]
    d /= np.linalg.norm(d)
    outline = [(-0.01, 0.018), (0.035, 0.066), (0.085, 0.112), (0.14, 0.132), (0.12, 0.082), (0.096, 0.034), (0.104, 0.0),
               (0.096, -0.034), (0.12, -0.082), (0.14, -0.132), (0.085, -0.112), (0.035, -0.066), (-0.01, -0.018)]
    T.add(sdf.slab(outline, 0.02, end - d * 0.01, d, np.array([0, 0, 1.0], dtype=np.float32), round_r=0.008), C['tail_top'], k=0.012)
    return T


def tail_post(V, N, col):
    under = smoothstep(0.15, -0.55, N[:, 2]) * (1 - smoothstep(0.36, 0.42, V[:, 0]) * 0.8)
    base = C['tail_top'] * (1 - under[:, None]) + C['tail_under'] * under[:, None]
    shade = col / np.maximum(C['tail_top'], 1e-4)
    return base * np.clip(shade.mean(axis=1, keepdims=True), 0.35, 1.0)


def sculpt_shoes():
    Sh = sdf.Field('shoes')
    for s in (-1, 1):
        x = s * 0.049
        Sh.add(sdf.ellipsoid((x, -0.016, 0.03), (0.034, 0.056, 0.033)), C['shoe'], k=0.0)
        Sh.carve(sdf.rounded_box((x, -0.016, -0.03), (0.06, 0.08, 0.03), 0.0), k=0.004)
        Sh.tube([np.array(p, dtype=np.float32) for p in [(x - 0.032, -0.02, 0.036), (x, -0.03, 0.058), (x + 0.032, -0.02, 0.036)]], 0.0045, C['shoe'], k=0.003)
        Sh.add(sdf.sphere((x + s * 0.03, -0.024, 0.04), 0.0055), C['gold'], k=0.002)
    return Sh


def sculpt_accents():
    A = sdf.Field('accents')
    for s in (-1, 1):   # light-blue bows at the ends of the headdress
        add_bow(A, head_pt(s * 78, 24, 0.062), 0.062, (s * 0.7, -0.7, 0.12), C['bow'], knot_col=C['bow_white'], roll=s * 0.3)
        add_bow(A, (s * 0.118, -0.14, 0.31), 0.024, (s * 0.5, -0.86, 0.1), C['gold'], knot_col=C['dress'])
        A.add(sdf.sphere((s * 0.108, -0.028, 0.378), 0.0055), C['gold'], k=0.002)   # sleeve buttons
    return A


# ----------------------------------------------------------------------------- build

def build(out_path, with_anims=True):
    core.reset()
    core.clear_material_cache()
    M = dict(
        hair=core.material('fig_hair', '#ffffff', extras={'rough': 0.46, 'coat': 0.25, 'coatRough': 0.35, 'sheen': 0.6, 'sheenColor': '#a9ccff', 'env': 0.85}),
        skin=core.material('fig_skin', '#ffffff', extras={'rough': 0.62, 'sheen': 0.5, 'sheenColor': '#ffd2c4', 'env': 0.7, 'emissive': '#ffb8a0', 'emissiveIntensity': 0.06}),
        dress=core.material('fig_dress', '#ffffff', extras={'rough': 0.7, 'sheen': 0.6, 'sheenColor': '#6f86d8', 'env': 0.8}),
        white=core.material('fig_white', '#ffffff', extras={'rough': 0.65, 'sheen': 0.4, 'sheenColor': '#dfe8ff', 'env': 0.8}),
        fin=core.material('fig_fin', '#ffffff', extras={'rough': 0.45, 'coat': 0.3, 'env': 0.9}),
        tail=core.material('fig_tail', '#ffffff', extras={'rough': 0.42, 'coat': 0.35, 'env': 0.9}),
        shoe=core.material('fig_shoe', '#ffffff', extras={'rough': 0.25, 'coat': 1.0, 'coatRough': 0.08, 'env': 1.1}),
        accents=core.material('fig_accents', '#ffffff', extras={'rough': 0.4, 'coat': 0.4, 'env': 1.0}),
        face=core.material('face_bluefish', '#ffffff', image=TEX, alpha='image'),
    )
    objs = {}
    base = realize(sculpt_hair(), 'hair', M['hair'], voxel=0.0026, target=9000, post=hair_post, cav=0.25, cav_dist=0.01)
    locks = S.obj('hair_locks', S.merge_geos(*hair_locks()), M['hair'], fix_normals=False)
    S.recalc_normals(locks)
    core.paint(locks, lambda co: hair_post(co, None, np.tile(C['hair_mid'], (len(co), 1))))
    objs['hair'] = core.join([base, locks], 'hair')
    tris = core.tri_count(objs['hair'])
    if tris > 30000:
        core.add_modifier(objs['hair'], 'DECIMATE', ratio=30000 / tris, use_collapse_triangulate=True)
        core.apply_modifiers(objs['hair'])
    objs['skin'] = realize(sculpt_skin(), 'skin', M['skin'], voxel=0.0022, target=9000, cav=0.15)
    dress_field = sculpt_dress()
    objs['dress'] = realize(dress_field, 'dress', M['dress'], voxel=0.0024, target=9000, cav=0.35)
    wb, wl, wh = sculpt_white()
    objs['white'] = realize(wb, 'white', M['white'], voxel=0.0022, target=10000, cav=0.4)
    objs['white_limbs'] = realize(wl, 'white_limbs', M['white'], voxel=0.0018, target=3000, cav=0.3)
    objs['white_head'] = realize(wh, 'white_head', M['white'], voxel=0.002, target=5000, cav=0.35)
    objs['fins'] = realize(sculpt_fins(), 'fins', M['fin'], voxel=0.002, target=3000, cav=0.3)
    objs['tail'] = realize(sculpt_tail(), 'tail', M['tail'], voxel=0.0025, target=4000, post=tail_post, cav=0.2)
    objs['shoes'] = realize(sculpt_shoes(), 'shoes', M['shoe'], voxel=0.002, target=2500, cav=0.2)
    objs['accents'] = realize(sculpt_accents(), 'accents', M['accents'], voxel=0.0018, target=4000, cav=0.3)

    # face decals projected onto the sculpted head
    bvh = F.surface_bvh(objs['skin'])
    ex = 0.062
    objs['expr_eyes_open'] = core.join([F.decal('eyeR', bvh, (-ex, -0.3, EYE_Z), (0.092, 0.118), (0, 0), M['face']),
                                        F.decal('eyeL', bvh, (ex, -0.3, EYE_Z), (0.092, 0.118), (0, 0), M['face'], mirror=True)], 'expr_eyes_open')
    objs['expr_eyes_happy'] = core.join([F.decal('eyeRh', bvh, (-ex, -0.3, EYE_Z - 0.004), (0.084, 0.1), (1, 0), M['face']),
                                         F.decal('eyeLh', bvh, (ex, -0.3, EYE_Z - 0.004), (0.084, 0.1), (1, 0), M['face'], mirror=True)], 'expr_eyes_happy')
    objs['expr_mouth_open'] = F.decal('expr_mouth_open', bvh, (0, -0.3, 0.574), (0.07, 0.07), (0, 1), M['face'])
    objs['expr_mouth_small'] = F.decal('expr_mouth_small', bvh, (0, -0.3, 0.587), (0.05, 0.05), (1, 1), M['face'])
    objs['expr_mouth_round'] = F.decal('expr_mouth_round', bvh, (0, -0.3, 0.587), (0.044, 0.044), (2, 1), M['face'])
    objs['expr_mouth_cat'] = F.decal('expr_mouth_cat', bvh, (0, -0.3, 0.589), (0.054, 0.054), (3, 1), M['face'])
    objs['face_blush'] = core.join([F.decal('blushR', bvh, (-0.093, -0.3, 0.602), (0.07, 0.042), (0, 2), M['face'], offset=0.0008),
                                    F.decal('blushL', bvh, (0.093, -0.3, 0.602), (0.07, 0.042), (0, 2), M['face'], mirror=True, offset=0.0008)], 'face_blush')
    objs['emblem'] = F.decal('emblem', F.surface_bvh(objs['white']), (0, -0.4, 0.33), (0.075, 0.075), (2, 2), M['face'], offset=0.0012)

    arm = rig(objs, dress_field.parts)
    if with_anims:
        from . import bluefish_anims
        bluefish_anims.add(arm)
    stats = {k: core.tri_count(v) for k, v in objs.items()}
    core.export_glb(out_path)
    return stats


# ----------------------------------------------------------------------------- rig

def rig(objs, dress_parts):
    tp = [np.array(p) for p in TAIL_PATH]
    bones = [
        ('root', (0, 0, 0), (0, 0, 0.08), None),
        ('hips', (0, 0, 0.33), (0, 0, 0.40), 'root'),
        ('spine', (0, 0, 0.40), (0, 0, 0.45), 'hips'),
        ('chest', (0, 0, 0.45), (0, 0, 0.50), 'spine'),
        ('neck', (0, 0, 0.50), (0, 0, 0.55), 'chest'),
        ('head', (0, 0, 0.55), (0, 0, 0.82), 'neck'),
        ('eye.L', (0.063, -0.13, EYE_Z), (0.063, -0.16, EYE_Z), 'head'),
        ('eye.R', (-0.063, -0.13, EYE_Z), (-0.063, -0.16, EYE_Z), 'head'),
        ('ahoge', (0, 0.03, 0.83), (0, -0.03, 0.94), 'head'),
        ('fin.L', (0.165, -0.006, 0.64), (0.32, 0.02, 0.6), 'head'),
        ('fin.R', (-0.165, -0.006, 0.64), (-0.32, 0.02, 0.6), 'head'),
        ('hair.B.1', (0, 0.15, 0.62), (0, 0.2, 0.46), 'head'),
        ('hair.B.2', (0, 0.2, 0.46), (0, 0.24, 0.28), 'hair.B.1'),
        ('hair.L.1', (0.14, 0.1, 0.62), (0.21, 0.12, 0.46), 'head'),
        ('hair.L.2', (0.21, 0.12, 0.46), (0.25, 0.12, 0.3), 'hair.L.1'),
        ('hair.R.1', (-0.14, 0.1, 0.62), (-0.21, 0.12, 0.46), 'head'),
        ('hair.R.2', (-0.21, 0.12, 0.46), (-0.25, 0.12, 0.3), 'hair.R.1'),
        ('lock.L', (0.17, -0.06, 0.58), (0.2, -0.06, 0.38), 'head'),
        ('lock.R', (-0.17, -0.06, 0.58), (-0.2, -0.06, 0.38), 'head'),
        ('upperarm.L', (0.066, 0, 0.482), (0.112, -0.022, 0.405), 'chest'),
        ('lowerarm.L', (0.112, -0.022, 0.405), (0.132, -0.042, 0.35), 'upperarm.L'),
        ('hand.L', (0.132, -0.042, 0.35), (0.142, -0.052, 0.305), 'lowerarm.L'),
        ('upperarm.R', (-0.066, 0, 0.482), (-0.112, -0.022, 0.405), 'chest'),
        ('lowerarm.R', (-0.112, -0.022, 0.405), (-0.132, -0.042, 0.35), 'upperarm.R'),
        ('hand.R', (-0.132, -0.042, 0.35), (-0.142, -0.052, 0.305), 'lowerarm.R'),
        ('upperleg.L', (0.047, 0, 0.30), (0.048, -0.004, 0.16), 'hips'),
        ('lowerleg.L', (0.048, -0.004, 0.16), (0.049, 0, 0.06), 'upperleg.L'),
        ('foot.L', (0.049, 0, 0.06), (0.049, -0.06, 0.02), 'lowerleg.L'),
        ('upperleg.R', (-0.047, 0, 0.30), (-0.048, -0.004, 0.16), 'hips'),
        ('lowerleg.R', (-0.048, -0.004, 0.16), (-0.049, 0, 0.06), 'upperleg.R'),
        ('foot.R', (-0.049, 0, 0.06), (-0.049, -0.06, 0.02), 'lowerleg.R'),
        ('prop', (0, -0.13, 0.38), (0, -0.13, 0.43), 'chest'),
    ]
    tail_names = []
    for i in range(len(tp) - 1):
        n = f'tail.{i + 1}'
        bones.append((n, tuple(tp[i]), tuple(tp[i + 1]), 'hips' if i == 0 else f'tail.{i}'))
        tail_names.append(n)
    arm = core.armature('rig_bluefish', bones)
    segs = core.bone_segments(arm)

    def dist_to(co, name):
        return core.seg_dist(co, *segs[name])[0]

    def rigid(o, b):
        core.bind(o, arm, core.rigid(len(o.data.vertices), b))

    for key in ('expr_mouth_open', 'expr_mouth_small', 'expr_mouth_round', 'expr_mouth_cat', 'face_blush'):
        rigid(objs[key], 'head')
    for key in ('expr_eyes_open', 'expr_eyes_happy'):
        co = core.verts_of(objs[key])
        core.bind(objs[key], arm, {'eye.L': (co[:, 0] > 0).astype(float), 'eye.R': (co[:, 0] <= 0).astype(float)})
    rigid(objs['emblem'], 'hips')

    # fins
    co = core.verts_of(objs['fins'])
    core.bind(objs['fins'], arm, {'fin.L': (co[:, 0] > 0).astype(float), 'fin.R': (co[:, 0] <= 0).astype(float)})

    # hair: head on top, hanging parts follow the hair bones
    co = core.verts_of(objs['hair'])
    hang = smoothstep(0.6, 0.45, co[:, 2])
    names = ['hair.B.1', 'hair.B.2', 'hair.L.1', 'hair.L.2', 'hair.R.1', 'hair.R.2', 'lock.L', 'lock.R']
    pw = core.proximity_weights(co, segs, names, falloff=3.0)
    tot = sum(pw.values())
    tot[tot == 0] = 1
    w = {n: pw[n] / tot * hang for n in names}
    w['head'] = 1 - hang
    ah = (co[:, 2] > 0.84) & (np.abs(co[:, 0]) < 0.02)
    w = {k: np.where(ah, 0, v) for k, v in w.items()}
    w['ahoge'] = ah.astype(float)
    core.bind(objs['hair'], arm, w)

    # skin: head/neck, hands, legs
    co = core.verts_of(objs['skin'])
    wts = {n: np.zeros(len(co)) for n in ['head', 'neck', 'hand.L', 'hand.R', 'upperleg.L', 'lowerleg.L', 'upperleg.R', 'lowerleg.R']}
    head = co[:, 2] > 0.5
    wts['head'] = head * smoothstep(0.52, 0.56, co[:, 2])
    wts['neck'] = head * (1 - smoothstep(0.52, 0.56, co[:, 2]))
    hands = (~head) & (np.abs(co[:, 0]) > 0.1) & (co[:, 2] > 0.28)
    wts['hand.L'] = hands & (co[:, 0] > 0)
    wts['hand.R'] = hands & (co[:, 0] < 0)
    legs = (~head) & (~hands)
    for s, sgn in (('L', 1), ('R', -1)):
        side = legs & (np.sign(co[:, 0]) == sgn)
        cw = core.chain_weights(co, segs, [f'upperleg.{s}', f'lowerleg.{s}'], blend=0.3)
        wts[f'upperleg.{s}'] = side * cw[f'upperleg.{s}']
        wts[f'lowerleg.{s}'] = side * cw[f'lowerleg.{s}']
    core.bind(objs['skin'], arm, {k: v.astype(float) for k, v in wts.items()})

    # dress: torso/skirt on the spine, sleeves on the arms (decided by which sculpt part is nearest),
    # skirt hem pulled a little by the thighs
    co = core.verts_of(objs['dress'])
    P = co.astype(np.float32)
    dist = {k: np.min(np.stack([f(P) for f in fs]), axis=0) for k, fs in dress_parts.items()}
    arml = {s: (dist[f'sleeve.{s}'] < dist['body']) for s in ('L', 'R')}
    wd = {}
    for s in ('L', 'R'):
        cw = core.chain_weights(co, segs, [f'upperarm.{s}', f'lowerarm.{s}'], blend=0.3)
        blend_in = smoothstep(0.0, 0.012, dist['body'] - dist[f'sleeve.{s}'])
        wd[f'upperarm.{s}'] = arml[s] * cw[f'upperarm.{s}'] * blend_in
        wd[f'lowerarm.{s}'] = arml[s] * cw[f'lowerarm.{s}'] * blend_in
    body = 1 - (wd['upperarm.L'] + wd['lowerarm.L'] + wd['upperarm.R'] + wd['lowerarm.R'])
    kleg = np.clip((0.3 - co[:, 2]) / 0.1, 0, 1) * 0.3
    wd['chest'] = body * smoothstep(0.43, 0.47, co[:, 2])
    wd['spine'] = body * smoothstep(0.38, 0.42, co[:, 2]) * (1 - smoothstep(0.43, 0.47, co[:, 2]))
    hipw = body * (1 - smoothstep(0.38, 0.42, co[:, 2]))
    wd['hips'] = hipw * (1 - kleg)
    wd['upperleg.L'] = hipw * kleg * (co[:, 0] > 0)
    wd['upperleg.R'] = hipw * kleg * (co[:, 0] <= 0)
    core.bind(objs['dress'], arm, {k: v.astype(float) for k, v in wd.items()})

    # white parts: apron/petticoat on the body, headdress on the head, cuffs/socks on the limbs
    co = core.verts_of(objs['white'])
    kleg = np.clip((0.3 - co[:, 2]) / 0.1, 0, 1) * 0.3
    upper = co[:, 2] > 0.45
    core.bind(objs['white'], arm, {'chest': upper.astype(float), 'hips': (~upper) * (1 - kleg),
                                   'upperleg.L': (~upper) * kleg * (co[:, 0] > 0), 'upperleg.R': (~upper) * kleg * (co[:, 0] <= 0)})
    rigid(objs['white_head'], 'head')
    co = core.verts_of(objs['white_limbs'])
    cuff = co[:, 2] > 0.2
    core.bind(objs['white_limbs'], arm, {'lowerarm.L': (cuff & (co[:, 0] > 0)).astype(float), 'lowerarm.R': (cuff & (co[:, 0] <= 0)).astype(float),
                                         'lowerleg.L': (~cuff & (co[:, 0] > 0)).astype(float), 'lowerleg.R': (~cuff & (co[:, 0] <= 0)).astype(float)})

    # accents: head bows with head, skirt bows with hips, sleeve buttons with arms
    co = core.verts_of(objs['accents'])
    headp = co[:, 2] > 0.6
    btn = (~headp) & (co[:, 2] > 0.34)
    core.bind(objs['accents'], arm, {'head': headp.astype(float), 'upperarm.L': (btn & (co[:, 0] > 0)).astype(float),
                                     'upperarm.R': (btn & (co[:, 0] < 0)).astype(float), 'hips': (~headp & ~btn).astype(float)})
    co = core.verts_of(objs['shoes'])
    core.bind(objs['shoes'], arm, {'foot.L': (co[:, 0] > 0).astype(float), 'foot.R': (co[:, 0] <= 0).astype(float)})
    co = core.verts_of(objs['tail'])
    core.bind(objs['tail'], arm, core.chain_weights(co, segs, tail_names, blend=0.4))
    return arm
