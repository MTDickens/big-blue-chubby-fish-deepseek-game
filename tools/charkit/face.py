"""charkit.face — texture-atlas decals projected onto a surface (eyes, mouth, blush, emblems)."""
import bpy  # noqa: F401  (must precede mathutils when running as a module)
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import core


def cell_uv(col, row, cells=4):
    """UV rectangle (u0, v0, u1, v1) of an atlas cell; row 0 is the top row of the image."""
    s = 1.0 / cells
    u0 = col * s
    v1 = 1.0 - row * s
    return u0, v1 - s, u0 + s, v1


def surface_bvh(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    return [BVHTree.FromObject(o, dg) for o in objs]


def _cast(bvhs, origin, direction):
    best = None
    for b in bvhs:
        hit = b.ray_cast(origin, direction)
        if hit[0] is not None and (best is None or hit[3] < best[3]):
            best = hit
    return best


def decal(name, bvhs, center, size, cell, mat, mirror=False, res=10, offset=0.0012,
          direction=(0, 1, 0), right=(1, 0, 0), rotate=0.0, cells=4):
    """Project an atlas cell onto the surfaces in `bvhs`.

    The grid lies in the plane spanned by `right` and up (= direction x right) and is shot along
    `direction` (default: from the front of a character facing -Y toward +Y).
    """
    d = Vector(direction).normalized()
    r = Vector(right).normalized()
    up = r.cross(d).normalized()  # e.g. right +X, shot along +Y -> up +Z
    if rotate:
        import math
        c, s = math.cos(rotate), math.sin(rotate)
        r, up = r * c + up * s, up * c - r * s
    u0, v0, u1, v1 = cell_uv(*cell, cells=cells)
    if mirror:
        u0, u1 = u1, u0
    w, h = size
    C = Vector(center)
    verts, uvs = [], []
    for j in range(res + 1):
        for i in range(res + 1):
            a, b = i / res - 0.5, j / res - 0.5
            p = C + r * (a * w) + up * (b * h)
            hit = _cast(bvhs, p - d * 0.5, d)
            if hit is None:
                loc, nrm = p, -d
            else:
                loc, nrm = hit[0], hit[1]
                if nrm.dot(d) > 0:
                    nrm = -nrm
            verts.append(tuple(loc + nrm * offset))
            uvs.append((u0 + (u1 - u0) * i / res, v0 + (v1 - v0) * j / res))
    faces = []
    for j in range(res):
        for i in range(res):
            a = j * (res + 1) + i
            faces.append((a, a + 1, a + res + 2, a + res + 1))
    o = core.mesh_from_arrays(name, np.array(verts), faces, uvs=np.array(uvs), mat=mat)
    core.set_color(o, (1, 1, 1, 1))
    return o
