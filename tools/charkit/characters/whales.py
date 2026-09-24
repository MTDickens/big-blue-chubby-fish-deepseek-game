"""Whales: 小鲸鱼宝宝 (three baby whale variants, EP1/EP2 beach) and 大圆鲸 (the big round plush whale,
EP3 "救出被抓走的用户"). Sculpted with signed distance fields for a soft plush-figure look.

Both face -Y. Baby whales: bullet-shaped, blue back, white belly, bead eyes, tiny spout, tail curled
down to the ground. Big whale: almost a ball, white face/belly, big glossy eyes, blush, open smile,
heart-shaped spout, side flippers and a fluke curled up behind.
"""
import math
import os

import bpy  # noqa: F401
import numpy as np

from .. import core, face as F, sdf, shapes as S
from .bluefish import TEX, lin, realize, smoothstep

BABY_VARIANTS = {
    'a': dict(size=1.0, top='#4a86d2', spout='#7cc0ff', lean=18),
    'b': dict(size=0.82, top='#5b97dc', spout='#8fcaff', lean=8),
    'c': dict(size=1.16, top='#3f77c6', spout='#71b6ff', lean=26),
}


def _mats(prefix):
    return dict(
        body=core.material(f'fig_{prefix}_body', '#ffffff', extras={'rough': 0.55, 'sheen': 0.7, 'sheenColor': '#bcd6ff', 'coat': 0.15, 'env': 0.85}),
        bead=core.material(f'fig_{prefix}_bead', '#ffffff', extras={'rough': 0.12, 'coat': 1.0, 'coatRough': 0.05, 'env': 1.2}),
        face=core.material('face_bluefish', '#ffffff', image=TEX, alpha='image'),
    )


# ----------------------------------------------------------------------------- baby whale

def baby_fields(v):
    k = v['size']
    top, belly = lin(v['top']), lin('#f3f6fb')
    B = sdf.Field('baby')
    head = np.array([0, -0.035, 0.105]) * k
    B.add(sdf.ellipsoid(head, np.array([0.068, 0.075, 0.072]) * k), top, k=0.0)
    B.add(sdf.ellipsoid(np.array([0, 0.03, 0.085]) * k, np.array([0.058, 0.07, 0.058]) * k), top, k=0.04 * k)
    tail = [np.array(p, dtype=np.float32) * k for p in [(0, 0.07, 0.08), (0, 0.12, 0.05), (0, 0.15, 0.022), (0, 0.17, 0.012)]]
    B.tube(tail, [0.042 * k, 0.03 * k, 0.02 * k, 0.014 * k], top, k=0.03 * k)
    fl = [(-0.01, 0.012), (0.03, 0.028), (0.062, 0.052), (0.058, 0.02), (0.07, 0.0), (0.058, -0.02), (0.062, -0.052), (0.03, -0.028), (-0.01, -0.012)]
    fl = [(x * k, y * k) for x, y in fl]
    # horizontal fluke resting on the ground behind
    B.add(sdf.slab(fl, 0.012 * k, tail[-1] + np.array([0, -0.004, 0.0]) * k, np.array([0, 1.0, -0.15]), np.array([1.0, 0, 0]), round_r=0.005 * k), top, k=0.01 * k)
    for s in (-1, 1):   # little pectoral fins
        B.add(sdf.ellipsoid(np.array([s * 0.058, -0.01, 0.05]) * k, np.array([0.03, 0.014, 0.012]) * k, rot=(0, s * 35, s * 25)), top, k=0.012 * k)
    # white belly and lower face
    B.paint(sdf.ellipsoid(np.array([0, -0.06, 0.035]) * k, np.array([0.075, 0.09, 0.075]) * k), belly, k=0.01 * k)
    # spout: two tiny tufts
    A = sdf.Field('baby_bits')
    sp = lin(v['spout'])
    base = head + np.array([0, 0.012, 0.07]) * k
    for s in (-1, 1):
        A.tube([base, base + np.array([s * 0.008, 0, 0.018]) * k, base + np.array([s * 0.022, 0, 0.026]) * k], [0.006 * k, 0.005 * k, 0.003 * k], sp, k=0.004 * k)
    A.add(sdf.sphere(base + np.array([0, 0, 0.004]) * k, 0.006 * k), sp, k=0.004 * k)
    # bead eyes + smile
    E = sdf.Field('baby_eyes')
    for s in (-1, 1):
        E.add(sdf.sphere(head + np.array([s * 0.05, -0.05, 0.004]) * k, 0.0085 * k), lin('#0d1426'), k=0.0)
    smile = [head + np.array([x, -0.071 + 0.35 * x * x, -0.025 + 3.2 * x * x]) * k for x in np.linspace(-0.018, 0.018, 5)]
    E.tube(smile, 0.0022 * k, lin('#3a2030'), k=0.001)
    return B, A, E


def build_baby(out_path, variant='a'):
    core.reset()
    core.clear_material_cache()
    v = BABY_VARIANTS[variant]
    M = _mats('baby')
    Bf, Af, Ef = baby_fields(v)
    k = v['size']
    objs = {
        'body': realize(Bf, 'body', M['body'], voxel=0.0016 * k, target=5000, cav=0.2),
        'spout': realize(Af, 'spout', M['body'], voxel=0.001 * k, target=800, cav=0.0),
        'eyes': realize(Ef, 'eyes', M['bead'], voxel=0.0008 * k, target=900, cav=0.0),
    }
    lean = v['lean']
    # lean the whole whale so the head is up and the tail rests on the sand
    for o in objs.values():
        o.rotation_euler = (math.radians(-lean), 0, 0)
        o.location = (0, 0, 0.012 * lean / 20 * k)
        bpy.context.view_layer.update()
        core.apply_transform(o)
    arm = baby_rig(objs, k, lean)
    baby_anims(arm, k)
    stats = {kk: core.tri_count(o) for kk, o in objs.items()}
    core.export_glb(out_path)
    return stats


def baby_rig(objs, k, lean):
    c, s = math.cos(math.radians(-lean)), math.sin(math.radians(-lean))

    def R(p):
        x, y, z = p
        return (x, y * c - z * s, y * s + z * c + 0.012 * lean / 20 * k)
    bones = [
        ('root', (0, 0, 0), (0, 0, 0.04 * k), None),
        ('body', R((0, 0.0, 0.06 * k)), R((0, -0.02 * k, 0.16 * k)), 'root'),
        ('tail.1', R((0, 0.06 * k, 0.08 * k)), R((0, 0.12 * k, 0.05 * k)), 'body'),
        ('tail.2', R((0, 0.12 * k, 0.05 * k)), R((0, 0.17 * k, 0.012 * k)), 'tail.1'),
        ('fin.L', R((0.05 * k, -0.01 * k, 0.05 * k)), R((0.085 * k, -0.01 * k, 0.03 * k)), 'body'),
        ('fin.R', R((-0.05 * k, -0.01 * k, 0.05 * k)), R((-0.085 * k, -0.01 * k, 0.03 * k)), 'body'),
    ]
    arm = core.armature('rig_baby', bones)
    segs = core.bone_segments(arm)
    co = core.verts_of(objs['body'])
    tailw = core.chain_weights(co, segs, ['tail.1', 'tail.2'], blend=0.4)
    d_tail = core.seg_dist(co, *segs['tail.1'])[0]
    t_in = smoothstep(0.05 * k, 0.02 * k, d_tail) * smoothstep(0.05 * k, 0.08 * k, co[:, 1] * c + (co[:, 2]) * 0 + 0.0 * k)
    fins = {sd: (core.seg_dist(co, *segs[f'fin.{sd}'])[0] < 0.022 * k) & (np.abs(co[:, 0]) > 0.05 * k) for sd in ('L', 'R')}
    w = {'tail.1': tailw['tail.1'] * t_in, 'tail.2': tailw['tail.2'] * t_in,
         'fin.L': fins['L'].astype(float), 'fin.R': fins['R'].astype(float)}
    w['body'] = np.clip(1 - sum(w.values()), 0, 1)
    core.bind(objs['body'], arm, w)
    for kk in ('spout', 'eyes'):
        core.bind(objs[kk], arm, core.rigid(len(objs[kk].data.vertices), 'body'))
    return arm


def baby_anims(arm, k):
    TAU = 2 * math.pi

    def idle(f, ph):
        b = math.sin(TAU * ph)
        return {'body': {'rot': (3 * b, 0, 3 * math.sin(TAU * ph + 1)), 'scale': (1, 1 + 0.02 * b, 1)},
                'tail.1': {'rot': (0, 0, 10 * math.sin(TAU * ph))}, 'tail.2': {'rot': (0, 0, 14 * math.sin(TAU * ph - 0.8))},
                'fin.L': {'rot': (0, 10 * b, 0)}, 'fin.R': {'rot': (0, -10 * b, 0)}}
    core.action(arm, 'idle', 60, idle)

    def hop(f, ph):
        up = max(0.0, math.sin(math.pi * min(1.0, ph / 0.7)))
        squash = 1 - 0.12 * max(0.0, math.sin(math.pi * max(0.0, (ph - 0.7) / 0.3)))
        return {'root': {'loc': (0, -0.02 * k * ph, 0.06 * k * up)},
                'body': {'rot': (-12 * up, 0, 0), 'scale': (1 / squash ** 0.5, squash, 1 / squash ** 0.5)},
                'tail.1': {'rot': (18 * up, 0, 0)}, 'tail.2': {'rot': (14 * up, 0, 0)},
                'fin.L': {'rot': (0, 30 * up, 0)}, 'fin.R': {'rot': (0, -30 * up, 0)}}
    core.action(arm, 'hop', 24, hop)

    def flap(f, ph):
        a = math.sin(TAU * 2 * ph)
        return {'fin.L': {'rot': (0, 35 * a, 0)}, 'fin.R': {'rot': (0, -35 * a, 0)}, 'body': {'rot': (0, 0, 4 * a)},
                'tail.2': {'rot': (0, 0, 10 * a)}}
    core.action(arm, 'flap', 30, flap)

    def spin(f, ph):
        return {'root': {'rot': (0, 0, 360 * ph), 'loc': (0, 0, 0.02 * k * math.sin(math.pi * ph))},
                'tail.1': {'rot': (0, 0, -20)}, 'fin.L': {'rot': (0, 25, 0)}, 'fin.R': {'rot': (0, -25, 0)}}
    core.action(arm, 'spin', 36, spin)
    core.finish_actions(arm, 'idle')


# ----------------------------------------------------------------------------- big round whale

BIG_C = np.array([0, 0.0, 0.3], dtype=np.float32)


def big_fields():
    top, belly = lin('#2f64c6'), lin('#f4f7fc')
    B = sdf.Field('big')
    B.add(sdf.ellipsoid(BIG_C, (0.29, 0.27, 0.275)), top, k=0.0)
    # tail curling up behind, fluke up
    tail = [np.array(p, dtype=np.float32) for p in [(0.0, 0.2, 0.2), (0.0, 0.3, 0.2), (0.0, 0.37, 0.25), (0.0, 0.4, 0.31)]]
    B.tube(tail, [0.1, 0.06, 0.038, 0.026], top, k=0.05)
    fl = [(-0.01, 0.02), (0.04, 0.06), (0.1, 0.1), (0.094, 0.04), (0.11, 0.0), (0.094, -0.04), (0.1, -0.1), (0.04, -0.06), (-0.01, -0.02)]
    B.add(sdf.slab(fl, 0.026, tail[-1], np.array([0, 0.2, 1.0]), np.array([1.0, 0, 0]), round_r=0.01), top, k=0.02)
    for s in (-1, 1):
        B.add(sdf.ellipsoid(BIG_C + np.array([s * 0.27, -0.03, -0.1]), (0.08, 0.035, 0.03), rot=(0, s * 30, s * 30)), top, k=0.03)
    B.paint(sdf.ellipsoid(BIG_C + np.array([0, -0.2, -0.13]), (0.3, 0.26, 0.24)), belly, k=0.015)
    A = sdf.Field('big_spout')
    sp = lin('#6fb6ff')
    base = BIG_C + np.array([0, -0.03, 0.27])
    A.tube([base - np.array([0, 0, 0.02]), base + np.array([0, 0, 0.03])], [0.018, 0.016], sp, k=0.01)
    for s in (-1, 1):   # heart-shaped spout lobes
        lobe = [base + np.array([0, 0, 0.028]), base + np.array([s * 0.02, 0, 0.06]), base + np.array([s * 0.05, 0, 0.075]),
                base + np.array([s * 0.07, 0, 0.06]), base + np.array([s * 0.065, 0, 0.036])]
        A.tube(lobe, [0.014, 0.018, 0.02, 0.018, 0.012], sp, k=0.012)
    return B, A


def build_big(out_path):
    core.reset()
    core.clear_material_cache()
    M = _mats('big')
    Bf, Af = big_fields()
    objs = {
        'body': realize(Bf, 'body', M['body'], voxel=0.003, target=9000, cav=0.15),
        'spout': realize(Af, 'spout', M['body'], voxel=0.0018, target=2000, cav=0.1),
    }
    bvh = F.surface_bvh(objs['body'])
    ex, ez = 0.1, 0.36
    objs['expr_eyes_open'] = core.join([F.decal('weyeR', bvh, (-ex, -0.6, ez), (0.12, 0.12), (3, 0), M['face']),
                                        F.decal('weyeL', bvh, (ex, -0.6, ez), (0.12, 0.12), (3, 0), M['face'], mirror=True)], 'expr_eyes_open')
    objs['expr_eyes_happy'] = core.join([F.decal('weyeRh', bvh, (-ex, -0.6, ez), (0.12, 0.11), (1, 0), M['face']),
                                         F.decal('weyeLh', bvh, (ex, -0.6, ez), (0.12, 0.11), (1, 0), M['face'], mirror=True)], 'expr_eyes_happy')
    objs['expr_mouth_open'] = F.decal('expr_mouth_open', bvh, (0, -0.6, 0.265), (0.13, 0.13), (0, 1), M['face'])
    objs['expr_mouth_small'] = F.decal('expr_mouth_small', bvh, (0, -0.6, 0.27), (0.11, 0.11), (1, 1), M['face'])
    objs['face_blush'] = core.join([F.decal('wblushR', bvh, (-0.19, -0.6, 0.29), (0.1, 0.07), (0, 2), M['face'], offset=0.001),
                                    F.decal('wblushL', bvh, (0.19, -0.6, 0.29), (0.1, 0.07), (0, 2), M['face'], mirror=True, offset=0.001)], 'face_blush')
    arm = big_rig(objs)
    big_anims(arm)
    stats = {kk: core.tri_count(o) for kk, o in objs.items()}
    core.export_glb(out_path)
    return stats


def big_rig(objs):
    bones = [
        ('root', (0, 0, 0), (0, 0, 0.05), None),
        ('body', (0, 0, 0.1), (0, 0, 0.5), 'root'),
        ('tail.1', (0, 0.22, 0.2), (0, 0.32, 0.21), 'body'),
        ('tail.2', (0, 0.32, 0.21), (0, 0.4, 0.31), 'tail.1'),
        ('fin.L', (0.24, -0.03, 0.2), (0.33, -0.04, 0.16), 'body'),
        ('fin.R', (-0.24, -0.03, 0.2), (-0.33, -0.04, 0.16), 'body'),
        ('spout', (0, -0.03, 0.56), (0, -0.03, 0.64), 'body'),
        ('eye.L', (0.1, -0.26, 0.36), (0.1, -0.3, 0.36), 'body'),
        ('eye.R', (-0.1, -0.26, 0.36), (-0.1, -0.3, 0.36), 'body'),
    ]
    arm = core.armature('rig_bigwhale', bones)
    segs = core.bone_segments(arm)
    co = core.verts_of(objs['body'])
    tail = smoothstep(0.24, 0.3, co[:, 1])
    tw = core.chain_weights(co, segs, ['tail.1', 'tail.2'], blend=0.4)
    fins = {sd: ((np.abs(co[:, 0]) > 0.265) & (np.sign(co[:, 0]) == (1 if sd == 'L' else -1)) & (co[:, 2] < 0.26)).astype(float) for sd in ('L', 'R')}
    w = {'tail.1': tw['tail.1'] * tail, 'tail.2': tw['tail.2'] * tail, 'fin.L': fins['L'], 'fin.R': fins['R']}
    w['body'] = np.clip(1 - sum(w.values()), 0, 1)
    core.bind(objs['body'], arm, w)
    core.bind(objs['spout'], arm, core.rigid(len(objs['spout'].data.vertices), 'spout'))
    for kk in ('expr_mouth_open', 'expr_mouth_small', 'face_blush'):
        core.bind(objs[kk], arm, core.rigid(len(objs[kk].data.vertices), 'body'))
    for kk in ('expr_eyes_open', 'expr_eyes_happy'):
        co = core.verts_of(objs[kk])
        core.bind(objs[kk], arm, {'eye.L': (co[:, 0] > 0).astype(float), 'eye.R': (co[:, 0] <= 0).astype(float)})
    return arm


def big_anims(arm):
    TAU = 2 * math.pi

    def idle(f, ph):
        b = math.sin(TAU * ph)
        return {'body': {'scale': (1 + 0.015 * b, 1 + 0.015 * b, 1 - 0.02 * b), 'rot': (0, 0, 2 * math.sin(TAU * ph + 1))},
                'spout': {'rot': (0, 6 * b, 0), 'scale': (1, 1, 1 + 0.08 * b)},
                'tail.1': {'rot': (6 * b, 0, 0)}, 'tail.2': {'rot': (10 * math.sin(TAU * ph - 0.7), 0, 0)},
                'fin.L': {'rot': (0, 8 * b, 0)}, 'fin.R': {'rot': (0, -8 * b, 0)}}
    core.action(arm, 'idle', 90, idle)

    def happy(f, ph):
        a = math.sin(TAU * 2 * ph)
        return {'body': {'rot': (0, 8 * a, 6 * math.sin(TAU * ph))}, 'spout': {'rot': (0, -14 * a, 0), 'scale': (1.1, 1.1, 1.2)},
                'fin.L': {'rot': (0, 40 * a, 0)}, 'fin.R': {'rot': (0, -40 * a, 0)}, 'tail.2': {'rot': (20 * a, 0, 0)}}
    core.action(arm, 'happy', 40, happy)

    def hop(f, ph):
        up = max(0.0, math.sin(math.pi * min(1.0, ph / 0.65)))
        land = max(0.0, math.sin(math.pi * max(0.0, (ph - 0.65) / 0.35)))
        return {'root': {'loc': (0, 0, 0.1 * up)}, 'body': {'scale': (1 + 0.1 * land - 0.04 * up, 1 + 0.1 * land - 0.04 * up, 1 - 0.14 * land + 0.06 * up)},
                'fin.L': {'rot': (0, 35 * up, 0)}, 'fin.R': {'rot': (0, -35 * up, 0)}, 'tail.2': {'rot': (-15 * up, 0, 0)}}
    core.action(arm, 'hop', 30, hop)

    def struggle(f, ph):
        a = math.sin(TAU * 3 * ph)
        return {'body': {'rot': (0, 10 * a, 0)}, 'fin.L': {'rot': (0, 25 * a, 0)}, 'fin.R': {'rot': (0, 25 * a, 0)},
                'tail.2': {'rot': (25 * a, 0, 0)}, 'spout': {'rot': (0, -15 * a, 0)}}
    core.action(arm, 'struggle', 36, struggle)

    def blink(f, ph):
        kk = 1 - math.sin(math.pi * ph) ** 0.6 * 0.92
        return {'eye.L': {'scale': (1, 1, kk)}, 'eye.R': {'scale': (1, 1, kk)}}
    core.action(arm, 'blink', 8, blink, loop=False)
    core.finish_actions(arm, 'idle')


def build(out_path):
    """Builds all whales next to out_path's directory; returns stats of the big whale plus babies."""
    d = os.path.dirname(out_path)
    stats = {}
    for v in BABY_VARIANTS:
        st = build_baby(os.path.join(d, f'whale_baby_{v}.glb'), v)
        stats.update({f'baby_{v}.{kk}': n for kk, n in st.items()})
    st = build_big(os.path.join(d, 'whale_big.glb'))
    stats.update({f'big.{kk}': n for kk, n in st.items()})
    return stats
