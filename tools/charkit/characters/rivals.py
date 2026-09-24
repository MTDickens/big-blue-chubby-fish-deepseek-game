"""Rivals: 白色龙娘 (the white dragon girl, EP3) and 豆包帮首领 (the Doubao gang boss mascot, EP2).

The dragon girl is kept chibi (~2.8 heads) so she sits in the same figure line-up as 蓝色大肥鱼:
long white wavy hair, curved horns, elf ears, lavender eyes, white frilled dress with detached
sleeves and a rose, white bat wings and a long scaled tail. The Doubao boss is a pear-shaped
orange mascot with a cream belly, brown center-parted bob and dark hands/feet.
"""
import math
import os

import bpy  # noqa: F401
import numpy as np

from .. import core, face as F, sdf, shapes as S
from .bluefish import TEX, add_bow, lin, lock, realize, smoothstep

TAU = 2 * math.pi


def hdir(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)], dtype=np.float32)


def hpt(c, r, az, el, off=0.0):
    d = hdir(az, el)
    rr = 1.0 / math.sqrt((d[0] / r[0]) ** 2 + (d[1] / r[1]) ** 2 + (d[2] / r[2]) ** 2)
    return np.asarray(c, dtype=np.float32) + d * (rr + off)


# ============================================================================ dragon girl

DC = np.array([0, 0, 0.86], dtype=np.float32)
DR = np.array([0.14, 0.135, 0.14], dtype=np.float32)
D_EYE_Z = 0.832
DPAL = dict(skin=lin('#fbe6dd'), hair_root=lin('#f6f5fb'), hair_tip=lin('#d9d2ef'), dress=lin('#fbfbff'), lace=lin('#eef0fb'),
            horn_base=lin('#b7acd6'), horn_tip=lin('#f9f7ff'), wing=lin('#f2effa'), membrane=lin('#dcd4f0'),
            tail=lin('#f1eff8'), tail_scale=lin('#cbc2e6'), rose=lin('#e8e6f2'), shoe=lin('#f4f4fa'), silver=lin('#c9cbe0'))
D_TAIL = [(0.0, 0.07, 0.46), (0.06, 0.19, 0.32), (0.16, 0.29, 0.15), (0.3, 0.3, 0.06), (0.43, 0.22, 0.05), (0.52, 0.11, 0.07)]


def dragon_skin():
    K = sdf.Field('skin')
    sk = DPAL['skin']
    K.add(sdf.ellipsoid(DC, DR), sk, k=0.0)
    for s in (-1, 1):
        K.add(sdf.sphere((s * 0.058, -0.066, 0.79), 0.062), sk, k=0.045)
    K.add(sdf.sphere((0, -0.08, 0.75), 0.032), sk, k=0.045)
    K.add(sdf.round_cone((0, 0.004, 0.64), (0, 0.006, 0.76), 0.026, 0.024), sk, k=0.01)
    for s in (-1, 1):   # pointed elf ears
        K.ribbon([np.array((s * 0.125, 0.012, 0.85)), np.array((s * 0.17, 0.03, 0.875)), np.array((s * 0.215, 0.05, 0.905))],
                 [0.024, 0.016, 0.003], [0.008, 0.006, 0.002], sk, k=0.012, up=np.array((0, -1.0, 0.2)))
        sh = np.array((s * 0.07, 0.0, 0.655))
        el = np.array((s * 0.112, -0.012, 0.56))
        wr = np.array((s * 0.13, -0.035, 0.48))
        K.add(sdf.round_cone(sh, el, 0.024, 0.019), sk, k=0.01)
        K.add(sdf.round_cone(el, wr, 0.019, 0.016), sk, k=0.004)
        K.add(sdf.ellipsoid(wr + np.array((s * 0.004, -0.008, -0.024)), (0.015, 0.012, 0.022), rot=(10, s * 15, 0)), sk, k=0.006)
    return K


def dragon_dress():
    D = sdf.Field('dress')
    wc = DPAL['dress']
    bodice = [(0, 0.48), (0.062, 0.48), (0.07, 0.53), (0.074, 0.59), (0.07, 0.63), (0.06, 0.648), (0, 0.648)]
    D.add(sdf.lathe(bodice, squash_y=0.82), wc, k=0.0)

    def folds(th, z):
        t = np.clip((0.5 - z) / 0.45, 0, 1)
        return 1 + (0.045 * np.sin(th * 8) + 0.015 * np.sin(th * 5 + 1)) * t ** 1.2
    skirt = [(0, 0.52), (0.07, 0.52), (0.1, 0.46), (0.15, 0.34), (0.2, 0.2), (0.24, 0.08), (0.25, 0.05), (0, 0.05)]
    D.add(sdf.lathe(skirt, mod=folds), wc, k=0.012)
    # gathered tiers
    for z, r, hgt in ((0.07, 0.25, 0.06), (0.26, 0.19, 0.05)):
        ring = [np.array((r * math.cos(a), r * math.sin(a), z), dtype=np.float32) for a in np.linspace(0, TAU, 24, endpoint=False)]
        sdf.frill(D, ring, hgt, 0.005, 26, 0.01, DPAL['lace'], lambda P, T: np.array([P[0] * 0.3, P[1] * 0.3, -1.0]), closed=True, k=0.01)
    # neckline frill and choker ribbon
    ring = [np.array((0.064 * math.cos(a), 0.064 * math.sin(a) * 0.82, 0.646), dtype=np.float32) for a in np.linspace(0, TAU, 16, endpoint=False)]
    sdf.frill(D, ring, 0.022, 0.004, 14, 0.004, DPAL['lace'], lambda P, T: np.array([P[0], P[1], 0.5]), closed=True, k=0.006)
    D.tube([np.array((0.027 * math.cos(a), 0.027 * math.sin(a), 0.72), dtype=np.float32) for a in np.linspace(0, TAU, 12, endpoint=False)],
           0.004, DPAL['silver'], k=0.002, closed=True)
    # rose ornament at the waist
    rc = np.array((0.055, -0.058, 0.5), dtype=np.float32)
    for i, a in enumerate(np.linspace(0, TAU, 7, endpoint=False)):
        D.add(sdf.ellipsoid(rc + np.array((0.012 * math.cos(a), -0.004, 0.012 * math.sin(a))), (0.01, 0.006, 0.009), rot=(0, math.degrees(a), 0)), DPAL['rose'], k=0.004)
    D.add(sdf.sphere(rc + np.array((0, -0.006, 0)), 0.008), DPAL['rose'], k=0.004)
    # heels peeking out under the hem
    for s in (-1, 1):
        D.add(sdf.ellipsoid((s * 0.045, -0.04, 0.022), (0.026, 0.044, 0.022)), DPAL['shoe'], k=0.0)
        D.carve(sdf.rounded_box((s * 0.045, -0.04, -0.02), (0.05, 0.07, 0.02), 0.0), k=0.003)
    return D


def dragon_sleeves():
    L = sdf.Field('sleeves')
    for s in (-1, 1):
        el = np.array((s * 0.112, -0.012, 0.56), dtype=np.float32)
        wr = np.array((s * 0.13, -0.035, 0.48), dtype=np.float32)
        d = (wr - el) / np.linalg.norm(wr - el)
        # flared detached sleeve from above the elbow to past the wrist, frilled edge
        L.tube([el - d * 0.03, el, wr - d * 0.005], [0.024, 0.028, 0.044], DPAL['dress'], k=0.004)
        ring = [wr - d * 0.004 + np.array((0.046 * math.cos(a), 0.046 * math.sin(a) * 0.9, 0.0), dtype=np.float32) for a in np.linspace(0, TAU, 12, endpoint=False)]
        sdf.frill(L, ring, 0.03, 0.004, 12, 0.006, DPAL['lace'], lambda P, T, wr=wr: (P - wr) * np.array([1, 1, 0]) + np.array([0, 0, -0.03]), closed=True, k=0.006)
    return L


def dragon_hair_base():
    H = sdf.Field('hair')
    col = DPAL['hair_root']
    H.add(sdf.ellipsoid(DC + np.array((0, 0.014, 0.02)), DR + np.array((0.026, 0.028, 0.024))), col, k=0.01)
    H.carve(sdf.ellipsoid(np.array((0, -0.2, 0.79)), (0.112, 0.13, 0.108)), k=0.02)

    def shell(P):
        x, y, z = P[..., 0], P[..., 1] - 0.03, P[..., 2]
        rho = np.sqrt(x * x + y * y)
        phi = np.arctan2(x, y)
        r_in = np.interp(z, [0.2, 0.5, 0.72, 0.8, 0.9], [0.17, 0.16, 0.13, 0.1, 0.07])
        r_out = np.interp(z, [0.2, 0.35, 0.55, 0.72, 0.84, 0.92], [0.27, 0.27, 0.25, 0.2, 0.16, 0.1]) + 0.01 * np.sin(10 * phi + 12 * z)
        dr = np.maximum(r_in - rho, rho - r_out)
        dz = np.maximum(0.3 - z, z - 0.9)
        q = np.stack([np.maximum(dr, 0), np.maximum(dz, 0)], -1)
        d = np.minimum(np.maximum(dr, dz), 0) + np.sqrt((q * q).sum(-1))
        return np.maximum(d, (np.abs(phi) - math.radians(108)) * rho) - 0.006
    H.add((shell, (np.array((-0.3, -0.28, 0.25)), np.array((0.3, 0.32, 0.95)))), col, k=0.05)
    return H


def dragon_hair_locks():
    geos = []
    rng = np.random.default_rng(8)
    # side-swept bangs
    for i, az in enumerate(np.linspace(-78, 78, 12)):
        azt = az + 10 + 6 * math.sin(i)
        elt = 6 + 5 * math.sin(1.7 * i)
        pts = [hpt(DC, DR, az + (azt - az) * t ** 1.3, 64 + (elt - 64) * t ** 0.8, off=0.024 + 0.01 * math.sin(math.pi * t) - 0.008 * t) for t in np.linspace(0, 1, 6)]
        tip = pts[-1] + hdir(azt + 8, elt - 30) * 0.016 - hdir(azt, elt) * 0.006
        geos.append(lock(pts + [tip], 0.03, 0.42, n=18, up=hdir(az, 55), root=0.9, tip_start=0.62))
    # face-framing side locks, long and wavy
    for side in (-1, 1):
        for k, (az, zend, xo) in enumerate([(66, 0.42, 0.0), (82, 0.36, 0.03)]):
            p = [hpt(DC, DR, side * az, 36, 0.024), hpt(DC, DR, side * (az + 3), 6, 0.03), hpt(DC, DR, side * (az + 5), -22, 0.032)]
            b = p[-1]
            for z, dx in ((0.68, 0.02), (0.62, -0.006), (0.55, 0.022), (0.48, -0.004), (zend, 0.012)):
                p.append(np.array((side * (0.17 + xo + dx), b[1] + 0.008 * k, z)))
            geos.append(lock(p, 0.032 + 0.004 * k, 0.45, n=36, up=hdir(side * az, 10), tip_start=0.8))
    # long back locks reaching the knees
    for layer, azs in enumerate([np.linspace(116, 244, 9), list(np.linspace(108, 252, 12)) + [s * a for s in (-1, 1) for a in (96, 104)]]):
        for i, az in enumerate(azs):
            azr = az % 360
            side = math.sin(math.radians(azr))
            sidek = 1.0 if (azr < 108 or azr > 252) else 0.0
            pts = [hpt(DC, DR, azr, el, off=-0.004 + layer * 0.004 + 0.028 * (22 - el) / 22) for el in (22, 11, 0)]
            base = pts[-1]
            radial = np.array((base[0], base[1] - 0.03, 0.0), dtype=np.float32)
            radial /= np.linalg.norm(radial)
            tang = np.cross(np.array((0, 0, 1.0), dtype=np.float32), radial)
            z_end = 0.24 + 0.06 * abs(side) + rng.uniform(-0.03, 0.03)
            ph = 1.1 * i + rng.uniform(0, 0.8) + layer
            amp = 0.028 + rng.uniform(0, 0.012)
            r0 = float(np.linalg.norm(base[:2] - np.array((0, 0.03))))
            for kk, z in enumerate(np.linspace(base[2] - 0.05, z_end, 11)):
                t = (kk + 1) / 11
                spread = float(np.interp(z, [0.2, 0.35, 0.55, 0.72], [0.3, 0.29, 0.265, 0.22])) + layer * 0.012
                rho = max(spread + sidek * 0.03 * t, r0 + 0.004 * kk) + 0.01 * math.cos(ph + t * 10)
                q = np.array((0, 0.03, 0), dtype=np.float32) + radial * rho + tang * amp * math.sin(ph + t * 10)
                q[2] = z
                pts.append(q)
            last = pts[-1]
            curl = 1 if (i + layer) % 2 else -1
            pts.append(last + tang * 0.02 * curl + radial * 0.016)
            pts.append(last + tang * 0.03 * curl + radial * 0.03 + np.array((0, 0, 0.02), dtype=np.float32))
            geos.append(lock(pts, 0.046 + rng.uniform(-0.004, 0.006), 0.4, n=40, up=radial, root=0.25, tip_start=0.8))
    return geos


def dragon_hair_colors(co):
    t = smoothstep(0.75, 0.3, co[:, 2])[:, None]
    return DPAL['hair_root'] * (1 - t) + DPAL['hair_tip'] * t


def dragon_horns():
    Hn = sdf.Field('horns')
    for s in (-1, 1):
        path = [np.array(p, dtype=np.float32) for p in [(s * 0.085, -0.02, 0.965), (s * 0.12, 0.03, 1.04), (s * 0.16, 0.1, 1.055), (s * 0.18, 0.15, 1.01), (s * 0.17, 0.16, 0.965)]]
        Hn.tube(path, [0.026, 0.022, 0.016, 0.01, 0.003], DPAL['horn_base'], k=0.004)
        # tip paint (lighter toward the tip)
        Hn.paint(sdf.sphere(path[2], 0.05), DPAL['horn_tip'], k=0.03)
        Hn.paint(sdf.sphere(path[4], 0.05), DPAL['horn_tip'], k=0.02)
    return Hn


def dragon_wings():
    W = sdf.Field('wings')
    for s in (-1, 1):
        root = np.array((s * 0.05, 0.08, 0.62), dtype=np.float32)
        elbow = np.array((s * 0.3, 0.26, 0.98), dtype=np.float32)
        tip = np.array((s * 0.56, 0.3, 0.86), dtype=np.float32)
        W.tube([root, elbow], [0.016, 0.012], DPAL['wing'], k=0.004)
        W.tube([elbow, tip], [0.011, 0.004], DPAL['wing'], k=0.004)
        W.add(sdf.sphere(elbow, 0.014), DPAL['wing'], k=0.006)
        u = (tip - root) / np.linalg.norm(tip - root)
        down = np.array((0, 0.25, -1.0), dtype=np.float32)
        L = float(np.linalg.norm(tip - root))
        # membrane with scalloped trailing edge (outline in the wing plane: x along the arm, y down)
        o_ = [(0.0, 0.01), (L * 0.55, 0.09), (L, 0.01), (L * 0.92, -0.12), (L * 0.8, -0.16), (L * 0.68, -0.11), (L * 0.54, -0.24),
              (L * 0.42, -0.17), (L * 0.28, -0.3), (L * 0.15, -0.2), (0.03, -0.26)]
        o_ = [(x, -y) for x, y in o_]
        W.add(sdf.slab(o_, 0.009, root, u, -down, round_r=0.0035), DPAL['membrane'], k=0.006)
        for f_ in (0.26, 0.52, 0.78):   # finger bones
            a = root + (tip - root) * f_ * 0.95
            b = root + (tip - root) * f_ + down / np.linalg.norm(down) * (0.28 if f_ < 0.3 else 0.23 if f_ < 0.6 else 0.15)
            W.tube([elbow * 0.6 + a * 0.4, b], [0.006, 0.003], DPAL['wing'], k=0.004)
    return W


def dragon_tail():
    T = sdf.Field('tail')
    pts = [np.array(p, dtype=np.float32) for p in D_TAIL]
    T.tube(pts, [0.058, 0.05, 0.04, 0.03, 0.02, 0.006], DPAL['tail'], k=0.0)
    return T


def dragon_tail_colors(co, normals):
    # soft scale bands on the top, pale belly
    P = S.catmull_rom(np.array(D_TAIL), 200)
    d = np.linalg.norm(co[:, None, :] - P[None, ::2, :], axis=2)
    idx = np.argmin(d, axis=1)
    band = 0.5 + 0.5 * np.cos(idx * 1.3)
    top = smoothstep(-0.2, 0.5, normals[:, 2])
    t = (band * top * 0.55)[:, None]
    return DPAL['tail'] * (1 - t) + DPAL['tail_scale'] * t


def build_dragon(out_path):
    core.reset()
    core.clear_material_cache()
    M = dict(
        skin=core.material('fig_skin', '#ffffff', extras={'rough': 0.62, 'sheen': 0.5, 'sheenColor': '#ffd6ca', 'env': 0.7, 'emissive': '#ffc0b0', 'emissiveIntensity': 0.05}),
        hair=core.material('fig_hair_white', '#ffffff', extras={'rough': 0.45, 'coat': 0.3, 'sheen': 0.6, 'sheenColor': '#e6e0ff', 'env': 0.85}),
        dress=core.material('fig_dress_white', '#ffffff', extras={'rough': 0.6, 'sheen': 0.6, 'sheenColor': '#e8ecff', 'env': 0.8}),
        horn=core.material('fig_horn', '#ffffff', extras={'rough': 0.3, 'coat': 0.7, 'env': 1.0}),
        wing=core.material('fig_wing', '#ffffff', extras={'rough': 0.5, 'sheen': 0.5, 'sheenColor': '#ece6ff', 'env': 0.8, 'double': True}),
        tail=core.material('fig_tail_white', '#ffffff', extras={'rough': 0.4, 'coat': 0.4, 'env': 0.9}),
        face=core.material('face_bluefish', '#ffffff', image=TEX, alpha='image'),
    )
    objs = {}
    objs['skin'] = realize(dragon_skin(), 'skin', M['skin'], voxel=0.002, target=9000, cav=0.15)
    base = realize(dragon_hair_base(), 'hair_base', M['hair'], voxel=0.0026, target=8000, cav=0.2)
    locks = S.obj('hair_locks', S.merge_geos(*dragon_hair_locks()), M['hair'], fix_normals=False)
    S.recalc_normals(locks)
    core.paint(locks, dragon_hair_colors)
    core.paint(base, dragon_hair_colors)
    objs['hair'] = core.join([base, locks], 'hair')
    tris = core.tri_count(objs['hair'])
    if tris > 30000:
        core.add_modifier(objs['hair'], 'DECIMATE', ratio=30000 / tris, use_collapse_triangulate=True)
        core.apply_modifiers(objs['hair'])
    objs['dress'] = realize(dragon_dress(), 'dress', M['dress'], voxel=0.0024, target=14000, cav=0.35)
    objs['sleeves'] = realize(dragon_sleeves(), 'sleeves', M['dress'], voxel=0.002, target=3000, cav=0.3)
    objs['horns'] = realize(dragon_horns(), 'horns', M['horn'], voxel=0.0018, target=2500, cav=0.1)
    objs['wings'] = realize(dragon_wings(), 'wings', M['wing'], voxel=0.002, target=5000, cav=0.2)
    objs['tail'] = realize(dragon_tail(), 'tail', M['tail'], voxel=0.0025, target=3500, cav=0.1, post=lambda V, N, c: dragon_tail_colors(V, N))

    bvh = F.surface_bvh(objs['skin'])
    ex = 0.056
    objs['expr_eyes_open'] = core.join([F.decal('deyeR', bvh, (-ex, -0.4, D_EYE_Z), (0.078, 0.1), (0, 3), M['face']),
                                        F.decal('deyeL', bvh, (ex, -0.4, D_EYE_Z), (0.078, 0.1), (0, 3), M['face'], mirror=True)], 'expr_eyes_open')
    objs['expr_eyes_happy'] = core.join([F.decal('deyeRh', bvh, (-ex, -0.4, D_EYE_Z - 0.004), (0.078, 0.092), (1, 0), M['face']),
                                         F.decal('deyeLh', bvh, (ex, -0.4, D_EYE_Z - 0.004), (0.078, 0.092), (1, 0), M['face'], mirror=True)], 'expr_eyes_happy')
    objs['expr_mouth_small'] = F.decal('expr_mouth_small', bvh, (0, -0.4, 0.77), (0.042, 0.042), (1, 1), M['face'])
    objs['expr_mouth_open'] = F.decal('expr_mouth_open', bvh, (0, -0.4, 0.768), (0.05, 0.05), (0, 1), M['face'])
    objs['face_blush'] = core.join([F.decal('dblushR', bvh, (-0.083, -0.4, 0.797), (0.058, 0.036), (0, 2), M['face'], offset=0.0008),
                                    F.decal('dblushL', bvh, (0.083, -0.4, 0.797), (0.058, 0.036), (0, 2), M['face'], mirror=True, offset=0.0008)], 'face_blush')
    arm = dragon_rig(objs)
    dragon_anims(arm)
    stats = {k: core.tri_count(v) for k, v in objs.items()}
    core.export_glb(out_path)
    return stats


def dragon_rig(objs):
    bones = [
        ('root', (0, 0, 0), (0, 0, 0.08), None),
        ('hips', (0, 0, 0.44), (0, 0, 0.52), 'root'),
        ('spine', (0, 0, 0.52), (0, 0, 0.59), 'hips'),
        ('chest', (0, 0, 0.59), (0, 0, 0.65), 'spine'),
        ('neck', (0, 0, 0.65), (0, 0, 0.74), 'chest'),
        ('head', (0, 0, 0.74), (0, 0, 1.0), 'neck'),
        ('eye.L', (0.056, -0.12, D_EYE_Z), (0.056, -0.15, D_EYE_Z), 'head'),
        ('eye.R', (-0.056, -0.12, D_EYE_Z), (-0.056, -0.15, D_EYE_Z), 'head'),
        ('hair.B', (0, 0.14, 0.78), (0, 0.25, 0.3), 'head'),
        ('hair.L', (0.14, 0.06, 0.78), (0.26, 0.1, 0.3), 'head'),
        ('hair.R', (-0.14, 0.06, 0.78), (-0.26, 0.1, 0.3), 'head'),
        ('upperarm.L', (0.07, 0, 0.655), (0.112, -0.012, 0.56), 'chest'),
        ('lowerarm.L', (0.112, -0.012, 0.56), (0.13, -0.035, 0.48), 'upperarm.L'),
        ('hand.L', (0.13, -0.035, 0.48), (0.136, -0.045, 0.44), 'lowerarm.L'),
        ('upperarm.R', (-0.07, 0, 0.655), (-0.112, -0.012, 0.56), 'chest'),
        ('lowerarm.R', (-0.112, -0.012, 0.56), (-0.13, -0.035, 0.48), 'upperarm.R'),
        ('hand.R', (-0.13, -0.035, 0.48), (-0.136, -0.045, 0.44), 'lowerarm.R'),
        ('upperleg.L', (0.045, 0, 0.44), (0.045, 0, 0.22), 'hips'),
        ('lowerleg.L', (0.045, 0, 0.22), (0.045, -0.02, 0.03), 'upperleg.L'),
        ('upperleg.R', (-0.045, 0, 0.44), (-0.045, 0, 0.22), 'hips'),
        ('lowerleg.R', (-0.045, 0, 0.22), (-0.045, -0.02, 0.03), 'upperleg.R'),
        ('wing.L', (0.05, 0.08, 0.62), (0.3, 0.26, 0.98), 'chest'),
        ('wingtip.L', (0.3, 0.26, 0.98), (0.56, 0.3, 0.86), 'wing.L'),
        ('wing.R', (-0.05, 0.08, 0.62), (-0.3, 0.26, 0.98), 'chest'),
        ('wingtip.R', (-0.3, 0.26, 0.98), (-0.56, 0.3, 0.86), 'wing.R'),
    ]
    tail_names = []
    for i in range(len(D_TAIL) - 1):
        n = f'tail.{i + 1}'
        bones.append((n, D_TAIL[i], D_TAIL[i + 1], 'hips' if i == 0 else f'tail.{i}'))
        tail_names.append(n)
    arm = core.armature('rig_dragon', bones)
    segs = core.bone_segments(arm)

    def rigid(o, b):
        core.bind(o, arm, core.rigid(len(o.data.vertices), b))
    for k in ('horns', 'expr_mouth_small', 'expr_mouth_open', 'face_blush'):
        rigid(objs[k], 'head')
    for k in ('expr_eyes_open', 'expr_eyes_happy'):
        co = core.verts_of(objs[k])
        core.bind(objs[k], arm, {'eye.L': (co[:, 0] > 0).astype(float), 'eye.R': (co[:, 0] <= 0).astype(float)})
    # skin: head/neck vs arms
    co = core.verts_of(objs['skin'])
    headp = co[:, 2] > 0.7
    armp = (~headp) & (np.abs(co[:, 0]) > 0.055)
    w = {'head': headp * smoothstep(0.72, 0.76, co[:, 2]), 'neck': headp * (1 - smoothstep(0.72, 0.76, co[:, 2])) + (~headp & ~armp)}
    for s, sg in (('L', 1), ('R', -1)):
        cw = core.chain_weights(co, segs, [f'upperarm.{s}', f'lowerarm.{s}', f'hand.{s}'], blend=0.3)
        m = armp & (np.sign(co[:, 0]) == sg)
        for b in cw:
            w[b] = m * cw[b]
    core.bind(objs['skin'], arm, {k: np.asarray(v, dtype=float) for k, v in w.items()})
    co = core.verts_of(objs['sleeves'])
    w = {}
    for s, sg in (('L', 1), ('R', -1)):
        m = np.sign(co[:, 0]) == sg
        cw = core.chain_weights(co, segs, [f'upperarm.{s}', f'lowerarm.{s}'], blend=0.3)
        w[f'upperarm.{s}'] = m * cw[f'upperarm.{s}']
        w[f'lowerarm.{s}'] = m * cw[f'lowerarm.{s}']
    core.bind(objs['sleeves'], arm, w)
    # dress: bodice on chest/spine, skirt on hips with a little leg pull
    co = core.verts_of(objs['dress'])
    kleg = np.clip((0.4 - co[:, 2]) / 0.3, 0, 1) * 0.35
    top = co[:, 2] > 0.55
    shoes = co[:, 2] < 0.05
    core.bind(objs['dress'], arm, {'chest': top.astype(float), 'hips': (~top & ~shoes) * (1 - kleg),
                                   'upperleg.L': (~top & ~shoes) * kleg * (co[:, 0] > 0), 'upperleg.R': (~top & ~shoes) * kleg * (co[:, 0] <= 0),
                                   'lowerleg.L': shoes * (co[:, 0] > 0), 'lowerleg.R': shoes * (co[:, 0] <= 0)})
    # hair: top with head, long hair on hair bones
    co = core.verts_of(objs['hair'])
    hang = smoothstep(0.78, 0.6, co[:, 2])
    pw = core.proximity_weights(co, segs, ['hair.B', 'hair.L', 'hair.R'], falloff=3.0)
    tot = sum(pw.values())
    tot[tot == 0] = 1
    w = {n: pw[n] / tot * hang for n in pw}
    w['head'] = 1 - hang
    core.bind(objs['hair'], arm, w)
    co = core.verts_of(objs['wings'])
    w = {}
    for s, sg in (('L', 1), ('R', -1)):
        m = np.sign(co[:, 0]) == sg
        t = smoothstep(0.26, 0.36, np.abs(co[:, 0]))
        w[f'wing.{s}'] = m * (1 - t)
        w[f'wingtip.{s}'] = m * t
    core.bind(objs['wings'], arm, w)
    co = core.verts_of(objs['tail'])
    core.bind(objs['tail'], arm, core.chain_weights(co, segs, tail_names, blend=0.4))
    return arm


def dragon_anims(arm):
    dirs = core.bone_dirs(arm)

    def tail(ph, a=10, sp=1.0):
        return {f'tail.{i}': {'rot': (0, 0, a * math.sin(TAU * (ph * sp - 0.12 * i)))} for i in range(1, 6)}

    def idle(f, ph):
        b = math.sin(TAU * ph)
        return {'spine': {'rot': (-2, 0, 3 * b)}, 'head': {'rot': (-4, 4 * math.sin(TAU * ph + 0.5), 6)},
                'upperarm.L': {'rot': (0, 0, 4 + 2 * b)}, 'upperarm.R': {'rot': (0, 0, -4 - 2 * b)},
                'wing.L': {'rot': (0, -6 * b, 4 * b)}, 'wing.R': {'rot': (0, 6 * b, -4 * b)},
                'wingtip.L': {'rot': (0, -8 * b, 0)}, 'wingtip.R': {'rot': (0, 8 * b, 0)},
                'hair.B': {'rot': (2 * b, 0, 0)}, **tail(ph, 8)}
    core.action(arm, 'idle', 90, idle)

    def walk(f, ph):
        a = math.sin(TAU * ph)
        return {'root': {'loc': (0, 0, 0.01 * (1 - math.cos(2 * TAU * ph)) / 2)}, 'hips': {'rot': (0, 3 * a, 5 * a)},
                'spine': {'rot': (0, 0, -4 * a)}, 'head': {'rot': (-4, 0, 2 * a)},
                'upperleg.L': {'rot': (-18 * a, 0, 0)}, 'upperleg.R': {'rot': (18 * a, 0, 0)},
                'lowerleg.L': {'rot': (20 * max(0.0, math.sin(TAU * ph + 1.5)), 0, 0)}, 'lowerleg.R': {'rot': (20 * max(0.0, math.sin(TAU * ph - 1.6)), 0, 0)},
                'upperarm.L': {'rot': (16 * a, 0, 6)}, 'upperarm.R': {'rot': (-16 * a, 0, -6)},
                'wing.L': {'rot': (0, -8 * math.sin(2 * TAU * ph), 0)}, 'wing.R': {'rot': (0, 8 * math.sin(2 * TAU * ph), 0)},
                'hair.B': {'rot': (5 * math.sin(2 * TAU * ph), 0, 0)}, **tail(ph, 14)}
    core.action(arm, 'walk', 30, walk)

    def flap(f, ph):
        a = math.sin(TAU * ph)
        return {'wing.L': {'rot': (0, -30 * a, 18 * a)}, 'wing.R': {'rot': (0, 30 * a, -18 * a)},
                'wingtip.L': {'rot': (0, -25 * math.sin(TAU * ph - 0.6), 0)}, 'wingtip.R': {'rot': (0, 25 * math.sin(TAU * ph - 0.6), 0)},
                'root': {'loc': (0, 0, 0.03 + 0.02 * a)}, 'hair.B': {'rot': (-6 * a, 0, 0)}, **tail(ph, 16, 1)}
    core.action(arm, 'flap', 30, flap)

    from mathutils import Vector
    q1 = core.aim(dirs['upperarm.R'], Vector((-0.06, -0.14, 0.05)))
    q2 = core.aim(dirs['lowerarm.R'], Vector((-0.02, -0.1, 0.02)), q1)

    def point(f, ph):
        a = math.sin(TAU * ph)
        return {'upperarm.R': {'q': q1}, 'lowerarm.R': {'q': q2}, 'upperarm.L': {'rot': (-30, 0, -40)}, 'lowerarm.L': {'rot': (0, 0, -70)},
                'spine': {'rot': (-4, 0, 6)}, 'head': {'rot': (-8, 0, -8 + 3 * a)}, 'wing.L': {'rot': (0, -12, 6)}, 'wing.R': {'rot': (0, 12, -6)},
                **tail(ph, 20, 2)}
    core.action(arm, 'point', 45, point)

    def blink(f, ph):
        kk = 1 - math.sin(math.pi * ph) ** 0.6 * 0.92
        return {'eye.L': {'scale': (1, 1, kk)}, 'eye.R': {'scale': (1, 1, kk)}}
    core.action(arm, 'blink', 8, blink, loop=False)
    core.finish_actions(arm, 'idle')


# ============================================================================ Doubao boss

BC = np.array((0, -0.01, 0.98), dtype=np.float32)
BR = np.array((0.2, 0.185, 0.2), dtype=np.float32)
BPAL = dict(skin=lin('#eaa43c'), belly=lin('#f3dcc0'), dark=lin('#4a2d1c'), hair=lin('#5a3522'), hair_hi=lin('#7a4a30'))


def doubao_body():
    Bf = sdf.Field('body')
    sk = BPAL['skin']
    Bf.add(sdf.ellipsoid((0, 0, 0.5), (0.25, 0.21, 0.32)), sk, k=0.0)
    Bf.add(sdf.ellipsoid(BC, BR), sk, k=0.07)
    for s in (-1, 1):
        Bf.tube([np.array((s * 0.2, 0.0, 0.7)), np.array((s * 0.27, -0.02, 0.56)), np.array((s * 0.285, -0.03, 0.44))], [0.055, 0.05, 0.046], sk, k=0.04)
        Bf.add(sdf.round_cone((s * 0.1, 0.0, 0.3), (s * 0.11, -0.005, 0.05), 0.075, 0.066), sk, k=0.05)
        Bf.paint(sdf.sphere((s * 0.285, -0.03, 0.42), 0.05), BPAL['dark'], k=0.012)   # dark hand tips
        Bf.paint(sdf.ellipsoid((s * 0.11, -0.01, 0.02), (0.09, 0.09, 0.05)), BPAL['dark'], k=0.012)   # dark feet
        Bf.carve(sdf.rounded_box((s * 0.11, 0, -0.03), (0.1, 0.1, 0.03), 0.0), k=0.004)
    Bf.paint(sdf.ellipsoid((0, -0.2, 0.5), (0.2, 0.14, 0.24)), BPAL['belly'], k=0.02)
    return Bf


def doubao_hair():
    H = sdf.Field('hair')
    hc = BPAL['hair']
    H.add(sdf.ellipsoid(BC + np.array((0, 0.02, -0.01)), (0.232, 0.222, 0.255)), hc, k=0.0)
    H.carve(sdf.ellipsoid(BC + np.array((0, -0.2, -0.06)), (0.158, 0.17, 0.2)), k=0.025)
    H.carve(sdf.rounded_box(BC + np.array((0, 0, -0.34)), (0.3, 0.3, 0.2), 0.0), k=0.02)
    H.carve(sdf.ellipsoid(BC + np.array((0, 0.02, -0.02)), (0.19, 0.18, 0.22)), k=0.01)   # hollow so it sits over the head
    H.carve(sdf.ellipsoid(BC + np.array((0, -0.1, 0.24)), (0.006, 0.18, 0.03)), k=0.006)   # center part
    H.add(sdf.ellipsoid(BC + np.array((0, 0.02, -0.01)), (0.2, 0.19, 0.225)), hc, k=0.0)   # inner fill behind the face
    H.carve(sdf.ellipsoid(BC + np.array((0, -0.2, -0.06)), (0.158, 0.17, 0.2)), k=0.025)
    H.carve(sdf.rounded_box(BC + np.array((0, 0, -0.34)), (0.3, 0.3, 0.2), 0.0), k=0.02)
    return H


def build_doubao(out_path):
    core.reset()
    core.clear_material_cache()
    M = dict(
        body=core.material('fig_mascot', '#ffffff', extras={'rough': 0.6, 'sheen': 0.5, 'sheenColor': '#ffd9a0', 'env': 0.8}),
        hair=core.material('fig_hair_brown', '#ffffff', extras={'rough': 0.4, 'coat': 0.35, 'sheen': 0.4, 'sheenColor': '#c89070', 'env': 0.9}),
        face=core.material('face_bluefish', '#ffffff', image=TEX, alpha='image'),
    )
    objs = {'body': realize(doubao_body(), 'body', M['body'], voxel=0.003, target=10000, cav=0.15),
            'hair': realize(doubao_hair(), 'hair', M['hair'], voxel=0.0028, target=6000, cav=0.25)}
    bvh = F.surface_bvh(objs['body'])
    ex, ez = 0.07, 0.96
    objs['expr_eyes_open'] = core.join([F.decal('beyeR', bvh, (-ex, -0.5, ez), (0.085, 0.1), (1, 3), M['face']),
                                        F.decal('beyeL', bvh, (ex, -0.5, ez), (0.085, 0.1), (1, 3), M['face'], mirror=True)], 'expr_eyes_open')
    objs['brows'] = core.join([F.decal('bbrowR', bvh, (-0.07, -0.5, 1.03), (0.07, 0.045), (2, 3), M['face'], rotate=math.radians(-5)),
                               F.decal('bbrowL', bvh, (0.07, -0.5, 1.03), (0.07, 0.045), (2, 3), M['face'], mirror=True, rotate=math.radians(5))], 'brows')
    objs['expr_mouth_small'] = F.decal('expr_mouth_small', bvh, (0, -0.5, 0.875), (0.07, 0.07), (3, 3), M['face'])
    objs['expr_mouth_round'] = F.decal('expr_mouth_round', bvh, (0, -0.5, 0.875), (0.05, 0.05), (2, 1), M['face'])
    objs['face_blush'] = core.join([F.decal('bbR', bvh, (-0.115, -0.5, 0.905), (0.07, 0.045), (0, 2), M['face'], offset=0.001),
                                    F.decal('bbL', bvh, (0.115, -0.5, 0.905), (0.07, 0.045), (0, 2), M['face'], mirror=True, offset=0.001)], 'face_blush')
    arm = doubao_rig(objs)
    doubao_anims(arm)
    stats = {k: core.tri_count(v) for k, v in objs.items()}
    core.export_glb(out_path)
    return stats


def doubao_rig(objs):
    bones = [
        ('root', (0, 0, 0), (0, 0, 0.08), None),
        ('hips', (0, 0, 0.3), (0, 0, 0.55), 'root'),
        ('spine', (0, 0, 0.55), (0, 0, 0.78), 'hips'),
        ('head', (0, 0, 0.78), (0, 0, 1.18), 'spine'),
        ('eye.L', (0.07, -0.17, 0.96), (0.07, -0.2, 0.96), 'head'),
        ('eye.R', (-0.07, -0.17, 0.96), (-0.07, -0.2, 0.96), 'head'),
        ('arm.L', (0.2, 0, 0.7), (0.27, -0.02, 0.56), 'spine'),
        ('forearm.L', (0.27, -0.02, 0.56), (0.285, -0.03, 0.42), 'arm.L'),
        ('arm.R', (-0.2, 0, 0.7), (-0.27, -0.02, 0.56), 'spine'),
        ('forearm.R', (-0.27, -0.02, 0.56), (-0.285, -0.03, 0.42), 'arm.R'),
        ('leg.L', (0.1, 0, 0.3), (0.11, -0.005, 0.03), 'hips'),
        ('leg.R', (-0.1, 0, 0.3), (-0.11, -0.005, 0.03), 'hips'),
    ]
    arm = core.armature('rig_doubao', bones)
    segs = core.bone_segments(arm)
    co = core.verts_of(objs['body'])
    headp = smoothstep(0.76, 0.84, co[:, 2])
    armp = {s: ((np.abs(co[:, 0]) > 0.215) & (np.sign(co[:, 0]) == sg) & (co[:, 2] < 0.74)) for s, sg in (('L', 1), ('R', -1))}
    legp = {s: ((co[:, 2] < 0.26) & (np.sign(co[:, 0]) == sg)) for s, sg in (('L', 1), ('R', -1))}
    w = {'head': headp}
    for s in ('L', 'R'):
        cw = core.chain_weights(co, segs, [f'arm.{s}', f'forearm.{s}'], blend=0.3)
        w[f'arm.{s}'] = armp[s] * cw[f'arm.{s}']
        w[f'forearm.{s}'] = armp[s] * cw[f'forearm.{s}']
        w[f'leg.{s}'] = legp[s] * smoothstep(0.26, 0.18, co[:, 2])
    rest = np.clip(1 - sum(np.asarray(v, dtype=float) for v in w.values()), 0, 1)
    w['spine'] = rest * smoothstep(0.5, 0.62, co[:, 2])
    w['hips'] = rest * (1 - smoothstep(0.5, 0.62, co[:, 2]))
    core.bind(objs['body'], arm, {k: np.asarray(v, dtype=float) for k, v in w.items()})
    for k in ('hair', 'brows', 'expr_mouth_small', 'expr_mouth_round', 'face_blush'):
        core.bind(objs[k], arm, core.rigid(len(objs[k].data.vertices), 'head'))
    co = core.verts_of(objs['expr_eyes_open'])
    core.bind(objs['expr_eyes_open'], arm, {'eye.L': (co[:, 0] > 0).astype(float), 'eye.R': (co[:, 0] <= 0).astype(float)})
    return arm


def doubao_anims(arm):
    def idle(f, ph):
        b = math.sin(TAU * ph)
        return {'spine': {'rot': (0, 0, 3 * b)}, 'head': {'rot': (2 * b, 0, -3 * b)}, 'hips': {'scale': (1 + 0.01 * b, 1 + 0.01 * b, 1 - 0.01 * b)},
                'arm.L': {'rot': (0, 0, 3 * b)}, 'arm.R': {'rot': (0, 0, -3 * b)}}
    core.action(arm, 'idle', 90, idle)

    def walk(f, ph):
        a = math.sin(TAU * ph)
        return {'root': {'loc': (0, 0, 0.015 * abs(math.sin(TAU * ph)))}, 'hips': {'rot': (0, 7 * a, 0)}, 'spine': {'rot': (0, -4 * a, 0)},
                'leg.L': {'rot': (-20 * a, 0, 0)}, 'leg.R': {'rot': (20 * a, 0, 0)}, 'arm.L': {'rot': (15 * a, 0, 0)}, 'arm.R': {'rot': (-15 * a, 0, 0)},
                'head': {'rot': (0, -3 * a, 0)}}
    core.action(arm, 'walk', 30, walk)

    def stomp(f, ph):
        a = math.sin(TAU * 2 * ph)
        lift = max(0.0, a)
        return {'leg.R': {'rot': (-25 * lift, 0, 0)}, 'root': {'loc': (0, 0, -0.01 * max(0.0, -a))},
                'arm.L': {'rot': (-20, -30, 0)}, 'arm.R': {'rot': (-20, 30, 0)}, 'forearm.L': {'rot': (-60, 0, 0)}, 'forearm.R': {'rot': (-60, 0, 0)},
                'head': {'rot': (6, 0, 4 * a)}, 'spine': {'rot': (4, 0, 0)}}
    core.action(arm, 'stomp', 30, stomp)

    def knocked(f, ph):
        t = min(1.0, ph / 0.5)
        e = 1 - (1 - t) ** 3
        bounce = 0.02 * math.sin(math.pi * min(1.0, max(0.0, (ph - 0.5) / 0.2)))
        return {'root': {'rot': (-85 * e, 0, 10 * e), 'loc': (0, 0.18 * e, 0.24 * e + bounce)},
                'arm.L': {'rot': (0, -60 * e, 0)}, 'arm.R': {'rot': (0, 60 * e, 0)},
                'leg.L': {'rot': (-30 * e, 0, 10 * e)}, 'leg.R': {'rot': (-20 * e, 0, -10 * e)}, 'head': {'rot': (-10 * e, 0, 15 * e)}}
    core.action(arm, 'knocked', 45, knocked, loop=False)

    def blink(f, ph):
        kk = 1 - math.sin(math.pi * ph) ** 0.6 * 0.92
        return {'eye.L': {'scale': (1, 1, kk)}, 'eye.R': {'scale': (1, 1, kk)}}
    core.action(arm, 'blink', 8, blink, loop=False)
    core.finish_actions(arm, 'idle')


def build(out_path):
    d = os.path.dirname(out_path)
    stats = {}
    for name, fn in (('dragon', build_dragon), ('doubao', build_doubao)):
        st = fn(os.path.join(d, f'{name}.glb'))
        stats.update({f'{name}.{k}': v for k, v in st.items()})
    return stats
