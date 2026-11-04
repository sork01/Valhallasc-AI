#!/usr/bin/env python3
"""Greenmeadow Ironhide Beetle, slime style, rigid shell (redo): preview | build | export | verify.

The shell, head and horn never squash or stretch: they translate and tilt as solid parts on six jointed legs.
Planted feet rest exactly on the anchor row (Painter y=0, row 90).  The attack is a rear-up (wind-up), a horn
slam forward (strike) and a recovery, eight distinct frames.  The death cracks the shell, buckles the legs and
rolls the beetle onto its back with its legs in the air.  Frame size is free per zone (owner, 2026-11-04): the
Painter draws on 96x96 and every frame is cropped to FW x FH (96x78, anchor 40,72).

--replace is refused.  Old sources stay saved; export preserves saved editor frames.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.error
import urllib.request

import numpy as np
from PIL import Image, ImageDraw
from wyrd_slime_v1_redraw import Painter, mix
from deep_slime_redraw import sm, bez, taper

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
OUT = ROOT/'test-results/meadow-slime'
REGISTRY = ROOT/'scripts/meadow_slime_sources.txt'
PREFIX = 'valhallasc_meadow_ironhide_redo_b_'
KIND = 'beetle'
CLIPS = {'idle': (6, 6), 'walk': (10, 8), 'attack': (12, 8), 'hurt': (10, 4), 'die': (8, 8)}
FW, FH = 96, 78                    # exported frame
X0, Y0 = 0, 18                     # crop origin inside the 96x96 Painter canvas
CX = 40                            # Painter x origin (the beetle's local x = 0)
AX, AY = CX-X0, 90-Y0              # anchor inside the exported frame: (40, 72)
PALETTE = ['#00000000', '#282131', '#ffffff', '#edf6e9', '#e6a0a5',
           '#25364c', '#3b5571', '#6084a4', '#8bb4cb', '#bfdee2',
           '#5b4031', '#8a5e3c', '#bd8b50', '#ebc879', '#fff1bd']
assert len(set(PALETTE)) == len(PALETTE), 'duplicate palette hex'
STEEL = [5, 6, 7, 8, 9]
GOLD = [10, 11, 12, 13, 14]
HORN = [10, 10, 12, 13, 14]                           # dark outline, bronze body, bright edge

# Attack: rear up on the hind legs (wind-up), slam the horn forward and down (strike), then recover.
ATK_OX = [0, -1, -1, 0, 3, 4, 2, 1]
ATK_PITCH = [4, 11, 20, 9, -6, -9, -3, 1]          # degrees, positive = nose up
LEG_X = (-20, -6, 8)                                  # near hips, rear to front
KD = (-1, .3, 1)                                      # how each leg splays forward or back


def lerp_pts(a, b, t):
    return [(mix(p[0], q[0], t), mix(p[1], q[1], t)) for p, q in zip(a, b)]


def beetle(clip, n):
    ox = bob = th = 0.
    r = sag = 0.
    walk = False
    if clip == 'idle':
        bob = [0, .8, 1.6, .8, 0, -.6][n]
        th = [0, 1, 2, 1, 0, -1][n]
    elif clip == 'walk':
        ph = n*math.pi/4
        bob = 1.1*math.cos(2*ph)
        th = 1.2*math.sin(2*ph)
        walk = True
    elif clip == 'attack':
        ox, th = ATK_OX[n], ATK_PITCH[n]
        bob = [0, 1, 2, 1, -1, -1, 0, 0][n]
    elif clip == 'hurt':
        ox, th, bob = [-4, -3, -1, 0][n], [9, 5, 2, 0][n], [1, 0, 0, 0][n]
    else:
        r = [0, 0, 0, .2, .5, .8, .95, 1][n]
        sag = [0, 1.5, 4, 4, 0, 0, 0, 0][n]
        ox = [-2, -3, -3, -3, -3, -3, -3, -3][n]
        th = 0.
    sr = sm(r)
    dead = clip == 'die'
    rad = math.radians(th)
    c, s = math.cos(rad), math.sin(rad)
    PX, PY = -12, 6

    def T(x, y):
        dx, dy = x-PX, y-PY
        return PX+dx*c-dy*s+ox, PY+dx*s+dy*c+bob

    a = Painter(cx=CX)
    ph = n*math.pi/4

    def legs(far):
        for k in range(3):
            hx = LEG_X[k]+(4 if far else 0)
            kd = KD[k]
            lift = 0.
            push = 0.
            if walk:
                grp = (k % 2)+(1 if far else 0)
                sp = ph+(math.pi if grp % 2 else 0)
                lift, push = max(0, math.sin(sp))*4, math.cos(sp)*3
            elif clip in ('attack', 'hurt') and th > 0:
                lift = th*(.36 if k == 2 else .15 if k == 1 else 0)
            elif clip == 'attack' and th < 0 and k == 2:
                push = 3
            hip = T(hx, 15-sag)
            foot = (hx+kd*3+push+ox*.7, 3+lift)
            if dead and r > 0:
                hip = (hx+ox, mix(15-sag, 26, sr))
                curl = [0, 0, 0, 0, 0, 0, .5, 1][n]            # the legs go limp and curl inward
                back = (hx+kd*(9-5*curl)-2*math.sin(n*1.7+k)*(n == 5), 44+(k % 2)*2-5*curl)
                foot = (mix(foot[0], back[0], sr)+kd*7*math.sin(math.pi*r), mix(3, back[1], sr)+(0 if r < 1 else 0))
            if dead and r == 0 and sag:
                foot = (foot[0]+kd*sag*.8, foot[1])
            mid = ((hip[0]+foot[0])/2+kd*4, (hip[1]+foot[1])/2-1)
            ramp = [5, 5, 6, 6, 7] if far else STEEL
            if dead and r > 0:
                a.limb([hip, mid, foot], ramp, 4)
                a.ball(foot[0], foot[1], 3.4, 3, GOLD[:4])
            else:
                a.limb([hip, mid, (foot[0], foot[1])], ramp, 4)
                a.ball(foot[0], foot[1], 3.6, 3, GOLD[:4])    # integer ry, centre y = 3+lift: lowest pixel row 90

    legs(True)
    shell = (-6+ox*(1 if dead else 0), mix(27-sag, 15, sr)+8*math.sin(math.pi*r))
    if dead:
        sx, sy = shell
    else:
        sx, sy = T(-6, 27)
    a.ball(sx, sy, 22, 15, STEEL)
    if not dead or sr < .6:
        a.line([T(x, y) for x, y in [(-1, 41), (3, 34), (5, 26), (3, 17)]], 5, 2)
        a.line([T(x, y) for x, y in [(-3, 40), (1, 33), (3, 26)]], 9, 1)
        for ex, ey in [(-16, 36), (-21, 31), (-11, 39)]:
            tx, ty = T(ex, ey)
            a.ellipse(tx, ty, 2, 1.2, 9)
        a.line([T(x, y) for x, y in [(-26, 16), (-18, 13), (-4, 12), (8, 14)]], 5, 3)
    else:
        for k in range(3):                                # belly segments of the upturned beetle
            a.line([(sx-16+k*11, sy+6+k), (sx-11+k*11, sy-4)], 6, 2)
        a.ellipse(sx+4, sy+8, 5, 2, 7)
    if dead and r < 1:                                    # fractures open across the shell
        pts = [(-16, 38), (-12, 32), (-16, 26), (-10, 20), (-14, 15)]
        shown = pts[:min(len(pts), max(0, n))]
        if r < .6 and len(shown) >= 2:
            a.line([T(*p) for p in shown], 1, 2)
            a.line([T(p[0]+1, p[1]) for p in shown], 8, 1)
            if n >= 3:
                a.line([T(*p) for p in [(14, 36), (9, 30), (13, 24), (7, 18)][:n-1]], 1, 2)
    legs(False)
    # head, blush, mouth and a tapered bronze horn
    if dead:
        hx, hy = mix(17, 19, sr)+ox, mix(24-sag, 10, sr)+3*math.sin(math.pi*r)
    else:
        hx, hy = T(17, 24)
    a.ball(hx, hy, 11, 10, GOLD)
    # Rhinoceros-beetle horn: rooted on top of the head, rising and sweeping forward with an upturned tip and a short
    # second tine.  Drawn as a tapered, outlined curve so it reads as a horn, not a cone.
    horn_parts = [(bez((17, 30), (19, 44), (34, 43), 10), bez((27, 15), (36, 20), (47, 14), 10), 9, 2.5),
                  (bez((27, 42), (31, 46), (33, 48), 4), bez((38, 18), (41, 20), (43, 20), 4), 4.5, 1.5)]
    tip = None
    for rest_pts, back_pts, w0, w1 in horn_parts:
        if dead:
            shift = (hx-mix(17, 19, sr), hy-mix(24, 10, sr))
            pts = [(p[0]+shift[0], p[1]+shift[1]) for p in lerp_pts(rest_pts, back_pts, sr)]
        else:
            pts = [T(*p) for p in rest_pts]
        taper(a, pts, HORN, w0, w1)
        tip = tip or pts[-1]
    ey = hy+1
    for dx, dy in ((-4, 1), (5, -1)):
        a.eye(hx+dx, ey+dy, clip, n, .72)
    if not (dead and n >= 2):
        a.ellipse(hx-7, hy-5, 2.5, 1.3, 4)
    a.line([(hx-3, hy-6), (hx, hy-7.5), (hx+3, hy-6)], 1)
    if clip == 'attack' and n in (4, 5):                  # impact sparks and dust
        tx, ty = tip
        for k in range(3):
            a.ellipse(tx+.5+k*1.2, ty+3.5-k*3.8, 2.2-k*.4, 2.2-k*.4, 14 if k % 2 == 0 else 13)
        for k in range(3):
            a.ellipse(-32+ox*.7-k*3, 2+(k % 2), 3-k*.6, 2-k*.3, 3)
    if dead and n >= 4:                                   # shell chips fall and lie around
        fy = max(1, 22-(n-4)*7)
        for k, (cxp, w) in enumerate(((-31-(n-4)*1, 3), (24+(n-4)*2.4, 3), (-8+(n-4)*(-1), 2))):
            cyp = max(1.5, fy-k*3)
            a.poly([(cxp, cyp-w), (cxp+w, cyp), (cxp, cyp+w*.7), (cxp-w, cyp)], STEEL[1+k])
    return a


def frame(clip, n):
    a = beetle(clip, n)
    grid = np.array(a.im)
    low = int(np.nonzero(grid.any(axis=1))[0].max())
    if low > 90:                                          # a rigid body never sinks below the floor row
        grid = np.roll(grid, 90-low, axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = 3
    grid = grid[Y0:Y0+FH, X0:X0+FW].copy()
    assert grid.any(), (clip, n, 'empty')
    assert not (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()), (clip, n, 'border')
    return grid


def rgba(grid, palette=PALETTE):
    colors = np.array([[int(c[i:i+2], 16) for i in (1, 3, 5)]+[0 if k == 0 else 255]
                       for k, c in enumerate(palette)], dtype=np.uint8)
    return Image.fromarray(colors[grid])


def frames():
    return {clip: np.array([frame(clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def api(route, body=None):
    env = Path(os.environ.get('PIXELFLOW_ENV', '/home/serveperry/webserver/www/pixelflow/.env'))
    key = re.search(r'^PIXELFLOW_API_KEY=(\S+)', env.read_text(), re.M).group(1)
    base = os.environ.get('PIXELFLOW_API_URL', 'https://localhost/pixelflow/api/sprites/')
    req = urllib.request.Request(base+route, None if body is None else json.dumps(body).encode(),
                                 {'Content-Type': 'application/json', 'Authorization': 'Bearer '+key})
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
        raise RuntimeError(result.get('errors', result.get('error', 'PixelFlow request failed'))) from None
    if result.get('ok') is False:
        raise RuntimeError(result.get('errors', 'PixelFlow request failed'))
    return result


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved source and export.')
    saved = registry()
    if KIND in saved:
        print('Preserving saved source', saved[KIND], flush=True)
        return
    existing = {s['name']: s['sprite_id'] for s in api('list')['sprites']}
    name = PREFIX+'all'
    assert name not in existing, 'Unregistered source already exists: '+name
    data = frames()                                       # validate every frame before saving anything
    np.savez_compressed(ROOT/'scripts/meadow_slime_redo_raw.npz', **data)
    sid = api('create', dict(name=name, width=FW, height=FH, frames=34, layers=1, fps=10, palette=PALETTE,
                             persist=True, ops=[dict(op='set_layer', layer=0, name='ironhide')]))['sprite_id']
    saved[KIND] = sid
    REGISTRY.write_text(json.dumps(saved, indent=2)+'\n')
    offset = 0
    for clip, grids in data.items():
        for n, grid in enumerate(grids):
            api('draw', dict(sprite_id=sid, frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    print(KIND, sid, offset, 'frames saved', flush=True)


def refresh():
    """Rewrite the saved source's frames from the drawer (same ID). Overwrites editor edits: candidate only."""
    sid = registry()[KIND]
    data = frames()
    np.savez_compressed(ROOT/'scripts/meadow_slime_redo_raw.npz', **data)
    offset = 0
    for clip, grids in data.items():
        for n, grid in enumerate(grids):
            api('draw', dict(sprite_id=sid, frame=offset+n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    print('Refreshed', sid, offset, 'frames', flush=True)


def cel_grid(cel):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(FH, FW)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    sid = registry()[KIND]
    sp = api('get?sprite_id='+sid)['sprite']
    assert (sp['width'], sp['height'], len(sp['frames'])) == (FW, FH, 34)
    atlas = Image.new('RGBA', (8*FW, 5*FH))
    meta = dict(frame=[FW, FH], anchor=[AX, AY], kinds=[KIND], clips={}, sprites={KIND: sid}, tops={},
                artStyle='greenmeadow-slime-rigid-shell')
    rows = []
    offset = 0
    for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
        meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
        for n in range(count):
            im = rgba(cel_grid(sp['frames'][offset+n]['cels'][0]), sp['palette'])
            bounds = im.getbbox()
            assert bounds and bounds[0] > 0 and bounds[1] > 0 and bounds[2] < FW and bounds[3] < FH
            atlas.alpha_composite(im, (n*FW, row*FH))
            rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
        offset += count
    meta['tops'][KIND] = int(AY-min(r['bounds'][1] for r in rows if r['clip'] == 'idle'))
    atlas.save(ASSETS/'ironhide.png', optimize=True)
    (ASSETS/'ironhide.txt').write_text(json.dumps(meta, indent=2)+'\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'editor-export-proof.json').write_text(json.dumps(dict(source=sid, frames=rows), indent=2)+'\n')
    print('Exported 34 saved PixelFlow frames and derived the health-bar top.', flush=True)


def verify():
    """Compare the installed atlas directly to the saved editor frames, not to the drawer."""
    meta = json.loads((ASSETS/'ironhide.txt').read_text())
    sid = registry()[KIND]
    assert meta['sprites'][KIND] == sid
    sp = api('get?sprite_id='+sid)['sprite']
    atlas = Image.open(ASSETS/'ironhide.png').convert('RGBA')
    offset = 0
    for row, (clip, (_, count)) in enumerate(CLIPS.items()):
        for n in range(count):
            cell = atlas.crop((n*FW, row*FH, (n+1)*FW, (row+1)*FH))
            assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset+n]['cels'][0]), sp['palette']).tobytes(), (clip, n, 'editor mismatch')
        offset += count
    print('34 saved editor frames equal the exported atlas', flush=True)


def preview():
    OUT.mkdir(parents=True, exist_ok=True)
    data = frames()
    z = 2
    sheet = Image.new('RGB', (8*FW*z, 5*(FH*z+22)), '#344b40')
    d = ImageDraw.Draw(sheet)
    for row, (clip, grids) in enumerate(data.items()):
        for n, grid in enumerate(grids):
            im = rgba(grid).resize((FW*z, FH*z), Image.Resampling.NEAREST)
            sheet.paste(im, (n*FW*z, row*(FH*z+22)), im)
            d.text((n*FW*z+6, row*(FH*z+22)+FH*z+4), f'{clip} {n}', fill='white')
            d.line([(n*FW*z, row*(FH*z+22)+AY*z+z), (n*FW*z+FW*z, row*(FH*z+22)+AY*z+z)], fill='#5a7a68')
    sheet.save(OUT/'preview-beetle.png')
    print(OUT/'preview-beetle.png')


if __name__ == '__main__':
    {'preview': preview, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
