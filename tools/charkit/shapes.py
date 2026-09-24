"""charkit.shapes — numpy geometry generators that return (verts, faces, uvs) or Blender objects.

All generators work in meters, Z-up, character facing -Y.
"""
import math

import bpy  # must be imported before bmesh/mathutils when running as a module
import bmesh
import numpy as np

from . import core


# --------------------------------------------------------------------------- curves

def _as_fn(v):
    if callable(v):
        return v
    if isinstance(v, (list, tuple, np.ndarray)) and np.ndim(v) == 1 and len(v) > 1:
        arr = np.asarray(v, dtype=float)
        xs = np.linspace(0, 1, len(arr))
        return lambda s: np.interp(s, xs, arr)
    return lambda s: np.full_like(np.asarray(s, dtype=float), float(v))


def catmull_rom(points, n, alpha=0.5, closed=False):
    """Centripetal Catmull-Rom through `points`, resampled to n points uniformly by arc length."""
    P = np.asarray(points, dtype=float)
    if len(P) < 2:
        raise ValueError('need at least two points')
    if closed:
        P = np.vstack([P[-1], P, P[0], P[1]])
    elif len(P) == 2:
        P = np.vstack([P[0], P[0] * 2 / 3 + P[1] / 3, P[0] / 3 + P[1] * 2 / 3, P[1]])
        P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    else:
        P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    dense = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        for t in np.linspace(t1, t2, 24, endpoint=False):
            a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
            b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
            dense.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    dense.append(P[-2])
    D = np.array(dense)
    seg = np.linalg.norm(np.diff(D, axis=0), axis=1)
    L = np.r_[0, np.cumsum(seg)]
    targets = np.linspace(0, L[-1], n + (1 if closed else 0))
    if closed:
        targets = targets[:-1]
    out = np.stack([np.interp(targets, L, D[:, k]) for k in range(3)], axis=1)
    return out


def transport_frames(path, up=(0, 0, 1), closed=False):
    P = np.asarray(path, dtype=float)
    if closed:
        T = np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)
    else:
        T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    up = np.asarray(up, dtype=float)
    n0 = up - (up @ T[0]) * T[0]
    if np.linalg.norm(n0) < 1e-6:
        alt = np.array([1.0, 0, 0]) if abs(T[0][0]) < 0.9 else np.array([0, 1.0, 0])
        n0 = alt - (alt @ T[0]) * T[0]
    N = [n0 / np.linalg.norm(n0)]
    for i in range(1, len(P)):
        v = np.cross(T[i - 1], T[i])
        s = np.linalg.norm(v)
        n = N[-1]
        if s > 1e-9:
            v /= s
            ang = math.atan2(s, float(T[i - 1] @ T[i]))
            n = n * math.cos(ang) + np.cross(v, n) * math.sin(ang) + v * (v @ n) * (1 - math.cos(ang))
        n = n - (n @ T[i]) * T[i]
        N.append(n / np.linalg.norm(n))
    N = np.array(N)
    B = np.cross(T, N)
    return T, N, B


# --------------------------------------------------------------------------- profiles (closed 2D loops, CCW)

def prof_circle(m=8):
    a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    return np.stack([np.cos(a), np.sin(a)], axis=1)


def prof_lens(m=10, sharp=0.6):
    """Flattened leaf/lens cross-section, pointed at +-x (good for anime hair clumps)."""
    a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    x = np.cos(a)
    y = np.sin(a) * (np.abs(np.sin(a)) ** (sharp * 0.5))
    return np.stack([x, y], axis=1)


def prof_ribbon(m=8, bulge=0.25):
    """Thin rounded rectangle (ribbons, bows, straps)."""
    a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    x = np.sign(np.cos(a)) * np.abs(np.cos(a)) ** 0.35
    y = np.sin(a) * bulge
    return np.stack([x, y], axis=1)


# --------------------------------------------------------------------------- sweep

def sweep(path, n=24, profile=None, width=0.05, thick=None, up=(0, 0, 1), twist=0.0,
          cap0=True, cap1=True, tip0=False, tip1=False, closed=False, resample=True, offset=None):
    """Sweep a 2D profile along a path.

    width/thick: scalar | list (interpolated along s) | fn(s) -> half-size along binormal / normal.
    twist: radians, same forms.  offset: fn(s) -> (dx, dy) shift of the profile in the (B, N) frame.
    tip0/tip1 end the tube in a single point (hair tips, horns).
    Returns (verts, faces, uvs) with uv = (around, along).
    """
    prof = prof_circle(8) if profile is None else np.asarray(profile, dtype=float)
    M = len(prof)
    P = catmull_rom(path, n, closed=closed) if resample else np.asarray(path, dtype=float)
    n = len(P)
    T, N, B = transport_frames(P, up, closed=closed)
    s = np.linspace(0, 1, n, endpoint=not closed)
    w = _as_fn(width)(s)
    th = _as_fn(thick if thick is not None else width)(s)
    tw = _as_fn(twist)(s)
    off = offset(s) if offset else np.zeros((n, 2))
    verts, uvs = [], []
    ring_ids = []
    for i in range(n):
        if (i == n - 1 and tip1 and not closed) or (i == 0 and tip0 and not closed):
            ring_ids.append([len(verts)])
            verts.append(P[i])
            uvs.append((0.5, s[i]))
            continue
        c, sn = math.cos(tw[i]), math.sin(tw[i])
        ids = []
        for j, (x, y) in enumerate(prof):
            xr, yr = x * c - y * sn, x * sn + y * c
            p = P[i] + B[i] * (xr * w[i] + off[i][0]) + N[i] * (yr * th[i] + off[i][1])
            ids.append(len(verts))
            verts.append(p)
            uvs.append((j / M, s[i]))
        ring_ids.append(ids)
    faces = []
    rng = range(n) if closed else range(n - 1)
    for i in rng:
        a, b = ring_ids[i], ring_ids[(i + 1) % n]
        if len(a) == 1 and len(b) > 1:
            for j in range(M):
                faces.append((a[0], b[j], b[(j + 1) % M]))
        elif len(b) == 1 and len(a) > 1:
            for j in range(M):
                faces.append((a[j], a[(j + 1) % M], b[0]))
        else:
            for j in range(M):
                faces.append((a[j], a[(j + 1) % M], b[(j + 1) % M], b[j]))
    if not closed:
        if cap0 and not tip0:
            c0 = len(verts)
            verts.append(P[0])
            uvs.append((0.5, 0.0))
            r = ring_ids[0]
            for j in range(M):
                faces.append((c0, r[(j + 1) % M], r[j]))
        if cap1 and not tip1:
            c1 = len(verts)
            verts.append(P[-1])
            uvs.append((0.5, 1.0))
            r = ring_ids[-1]
            for j in range(M):
                faces.append((c1, r[j], r[(j + 1) % M]))
    return np.array(verts), faces, np.array(uvs)


# --------------------------------------------------------------------------- lathe

def lathe(profile_rz, n_seg=48, mod=None, cap_bottom=False, cap_top=False, theta0=0.0, theta_len=2 * np.pi):
    """Surface of revolution around Z. profile_rz: (M,2) (radius, z) from bottom to top.
    mod(theta (n,), t (M,)) -> (n, M) radial scale, for wavy hems / non-round sections."""
    prof = np.asarray(profile_rz, dtype=float)
    M = len(prof)
    full = abs(theta_len - 2 * np.pi) < 1e-6
    th = theta0 + np.linspace(0, theta_len, n_seg, endpoint=not full)
    t = np.linspace(0, 1, M)
    S = mod(th, t) if mod else np.ones((len(th), M))
    verts, uvs = [], []
    for i in range(M):
        for k in range(len(th)):
            r = prof[i, 0] * S[k, i]
            verts.append((r * math.cos(th[k]), r * math.sin(th[k]), prof[i, 1]))
            uvs.append((k / len(th), t[i]))
    K = len(th)
    faces = []
    kr = range(K) if full else range(K - 1)
    for i in range(M - 1):
        for k in kr:
            a = i * K + k
            b = i * K + (k + 1) % K
            faces.append((a, b, b + K, a + K))
    if cap_bottom:
        c = len(verts)
        verts.append((0, 0, prof[0, 1]))
        uvs.append((0.5, 0))
        for k in kr:
            faces.append((c, (k + 1) % K, k))
    if cap_top:
        c = len(verts)
        verts.append((0, 0, prof[-1, 1]))
        uvs.append((0.5, 1))
        base = (M - 1) * K
        for k in kr:
            faces.append((c, base + k, base + (k + 1) % K))
    return np.array(verts), faces, np.array(uvs)


# --------------------------------------------------------------------------- spheres

def sphere(radii=(1, 1, 1), nu=32, nv=18, deform=None):
    """UV sphere centered at origin. deform(p (N,3) on the unit sphere) -> (N,3) displaced points
    (applied before scaling by radii)."""
    verts, uvs = [(0, 0, -1)], [(0.5, 0)]
    for j in range(1, nv):
        phi = -np.pi / 2 + np.pi * j / nv
        for i in range(nu):
            th = 2 * np.pi * i / nu
            verts.append((math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)))
            uvs.append((i / nu, j / nv))
    verts.append((0, 0, 1))
    uvs.append((0.5, 1))
    V = np.array(verts)
    if deform:
        V = deform(V)
    V = V * np.asarray(radii, dtype=float)
    faces = []
    for i in range(nu):
        faces.append((0, 1 + (i + 1) % nu, 1 + i))
    for j in range(nv - 2):
        r0 = 1 + j * nu
        r1 = r0 + nu
        for i in range(nu):
            faces.append((r0 + i, r0 + (i + 1) % nu, r1 + (i + 1) % nu, r1 + i))
    top = len(V) - 1
    r0 = 1 + (nv - 2) * nu
    for i in range(nu):
        faces.append((r0 + i, r0 + (i + 1) % nu, top))
    return V, faces, np.array(uvs)


# --------------------------------------------------------------------------- object helpers

def obj(name, geo, mat=None, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), colors=None, smooth=True, fix_normals=True):
    """Make a Blender object from a (verts, faces, uvs) tuple and bake the transform into the mesh."""
    V, F, UV = geo
    o = core.mesh_from_arrays(name, V, F, uvs=UV, colors=colors, mat=mat, smooth=smooth)
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    o.scale = scale
    bpy.context.view_layer.update()
    core.apply_transform(o)
    if fix_normals:
        recalc_normals(o)
    return o


def recalc_normals(o, inside=False):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    if inside:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return o


def outline_obj(name, outline, mat=None, plane='XZ', thickness=0.01, subdiv=2, loc=(0, 0, 0), rot=(0, 0, 0), pillow=0.0):
    """Flat 2D outline (M,2) turned into a rounded slab (fins, flukes, ears, wing membranes).
    plane: which world plane the 2D coords map to ('XZ' -> x=u, z=v, thickness along Y)."""
    out = np.asarray(outline, dtype=float)
    if plane == 'XZ':
        V = np.stack([out[:, 0], np.zeros(len(out)), out[:, 1]], axis=1)
    elif plane == 'XY':
        V = np.stack([out[:, 0], out[:, 1], np.zeros(len(out))], axis=1)
    else:  # YZ
        V = np.stack([np.zeros(len(out)), out[:, 0], out[:, 1]], axis=1)
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in V]
    bm.faces.new(vs)
    bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
    bmesh.ops.subdivide_edges(bm, edges=[e for e in bm.edges if not e.is_boundary], cuts=1, use_grid_fill=True)
    bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=bm.edges[:])
    bm.to_mesh(me)
    bm.free()
    o = core.link(bpy.data.objects.new(name, me))
    if mat is not None:
        me.materials.append(mat)
    core.add_modifier(o, 'SOLIDIFY', thickness=thickness, offset=0.0, use_even_offset=True, use_rim=True)
    if subdiv:
        core.add_modifier(o, 'SUBSURF', levels=subdiv, render_levels=subdiv, quality=3)
    core.apply_modifiers(o)
    if pillow > 0:
        # plush look: thicken the middle, keep the rim thin (scale the thickness axis by distance to the rim)
        co = core.verts_of(o, world=False)
        ax = {'XZ': 1, 'XY': 2, 'YZ': 0}[plane]
        uv_axes = [a for a in range(3) if a != ax]
        c2 = co[:, uv_axes]
        rim = V[:, uv_axes]
        d = np.min(np.linalg.norm(c2[:, None, :] - rim[None, :, :], axis=2), axis=1)
        k = 1.0 + pillow * np.sqrt(d / max(d.max(), 1e-9))
        co[:, ax] *= k
        core.set_verts(o, co)
    o.data.shade_smooth()
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    bpy.context.view_layer.update()
    core.apply_transform(o)
    recalc_normals(o)
    return o


def merge_geos(*geos):
    V, F, UV = [], [], []
    off = 0
    for v, f, uv in geos:
        V.append(np.asarray(v))
        UV.append(np.asarray(uv))
        F.extend([tuple(i + off for i in face) for face in f])
        off += len(v)
    return np.vstack(V), F, np.vstack(UV)


def transform_geo(geo, loc=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1)):
    """Apply scale, then XYZ Euler rotation (degrees), then translation to a geometry tuple."""
    V, F, UV = geo
    V = np.asarray(V, dtype=float) * np.asarray(scale, dtype=float)
    rx, ry, rz = [math.radians(a) for a in rot]
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    R = Rz @ Ry @ Rx
    V = V @ R.T + np.asarray(loc, dtype=float)
    return V, F, UV


def mirror_x(geo):
    V, F, UV = geo
    V = np.asarray(V, dtype=float).copy()
    V[:, 0] *= -1
    F = [tuple(reversed(f)) for f in F]
    return V, F, UV
