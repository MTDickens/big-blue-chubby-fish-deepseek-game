"""charkit.core — scene, mesh, material, armature, animation and export helpers (Blender 4.5 bpy).

Conventions
- Meters, Blender Z-up. Characters stand at the origin and face -Y (Blender "front" view);
  glTF export turns that into +Z forward / +Y up, i.e. facing a three.js camera placed on +Z.
- Material names carry a style prefix that the web gallery maps to shaders:
    toon_*  anime MToon shading with outline     face_*  unlit decal (eyes, mouth, blush)
    pbr_*   realistic PBR (props)                metal_* metallic PBR (golden rice cooker)
  Extra shading parameters travel as material custom properties (exported as glTF extras).
"""
import json
import math

import bpy  # must be imported before bmesh/mathutils when running as a module
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector


# --------------------------------------------------------------------------- scene

def reset(fps=30):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scn = bpy.context.scene
    scn.render.fps = fps
    scn.unit_settings.system = 'METRIC'
    return scn


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


# --------------------------------------------------------------------------- colors

def srgb_to_linear(c):
    c = np.asarray(c, dtype=float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def hexc(h, alpha=1.0):
    """'#rrggbb' -> linear RGBA tuple (what Blender/glTF color factors expect)."""
    h = h.lstrip('#')
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(srgb_to_linear(rgb).tolist()) + (alpha,)


# --------------------------------------------------------------------------- materials

_MATS = {}


def material(name, color='#ffffff', rough=0.8, metal=0.0, image=None, alpha=None, extras=None, emissive=None):
    """Create (or reuse) a Principled material. `image` is a path to a PNG used as base color."""
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = hexc(color) if isinstance(color, str) else color
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    if emissive:
        bsdf.inputs['Emission Color'].default_value = hexc(emissive)
        bsdf.inputs['Emission Strength'].default_value = 1.0
    if image:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(image)
        tex.interpolation = 'Linear'
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
        if alpha == 'image':
            nt.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
            m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    elif alpha is not None:
        bsdf.inputs['Alpha'].default_value = alpha
    if extras:
        m['style'] = json.dumps(extras)
    _MATS[name] = m
    return m


def clear_material_cache():
    _MATS.clear()


# --------------------------------------------------------------------------- meshes

def mesh_from_arrays(name, verts, faces, uvs=None, colors=None, mat=None, smooth=True):
    """verts (N,3); faces list of index tuples; uvs per-vertex (N,2); colors per-vertex (N,3|4) linear."""
    verts = np.asarray(verts, dtype=float)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts.tolist(), [], [tuple(int(i) for i in f) for f in faces])
    me.validate(clean_customdata=False)
    me.update()
    loop_vi = np.empty(len(me.loops), dtype=np.int32)
    me.loops.foreach_get('vertex_index', loop_vi)
    if uvs is not None:
        uvs = np.asarray(uvs, dtype=float)
        uvl = me.uv_layers.new(name='UVMap')
        uvl.data.foreach_set('uv', uvs[loop_vi].ravel())
    if colors is not None:
        colors = np.asarray(colors, dtype=float)
        if colors.shape[1] == 3:
            colors = np.concatenate([colors, np.ones((len(colors), 1))], axis=1)
        ca = me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
        ca.data.foreach_set('color', colors.ravel())
        me.color_attributes.active_color = ca
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
    if smooth:
        me.shade_smooth()
    obj = link(bpy.data.objects.new(name, me))
    if mat is not None:
        me.materials.append(mat)
    return obj


def verts_of(obj, world=True):
    me = obj.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    if world:
        mw = np.array(obj.matrix_world)
        co = co @ mw[:3, :3].T + mw[:3, 3]
    return co


def set_verts(obj, co):
    obj.data.vertices.foreach_set('co', np.asarray(co, dtype=float).ravel())
    obj.data.update()


def apply_transform(obj):
    mw = obj.matrix_world.copy()
    obj.data.transform(mw)
    obj.matrix_world = Matrix.Identity(4)


def add_modifier(obj, kind, **kw):
    mod = obj.modifiers.new(kind.lower(), kind)
    for k, v in kw.items():
        setattr(mod, k, v)
    return mod


def apply_modifiers(obj):
    """Bake all modifiers into the mesh data (evaluated mesh replaces the original)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    bpy.data.meshes.remove(old)
    return obj


def subdivide(obj, levels=1):
    add_modifier(obj, 'SUBSURF', levels=levels, render_levels=levels, quality=3)
    return apply_modifiers(obj)


def solidify(obj, thickness, offset=0.0):
    add_modifier(obj, 'SOLIDIFY', thickness=thickness, offset=offset, use_even_offset=True)
    return apply_modifiers(obj)


def set_color(obj, color):
    """Fill (or create) the vertex color attribute with a single linear color."""
    n = len(obj.data.vertices)
    c = np.tile(np.array(hexc(color) if isinstance(color, str) else color, dtype=float), (n, 1))
    me = obj.data
    ca = me.color_attributes.get('Color') or me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
    ca.data.foreach_set('color', c.ravel())
    me.color_attributes.active_color = ca
    return obj


def paint(obj, fn):
    """fn(world_verts (N,3)) -> (N,3|4) linear colors."""
    co = verts_of(obj)
    c = np.asarray(fn(co), dtype=float)
    if c.shape[1] == 3:
        c = np.concatenate([c, np.ones((len(c), 1))], axis=1)
    me = obj.data
    ca = me.color_attributes.get('Color') or me.color_attributes.new(name='Color', type='FLOAT_COLOR', domain='POINT')
    ca.data.foreach_set('color', c.ravel())
    me.color_attributes.active_color = ca
    return obj


def join(objs, name):
    objs = [o for o in objs if o is not None]
    ctx = {'active_object': objs[0], 'selected_editable_objects': objs, 'selected_objects': objs}
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.join()
    objs[0].name = name
    objs[0].data.name = name
    return objs[0]


def tri_count(obj):
    me = obj.data
    me.calc_loop_triangles()
    return len(me.loop_triangles)


# --------------------------------------------------------------------------- armature

def armature(name, bones):
    """bones: list of (name, head, tail, parent_or_None[, roll]). Returns the armature object."""
    arm = bpy.data.armatures.new(name)
    obj = link(bpy.data.objects.new(name, arm))
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for b in bones:
        bname, head, tail, parent = b[:4]
        eb = arm.edit_bones.new(bname)
        eb.head, eb.tail = Vector(head), Vector(tail)
        eb.roll = b[4] if len(b) > 4 else 0.0
        if parent:
            eb.parent = arm.edit_bones[parent]
        eb.use_connect = False
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.show_in_front = True
    return obj


def bone_segments(arm_obj):
    """{name: (head, tail)} in world space (rest pose)."""
    mw = arm_obj.matrix_world
    return {b.name: (np.array(mw @ b.head_local), np.array(mw @ b.tail_local)) for b in arm_obj.data.bones}


def bind(mesh_obj, arm_obj, weights):
    """weights: {bone_name: (N,) array}. Normalized per vertex, top-4 kept."""
    names = list(weights.keys())
    W = np.stack([np.asarray(weights[n], dtype=float) for n in names], axis=1)
    if W.shape[1] > 4:
        idx = np.argsort(-W, axis=1)[:, 4:]
        np.put_along_axis(W, idx, 0.0, axis=1)
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1
    W = W / s
    for j, n in enumerate(names):
        vg = mesh_obj.vertex_groups.get(n) or mesh_obj.vertex_groups.new(name=n)
        col = W[:, j]
        nz = np.nonzero(col > 1e-4)[0]
        # group identical weights for fewer API calls
        vals = np.round(col[nz], 3)
        for v in np.unique(vals):
            ids = nz[vals == v].tolist()
            vg.add(ids, float(v), 'REPLACE')
    mod = mesh_obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm_obj
    mesh_obj.parent = arm_obj
    return mesh_obj


def rigid(n, bone):
    return {bone: np.ones(n)}


def seg_dist(p, a, b):
    """Distance from points p (N,3) to segment a-b, and the segment parameter t in [0,1]."""
    ab = b - a
    t = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    proj = a + t[:, None] * ab
    return np.linalg.norm(p - proj, axis=1), t


def proximity_weights(co, segs, names, falloff=2.0, radius=None):
    """Smooth weights by inverse distance to bone segments. radius: per-bone influence scale (dict)."""
    out = {}
    D = []
    for n in names:
        d, _ = seg_dist(co, *segs[n])
        r = (radius or {}).get(n, 1.0)
        D.append(d / r)
    D = np.stack(D, axis=1)
    W = 1.0 / np.maximum(D, 1e-4) ** falloff
    # keep only bones reasonably close to the nearest one
    dmin = D.min(axis=1, keepdims=True)
    W[D > dmin * 2.2 + 0.02] = 0
    for j, n in enumerate(names):
        out[n] = W[:, j]
    return out


def chain_weights(co, segs, chain, blend=0.35):
    """Weights along a bone chain by projected parameter (for tails, hair, skirts)."""
    pts = [segs[chain[0]][0]] + [segs[c][1] for c in chain]
    pts = np.array(pts)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    # parameter of each vertex along the polyline: nearest segment + local t
    best = np.full(len(co), 1e9)
    s = np.zeros(len(co))
    for i in range(len(chain)):
        d, t = seg_dist(co, pts[i], pts[i + 1])
        m = d < best
        best[m] = d[m]
        s[m] = L[i] + t[m] * (L[i + 1] - L[i])
    out = {}
    for i, c in enumerate(chain):
        mid = (L[i] + L[i + 1]) / 2
        half = (L[i + 1] - L[i]) / 2
        w = np.clip(1 - np.abs(s - mid) / (half * (1 + blend * 2)), 0, 1)
        out[c] = w
    tot = sum(out.values())
    first, last = chain[0], chain[-1]
    out[first] = np.where(tot == 0, (s <= L[1]).astype(float), out[first])
    out[last] = np.where((tot == 0) & (s > L[1]), 1.0, out[last])
    return out


def merge_weights(*ws):
    out = {}
    for w in ws:
        for k, v in w.items():
            out[k] = out.get(k, 0) + v
    return out


# --------------------------------------------------------------------------- animation

def _pb(arm_obj, name):
    pb = arm_obj.pose.bones[name]
    pb.rotation_mode = 'QUATERNION'
    return pb


def action(arm_obj, name, length, keys, loop=True, step=1):
    """Create an action by sampling `keys(frame, phase)` -> {bone: {...}}.

    Per bone:  'q'     mathutils.Quaternion in armature axes (e.g. from aim()), combined with 'rot'
               'rot'   (x, y, z) degrees, XYZ Euler about the ARMATURE's rest axes
                        (X = character's left, Y = back, Z = up), pivoting at the bone head;
               'loc'   (x, y, z) meters in armature axes;
               'scale' (x, y, z) in the bone's own local axes (Y = along the bone).
    phase = frame/length in [0, 1). For looping actions the last frame equals the first.
    """
    ad = arm_obj.animation_data or arm_obj.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ad.action = act
    rest = {b.name: b.matrix_local.to_3x3() for b in arm_obj.data.bones}
    frames = list(range(0, length + 1, step))
    if frames[-1] != length:
        frames.append(length)
    for f in frames:
        ph = (f % length) / length if loop else f / length
        pose = keys(f, ph)
        for bname, tr in pose.items():
            pb = _pb(arm_obj, bname)
            R = rest[bname]
            if 'rot' in tr or 'q' in tr:
                Q = Euler([math.radians(a) for a in tr.get('rot', (0, 0, 0))], 'XYZ').to_matrix()
                if 'q' in tr:  # extra rotation (mathutils Quaternion, armature axes) applied after the Euler part
                    Q = tr['q'].to_matrix() @ Q
                pb.rotation_quaternion = (R.transposed() @ Q @ R).to_quaternion()
                pb.keyframe_insert('rotation_quaternion', frame=f, group=bname)
            if 'loc' in tr:
                pb.location = R.transposed() @ Vector(tr['loc'])
                pb.keyframe_insert('location', frame=f, group=bname)
            if 'scale' in tr:
                pb.scale = Vector(tr['scale'])
                pb.keyframe_insert('scale', frame=f, group=bname)
    # reset pose so the next action starts clean
    for pb in arm_obj.pose.bones:
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = Vector((0, 0, 0))
        pb.scale = Vector((1, 1, 1))
    act.frame_range = (0, length)
    return act


def finish_actions(arm_obj, default=None):
    ad = arm_obj.animation_data
    if ad is None:
        return
    ad.action = bpy.data.actions.get(default) if default else None


# --------------------------------------------------------------------------- export

def export_glb(path, objects=None):
    if objects is not None:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objects:
            o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=objects is not None,
        export_apply=True, export_yup=True, export_extras=True,
        export_texcoords=True, export_normals=True, export_materials='EXPORT',
        export_vertex_color='ACTIVE', export_all_vertex_colors=False,
        export_image_format='AUTO',
        export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
        export_optimize_animation_size=True, export_skins=True, export_def_bones=False,
        export_morph=True, export_leaf_bone=False, export_rest_position_armature=True,
        export_reset_pose_bones=True, export_anim_single_armature=True,
    )
    return path


def aim(rest_dir, target_dir, parent_q=None):
    """Armature-space rotation turning a bone's rest direction toward target_dir.
    parent_q: the parent's armature-space rotation (children inherit it), so the result is relative."""
    t = Vector(target_dir).normalized()
    if parent_q is not None:
        t = parent_q.inverted() @ t
    return Vector(rest_dir).normalized().rotation_difference(t)


def bone_dirs(arm_obj):
    return {b.name: (b.tail_local - b.head_local).normalized() for b in arm_obj.data.bones}
