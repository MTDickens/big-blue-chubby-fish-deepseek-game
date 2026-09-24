"""蓝色大肥鱼 — the chibi maid whale girl (main character).

Built procedurally from the video references (EP1 beach ending / overpass / EP2 close-up):
~0.9 m tall, ~2.5 heads, navy->sky-blue wavy hair with an ahoge, white ruffled maid headband with
light-blue bows, navy whale-fin ears with white fluff, navy maid dress + white apron with a whale
emblem, white frilled socks, navy Mary Janes, and a big navy whale tail with a pale underside.
"""
import math
import os

import bpy  # noqa: F401
import numpy as np

from .. import core, face as F, shapes as S

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', 'textures', 'face_bluefish.png'))

P = dict(
    skin='#fddccb', skin_shade='#f1ae9f', skin_line='#c98476',
    hair_root='#1f3272', hair_mid='#2b4f9f', hair_tip='#5192dc', hair_inner='#142050',
    dress='#1c2654', dress_band='#2b3b78', dress_shade='#0c1233',
    white='#f7f8fd', white_shade='#c3cbe6', white_line='#8e98c0',
    fin='#1d2c62', fin_shade='#0c1438',
    tail_top='#1d2e66', tail_under='#cbd6ee',
    shoe='#1b2349', gold='#e3b44f', bow='#4f93ea', silver='#dde2ee',
)

HEAD_C = np.array([0.0, 0.0, 0.715])
HEAD_R = np.array([0.150, 0.142, 0.150])


# ----------------------------------------------------------------------------- helpers

def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mix(a, b, t):
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


def lin(h):
    return np.array(core.hexc(h)[:3])


def head_dir(az, el):
    """az: 0 = front (-Y), 90 = character's left (+X); el: 0 = equator, 90 = top."""
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])


def head_pt(az, el, off=0.0, radii=HEAD_R, center=HEAD_C):
    d = head_dir(az, el)
    r = 1.0 / math.sqrt((d[0] / radii[0]) ** 2 + (d[1] / radii[1]) ** 2 + (d[2] / radii[2]) ** 2)
    return center + d * (r + off)


def width_profile(w, root=0.75, peak=0.3, tip_start=0.55, blunt=0.0):
    def f(s):
        s = np.asarray(s, dtype=float)
        grow = root + (1 - root) * smoothstep(0, peak, s)
        taper = (1 - smoothstep(tip_start, 1.0, s)) ** 0.9
        return w * grow * (blunt + (1 - blunt) * taper) + 1e-4
    return f


def clump(path, w, th, n=22, up=None, prof=None, tip=True, root=0.75, tip_start=0.55, twist=0.0, blunt=0.0):
    prof = S.prof_lens(8, 0.8) if prof is None else prof
    if up is None:
        p0 = np.asarray(path[0], dtype=float)
        up = (p0 - HEAD_C) / np.linalg.norm(p0 - HEAD_C)
    return S.sweep(path, n=n, profile=prof, width=width_profile(w, root, 0.3, tip_start, blunt),
                   thick=width_profile(th, 0.9, 0.3, min(tip_start + 0.1, 0.95), blunt), up=up, tip1=tip, cap0=True, twist=twist)


def ruffle_ring(center_z, r_in, r_out, drop, pleats, amp, n=None, z_axis=None, thick=0.003, name='ruffle', mat=None):
    """Horizontal gathered ruffle (collars, petticoats): annulus from r_in to r_out, dropping by `drop`."""
    n = n or pleats * 5
    th = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rows = 4
    verts, uvs = [], []
    for j in range(rows):
        v = j / (rows - 1)
        for k in range(n):
            r = r_in + (r_out - r_in) * v
            r *= 1 + amp * v * math.sin(pleats * th[k])
            z = center_z - drop * v ** 1.3 + amp * 0.3 * v * math.cos(pleats * th[k]) * r_out
            verts.append((r * math.cos(th[k]), r * math.sin(th[k]), z))
            uvs.append((k / n, v))
    faces = []
    for j in range(rows - 1):
        for k in range(n):
            a = j * n + k
            b = j * n + (k + 1) % n
            faces.append((a, b, b + n, a + n))
    o = S.obj(name, (np.array(verts), faces, np.array(uvs)), mat)
    return core.solidify(o, thick, 0.0)


def pleated_strip(path_pts, n, height, pleats, amp, up_fn, thick=0.0025, name='frill', mat=None, edge_wave=0.12, closed=False):
    """A gathered frill standing out from a path. up_fn(P, T) -> outward direction per sample."""
    P = S.catmull_rom(path_pts, n, closed=closed)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    rows = 3
    verts, uvs = [], []
    for i in range(n):
        s = i / (n - 1 if not closed else n)
        out = np.asarray(up_fn(P[i], T[i]), dtype=float)
        out = out - (out @ T[i]) * T[i]
        out /= np.linalg.norm(out)
        side = np.cross(T[i], out)
        hmax = height * (1 + edge_wave * math.cos(2 * math.pi * pleats * s))
        for j in range(rows):
            v = j / (rows - 1)
            p = P[i] + out * (hmax * v) + side * (amp * math.sin(2 * math.pi * pleats * s) * (0.35 + 0.65 * v))
            verts.append(p)
            uvs.append((s, v))
    faces = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        for j in range(rows - 1):
            a = i * rows + j
            b = ((i + 1) % n) * rows + j
            faces.append((a, b, b + 1, a + 1))
    o = S.obj(name, (np.array(verts), faces, np.array(uvs)), mat, fix_normals=False)
    return core.solidify(o, thick, 0.0)


def bow(center, size, mat, knot_mat=None, facing=(0, -1, 0), roll=0.0, tails=True, name='bow'):
    """Ribbon bow in the plane facing `facing`."""
    f = np.asarray(facing, dtype=float)
    f /= np.linalg.norm(f)
    upv = np.array([0, 0, 1.0])
    right = np.cross(f, upv)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0, 0])
    right /= np.linalg.norm(right)
    upv = np.cross(right, f)
    c, s = math.cos(roll), math.sin(roll)
    right, upv = right * c + upv * s, upv * c - right * s
    C = np.asarray(center, dtype=float)
    parts = []
    for side in (-1, 1):
        loop = [C + right * side * size * x + upv * size * y + f * size * z for x, y, z in
                [(0.05, 0.05, 0), (0.45, 0.42, -0.04), (0.95, 0.36, -0.1), (1.0, -0.1, -0.1), (0.6, -0.34, -0.05), (0.08, -0.06, 0)]]
        parts.append(S.sweep(loop, n=26, profile=S.prof_ribbon(10, 0.28), width=size * 0.2, thick=size * 0.06,
                             up=f, closed=True))
        if tails:
            tail = [C + right * side * size * x + upv * size * y + f * size * 0.02 for x, y in
                    [(0.05, -0.08), (0.22, -0.45), (0.38, -0.85)]]
            parts.append(S.sweep(tail, n=10, profile=S.prof_ribbon(8, 0.25), width=[size * 0.14, size * 0.17],
                                 thick=size * 0.05, up=f, cap0=True, cap1=True))
    geo = S.merge_geos(*parts)
    o = S.obj(name, geo, mat, fix_normals=False)
    knot = S.obj(name + '_knot', S.transform_geo(S.sphere((size * 0.2, size * 0.14, size * 0.18), 16, 10), loc=C), knot_mat or mat)
    return core.join([o, knot], name)


# ----------------------------------------------------------------------------- build

def build(out_path, with_anims=True):
    core.reset()
    core.clear_material_cache()
    M = dict(
        skin=core.material('toon_skin', P['skin'], extras={'shade': P['skin_shade'], 'outline': 0.0012, 'outlineColor': P['skin_line'], 'rim': '#ffd9cc', 'rimStrength': 0.15}),
        hair=core.material('toon_hair', '#ffffff', extras={'shade': '#8f9bd6', 'outline': 0.0016, 'outlineColor': '#0b1333', 'rim': '#9cc8ff', 'rimStrength': 0.35, 'toony': 0.9}),
        dress=core.material('toon_dress', P['dress'], extras={'shade': P['dress_shade'], 'outline': 0.0016, 'outlineColor': '#060a1e', 'rim': '#6f8fd8', 'rimStrength': 0.3}),
        white=core.material('toon_white', P['white'], extras={'shade': P['white_shade'], 'outline': 0.0011, 'outlineColor': P['white_line'], 'rimStrength': 0.1}),
        fin=core.material('toon_fin', P['fin'], extras={'shade': P['fin_shade'], 'outline': 0.0015, 'outlineColor': '#060a1e', 'rim': '#7aa2ff', 'rimStrength': 0.35}),
        tail=core.material('toon_tail', '#ffffff', extras={'shade': '#8d96cc', 'outline': 0.0018, 'outlineColor': '#070b22', 'rim': '#8fb4ff', 'rimStrength': 0.3}),
        shoe=core.material('toon_shoe', P['shoe'], extras={'shade': '#0a0e26', 'outline': 0.0012, 'outlineColor': '#05071a', 'rim': '#8fa8ff', 'rimStrength': 0.55, 'rimPower': 2.5}),
        gold=core.material('toon_gold', P['gold'], extras={'shade': '#a8742a', 'outline': 0.0008, 'outlineColor': '#6b4715', 'rim': '#fff2c2', 'rimStrength': 0.4}),
        bow=core.material('toon_bow', P['bow'], extras={'shade': '#2c5cb8', 'outline': 0.001, 'outlineColor': '#173778'}),
        silver=core.material('toon_silver', P['silver'], extras={'shade': '#9aa3bb', 'outline': 0.0006}),
        face=core.material('face_bluefish', '#ffffff', image=TEX, alpha='image'),
    )

    parts = {}

    # ---------------- head
    def jaw(p):
        p = p.copy()
        low = np.clip(-p[:, 2], 0, 1)
        front = np.clip(-p[:, 1], 0, 1)
        p[:, 0] *= 1 - 0.13 * low ** 1.5 + 0.03 * front * np.exp(-((p[:, 2] + 0.25) / 0.3) ** 2)
        p[:, 1] *= 1 - 0.06 * low ** 1.5
        p[:, 1] -= 0.04 * front * low * (1 - low)  # soft chin/cheek volume forward
        p[:, 2] *= 1 - 0.02 * low
        return p
    head = S.obj('head', S.transform_geo(S.sphere(HEAD_R, 48, 32, deform=jaw), loc=HEAD_C), M['skin'])
    neck = S.obj('neck', S.sweep([(0, 0.01, 0.53), (0, 0.012, 0.61)], n=6, profile=S.prof_circle(16), width=0.029, cap0=False, cap1=False), M['skin'])

    # ---------------- face decals (projected along +Y onto the head)
    bvh = F.surface_bvh(head)
    EYE = (0.061, 0.688)
    eyes_open = [F.decal('eyeR', bvh, (-EYE[0], -0.2, EYE[1]), (0.082, 0.096), (0, 0), M['face']),
                 F.decal('eyeL', bvh, (EYE[0], -0.2, EYE[1]), (0.082, 0.096), (0, 0), M['face'], mirror=True)]
    eyes_happy = [F.decal('eyeRh', bvh, (-EYE[0], -0.2, EYE[1] - 0.004), (0.082, 0.09), (1, 0), M['face']),
                  F.decal('eyeLh', bvh, (EYE[0], -0.2, EYE[1] - 0.004), (0.082, 0.09), (1, 0), M['face'], mirror=True)]
    mouth_open = F.decal('mouth_open', bvh, (0, -0.2, 0.628), (0.058, 0.058), (0, 1), M['face'])
    mouth_small = F.decal('mouth_small', bvh, (0, -0.2, 0.632), (0.05, 0.05), (1, 1), M['face'])
    mouth_o = F.decal('mouth_round', bvh, (0, -0.2, 0.632), (0.045, 0.045), (2, 1), M['face'])
    mouth_cat = F.decal('mouth_cat', bvh, (0, -0.2, 0.634), (0.056, 0.056), (3, 1), M['face'])
    blush = [F.decal('blushR', bvh, (-0.09, -0.2, 0.648), (0.068, 0.042), (0, 2), M['face'], offset=0.0008),
             F.decal('blushL', bvh, (0.09, -0.2, 0.648), (0.068, 0.042), (0, 2), M['face'], mirror=True, offset=0.0008)]
    brows = []

    # ---------------- hair
    hair_geos = []
    # scalp cap with a face opening
    cap_r = HEAD_R + np.array([0.012, 0.012, 0.012])
    V, Fc, UV = S.sphere(cap_r, 40, 26)
    V = V + HEAD_C + np.array([0, 0.004, 0.004])
    keep = []
    for f in Fc:
        cxyz = V[list(f)].mean(axis=0) - HEAD_C
        d = cxyz / np.linalg.norm(cxyz)
        az = math.degrees(math.atan2(d[0], -d[1]))
        el = math.degrees(math.asin(d[2]))
        if abs(az) < 72 and el < 42:
            continue
        if el < -35 and abs(az) < 120:
            continue
        keep.append(f)
    hair_geos.append((V, keep, UV))

    # bangs: layered soft clumps from the crown front down to the eyelids
    bang_specs = [  # (az_root, az_tip, el_tip, width, off_tip, curl)
        (-66, -76, 4, 0.036, 0.024, -1), (-50, -58, 10, 0.04, 0.02, -1), (-36, -41, 2, 0.04, 0.019, -1),
        (-22, -24, 9, 0.038, 0.018, 0), (-9, -8, -1, 0.034, 0.018, 1), (3, 5, -6, 0.022, 0.02, 0),
        (13, 15, 3, 0.036, 0.018, -1), (26, 30, 10, 0.04, 0.018, 1), (40, 46, 1, 0.04, 0.019, 1),
        (54, 62, 9, 0.04, 0.02, 1), (68, 78, 3, 0.036, 0.024, 1),
    ]
    for azr, azt, elt, w, offt, curl in bang_specs:
        pts = [head_pt(azr + (azt - azr) * t ** 1.3, 66 + (elt - 66) * t ** 0.8, off=0.008 + (offt - 0.008) * t) for t in np.linspace(0, 1, 7)]
        tipdir = head_dir(azt + curl * 8, elt - 12)
        pts.append(pts[-1] + (tipdir - head_dir(azt, elt)) * 0.1 + np.array([0, -0.003, -0.01]))
        hair_geos.append(clump(pts, w, 0.014, n=18, tip_start=0.62, root=0.7))
    # side locks framing the face down to the chest (wavy)
    for side in (-1, 1):
        for k, (azr, width, zend, xo, yo) in enumerate([(66, 0.042, 0.46, 0.0, 0.0), (82, 0.046, 0.43, 0.03, 0.03)]):
            p0 = head_pt(side * azr, 40, 0.012)
            p1 = head_pt(side * (azr + 4), 8, 0.024)
            p2 = head_pt(side * (azr + 8), -20, 0.036) + np.array([side * 0.01, -0.004, 0])
            p3 = np.array([side * (0.19 + xo), -0.07 + yo, 0.575])
            p4 = np.array([side * (0.205 + xo), -0.066 + yo, 0.525])
            p5 = np.array([side * (0.19 + xo), -0.07 + yo, zend + 0.045])
            p6 = np.array([side * (0.205 + xo), -0.065 + yo, zend])
            hair_geos.append(clump([p0, p1, p2, p3, p4, p5, p6], width, 0.022, n=28, tip_start=0.72, blunt=0.12))
    # side volume puffs at cheek level (makes the wide silhouette of the reference)
    for side in (-1, 1):
        for azr, zend, flare in [(96, 0.47, 0.11), (112, 0.45, 0.12)]:
            pts = [head_pt(side * azr, el, off=0.016 + 0.02 * (1 - (el + 20) / 75)) for el in (55, 30, 5, -20)]
            b = pts[-1]
            pts += [b + np.array([side * 0.045, 0.01, -0.06]), b + np.array([side * flare, 0.02, -0.12]),
                    b + np.array([side * (flare + 0.005), 0.03, -0.2]), np.array([side * (0.2 + flare * 0.3), b[1] + 0.03, zend])]
            hair_geos.append(clump(pts, 0.07, 0.03, n=26, tip_start=0.78, root=0.8, blunt=0.15))
    # long wavy back hair: broad locks with coherent waves and softly curled tips, two layers
    rng = np.random.default_rng(11)
    for layer, (azs, zmid, fl, w0, amp0) in enumerate([
            (np.linspace(100, 260, 13), 0.30, 0.13, 0.098, 0.03),
            (np.linspace(120, 240, 8), 0.39, 0.09, 0.1, 0.024)]):
        for i, az in enumerate(azs):
            side = math.sin(math.radians(az))
            root_el = 62 - layer * 10 + rng.uniform(-3, 3)
            z_end = zmid + 0.045 * abs(side) + rng.uniform(-0.012, 0.012)
            flare = fl * (0.85 + 0.45 * abs(side))
            pts = [head_pt(az, el, off=0.014 + layer * 0.008 + 0.022 * (1 - (el + 8) / (root_el + 8))) for el in np.linspace(root_el, -8, 6)]
            base = pts[-1]
            radial = np.array([base[0], base[1], 0.0])
            radial /= np.linalg.norm(radial)
            tangent = np.cross([0, 0, 1.0], radial)
            ph = 0.9 + 0.55 * i + layer * 0.8
            zs = np.linspace(base[2] - 0.05, z_end, 8)
            for k, z in enumerate(zs):
                t = (k + 1) / len(zs)
                wave = math.sin(ph + t * 2 * np.pi * 1.35)
                p = base + radial * (flare * t ** 0.75 + 0.35 * amp0 * math.cos(ph + t * 2 * np.pi * 1.35)) + tangent * amp0 * wave
                p[2] = z
                pts.append(p)
            # soft curl at the tip
            last, prev = pts[-1], pts[-2]
            d = (last - prev) / np.linalg.norm(last - prev)
            curl = radial * 0.022 + np.array([0, 0, 0.012]) + tangent * 0.006 * (1 if i % 2 else -1)
            pts.append(last + d * 0.018 + curl * 0.6)
            w = w0 + rng.uniform(-0.006, 0.006)
            hair_geos.append(clump(pts, w, 0.032, n=30, tip_start=0.8, root=0.8, blunt=0.18))
    # inner curtain to hide gaps between back strands
    th0, th1 = math.radians(15), math.radians(165)
    prof = [(0.15, 0.68), (0.168, 0.58), (0.19, 0.48), (0.21, 0.40), (0.225, 0.34)]
    Vc, Fcur, UVc = S.lathe(prof, n_seg=40, theta0=th0, theta_len=th1 - th0)
    hair_geos.append((Vc + np.array([0, 0.012, 0]), Fcur, UVc))
    # ahoge
    ah = [(0.0, 0.03, 0.872), (0.004, 0.012, 0.935), (0.0, -0.035, 0.978), (-0.004, -0.078, 0.965), (-0.002, -0.084, 0.935)]
    hair_geos.append(S.sweep(ah, n=20, profile=S.prof_lens(8, 0.7), width=width_profile(0.013, 0.9, 0.2, 0.55),
                             thick=0.006, up=(1, 0, 0), tip1=True))
    hair = S.obj('hair', S.merge_geos(*hair_geos), M['hair'], fix_normals=False)
    S.recalc_normals(hair)

    def hair_colors(co):
        z = co[:, 2]
        t = smoothstep(0.86, 0.30, z)
        c = mix(lin(P['hair_root']), lin(P['hair_mid']), smoothstep(0, 0.35, t)[:, None])
        c = mix(c, lin(P['hair_tip']), smoothstep(0.4, 1.0, t)[:, None] ** 1.2)
        # inner layers (close to the body axis at the back) a little darker
        r = np.hypot(co[:, 0], co[:, 1] - 0.0)
        inner = (1 - smoothstep(0.15, 0.2, r)) * (z < 0.62)
        c = mix(c, c * 0.85, inner[:, None])
        return c
    core.paint(hair, hair_colors)

    # ---------------- headdress: ruffled band over the crown + bows
    tilt = math.radians(22)
    arc = []
    for t in np.linspace(-1, 1, 25):
        a = t * math.radians(98)
        d = np.array([math.sin(a), -math.sin(tilt) * math.cos(a), math.cos(a) * math.cos(tilt)])
        r = 1.0 / math.sqrt((d[0] / (HEAD_R[0] + 0.03)) ** 2 + (d[1] / (HEAD_R[1] + 0.03)) ** 2 + (d[2] / (HEAD_R[2] + 0.028)) ** 2)
        arc.append(HEAD_C + np.array([0, 0.005, 0.004]) + d * r)
    arc = np.array(arc)
    outward = lambda p, t: (p - HEAD_C) / np.linalg.norm(p - HEAD_C)
    band = S.obj('band', S.sweep(arc, n=60, profile=S.prof_ribbon(8, 0.3), width=0.011, thick=0.005, up=(0, -math.sin(tilt), math.cos(tilt))), M['white'])
    frill = pleated_strip(arc, 120, 0.032, 22, 0.006, outward, thick=0.0025, name='frill', mat=M['white'])
    lace = pleated_strip(arc, 110, 0.012, 22, 0.004,
                         lambda p, t: -((p - HEAD_C) / np.linalg.norm(p - HEAD_C)) * 0.3 + np.array([0, -1.0, -0.4]),
                         thick=0.002, name='lace', mat=M['white'], edge_wave=0.2)
    bows_head = [bow(head_pt(s * 80, 26, 0.04), 0.046, M['bow'], M['white'],
                     facing=(s * 0.75, -0.66, 0.1), roll=s * 0.25, name=f'hbow{s}') for s in (-1, 1)]
    headdress = core.join([band, frill, lace] + bows_head, 'headdress')

    # ---------------- whale-fin ears with white fluff (stick out past the hair like in the reference)
    fin_outline = [(0.0, 0.03), (0.04, 0.042), (0.08, 0.04), (0.114, 0.026), (0.136, 0.004), (0.13, -0.014),
                   (0.098, -0.024), (0.06, -0.03), (0.022, -0.035), (0.0, -0.032)]
    fins = []
    for side in (-1, 1):
        ol = [(x * side, z) for x, z in fin_outline]
        if side < 0:
            ol = ol[::-1]
        fn = S.outline_obj(f'fin{side}', ol, M['fin'], plane='XZ', thickness=0.016, subdiv=2, pillow=0.9)
        fluff_path = [(side * x, 0.0, z) for x, z in [(0.004, -0.03), (0.035, -0.032), (0.07, -0.027), (0.105, -0.017), (0.128, -0.006)]]
        prof = np.array([(math.cos(a) * (1 + 0.18 * math.sin(7 * a)), math.sin(a) * (1 + 0.18 * math.sin(7 * a))) for a in np.linspace(0, 2 * np.pi, 20, endpoint=False)])
        fl = S.obj(f'fluff{side}', S.sweep(fluff_path, n=24, profile=prof, width=[0.011, 0.013, 0.011, 0.007, 0.002], thick=[0.015, 0.016, 0.013, 0.009, 0.003], up=(0, -1, 0)), M['white'])
        f = core.join([fn, fl], f'fin_{"L" if side > 0 else "R"}')
        f.rotation_euler = (0, math.radians(10 * side), math.radians(-14 * side))
        f.location = (side * 0.172, 0.008, 0.712)
        bpy.context.view_layer.update()
        core.apply_transform(f)
        fins.append(f)

    # ---------------- torso, collar, bow, apron bib
    torso_prof = [(0.056, 0.40), (0.064, 0.44), (0.068, 0.48), (0.066, 0.51), (0.058, 0.535), (0.044, 0.552), (0.028, 0.562)]
    torso = S.obj('torso', S.lathe(torso_prof, 36, mod=lambda th, t: np.outer(1 - 0.18 * np.sin(th) ** 2, np.ones(len(t)))), M['dress'])
    collar = ruffle_ring(0.556, 0.03, 0.064, 0.012, 16, 0.08, name='collar', mat=M['white'])
    neckbow = bow((0, -0.062, 0.542), 0.024, M['dress'], M['silver'], facing=(0, -1, 0), name='neckbow')
    # apron bib: white panel on the chest front with frilled straps
    bib_pts = []
    bib = S.obj('bib', S.lathe([(0.0695, 0.43), (0.071, 0.47), (0.0685, 0.505), (0.06, 0.53)], 16,
                               theta0=math.radians(245), theta_len=math.radians(50),
                               mod=lambda th, t: np.outer(1 - 0.18 * np.sin(th) ** 2, np.ones(len(t))) + 0.004), M['white'])
    straps = []
    for side in (-1, 1):
        a0 = math.radians(270 + side * 26)
        path = []
        for z, r in [(0.43, 0.071), (0.47, 0.073), (0.505, 0.07), (0.53, 0.062), (0.548, 0.05)]:
            rr = r * (1 - 0.18 * math.sin(a0) ** 2) + 0.004
            path.append((rr * math.cos(a0), rr * math.sin(a0), z))
        path.append((side * 0.04, 0.02, 0.556))
        straps.append(pleated_strip(path, 60, 0.014, 9, 0.003, lambda p, t, s=side: np.array([s * 1.0, -0.4, 0.0]), thick=0.002, name=f'strap{side}', mat=M['white']))
    body = core.join([torso, collar, neckbow, bib] + straps, 'body')

    # ---------------- skirt, petticoat, apron skirt, bows
    skirt_prof = [(0.066, 0.43), (0.08, 0.415), (0.108, 0.39), (0.14, 0.35), (0.162, 0.315), (0.176, 0.29), (0.182, 0.278), (0.186, 0.268), (0.18, 0.262)]
    def folds(th, t):
        return 1 + np.outer(np.sin(th * 9) * 0.035 + np.sin(th * 4 + 1) * 0.012, t ** 1.4) - np.outer(0.08 * np.sin(th) ** 2 * 0 , t)
    skirt = S.obj('skirt', S.lathe(skirt_prof, 72, mod=folds), M['dress'])

    def skirt_colors(co):
        z = co[:, 2]
        base = lin(P['dress'])
        band = lin(P['dress_band'])
        c = np.tile(np.ones(3), (len(co), 1))
        t = ((z > 0.268) & (z < 0.30)).astype(float)
        c = mix(c, band / np.maximum(base, 1e-3), t[:, None] * 0.6)
        return np.clip(c, 0, 4)
    core.paint(skirt, skirt_colors)
    petti1 = ruffle_ring(0.285, 0.165, 0.198, 0.04, 30, 0.07, name='petti1', mat=M['white'])
    petti2 = ruffle_ring(0.258, 0.17, 0.205, 0.036, 34, 0.08, name='petti2', mat=M['white'])
    apron_prof = [(0.071, 0.425), (0.085, 0.405), (0.112, 0.38), (0.14, 0.345), (0.158, 0.315), (0.164, 0.305)]
    apron = S.obj('apron', S.lathe([(r + 0.006, z) for r, z in apron_prof], 30, theta0=math.radians(270 - 52), theta_len=math.radians(104),
                                   mod=lambda th, t: 1 + np.outer(np.sin(th * 9) * 0.035, np.array(t) ** 1.4)), M['white'])
    apron_edge = []
    for k in range(31):
        a = math.radians(270 - 52 + 104 * k / 30)
        r = (0.164 + 0.006) * (1 + math.sin(a * 9) * 0.035)
        apron_edge.append((r * math.cos(a), r * math.sin(a), 0.305))
    apron_frill = pleated_strip(apron_edge, 120, 0.03, 16, 0.005, lambda p, t: np.array([p[0] * 0.3, p[1] * 0.3, -1.0]), thick=0.0022, name='apron_frill', mat=M['white'])
    side_edges = []
    for s in (-1, 1):
        a = math.radians(270 + s * 52)
        path = []
        for r, z in apron_prof:
            rr = (r + 0.006) * (1 + math.sin(a * 9) * 0.035 * ((0.425 - z) / 0.12) ** 1.4)
            path.append((rr * math.cos(a), rr * math.sin(a), z))
        side_edges.append(pleated_strip(path, 50, 0.013, 7, 0.003, lambda p, t, s=s: np.array([s * 1.0, 0.2, 0.0]), thick=0.002, name=f'apron_side{s}', mat=M['white']))
    emblem = F.decal('emblem', F.surface_bvh(apron), (0, -0.3, 0.352), (0.075, 0.075), (2, 2), M['face'], offset=0.0012)
    gold_bows = [bow((s * 0.118, -0.128, 0.328), 0.017, M['gold'], M['dress'], facing=(s * 0.55, -0.83, 0.1), name=f'gbow{s}') for s in (-1, 1)]
    back_bow = bow((0, 0.082, 0.425), 0.038, M['white'], facing=(0, 1, 0), name='backbow')
    skirt_all = core.join([skirt, petti1, petti2, apron, apron_frill] + side_edges + gold_bows + [back_bow], 'skirt')

    # ---------------- arms (A-pose), cuffs, hands
    arms = []
    for side in (-1, 1):
        sh = np.array([side * 0.07, 0.0, 0.528])
        el = np.array([side * 0.128, -0.004, 0.445])
        wr = np.array([side * 0.162, -0.012, 0.378])
        sleeve = S.obj(f'sleeve{side}', S.sweep([sh, sh * 0.5 + el * 0.5 + np.array([side * 0.006, 0, 0.004]), el, wr], n=20,
                                                 profile=S.prof_circle(16), width=[0.03, 0.036, 0.03, 0.026, 0.028], cap0=True, cap1=True), M['dress'])
        d = (wr - el) / np.linalg.norm(wr - el)
        cuff_prof = np.array([(math.cos(a) * (1 + 0.1 * math.sin(14 * a)), math.sin(a) * (1 + 0.1 * math.sin(14 * a))) for a in np.linspace(0, 2 * np.pi, 42, endpoint=False)])
        cuff = S.obj(f'cuff{side}', S.sweep([wr - d * 0.004, wr + d * 0.006, wr + d * 0.014], n=5, profile=cuff_prof, width=[0.029, 0.033, 0.031],
                                             up=(0, -1, 0)), M['white'])
        hc = wr + d * 0.03
        hand = S.obj(f'hand{side}', S.transform_geo(S.sphere((0.019, 0.016, 0.024), 20, 14), loc=hc,
                                                    rot=(0, -side * 25, 0)), M['skin'])
        thumb = S.obj(f'thumb{side}', S.transform_geo(S.sphere((0.007, 0.007, 0.011), 12, 8), loc=hc + np.array([-side * 0.004, -0.014, 0.004]),
                                                      rot=(20, 0, 0)), M['skin'])
        cuff_btn = S.obj(f'btn{side}', S.transform_geo(S.sphere((0.004, 0.004, 0.004), 10, 6), loc=el * 0.35 + wr * 0.65 + np.array([side * 0.004, -0.026, 0])), M['gold'])
        arms.append(core.join([sleeve, cuff, hand, thumb, cuff_btn], f'arm_{"L" if side > 0 else "R"}'))

    # ---------------- legs, socks, shoes
    legs = []
    for side in (-1, 1):
        x = side * 0.044
        leg = S.obj(f'leg{side}', S.sweep([(x, 0.0, 0.36), (x * 1.02, -0.004, 0.24), (x * 1.03, -0.004, 0.15), (x * 1.03, 0.0, 0.07)], n=24,
                                          profile=S.prof_circle(16), width=[0.038, 0.034, 0.03, 0.027], cap0=True, cap1=True), M['skin'])

        def sock_col(co):
            t = smoothstep(0.128, 0.122, co[:, 2])
            skin_to_white = mix(np.ones(3), lin(P['white']) / lin(P['skin']), t[:, None])
            return skin_to_white
        core.paint(leg, sock_col)
        sock_prof = np.array([(math.cos(a) * (1 + 0.12 * math.sin(12 * a)), math.sin(a) * (1 + 0.12 * math.sin(12 * a))) for a in np.linspace(0, 2 * np.pi, 36, endpoint=False)])
        sock_top = S.obj(f'socktop{side}', S.sweep([(x * 1.03, -0.002, 0.108), (x * 1.03, -0.002, 0.121), (x * 1.03, -0.002, 0.134)], n=4,
                                                   profile=sock_prof, width=[0.03, 0.035, 0.032], up=(0, -1, 0)), M['white'])
        shoe = S.obj(f'shoe{side}', S.transform_geo(S.sphere((0.032, 0.056, 0.03), 28, 16,
                                                             deform=lambda p: np.stack([p[:, 0], p[:, 1], np.where(p[:, 2] < -0.35, -0.35 - (p[:, 2] + 0.35) * 0.25, p[:, 2])], 1)),
                                                   loc=(x * 1.05, -0.02, 0.03)), M['shoe'])
        strap = S.obj(f'strap{side}', S.sweep([(x * 1.05 - 0.03, -0.02, 0.03), (x * 1.05, -0.028, 0.058), (x * 1.05 + 0.03, -0.02, 0.03)], n=16,
                                              profile=S.prof_ribbon(8, 0.3), width=0.006, thick=0.002, up=(0, -1, 0.3)), M['shoe'])
        buckle = S.obj(f'buckle{side}', S.transform_geo(S.sphere((0.004, 0.003, 0.004), 10, 6), loc=(x * 1.05 + side * 0.028, -0.024, 0.036)), M['gold'])
        legs.append(core.join([leg, sock_top, shoe, strap, buckle], f'leg_{"L" if side > 0 else "R"}'))

    # ---------------- whale tail + upright fluke
    tail_path = [(0.0, 0.05, 0.37), (0.07, 0.12, 0.30), (0.16, 0.15, 0.22), (0.26, 0.13, 0.18), (0.34, 0.09, 0.18), (0.40, 0.06, 0.205)]
    tail = S.obj('tail', S.sweep(tail_path, n=40, profile=S.prof_circle(18), width=[0.064, 0.06, 0.05, 0.038, 0.026, 0.016],
                                 thick=[0.06, 0.056, 0.046, 0.034, 0.022, 0.013], up=(0, 0, 1), cap0=True, cap1=True), M['tail'])
    fl_out = [(0.0, 0.016), (0.04, 0.066), (0.09, 0.112), (0.142, 0.13), (0.122, 0.082), (0.098, 0.034), (0.106, 0.0),
              (0.098, -0.034), (0.122, -0.082), (0.142, -0.13), (0.09, -0.112), (0.04, -0.066), (0.0, -0.016)]
    fluke = S.outline_obj('fluke', fl_out, M['tail'], plane='XZ', thickness=0.014, subdiv=2, pillow=0.8)
    end = np.array(tail_path[-1])
    tdir = end - np.array(tail_path[-2])
    tdir /= np.linalg.norm(tdir)
    yaw = math.degrees(math.atan2(tdir[1], tdir[0]))
    pitch = math.degrees(math.asin(tdir[2]))
    # fluke lies in the vertical plane containing the tail direction (reads like the video from the front)
    fluke.rotation_euler = (0, math.radians(-pitch), math.radians(yaw))
    fluke.location = tuple(end - tdir * 0.014)
    bpy.context.view_layer.update()
    core.apply_transform(fluke)
    tail_all = core.join([tail, fluke], 'tail')
    me = tail_all.data

    def tail_colors(co):
        n = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get('normal', n)
        n = n.reshape(-1, 3)
        under = smoothstep(0.1, -0.6, n[:, 2]) * (1 - smoothstep(0.30, 0.36, co[:, 0]) * 0.7)
        return mix(lin(P['tail_top']), lin(P['tail_under']), under[:, None])
    core.paint(tail_all, tail_colors)

    # ---------------- groups for export
    face_group = core.join(eyes_open, 'expr_eyes_open')
    happy_group = core.join(eyes_happy, 'expr_eyes_happy')
    mouth_open.name = 'expr_mouth_open'
    mouth_small.name = 'expr_mouth_small'
    mouth_o.name = 'expr_mouth_round'
    mouth_cat.name = 'expr_mouth_cat'
    blush_group = core.join(blush, 'face_blush')
    head_all = core.join([head, neck], 'head')

    objs = dict(head=head_all, hair=hair, headdress=headdress, fin_L=fins[1], fin_R=fins[0], body=body, skirt=skirt_all,
                arm_L=arms[1], arm_R=arms[0], leg_L=legs[1], leg_R=legs[0], tail=tail_all,
                expr_eyes_open=face_group, expr_eyes_happy=happy_group, expr_mouth_open=mouth_open,
                expr_mouth_small=mouth_small, expr_mouth_round=mouth_o, expr_mouth_cat=mouth_cat, face_blush=blush_group,
                emblem=emblem)

    arm = rig(objs, tail_path)
    if with_anims:
        from . import bluefish_anims
        bluefish_anims.add(arm)
    stats = {k: core.tri_count(v) for k, v in objs.items()}
    core.export_glb(out_path)
    return stats


# ----------------------------------------------------------------------------- rig

def rig(objs, tail_path):
    tp = [np.array(p) for p in tail_path]
    bones = [
        ('root', (0, 0, 0), (0, 0, 0.08), None),
        ('hips', (0, 0, 0.38), (0, 0, 0.45), 'root'),
        ('spine', (0, 0, 0.45), (0, 0, 0.50), 'hips'),
        ('chest', (0, 0, 0.50), (0, 0, 0.555), 'spine'),
        ('neck', (0, 0, 0.555), (0, 0, 0.60), 'chest'),
        ('head', (0, 0, 0.60), (0, 0, 0.86), 'neck'),
        ('eye.L', (0.058, -0.14, 0.694), (0.058, -0.17, 0.694), 'head'),
        ('eye.R', (-0.058, -0.14, 0.694), (-0.058, -0.17, 0.694), 'head'),
        ('ahoge', (0, 0.03, 0.872), (0, -0.02, 0.975), 'head'),
        ('fin.L', (0.146, 0.018, 0.722), (0.235, 0.05, 0.69), 'head'),
        ('fin.R', (-0.146, 0.018, 0.722), (-0.235, 0.05, 0.69), 'head'),
        ('hair.B.1', (0, 0.15, 0.70), (0, 0.2, 0.52), 'head'),
        ('hair.B.2', (0, 0.2, 0.52), (0, 0.23, 0.32), 'hair.B.1'),
        ('hair.L.1', (0.13, 0.1, 0.70), (0.2, 0.12, 0.52), 'head'),
        ('hair.L.2', (0.2, 0.12, 0.52), (0.23, 0.13, 0.32), 'hair.L.1'),
        ('hair.R.1', (-0.13, 0.1, 0.70), (-0.2, 0.12, 0.52), 'head'),
        ('hair.R.2', (-0.2, 0.12, 0.52), (-0.23, 0.13, 0.32), 'hair.R.1'),
        ('lock.L', (0.15, -0.07, 0.66), (0.17, -0.06, 0.46), 'head'),
        ('lock.R', (-0.15, -0.07, 0.66), (-0.17, -0.06, 0.46), 'head'),
        ('upperarm.L', (0.07, 0, 0.528), (0.128, -0.004, 0.445), 'chest'),
        ('lowerarm.L', (0.128, -0.004, 0.445), (0.162, -0.012, 0.378), 'upperarm.L'),
        ('hand.L', (0.162, -0.012, 0.378), (0.178, -0.016, 0.34), 'lowerarm.L'),
        ('upperarm.R', (-0.07, 0, 0.528), (-0.128, -0.004, 0.445), 'chest'),
        ('lowerarm.R', (-0.128, -0.004, 0.445), (-0.162, -0.012, 0.378), 'upperarm.R'),
        ('hand.R', (-0.162, -0.012, 0.378), (-0.178, -0.016, 0.34), 'lowerarm.R'),
        ('upperleg.L', (0.044, 0, 0.36), (0.045, -0.004, 0.2), 'hips'),
        ('lowerleg.L', (0.045, -0.004, 0.2), (0.045, 0, 0.066), 'upperleg.L'),
        ('foot.L', (0.045, 0, 0.066), (0.046, -0.06, 0.02), 'lowerleg.L'),
        ('upperleg.R', (-0.044, 0, 0.36), (-0.045, -0.004, 0.2), 'hips'),
        ('lowerleg.R', (-0.045, -0.004, 0.2), (-0.045, 0, 0.066), 'upperleg.R'),
        ('foot.R', (-0.045, 0, 0.066), (-0.046, -0.06, 0.02), 'lowerleg.R'),
        ('prop', (0, -0.13, 0.42), (0, -0.13, 0.47), 'chest'),
    ]
    tail_names = []
    for i in range(len(tp) - 1):
        n = f'tail.{i + 1}'
        bones.append((n, tuple(tp[i]), tuple(tp[i + 1]), 'hips' if i == 0 else f'tail.{i}'))
        tail_names.append(n)
    arm = core.armature('rig_bluefish', bones)
    segs = core.bone_segments(arm)

    def w_rigid(o, b):
        return core.rigid(len(o.data.vertices), b)

    # head-mounted parts
    for key in ('head', 'headdress', 'expr_mouth_open', 'expr_mouth_small', 'expr_mouth_round', 'expr_mouth_cat', 'face_blush'):
        core.bind(objs[key], arm, w_rigid(objs[key], 'head'))
    for key in ('expr_eyes_open', 'expr_eyes_happy'):
        co = core.verts_of(objs[key])
        core.bind(objs[key], arm, {'eye.L': (co[:, 0] > 0).astype(float), 'eye.R': (co[:, 0] <= 0).astype(float)})
    core.bind(objs['fin_L'], arm, w_rigid(objs['fin_L'], 'fin.L'))
    core.bind(objs['fin_R'], arm, w_rigid(objs['fin_R'], 'fin.R'))

    # hair: head on top, hanging parts follow hair bones
    co = core.verts_of(objs['hair'])
    hang = smoothstep(0.66, 0.5, co[:, 2])
    names = ['hair.B.1', 'hair.B.2', 'hair.L.1', 'hair.L.2', 'hair.R.1', 'hair.R.2', 'lock.L', 'lock.R']
    pw = core.proximity_weights(co, segs, names, falloff=3.0)
    tot = sum(pw.values())
    tot[tot == 0] = 1
    w = {n: pw[n] / tot * hang for n in names}
    w['head'] = 1 - hang
    ah = (co[:, 2] > 0.88) & (np.abs(co[:, 0]) < 0.02)
    w = {k: np.where(ah, 0, v) for k, v in w.items()}
    w['ahoge'] = ah.astype(float)
    core.bind(objs['hair'], arm, w)

    # body
    co = core.verts_of(objs['body'])
    core.bind(objs['body'], arm, core.proximity_weights(co, segs, ['hips', 'spine', 'chest', 'neck'], falloff=2.5))
    # skirt: hips, lower part pulled a little by the thighs
    co = core.verts_of(objs['skirt'])
    k = np.clip((0.36 - co[:, 2]) / 0.1, 0, 1) * 0.35
    core.bind(objs['skirt'], arm, {'hips': 1 - k, 'upperleg.L': k * (co[:, 0] > 0), 'upperleg.R': k * (co[:, 0] <= 0)})
    # arms / legs
    for s in ('L', 'R'):
        co = core.verts_of(objs[f'arm_{s}'])
        core.bind(objs[f'arm_{s}'], arm, core.chain_weights(co, segs, [f'upperarm.{s}', f'lowerarm.{s}', f'hand.{s}'], blend=0.25))
        co = core.verts_of(objs[f'leg_{s}'])
        w = core.chain_weights(co, segs, [f'upperleg.{s}', f'lowerleg.{s}'], blend=0.25)
        shoe = co[:, 2] < 0.066
        w = {k2: np.where(shoe, 0, v) for k2, v in w.items()}
        w[f'foot.{s}'] = shoe.astype(float)
        core.bind(objs[f'leg_{s}'], arm, w)
    co = core.verts_of(objs['tail'])
    core.bind(objs['tail'], arm, core.chain_weights(co, segs, tail_names, blend=0.4))
    core.bind(objs['emblem'], arm, w_rigid(objs['emblem'], 'hips'))
    return arm
