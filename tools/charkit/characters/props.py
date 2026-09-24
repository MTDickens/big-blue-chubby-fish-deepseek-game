"""Props from the videos: 电饭煲 (EP1), 黄金电饭煲 (EP2), 「喜欢的话可以点赞谢谢喵」 sign (EP1/EP2 ending),
纸箱 with a peek slit (EP2), and the rope that tied up 大圆鲸 (EP3). Props are realistic PBR (pbr_/metal_)."""
import math
import os

import bpy  # noqa: F401
import numpy as np

from .. import core, face as F, sdf
from .bluefish import lin, realize

HERE = os.path.dirname(os.path.abspath(__file__))
SIGN_TEX = os.path.normpath(os.path.join(HERE, '..', 'textures', 'sign.png'))
TAU = 2 * math.pi


def _cooker(gold):
    body_c = lin('#e7b85a') if gold else lin('#f1f1ee')
    trim = lin('#b58a35') if gold else lin('#c9ccd1')
    B = sdf.Field('cooker')
    prof = [(0, 0.0), (0.092, 0.0), (0.104, 0.012), (0.108, 0.06), (0.106, 0.12), (0.1, 0.148), (0, 0.148)]
    B.add(sdf.lathe(prof), body_c, k=0.0)
    B.add(sdf.torus((0, 0, 0.148), 0.1, 0.006), trim, k=0.004)
    for s in (-1, 1):   # side handles
        B.add(sdf.ellipsoid((s * 0.112, 0, 0.118), (0.014, 0.034, 0.01)), trim, k=0.006)
    B.add(sdf.rounded_box((0, -0.098, 0.08), (0.045, 0.012, 0.032), 0.01), lin('#1a1a1e') if gold else lin('#d9dde3'), k=0.004)   # control panel
    for i, x in enumerate((-0.022, 0.0, 0.022)):
        B.add(sdf.sphere((x, -0.109, 0.072), 0.006), lin('#f2d27a') if gold else (lin('#e0503c') if i == 1 else lin('#9aa3ad')), k=0.001)
    for s in (-1, 1):   # little feet
        for t in (-1, 1):
            B.add(sdf.sphere((s * 0.06, t * 0.06, 0.004), 0.012), trim, k=0.004)
    L = sdf.Field('lid')
    lid = [(0, 0.148), (0.1, 0.148), (0.104, 0.156), (0.098, 0.176), (0.07, 0.196), (0, 0.202)]
    L.add(sdf.lathe(lid), body_c, k=0.0)
    L.add(sdf.rounded_box((0, 0.0, 0.212), (0.026, 0.012, 0.012), 0.008), trim, k=0.004)   # lid knob
    R = sdf.Field('rice')
    R.add(sdf.ellipsoid((0, 0, 0.14), (0.09, 0.09, 0.022)), lin('#fbfaf5'), k=0.0)
    rng = np.random.default_rng(1)
    for _ in range(60):
        a, r = rng.uniform(0, TAU), 0.085 * math.sqrt(rng.uniform(0, 1))
        R.add(sdf.ellipsoid((r * math.cos(a), r * math.sin(a), 0.155 - 0.8 * (r / 0.09) ** 2 * 0.02), (0.006, 0.003, 0.003),
                            rot=(0, 0, math.degrees(rng.uniform(0, TAU)))), lin('#ffffff'), k=0.003)
    return B, L, R


def build_cooker(out_path, gold=False):
    core.reset()
    core.clear_material_cache()
    if gold:
        mat = core.material('metal_gold', '#ffffff', rough=0.22, metal=1.0, extras={'env': 1.4})
    else:
        mat = core.material('pbr_cooker', '#ffffff', rough=0.35, extras={'env': 1.0})
    rice_mat = core.material('pbr_rice', '#ffffff', rough=0.7, extras={'env': 0.6})
    B, L, R = _cooker(gold)
    objs = {'body': realize(B, 'body', mat, voxel=0.0018, target=6000, cav=0.15),
            'lid': realize(L, 'lid', mat, voxel=0.0018, target=2500, cav=0.1),
            'rice': realize(R, 'rice', rice_mat, voxel=0.0012, target=2500, cav=0.2)}
    arm = core.armature('rig_cooker', [('root', (0, 0, 0), (0, 0, 0.05), None), ('lid', (0, 0.1, 0.15), (0, 0.1, 0.2), 'root')])
    core.bind(objs['body'], arm, core.rigid(len(objs['body'].data.vertices), 'root'))
    core.bind(objs['rice'], arm, core.rigid(len(objs['rice'].data.vertices), 'root'))
    core.bind(objs['lid'], arm, core.rigid(len(objs['lid'].data.vertices), 'lid'))
    core.action(arm, 'closed', 10, lambda f, ph: {'lid': {'rot': (0, 0, 0)}})
    core.action(arm, 'open', 20, lambda f, ph: {'lid': {'rot': (-105 * (1 - (1 - ph) ** 3), 0, 0)}}, loop=False)
    core.finish_actions(arm, 'closed')
    stats = {k: core.tri_count(v) for k, v in objs.items()}
    core.export_glb(out_path)
    return stats


def build_sign(out_path):
    core.reset()
    core.clear_material_cache()
    wood = core.material('pbr_wood', '#c99a60', rough=0.75, extras={'env': 0.6})
    face = core.material('face_sign', '#ffffff', image=SIGN_TEX, alpha='image', extras={'toneMapped': True})
    B = sdf.Field('sign')
    B.add(sdf.rounded_box((0, 0, 0), (0.15, 0.011, 0.095), 0.012), lin('#c99a60'), k=0.0)
    rng = np.random.default_rng(4)
    for _ in range(14):   # a few wood-grain dents
        x, z = rng.uniform(-0.13, 0.13), rng.uniform(-0.08, 0.08)
        B.paint(sdf.ellipsoid((x, 0.0, z), (0.04, 0.02, 0.004)), lin('#b7884f'), k=0.004)
    board = realize(B, 'board', wood, voxel=0.0015, target=3000, cav=0.1)
    front = F.decal('sign_face', F.surface_bvh(board), (0, -0.2, 0), (0.286, 0.18), (0, 0), face, res=6, cells=1)
    arm = core.armature('rig_sign', [('root', (0, 0, -0.1), (0, 0, -0.05), None)])
    for o in (board, front):
        core.bind(o, arm, core.rigid(len(o.data.vertices), 'root'))
    stats = {'board': core.tri_count(board), 'face': core.tri_count(front)}
    core.export_glb(out_path)
    return stats


def build_box(out_path):
    core.reset()
    core.clear_material_cache()
    card = core.material('pbr_cardboard', '#ffffff', rough=0.85, extras={'env': 0.5})
    B = sdf.Field('box')
    tan, dark, tape = lin('#c49a64'), lin('#a07a48'), lin('#d9c7a0')
    B.add(sdf.rounded_box((0, 0, 0.2), (0.2, 0.17, 0.2), 0.008), tan, k=0.0)
    B.carve(sdf.rounded_box((0, 0, 0.21), (0.19, 0.16, 0.2), 0.004), k=0.002)   # hollow, open at the bottom
    B.carve(sdf.rounded_box((0, -0.17, 0.3), (0.075, 0.03, 0.016), 0.012), k=0.003)   # peek slit
    for s in (-1, 1):   # top flaps slightly lifted
        B.add(sdf.rounded_box((s * 0.1, 0, 0.405), (0.1, 0.17, 0.004), 0.003, rot=(0, s * -8, 0)), tan, k=0.002)
    B.paint(sdf.rounded_box((0, 0, 0.405), (0.03, 0.2, 0.02), 0.0), tape, k=0.002)
    for x in (-0.2, 0.2):
        B.paint(sdf.rounded_box((x, 0, 0.2), (0.006, 0.2, 0.22), 0.0), dark, k=0.003)
    box = realize(B, 'box', card, voxel=0.003, target=5000, cav=0.25)
    arm = core.armature('rig_box', [('root', (0, 0, 0), (0, 0, 0.1), None)])
    core.bind(box, arm, core.rigid(len(box.data.vertices), 'root'))
    stats = {'box': core.tri_count(box)}
    core.export_glb(out_path)
    return stats


def build_rope(out_path):
    """A few loose coils sized to wrap 大圆鲸 (body center z=0.3, radius ~0.28)."""
    core.reset()
    core.clear_material_cache()
    mat = core.material('pbr_rope', '#ffffff', rough=0.9, extras={'env': 0.4})
    Rf = sdf.Field('rope')
    for i, (z, tilt) in enumerate(((0.24, 6), (0.32, -4), (0.4, 8))):
        pts = []
        for a in np.linspace(0, TAU, 40, endpoint=False):
            r = math.sqrt(max(0.0, 0.29 ** 2 * (1 - ((z - 0.3) / 0.28) ** 2))) + 0.012
            pts.append(np.array((r * math.cos(a), r * math.sin(a) * 0.95, z + math.radians(tilt) * r * math.cos(a)), dtype=np.float32))
        Rf.tube(pts, 0.011, lin('#b98f5a'), k=0.004, closed=True)
    rope = realize(Rf, 'rope', mat, voxel=0.0022, target=6000, cav=0.2,
                   post=lambda V, N, c: c * (0.85 + 0.15 * np.sin(np.arctan2(V[:, 1], V[:, 0]) * 90 + V[:, 2] * 400))[:, None])
    arm = core.armature('rig_rope', [('root', (0, 0, 0), (0, 0, 0.1), None)])
    core.bind(rope, arm, core.rigid(len(rope.data.vertices), 'root'))
    stats = {'rope': core.tri_count(rope)}
    core.export_glb(out_path)
    return stats


def build(out_path):
    d = os.path.dirname(out_path)
    stats = {}
    for name, fn in (('rice_cooker', lambda p: build_cooker(p, False)), ('golden_cooker', lambda p: build_cooker(p, True)),
                     ('sign', build_sign), ('box', build_box), ('rope', build_rope)):
        st = fn(os.path.join(d, f'{name}.glb'))
        stats.update({f'{name}.{k}': v for k, v in st.items()})
    return stats
