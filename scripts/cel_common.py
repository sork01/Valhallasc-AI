"""Shared machinery for the layered anime-cel class sprites (hunter, mage, warrior, assassin).

A class script defines its palette (MATS), clips (pose functions), gear names and a render_frame(clip, facing, k)
that returns {part: (index, depth)} for every layer, then hands a Sheet to sheet.cli(). This module owns everything
else: the cel renderer (Ink), the joint rig helpers (skeleton, base_body, head_frame, face), the frame cache, the
depth compositor, contact sheets, the PixelFlow build and the atlas export.

Layers per class: body + five equipment slots (armor, shoulders, gloves, head, weapon) in two variants each.
Atlas format (read by client/magesprite.js): one colour PNG and one depth PNG per part, 8 columns x (8 facings x 5
clips) rows of 160x160 frames, anchor (80,119), depth = R*256+G with offset 512, scale 64, smaller is nearer.
The rig (ik2, rotations, facing formula) comes from the original project's tools/make_warrior_sprites.py, imported
read-only from ../Valhalla/tools (set VALHALLA_TOOLS to move it).
"""
import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'client' / 'assets'
sys.path.insert(0, os.environ.get('VALHALLA_TOOLS', str(ROOT.parent / 'Valhalla' / 'tools')))
import make_warrior_sprites as rig  # noqa: E402

V, unit = rig.V, rig.unit
FW = FH = 160
AX, AY, SS, PX = 80, 119, 2, 1.03
DIRS = rig.DIRS
HIP, SHOULDER = 37, 66
SLOT_ORDER = ['armor', 'shoulders', 'gloves', 'head', 'weapon']
# Shared by every class so faces stay on one drawing; a class overrides 'iris'.
FACE_MATS = {
    'skin': ['#92595c', '#ce9182', '#f0bfac', '#ffe0ce'],
    'brow': ['#1d1218', '#2e1c1e', '#40282a', '#553836'],
    'white': ['#a6b6b0', '#d4e0da', '#f2f7f2', '#fffcf6'],
    'mouth': ['#5c2d45', '#86506a', '#c88493', '#e9a4ab'],
}


def palette_of(mats):
    palette = ['#00000000', '#18182a', '#ffffff'] + [c for r in mats.values() for c in r]
    assert len(palette) == len(set(palette)) and len(palette) <= 255, 'palette has duplicates or is too long'
    return palette, {name: [3 + 4 * i + k for k in range(4)] for i, name in enumerate(mats)}


class Ink:
    """Flat cel polygons with a depth gradient along projected limbs, plus curved ribbons."""
    def __init__(self, psi, color):
        self.turn = rig.rotz(psi)
        self.color = color
        self.index = np.zeros((FH * SS, FW * SS), np.uint8)
        self.z = np.full(self.index.shape, np.inf, np.float32)

    def project(self, point):
        x, y, z = self.turn @ point
        return V(AX + x * PX, AY - (y * .5 + z * math.sqrt(3) / 2) * PX), y * math.sqrt(3) / 2 - z * .5

    def poly(self, points, color, depth, outline=True, gradient=None):
        p = np.array(points, float)
        x0 = max(0, int(np.floor(p[:, 0].min() - 1.5)) * SS)
        y0 = max(0, int(np.floor(p[:, 1].min() - 1.5)) * SS)
        x1 = min(FW * SS, int(np.ceil(p[:, 0].max() + 2)) * SS)
        y1 = min(FH * SS, int(np.ceil(p[:, 1].max() + 2)) * SS)
        if x0 >= x1 or y0 >= y1:
            return
        mask = Image.new('L', (x1 - x0, y1 - y0))
        d = ImageDraw.Draw(mask)
        q = [(x * SS - x0, y * SS - y0) for x, y in p]
        d.polygon(q, fill=int(color))
        if outline:
            d.line(q + q[:1], fill=1, width=SS, joint='curve')
        idx = np.asarray(mask)
        if gradient is None:
            dep = np.full(idx.shape, depth, np.float32)
        else:
            a, b, za, zb = gradient
            yy, xx = np.mgrid[y0:y1, x0:x1] / SS
            dv = b - a
            t = np.clip(((xx - a[0]) * dv[0] + (yy - a[1]) * dv[1]) / max(float(dv @ dv), .01), 0, 1)
            dep = za + (zb - za) * t + depth
        cur = self.z[y0:y1, x0:x1]
        take = (idx > 0) & (dep <= cur + .001)
        cur[take] = dep[take]
        self.index[y0:y1, x0:x1][take] = idx[take]

    def plate(self, points, mat, tone=2, detail=False):
        proj = [self.project(p) for p in points]
        xy = [p[0] for p in proj]
        self.poly(xy, self.color[mat][tone], np.mean([p[1] for p in proj]) - .01, not detail)

    def bone(self, a, b, r1, r2, mat, zpush=0, tone=2):
        pa, za = self.project(a)
        pb, zb = self.project(b)
        direction = unit(pb - pa)
        side = V(-direction[1], direction[0])
        r1 *= PX
        r2 *= PX
        points = [pa - direction * r1 * .5 - side * r1, pa - direction * r1 * .65,
                  pa - direction * r1 * .5 + side * r1,
                  pb + side * r2, pb + direction * r2 * .45, pb - side * r2]
        grad = (pa, pb, za, zb)
        self.poly(points, self.color[mat][tone], -max(r1, r2) * .7 + zpush, gradient=grad)
        self.poly([pa + side * r1 * .1, pa + side * r1 * .72,
                   pb + side * r2 * .72, pb + side * r2 * .1], self.color[mat][tone - 1],
                  -max(r1, r2) * .7 + zpush - .025, False, grad)

    def ribbon(self, points, w0, w1, mat, tone=2, zpush=0, outline=True):
        """A curved strip along 3D points (a bow limb, a string, a blade): one polygon, so no seams."""
        proj = [self.project(p) for p in points]
        xy, zs = [p[0] for p in proj], [p[1] for p in proj]
        n = len(xy)
        left, right, centre = [], [], []
        for i in range(n):
            d = unit(xy[min(i + 1, n - 1)] - xy[max(i - 1, 0)])
            s = V(-d[1], d[0])
            w = (w0 + (w1 - w0) * i / max(n - 1, 1)) * PX
            left.append(xy[i] + s * w)
            right.append(xy[i] - s * w)
            centre.append((xy[i], s, w))
        grad = (xy[0], xy[-1], zs[0], zs[-1])
        depth = -max(w0, w1) * .7 + zpush
        self.poly(left + right[::-1], self.color[mat][tone], depth, outline, grad)
        if outline and tone > 0:
            shade = [c + s * w * .15 for c, s, w in centre] + [c + s * w * .8 for c, s, w in centre][::-1]
            self.poly(shade, self.color[mat][tone - 1], depth - .025, False, grad)

    def resolve(self, flash=False):
        idx = self.index[SS // 2::SS, SS // 2::SS].copy()
        z = self.z[SS // 2::SS, SS // 2::SS].copy()
        if flash:
            idx[(idx > 0) & (idx != 1)] = 2
        return idx, z


def skeleton(p, arm=13.5, leg=17):
    """Pose dict -> (R, xf, joints). xf maps body-local points to the world; joints are world positions."""
    R = rig.rotz(rig.rad(p['twist'])) @ rig.roty(rig.rad(p['roll'])) @ rig.rotx(rig.rad(-p['lean']))
    pivot, shift = V(0, 0, HIP), V(*p['root'])
    xf = lambda a: pivot + R @ (V(*a) - pivot) + shift
    joints = {}
    for sx, key in ((-1, 'L'), (1, 'R')):
        s = V(sx * 8, 0, SHOULDER)
        elbow, hand = rig.ik2(s, V(*p['hand' + key]), arm, arm, unit(V(sx, -.2, -.3)))
        hip = xf((sx * 4.2, 0, HIP))
        knee, ankle = rig.ik2(hip, V(*p['foot' + key]), leg, leg, unit(V(sx * .1, 1, .1)))
        joints[key] = {'shoulder': xf(s), 'elbow': xf(elbow), 'hand': xf(hand),
                       'hip': hip, 'knee': knee, 'ankle': ankle}
    if p['ground']:
        low = min([xf((0, 0, 87))[2] - 11, *[j['ankle'][2] - 4 for j in joints.values()]])
        dz = -low
        shift += V(0, 0, dz)
        for joint in joints.values():
            for key in joint:
                joint[key] += V(0, 0, dz)
    return R, xf, joints


def torso(ink, xf, mat, halfwidth, y, bottom=38, top=67):
    for sy in (-1, 1):
        pts = [(-halfwidth, sy * y, top), (halfwidth, sy * y, top),
               (halfwidth * .72, sy * y, 49), (halfwidth * .84, sy * y, bottom),
               (-halfwidth * .84, sy * y, bottom), (-halfwidth * .72, sy * y, 49)]
        ink.plate([xf(q) for q in pts], mat, 2 if sy == 1 else 1)
    for sx in (-1, 1):
        ink.plate([xf(q) for q in [(sx * halfwidth, -y, top), (sx * halfwidth, y, top),
                  (sx * halfwidth * .84, y, bottom), (sx * halfwidth * .84, -y, bottom)]], mat, 1)


def base_body(ink, xf, joints, R, w=1., cloth='cloth', pants='pants', torso_width=7.8, torso_depth=3.5):
    """The naked layer: undershirt torso, neck, trousered legs, bare arms and feet. w scales limb thickness."""
    torso(ink, xf, cloth, torso_width, torso_depth)
    ink.bone(xf((0, 0, 68)), xf((0, 0, 77)), 2.2 * w, 2.1 * w, 'skin')
    for key in 'LR':
        j = joints[key]
        ink.bone(j['hip'], j['knee'], 3.3 * w, 2.9 * w, pants)
        ink.bone(j['knee'], j['ankle'], 2.7 * w, 1.9 * w, pants)
        ink.bone(j['ankle'] + V(0, -1, -1.5), j['ankle'] + V(0, 4, -2), 2 * w, 2.1 * w, 'skin')
        ink.bone(j['shoulder'], j['elbow'], 2.6 * w, 2.1 * w, 'skin')
        ink.bone(j['elbow'], j['hand'], 2 * w, 1.6 * w, 'skin')
        ink.bone(j['hand'] - R @ V(0, 0, 1), j['hand'] + R @ V(0, 0, 1.8), 2.2 * w, 1.8 * w, 'skin', -.2)


def head_frame(ink, xf, psi, p, turn=.3):
    """The head is a billboard on its projected axis. The head turns only `turn` of the body's twist."""
    hc, hd = ink.project(xf((0, 0, 87)))
    up = unit(ink.project(xf((0, 0, 96)))[0] - hc)
    right = V(-up[1], up[0])
    front = -math.cos(psi + rig.rad(p['twist'] * turn))
    side = -math.sin(psi + rig.rad(p['twist'] * turn))
    return dict(H=lambda x, y: hc + right * x + up * y, hd=hd, front=front, side=side)


def face(ink, head, p, paint=None, back_hair=None, lashes=1.):
    """Skin, almond upswept eyes (iris from the class ramp), brows, nose, mouth, optional cheek stripes."""
    H, hd, front, side = head['H'], head['hd'], head['front'], head['side']
    C = ink.color
    skin_shape = [(-8, 7), (-9.5, 1), (-8.4, -5), (-4.3, -10), (0, -11.3), (4.3, -10), (8.4, -5), (9.5, 1), (8, 7), (0, 10)]
    ink.poly([H(*q) for q in skin_shape], C['skin'][2], hd - 4)
    ink.poly([H(*q) for q in [(4, 6), (8, 6), (9, 0), (7, -6), (0, -11), (3, -4)]], C['skin'][1], hd - 4.05, False)
    if front < -.4:
        return False
    for sx in (-1, 1):
        if abs(side) > .85 and sx * side < 0:
            continue
        ex = sx * 4 * max(.28, front) + side * 3.3
        ey = -1.3
        if p['eyes'] == 'closed':
            ink.poly([H(ex - 2.4, ey - .4), H(ex, ey - .9), H(ex + 2.4, ey + .9)], 1, hd - 5.8)
        else:
            lo, hi = ex - 2.7 * sx, ex + 2.7 * sx
            ink.poly([H(lo, ey + .2), H(ex - 1 * sx, ey + 2.2), H(hi, ey + 1.6),
                      H(hi - .3 * sx, ey - 1.6), H(ex + .2 * sx, ey - 2.1)], C['white'][2], hd - 5.3)
            ink.poly([H(ex - .7, ey + 1.7), H(ex + 1.3, ey + 1.2), H(ex + 1.2, ey - 1.8), H(ex - .7, ey - 1.8)], C['iris'][2], hd - 5.5, False)
            ink.poly([H(ex - .2, ey + .9), H(ex + .6, ey + .9), H(ex + .6, ey - 1.3), H(ex - .2, ey - 1.3)], 1, hd - 5.55, False)
            ink.poly([H(lo - .3 * sx, ey + 1.4), H(ex - 1 * sx, ey + 2.7 * lashes), H(hi + .8 * sx, ey + 2.3 * lashes), H(hi, ey + 1.1)], 1, hd - 5.6, False)
            ink.poly([H(ex - .8, ey + .8), H(ex + .1, ey + .8), H(ex + .1, ey + 1.6), H(ex - .8, ey + 1.6)], C['white'][3], hd - 5.7, False)
        ink.poly([H(ex - 2.1, 3.4), H(ex + 2.2, 3.9), H(ex + 1.8, 4.5), H(ex - 1.9, 4.0)], C['brow'][0], hd - 5.8, False)
        if paint:
            for dy in (0, 1.1):
                ink.poly([H(ex - 1.8 * sx, -4.0 - dy), H(ex + 1.9 * sx, -4.4 - dy), H(ex + 1.8 * sx, -5.0 - dy), H(ex - 1.7 * sx, -4.6 - dy)], C[paint[0]][paint[1]], hd - 5.65, False)
    nx = side * 5
    ink.poly([H(nx, -3.7), H(nx + .6, -5), H(nx + 1.5, -4.3)], C['skin'][1], hd - 5.5, False)
    ink.poly([H(nx - 1.1, -7.5), H(nx + 1.4, -7.4), H(nx + .7, -8)], C['mouth'][1], hd - 5.6, False)
    return True


def revision_of(sheet_sources, *objects):
    h = hashlib.sha256()
    for text in sheet_sources:
        h.update(text.encode())
    for obj in objects:
        h.update((obj if isinstance(obj, str) else inspect.getsource(obj)).encode())
    h.update(Path(__file__).read_bytes())
    h.update(Path(rig.__file__).read_bytes())
    return h.hexdigest()


class Sheet:
    """One class's atlas: frame cache, compositing, contact sheets, PixelFlow build and atlas export."""
    def __init__(self, name, *, files, pixel, mats, clips, slots, gear, render, revision, meta, default_equip, combos, legacy=(), groups=None):
        self.name, self.files, self.pixel = name, files, pixel          # files: asset prefix; pixel: sprite name prefix
        self.mats, self.clips, self.slots, self.gear, self.render = mats, clips, slots, gear, render
        self.palette, self.color = palette_of(mats)
        # `legacy` parts already exist as atlas files (an older class art we keep): never redrawn, never in PixelFlow.
        self.legacy = list(legacy)
        self.all_parts = ['body'] + [f'{slot}_{v}' for slot in SLOT_ORDER for v in slots[slot]]
        self.parts = [part for part in self.all_parts if part not in self.legacy]
        tier_parts = lambda t: [f'{slot}_{t}' for slot in ('armor', 'shoulders', 'gloves', 'head') if f'{slot}_{t}' in self.parts]
        t1, t2 = slots['armor']
        weapons = [f'weapon_{v}' for v in slots['weapon'] if f'weapon_{v}' in self.parts]
        ref = lambda: ['ref_body'] if 'body' in self.parts else []
        self.groups = groups or {t1: (['body'] if 'body' in self.parts else []) + tier_parts(t1), t2: ref() + tier_parts(t2), 'arms': ref() + weapons}
        self.groups = {g: layers for g, layers in self.groups.items() if any(not l.startswith('ref_') for l in layers)}
        self.cache = Path(__file__).resolve().parent / f'{name}_raw'
        self.revision, self.meta, self.default_equip, self.combos = revision, meta, default_equip, combos
        self.pal = np.array([[int(c[j:j + 2], 16) for j in (1, 3, 5)] + [0 if i == 0 else 255] for i, c in enumerate(self.palette)], np.uint8)

    def rgba(self, idx):
        return Image.fromarray(self.pal[idx], 'RGBA')

    def read_frame(self, clip, facing, k):
        path = self.cache / f'{clip}_{facing}_{k}.npz'
        valid = False
        if path.exists():
            with np.load(path) as saved:
                valid = 'revision' in saved and str(saved['revision']) == self.revision
        if not valid:
            self.cache.mkdir(exist_ok=True)
            parts = self.render(clip, facing, k)
            assert set(parts) == set(self.parts), (set(parts) ^ set(self.parts))
            np.savez_compressed(path, revision=self.revision,
                                **{f'{n}_index': d[0] for n, d in parts.items()},
                                **{f'{n}_depth': d[1].astype(np.float32) for n, d in parts.items()})
        with np.load(path) as saved:
            return {name: (saved[f'{name}_index'], saved[f'{name}_depth']) for name in self.parts}

    def legacy_layer(self, part, clip, facing, k):
        if not hasattr(self, '_legacy'):
            self._legacy = {}
        if part not in self._legacy:
            colour = np.asarray(Image.open(ASSETS / f'{self.files}_{part}.png').convert('RGBA'))
            depth = np.asarray(Image.open(ASSETS / f'{self.files}_{part}_depth.png').convert('RGB')).astype(np.int32)
            self._legacy[part] = (colour, depth)
        colour, depth = self._legacy[part]
        y = (self.clips_row0[clip] + DIRS.index(facing)) * FH
        x = k * FW
        rgba = colour[y:y + FH, x:x + FW]
        encoded = depth[y:y + FH, x:x + FW, 0] * 256 + depth[y:y + FH, x:x + FW, 1]
        z = np.where(rgba[..., 3] > 0, encoded / 64 - 512, np.inf)
        return rgba, z

    @property
    def clips_row0(self):
        return {clip: ci * 8 for ci, clip in enumerate(self.clips)}

    def layers(self, clip, facing, k):
        raw = self.read_frame(clip, facing, k)
        layers = {part: (self.pal[raw[part][0]], raw[part][1]) for part in self.parts}
        for part in self.legacy:
            layers[part] = self.legacy_layer(part, clip, facing, k)
        return layers

    def composite(self, layers, equip):
        """RGBA picture of the worn parts, nearest depth winning."""
        best = np.full((FH, FW), np.inf)
        out = np.zeros((FH, FW, 4), np.uint8)
        for part in ['body'] + [f'{slot}_{v}' for slot, v in equip.items() if v != 'none']:
            rgba, depth = layers[part]
            take = (rgba[..., 3] > 0) & (depth <= best)
            out[take], best[take] = rgba[take], depth[take]
        return Image.fromarray(out, 'RGBA')

    def preview(self, clips, out):
        out.mkdir(parents=True, exist_ok=True)
        for clip in clips:
            n = self.clips[clip][1]
            for label, equip in self.combos:
                sheet = Image.new('RGBA', (FW * n, FH * 8), '#487048')
                for di, facing in enumerate(DIRS):
                    for k in range(n):
                        parts = self.read_frame(clip, facing, k)
                        for part, (idx, z) in parts.items():
                            if (idx[0] > 0).any() or (idx[-1] > 0).any() or (idx[:, 0] > 0).any() or (idx[:, -1] > 0).any():
                                raise ValueError(f'clipped {clip}/{facing}/{k}/{part}')
                        sheet.alpha_composite(self.composite(self.layers(clip, facing, k), equip), (k * FW, di * FH))
                        ImageDraw.Draw(sheet).text((k * FW + 3, di * FH + 3), f'{facing} {k}', fill='white')
                sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(out / f'{self.name}_{clip}_{label}.png')
            print('preview', clip, 'eight facings; no clipped parts', flush=True)
        # One strip for the cross-class lineup: idle, facing the camera and three-quarters, every combo.
        strip = Image.new('RGBA', (FW * len(self.combos) * 2, FH), '#487048')
        for j, (label, equip) in enumerate(self.combos):
            for m, facing in enumerate(('S', 'SE')):
                strip.alpha_composite(self.composite(self.layers('idle', facing, 0), equip), ((j * 2 + m) * FW, 0))
        strip.save(out / f'{self.name}_lineup.png')

    def pixel_name(self, clip, facing, group):
        return f'{self.pixel}{clip}_{facing.lower()}_{group}'

    def pixel_api(self):
        sys.path.insert(0, os.path.expanduser('~/.claude/skills/makesprites'))
        import pf
        original = pf.api
        def retry(*args, **kwargs):
            for attempt in range(25):
                result = original(*args, **kwargs)
                if not any(e.get('code') == 'rate_limited' for e in result.get('errors', [])):
                    return result
                time.sleep(5)
            raise RuntimeError('PixelFlow request limit did not clear')
        pf.api = retry
        return pf

    def pixel_ids(self, pf):
        manifest = self.cache / 'editor_ids.txt'
        ids = json.loads(manifest.read_text()) if manifest.exists() else {}
        ids.update(pf.ids(self.pixel))      # list shows only the newest 100, so the manifest carries the rest
        return ids

    def build(self, replace=False):
        pf = self.pixel_api()
        existing = self.pixel_ids(pf)
        if existing and not replace:
            raise SystemExit(f'{self.name} sprites already exist; use export to keep edits, or build --replace to discard them.')
        for sid in existing.values():
            response = pf.api('delete', {'sprite_id': sid})
            assert response.get('ok') or any(e.get('code') == 'not_found' for e in response.get('errors', [])), response
        created, ids = [], {}
        try:
            for clip, (fps, n, _) in self.clips.items():
                for facing in DIRS:
                    frames = [self.read_frame(clip, facing, k) for k in range(n)]
                    for group, layers in self.groups.items():
                        assert FW * FH * len(layers) * n <= 1048576
                        name = self.pixel_name(clip, facing, group)
                        sid = pf.create(name, FW, FH, n, self.palette, fps=fps, layers=len(layers),
                                        layer_ops=[{'op': 'set_layer', 'layer': i, 'name': layer, 'visible': True} for i, layer in enumerate(layers)])
                        created.append(sid); ids[name] = sid
                        for k in range(n):
                            result = pf.api('draw', {'sprite_id': sid, 'frame': k, 'ops': [
                                {'op': 'grid', 'rows': frames[k][layer.replace('ref_', '')][0].astype(int).tolist(), 'x': 0, 'y': 0, 'layer': li}
                                for li, layer in enumerate(layers)]})
                            assert result.get('ok'), result
                            time.sleep(.1)
                        print(name, sid, flush=True)
        except BaseException:
            for sid in created:
                pf.api('delete', {'sprite_id': sid})
            raise
        self.cache.mkdir(exist_ok=True)
        (self.cache / 'editor_ids.txt').write_text(json.dumps(ids, indent=2) + '\n')

    def export(self, local=False):
        pf = None if local else self.pixel_api()
        ids = {} if local else self.pixel_ids(pf)
        meta_clips = {clip: {'row0': ci * 8, 'n': n, 'fps': fps} for ci, (clip, (fps, n, _)) in enumerate(self.clips.items())}
        size = (FW * 8, FH * 8 * len(self.clips))
        atlases = {part: Image.new('RGBA', size) for part in self.parts}
        depths = {part: Image.new('RGB', size, (255, 255, 0)) for part in self.parts}
        for clip, (_, n, _) in self.clips.items():
            for di, facing in enumerate(DIRS):
                edited = {}
                if not local:
                    for group, layers in self.groups.items():
                        sp, frames = pf.load(ids[self.pixel_name(clip, facing, group)])
                        assert (sp['width'], sp['height']) == (FW, FH) and len(frames) == n
                        assert [layer['name'] for layer in sp['layers']] == layers
                        for li, layer in enumerate(layers):
                            if not layer.startswith('ref_'):
                                edited[layer] = (sp['palette'], [f[li] for f in frames])
                for k in range(n):
                    raw = self.read_frame(clip, facing, k)
                    x, y = k * FW, (meta_clips[clip]['row0'] + di) * FH
                    for part in self.parts:
                        depth = raw[part][1].copy()
                        if edited:
                            palette, grids = edited[part]
                            idx = grids[k]
                            picture = Image.fromarray(pf.to_rgba(idx, palette), 'RGBA')
                            added = (idx > 0) & ~np.isfinite(depth)
                            if added.any():
                                nearest = ndi.distance_transform_edt(~np.isfinite(depth), return_distances=False, return_indices=True)
                                depth[added] = depth[tuple(nearest)][added]
                        else:
                            idx = raw[part][0]
                            picture = self.rgba(idx)
                        opaque = idx > 0
                        encoded = np.full((FH, FW), 65535, np.uint16)
                        encoded[opaque] = np.clip(np.round((depth[opaque] + 512) * 64), 0, 65534).astype(np.uint16)
                        rgb = np.zeros((FH, FW, 3), np.uint8)
                        rgb[..., 0], rgb[..., 1] = encoded >> 8, encoded & 255
                        atlases[part].paste(picture, (x, y))
                        depths[part].paste(Image.fromarray(rgb, 'RGB'), (x, y))
            print('export', clip, flush=True)
        for part in self.parts:
            atlases[part].save(ASSETS / f'{self.files}_{part}.png', optimize=True)
            depths[part].save(ASSETS / f'{self.files}_{part}_depth.png', optimize=True)
        meta = {'frame': [FW, FH], 'anchor': [AX, AY], 'dirs': DIRS, 'clips': meta_clips,
                'parts': {part: {'png': f'{self.files}_{part}.png', 'depth': f'{self.files}_{part}_depth.png'} for part in self.all_parts},
                'equipment': self.gear, 'defaultEquipment': self.default_equip,
                'sprites': ids, 'ramps': self.mats,
                'depth': {'encoding': 'R*256+G', 'offset': 512, 'scale': 64, 'near': 'smaller'},
                'facing': 'Same eight-direction formula and foot anchor as assassin_sprites.txt',
                'style': '2D Korean RPG anime cel illustration',
                'editing': f'Three PixelFlow sprites per clip and facing ({self.pixel}<clip>_<facing>_{"|".join(self.groups)}). '
                           'ref_body layers are read-only context. build --replace discards edits.',
                **self.meta}
        (ASSETS / f'{self.files}_sprites.txt').write_text(json.dumps(meta, indent=2) + '\n')
        print('exported', len(self.parts), 'parts and depth maps', size, flush=True)

    def cli(self):
        ap = argparse.ArgumentParser(description=f'{self.name}: preview | build [--replace] | export [--local]')
        ap.add_argument('command', choices=['preview', 'build', 'export'])
        ap.add_argument('clip', nargs='?', default='all', choices=['all'] + list(self.clips))
        ap.add_argument('directory', nargs='?', default=os.path.join(os.environ.get('TMPDIR', '/tmp'), f'valhalla-{self.name}-preview'))
        ap.add_argument('--replace', action='store_true')
        ap.add_argument('--local', action='store_true')
        args = ap.parse_args()
        if args.command == 'preview':
            self.preview(list(self.clips) if args.clip == 'all' else [args.clip], Path(args.directory))
        elif args.command == 'build':
            self.build(args.replace)
        else:
            self.export(args.local)
