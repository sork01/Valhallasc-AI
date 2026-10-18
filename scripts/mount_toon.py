"""A small 3D toon renderer for the mount sprites (make_mount_sprites.py).

Ellipsoids are ray-cast analytically in the same orthographic 2:1 camera as the class sprites (cel_common.Ink): scene
x is screen right, y is away from the camera, z is up; a scene point lands at (AX + x*PX, AY - (y*.5 + z*sqrt(3)/2)*PX)
and its depth is y*sqrt(3)/2 - z*.5, smaller is nearer. Because the depth matches the class atlases' encoding exactly
(R*256+G = (depth + 512) * 64), the client can composite a rider into a mount pixel by pixel.

Model space: origin on the ground under the saddle, +y is the way the animal faces, +z is up, x is its right/left.
`psi_for(facing)` turns it so it faces one of the eight screen directions (S is towards the camera).
Shading is hard cel bands (no dither); an outline surrounds the silhouette and the nearer of two overlapping parts.
"""
import math

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

FW = FH = 160
AX, AY, PX, SS = 80, 119, 1.03, 3
SINE, COSE = .5, math.sqrt(3) / 2
DIRS = ['S', 'SW', 'W', 'NW', 'N', 'NE', 'E', 'SE']
DIRVEC = {'S': (0, -1), 'SW': (-1, -1), 'W': (-1, 0), 'NW': (-1, 1), 'N': (0, 1), 'NE': (1, 1), 'E': (1, 0), 'SE': (1, -1)}
# Scene axes of the camera: screen right, screen up, towards the camera.
CAM_RIGHT, CAM_UP, CAM_NEAR = np.array([1, 0, 0.]), np.array([0, SINE, COSE]), np.array([0, -COSE, SINE])


def V(*a):
    return np.array(a, float)


def unit(v):
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else V(0, 0, 1)


def rotz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def psi_for(name):
    sx, sy = DIRVEC[name]
    return math.atan2(-sx, sy)


def frame_z(axis, hint=(1, 0, 0)):
    """Orthonormal matrix whose third column is `axis`."""
    z = unit(axis)
    h = V(*hint) if abs(np.dot(unit(hint), z)) < .9 else V(0, 1, 0)
    x = unit(np.cross(h, z))
    return np.stack([x, np.cross(z, x), z], 1)


class Ell:
    """An ellipsoid: centre c, radii r along the columns of M. `cam` (right, up, near) offsets the centre along the
    camera axes at render time, which is how an eye highlight stays on the upper left whichever way the animal faces."""
    def __init__(self, c, r, mat, M=None, cam=None, bias=0.):
        self.c, self.r, self.mat, self.cam, self.bias = np.array(c, float), np.array(r, float), mat, cam, bias
        self.M = np.eye(3) if M is None else np.array(M, float)


def limb(a, b, r0, mat, r1=None, ext=0., bias=0.):
    """A stretched ellipsoid from a to b with radius r0 (r1 for a tapered limb is approximated by the mean)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    r = r0 if r1 is None else (r0 + r1) / 2
    return Ell((a + b) / 2, (r, r, np.linalg.norm(b - a) / 2 + ext), mat, frame_z(b - a), bias=bias)


def cone(base, tip, r, mat, bias=0.):
    """A horn, ear, claw or fang: an ellipsoid standing on `base` and reaching `tip`, radius r at the base end."""
    base, tip = np.asarray(base, float), np.asarray(tip, float)
    length = np.linalg.norm(tip - base)
    return Ell(base + (tip - base) * .38, (r * .62, r * .62, length * .62), mat, frame_z(tip - base), bias=bias)


def ik2(S, T, l1, l2, pole):
    """Two-bone IK: the joint between S and T (T is clamped to reach), bending towards `pole`. -> (joint, end)."""
    v = T - S
    d = np.linalg.norm(v)
    dirv = v / max(d, 1e-9)
    d = min(max(d, abs(l1 - l2) + .5), l1 + l2 - .05)
    end = S + dirv * d
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    h = math.sqrt(max(l1 * l1 - a * a, 0))
    pv = pole - dirv * (pole @ dirv)
    pv = unit(pv) if np.linalg.norm(pv) > 1e-6 else unit(np.cross(dirv, V(1, 0, 0)))
    return S + dirv * a + pv * h, end


class Look:
    """The materials of one mount: name -> four tones (dark to light), plus flat materials with a fixed tone."""
    def __init__(self, mats, flat=None):
        self.names = list(mats)
        self.mats = mats
        self.flat = flat or {}
        self.index = {n: i for i, n in enumerate(self.names)}
        palette = ['#00000000', '#1d1322', '#ffffff']
        for n in self.names:
            palette += mats[n]
        self.palette = self.dedupe(palette)
        assert len(self.palette) <= 255, len(self.palette)

    @staticmethod
    def dedupe(palette):
        """PixelFlow merges identical colours and shifts every later index, so nudge repeats along the blue channel."""
        seen, out = set(), list(palette)
        for i, c in enumerate(out):
            if i == 0:
                seen.add(c)
                continue
            r, g, b = [int(c[k:k + 2], 16) for k in (1, 3, 5)]
            step = 0
            while c in seen:
                step += 1
                c = '#%02x%02x%02x' % (r, g, b - step if b >= step else b + step)
            seen.add(c)
            out[i] = c
        return out

    def rgba_table(self):
        return np.array([[int(c[j:j + 2], 16) for j in (1, 3, 5)] + [0 if i == 0 else 255] for i, c in enumerate(self.palette)], np.uint8)


LIGHT = unit(V(-.5, -.42, .75))


def render(prims, psi, look, flash=False):
    """-> (index image FHxFW uint8, depth image float32 with inf where empty)."""
    R = rotz(psi)
    Rinv = R.T
    d_s = V(0, COSE, -SINE)
    d_c = Rinv @ d_s
    NX, NY = FW * SS, FH * SS
    xs = ((np.arange(NX) + .5) / SS - AX) / PX
    ys = (AY - (np.arange(NY) + .5) / SS) / PX
    best_t = np.full((NY, NX), np.inf, np.float32)
    best_m = np.full((NY, NX), -1, np.int16)
    best_n = np.zeros((NY, NX, 3), np.float32)
    best_b = np.zeros((NY, NX), np.float32)
    for p in prims:
        c = p.c
        if p.cam is not None:
            scene = R @ p.c + p.cam[0] * CAM_RIGHT + p.cam[1] * CAM_UP + p.cam[2] * CAM_NEAR
            c = Rinv @ scene
        cs = R @ c
        u0, v0 = cs[0], cs[1] * SINE + cs[2] * COSE
        rb = float(np.linalg.norm(p.M * p.r, axis=0).max()) * 1.02
        x0 = max(0, int(math.floor(((u0 - rb) * PX + AX) * SS)))
        x1 = min(NX, int(math.ceil(((u0 + rb) * PX + AX) * SS)) + 1)
        y0 = max(0, int(math.floor((AY - (v0 + rb) * PX) * SS)))
        y1 = min(NY, int(math.ceil((AY - (v0 - rb) * PX) * SS)) + 1)
        if x1 <= x0 or y1 <= y0:
            continue
        ug, vg = np.meshgrid(xs[x0:x1], ys[y0:y1])
        ox, oy, oz = ug, vg * SINE, vg * COSE
        oc = np.stack([Rinv[0, 0] * ox + Rinv[0, 1] * oy, Rinv[1, 0] * ox + Rinv[1, 1] * oy, oz], -1).reshape(-1, 3) - c
        ol = (oc @ p.M) / p.r
        dl = (d_c @ p.M) / p.r
        a = dl @ dl
        b = ol @ dl
        cc = (ol * ol).sum(1) - 1
        disc = b * b - a * cc
        hit = disc > 0
        t = (-b - np.sqrt(np.where(hit, disc, 0))) / a
        nl = (ol + t[:, None] * dl) / p.r          # gradient of the unit sphere in local space, divided by r for the true normal
        n_c = nl @ p.M.T
        n_c /= np.linalg.norm(n_c, axis=1, keepdims=True) + 1e-9
        sl = (slice(y0, y1), slice(x0, x1))
        cur = best_t[sl].reshape(-1)
        upd = hit & (t < cur)
        if not upd.any():
            continue
        shape = (y1 - y0, x1 - x0)
        best_t[sl] = np.where(upd, t, cur).astype(np.float32).reshape(shape)
        best_m[sl] = np.where(upd, look.index[p.mat], best_m[sl].reshape(-1)).reshape(shape)
        best_n[sl] = np.where(upd[:, None], n_c @ R.T, best_n[sl].reshape(-1, 3)).reshape(shape + (3,))
        best_b[sl] = np.where(upd, p.bias, best_b[sl].reshape(-1)).reshape(shape)
    return resolve(best_t, best_m, best_n, best_b, look, flash)


def resolve(best_t, best_m, best_n, best_b, look, flash):
    cov = best_m >= 0
    diff = np.clip(best_n @ LIGHT, 0, 1)
    sky = np.clip(best_n[..., 2], 0, 1)
    sh = .27 + .6 * diff + .1 * sky + best_b
    for name, tone in look.flat.items():
        sh = np.where(best_m == look.index[name], (tone + .5) / 4, sh)

    def collapse(a):
        return a.reshape(FH, SS, FW, SS).transpose(0, 2, 1, 3).reshape(FH, FW, SS * SS)

    mm, cv, shs, tt = collapse(best_m), collapse(cov), collapse(sh), collapse(best_t)
    counts = np.stack([((mm == k) & cv).sum(-1) for k in range(len(look.names))], -1)
    mat = counts.argmax(-1)
    alpha = cv.sum(-1) >= SS * SS * .45
    sel = (mm == mat[..., None]) & cv
    tone = (shs * sel).sum(-1) / np.maximum(sel.sum(-1), 1)
    depth = np.where(cv, tt, np.inf).min(-1)
    level = np.where(tone < .40, 0, np.where(tone < .58, 1, np.where(tone < .80, 2, 3)))
    idx = (3 + 4 * mat + level).astype(np.uint8)
    if flash:
        idx = np.full_like(idx, 2)
    else:
        # Inner outline: a pixel with a much nearer surface beside it takes its material's darkest tone.
        far = np.zeros_like(alpha)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nd = np.roll(depth, (dy, dx), (0, 1))
            na = np.roll(alpha, (dy, dx), (0, 1))
            far |= alpha & na & (nd < depth - 3.2)
        idx = np.where(far, (3 + 4 * mat).astype(np.uint8), idx)
    out = np.zeros((FH, FW), np.uint8)
    out[alpha] = idx[alpha]
    ring = ndi.binary_dilation(alpha, structure=ndi.generate_binary_structure(2, 1)) & ~alpha
    out[ring] = 1
    nearest = ndi.distance_transform_edt(~alpha, return_distances=False, return_indices=True)
    resolved = np.where(alpha, depth, depth[tuple(nearest)])
    return out, np.where(out > 0, resolved, np.inf).astype(np.float32)


def to_image(idx, look, ground=None):
    return Image.fromarray(look.rgba_table()[idx], 'RGBA')
