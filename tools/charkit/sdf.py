"""charkit.sdf — sculpt soft, figure-like shapes with signed distance fields.

A Field is a list of primitives combined with smooth union / subtraction (colors blend with the
shapes). It is evaluated on a regular voxel grid, but every primitive only touches the grid block
around its own bounding box, so hundreds of hair segments stay cheap. Marching cubes turns the
field into a mesh with per-vertex colors.

Coordinates: meters, Z up, characters face -Y (same as the rest of charkit).
"""
import math

import numpy as np
from skimage.measure import marching_cubes

from . import shapes as S

BIG = 1.0


def _norm(v):
    return np.sqrt(np.einsum('...i,...i->...', v, v))


# ----------------------------------------------------------------------------- primitive distance functions
# Each returns a callable f(P) -> distance for points P (..., 3), plus a bounding box (lo, hi).

def sphere(c, r):
    c = np.asarray(c, dtype=np.float32)
    return (lambda P: _norm(P - c) - r), (c - r, c + r)


def ellipsoid(c, radii, rot=None):
    c = np.asarray(c, dtype=np.float32)
    r = np.asarray(radii, dtype=np.float32)
    R = None if rot is None else rot_matrix(rot)

    def f(P):
        q = P - c
        if R is not None:
            q = q @ R  # into local frame
        k0 = _norm(q / r)
        k1 = _norm(q / (r * r))
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    m = float(r.max())
    return f, (c - m, c + m)


def round_cone(a, b, ra, rb):
    """Capsule between a and b with radii ra, rb (iq's exact round cone)."""
    a = np.asarray(a, dtype=np.float32)
    b = np.asarray(b, dtype=np.float32)
    ba = b - a
    l2 = float(ba @ ba)
    rr = ra - rb
    a2 = l2 - rr * rr
    il2 = 1.0 / max(l2, 1e-12)

    def f(P):
        pa = P - a
        y = pa @ ba
        z = y - l2
        xv = pa * l2 - y[..., None] * ba
        x2 = np.einsum('...i,...i->...', xv, xv)
        y2 = y * y * l2
        z2 = z * z * l2
        k = np.sign(rr) * rr * rr * x2
        out = np.empty(y.shape, dtype=np.float32)
        m1 = np.sign(z) * a2 * z2 > k
        m2 = np.sign(y) * a2 * y2 < k
        m3 = ~(m1 | m2)
        out[m1] = np.sqrt(x2[m1] + z2[m1]) * il2 - rb
        out[m2] = np.sqrt(x2[m2] + y2[m2]) * il2 - ra
        out[m3] = (np.sqrt(x2[m3] * a2 * il2) + y[m3] * rr) * il2 - ra
        return out
    lo = np.minimum(a - ra, b - rb)
    hi = np.maximum(a + ra, b + rb)
    return f, (lo, hi)


def ellipsoid_m(c, radii, R):
    """Ellipsoid whose local axes are the columns of R (3x3, world directions)."""
    c = np.asarray(c, dtype=np.float32)
    r = np.asarray(radii, dtype=np.float32)
    R = np.asarray(R, dtype=np.float32)

    def f(P):
        q = (P - c) @ R
        k0 = _norm(q / r)
        k1 = _norm(q / (r * r))
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    m = float(r.max())
    return f, (c - m, c + m)


def rounded_box(c, half, radius=0.0, rot=None):
    c = np.asarray(c, dtype=np.float32)
    h = np.asarray(half, dtype=np.float32) - radius
    R = None if rot is None else rot_matrix(rot)

    def f(P):
        q = P - c
        if R is not None:
            q = q @ R
        d = np.abs(q) - h
        return _norm(np.maximum(d, 0)) + np.minimum(d.max(axis=-1), 0) - radius
    m = float(_norm(np.asarray(half)))
    return f, (c - m, c + m)


def torus(c, R, r, axis=(0, 0, 1)):
    c = np.asarray(c, dtype=np.float32)
    ax = np.asarray(axis, dtype=np.float32)
    ax /= np.linalg.norm(ax)

    def f(P):
        q = P - c
        h = q @ ax
        rad = _norm(q - h[..., None] * ax)
        return np.sqrt((rad - R) ** 2 + h * h) - r
    m = R + r
    return f, (c - m, c + m)


def lathe(profile, center=(0, 0, 0), mod=None, theta=None, squash_y=1.0):
    """Solid of revolution around Z from a closed 2D profile [(r, z), ...] (counter-clockwise or not).
    mod(theta, z) -> radial scale (folds, scallops). theta=(t0, t1) keeps an angular wedge (radians,
    measured from +X toward +Y; the character's front is theta = -pi/2)."""
    prof = np.asarray(profile, dtype=np.float32)
    c = np.asarray(center, dtype=np.float32)
    rmax = float(prof[:, 0].max()) * 1.25
    zlo, zhi = float(prof[:, 1].min()), float(prof[:, 1].max())

    def f(P):
        q = P - c
        x, y = q[..., 0], q[..., 1] / squash_y
        th = np.arctan2(y, x)
        r = np.sqrt(x * x + y * y)
        if mod is not None:
            r = r / mod(th, q[..., 2])
        d = poly2d_distance(np.stack([r, q[..., 2]], axis=-1), prof)
        if theta is not None:
            t0, t1 = theta
            mid = (t0 + t1) / 2
            half = (t1 - t0) / 2
            dth = np.abs((th - mid + np.pi) % (2 * np.pi) - np.pi) - half
            d = np.maximum(d, dth * np.maximum(r, 0.02))
        return d
    return f, (c + np.array([-rmax, -rmax * squash_y, zlo - 0.02], dtype=np.float32),
               c + np.array([rmax, rmax * squash_y, zhi + 0.02], dtype=np.float32))


def slab(outline, thickness, frame_origin, frame_u, frame_v, round_r=None):
    """A flat 2D outline extruded to `thickness` and rounded (fins, flukes, wings, sign boards).
    The outline lives in the plane (origin, u, v); thickness is along u x v."""
    o = np.asarray(frame_origin, dtype=np.float32)
    u = np.asarray(frame_u, dtype=np.float32)
    u /= np.linalg.norm(u)
    v = np.asarray(frame_v, dtype=np.float32)
    v = v - (v @ u) * u
    v /= np.linalg.norm(v)
    n = np.cross(u, v)
    poly = np.asarray(outline, dtype=np.float32)
    t = thickness / 2
    rr = t if round_r is None else round_r

    def f(P):
        q = P - o
        uv = np.stack([q @ u, q @ v], axis=-1)
        d2 = poly2d_distance(uv, poly) + rr * 0.6
        dz = np.abs(q @ n) - (t - rr * 0.6)
        # rounded extrusion
        w = np.stack([np.maximum(d2, 0), np.maximum(dz, 0)], axis=-1)
        return np.minimum(np.maximum(d2, dz), 0) + _norm(w) - rr * 0.6
    pts3 = o + poly[:, :1] * u + poly[:, 1:] * v
    lo = pts3.min(axis=0) - thickness - 0.01
    hi = pts3.max(axis=0) + thickness + 0.01
    return f, (lo, hi)


def poly2d_distance(p, poly):
    """Signed distance from 2D points p (..., 2) to a closed polygon (M, 2); negative inside."""
    d = np.full(p.shape[:-1], np.inf, dtype=np.float32)
    s = np.ones(p.shape[:-1], dtype=np.float32)
    n = len(poly)
    for i in range(n):
        a = poly[i]
        b = poly[(i + 1) % n]
        e = b - a
        w = p - a
        t = np.clip((w @ e) / max(float(e @ e), 1e-12), 0, 1)
        bvec = w - t[..., None] * e
        d = np.minimum(d, np.einsum('...i,...i->...', bvec, bvec))
        c1 = p[..., 1] >= a[1]
        c2 = p[..., 1] < b[1]
        c3 = e[0] * w[..., 1] > e[1] * w[..., 0]
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
    return s * np.sqrt(d)


def rot_matrix(rot):
    rx, ry, rz = [math.radians(a) for a in rot]
    Rx = np.array([[1, 0, 0], [0, math.cos(rx), -math.sin(rx)], [0, math.sin(rx), math.cos(rx)]])
    Ry = np.array([[math.cos(ry), 0, math.sin(ry)], [0, 1, 0], [-math.sin(ry), 0, math.cos(ry)]])
    Rz = np.array([[math.cos(rz), -math.sin(rz), 0], [math.sin(rz), math.cos(rz), 0], [0, 0, 1]])
    return (Rz @ Ry @ Rx).astype(np.float32)


# ----------------------------------------------------------------------------- field

class Field:
    def __init__(self, name):
        self.name = name
        self.ops = []  # (kind, fn, bbox, color, k)

    def add(self, prim, color=(1, 1, 1), k=0.004):
        f, bb = prim
        self.ops.append(('union', f, bb, np.asarray(color, dtype=np.float32), k))
        return self

    def carve(self, prim, k=0.004):
        f, bb = prim
        self.ops.append(('sub', f, bb, None, k))
        return self

    def paint(self, prim, color, k=0.004):
        """Recolor inside a region without changing the shape (color blends over k)."""
        f, bb = prim
        self.ops.append(('paint', f, bb, np.asarray(color, dtype=np.float32), k))
        return self

    def tube(self, path, radii, color=(1, 1, 1), k=0.004, n=None, inner_k=None, closed=False):
        """Variable-radius tube through `path` (smooth Catmull-Rom), built from round cones."""
        path = np.asarray(path, dtype=np.float32)
        L = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
        n = n or max(4, int(L / 0.012) + 2)
        P = S.catmull_rom(path, n, closed=closed).astype(np.float32)
        s = np.linspace(0, 1, n)
        R = np.interp(s, np.linspace(0, 1, len(radii)), radii) if np.ndim(radii) else np.full(n, radii)
        segs = [(P[i], P[i + 1], R[i], R[i + 1]) for i in range(n - 1)]
        if closed:
            segs.append((P[-1], P[0], R[-1], R[0]))
        # consecutive segments are unioned with a tiny k so the tube stays smooth
        first = True
        for a, b, ra, rb in segs:
            f, bb = round_cone(a, b, max(ra, 1e-4), max(rb, 1e-4))
            self.ops.append(('union', f, bb, np.asarray(color, dtype=np.float32),
                             k if first else (inner_k if inner_k is not None else 0.0015)))
            first = False
        return self

    def ribbon(self, path, half_w, half_t, color=(1, 1, 1), k=0.006, up=(0, 0, 1), n=None, inner_k=0.004, closed=False, resample=True):
        """A flattened lock: overlapping ellipsoids along a smooth path, wide along the binormal,
        thin along the normal (initial normal = `up`, parallel transported)."""
        path = np.asarray(path, dtype=np.float32)
        L = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
        if resample:
            n = n or max(5, int(L / 0.01) + 2)
            P = S.catmull_rom(path, n, closed=closed).astype(np.float32)
        else:
            P = path
            n = len(P)
        T, N, B = S.transport_frames(P, up, closed=closed)
        s = np.linspace(0, 1, n)
        W = np.interp(s, np.linspace(0, 1, len(half_w)), half_w) if np.ndim(half_w) else np.full(n, half_w)
        H = np.interp(s, np.linspace(0, 1, len(half_t)), half_t) if np.ndim(half_t) else np.full(n, half_t)
        step = L / max(n - 1, 1)
        for i in range(n):
            R = np.stack([T[i], B[i], N[i]], axis=1)
            a = max(step * 1.1, min(W[i], H[i]) * 1.2)
            self.ops.append(('union',) + ellipsoid_m(P[i], (a, max(W[i], 1e-4), max(H[i], 1e-4)), R) +
                            (np.asarray(color, dtype=np.float32), k if i == 0 else inner_k))
        return self

    # --------------------------------------------------------------------- evaluation
    def bounds(self, pad=0.02):
        lo = np.min([op[2][0] for op in self.ops if op[0] == 'union'], axis=0) - pad
        hi = np.max([op[2][1] for op in self.ops if op[0] == 'union'], axis=0) + pad
        return lo, hi

    def evaluate(self, voxel=0.0025, bounds=None):
        lo, hi = bounds or self.bounds()
        shape = np.ceil((hi - lo) / voxel).astype(int) + 1
        D = np.full(shape, BIG, dtype=np.float32)
        C = np.zeros(tuple(shape) + (3,), dtype=np.float32)
        axes = [lo[i] + np.arange(shape[i], dtype=np.float32) * voxel for i in range(3)]
        for kind, f, (blo, bhi), col, k in self.ops:
            m = k + 3 * voxel
            i0 = np.clip(np.floor((np.asarray(blo) - m - lo) / voxel).astype(int), 0, shape - 1)
            i1 = np.clip(np.ceil((np.asarray(bhi) + m - lo) / voxel).astype(int) + 1, 1, shape)
            if np.any(i1 <= i0):
                continue
            X, Y, Z = np.meshgrid(axes[0][i0[0]:i1[0]], axes[1][i0[1]:i1[1]], axes[2][i0[2]:i1[2]], indexing='ij')
            P = np.stack([X, Y, Z], axis=-1)
            d2 = f(P).astype(np.float32)
            sl = (slice(i0[0], i1[0]), slice(i0[1], i1[1]), slice(i0[2], i1[2]))
            d1 = D[sl]
            c1 = C[sl]
            if kind == 'union':
                if k <= 0:
                    h = (d2 < d1).astype(np.float32)
                    d = np.minimum(d1, d2)
                else:
                    h = np.clip(0.5 + 0.5 * (d1 - d2) / k, 0, 1)
                    d = d1 * (1 - h) + d2 * h - k * h * (1 - h)
                C[sl] = c1 * (1 - h[..., None]) + col * h[..., None]
                D[sl] = d
            elif kind == 'sub':
                h = np.clip(0.5 - 0.5 * (d1 + d2) / k, 0, 1)
                D[sl] = d1 * (1 - h) + (-d2) * h + k * h * (1 - h)
            elif kind == 'paint':
                h = np.clip(0.5 - 0.5 * d2 / k, 0, 1)
                C[sl] = c1 * (1 - h[..., None]) + col * h[..., None]
        self.grid = (D, C, lo, voxel)
        return self.grid

    def mesh(self, voxel=0.0025, bounds=None):
        D, C, lo, vx = self.evaluate(voxel, bounds)
        verts, faces, normals, _ = marching_cubes(D, level=0.0, spacing=(vx, vx, vx), allow_degenerate=False)
        verts = verts + lo
        # trilinear color lookup
        g = (verts - lo) / vx
        i0 = np.clip(np.floor(g).astype(int), 0, np.array(D.shape) - 2)
        t = g - i0
        col = np.zeros((len(verts), 3), dtype=np.float32)
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                    col += C[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz] * w[:, None]
        # skimage's default ('descent') winding already makes normals point toward larger values,
        # i.e. out of our negative-inside field
        return verts, faces, col


def sample(grid, pts):
    """Trilinear sample of an evaluated distance grid at points (N, 3)."""
    D, _, lo, vx = grid
    g = (np.asarray(pts, dtype=np.float32) - lo) / vx
    i0 = np.clip(np.floor(g).astype(int), 0, np.array(D.shape) - 2)
    t = np.clip(g - i0, 0, 1)
    out = np.zeros(len(g), dtype=np.float32)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                out += D[i0[:, 0] + dx, i0[:, 1] + dy, i0[:, 2] + dz] * w
    return out


def cavity(grid, verts, normals, dist=0.008, strength=0.45):
    """Darkening factor (1 = open, <1 = in a crease) from how close the field gets just outside the surface."""
    n = normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-9)
    acc = np.zeros(len(verts), dtype=np.float32)
    for k, dd in enumerate((dist * 0.5, dist, dist * 2)):
        d = sample(grid, verts + n * dd)
        acc += np.clip((dd - d) / dd, 0, 1) / (k + 1)
    acc /= (1 + 0.5 + 1 / 3)
    return 1 - strength * acc


def frill(field, path, height, thick, pleats, amp, color, outward, k=0.006, closed=False, n=None, edge=0.14, inner_k=0.003):
    """Gathered fabric frill standing out from `path`: a thin strip, `height` wide, pleated with
    `pleats` waves of amplitude `amp`. outward(P, T) gives the direction the frill extends to."""
    path = np.asarray(path, dtype=np.float32)
    L = float(np.sum(np.linalg.norm(np.diff(path, axis=0), axis=1)))
    n = n or max(24, pleats * 8)
    P = S.catmull_rom(path, n, closed=closed).astype(np.float32)
    T = (np.roll(P, -1, axis=0) - np.roll(P, 1, axis=0)) if closed else np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    O = np.asarray([outward(P[i], T[i]) for i in range(n)], dtype=np.float32)
    O -= np.einsum('ij,ij->i', O, T)[:, None] * T
    O /= np.linalg.norm(O, axis=1, keepdims=True)
    Nn = np.cross(T, O)
    s = np.linspace(0, 1, n, endpoint=not closed)
    wave = np.sin(2 * np.pi * pleats * s)
    hw = height * 0.5 * (1 + edge * np.cos(2 * np.pi * pleats * s))
    C = P + O * hw[:, None] + Nn * (amp * wave)[:, None]
    field.ribbon(C, hw, thick, color, k=k, up=Nn[0], closed=closed, resample=False, inner_k=inner_k)
    return field
