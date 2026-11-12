#!/usr/bin/env python3
"""The Drowned Longship: six original native PixelFlow enemies.
preview|extents|build|refresh KIND|export|verify.
Preserves all 140 unrelated Cathedral kinds and saved editor changes on export.
"""
import hashlib, json, math, os, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
import lapis_slime_redraw as L
from astral_slime_redraw import (
    Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE,
    BONE, PEARL, AZURE, SLATE, GOLD, TEAL, VIOLET, CRIMSON, GREEN, LEAF, BROWN, OLIVE, PINK, CORAL, AMBER, PURPLE,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/longship-slime'
REGISTRY = ROOT / 'scripts/longship_slime_sources.txt'
MANIFEST = ASSETS / 'cathedral.txt'
PREFIX = 'valhallasc_longship_slime_'
KINDS = [
    'keel_crab', 'keel_deckhand', 'keel_lantern', 'keel_cargomaw', 'keel_bosun', 'keel_captain',
]
NAMES = dict(zip(KINDS, ['Copperclaw Scavenger', 'Drowned Deckhand', 'Bilge Lantern', 'Gullveig, the Cargo Maw', 'Bosun Brinehook', 'Captain Svala Nineknots']))
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = {k: (176, 172, 88, 164) for k in KINDS}

SCALE = dict(keel_crab=.80, keel_deckhand=.75, keel_lantern=.80, keel_cargomaw=.85, keel_bosun=.70, keel_captain=.65)
CLIPS = {'idle': (6, 6), 'walk': (10, 8), 'attack': (12, 8), 'hurt': (10, 4), 'die': (8, 8)}
FLYING = ('keel_lantern',)
STRICT = True
BAD = []
LOWEST = {}


def kind_frame(kind):
    fr = kindframe.check_frame(*KIND_FRAMES[kind])
    assert fr[0] * fr[1] * 34 <= 1048576, 'native PixelFlow source exceeds its cell limit'
    return fr


class Painter(BasePainter):
    def __init__(self, kind):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.S = SCALE[kind]
        self.xscale = dict(keel_deckhand=1.26,keel_lantern=1.30,keel_cargomaw=.96,keel_bosun=1.15,keel_captain=1.35).get(kind,1.0)
        self.yscale = dict(keel_crab=1.14,keel_deckhand=.84,keel_lantern=1.17,keel_cargomaw=1.27,keel_bosun=.93,keel_captain=.87).get(kind,1.0)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax
        self.ay = 115

    def pos(self, x, y):
        return round(self.cx + x * self.S * self.xscale), round(self.ay - y * self.S * self.yscale)

    def ellipse(self, x, y, rx, ry, col):
        super().ellipse(x, y, rx * self.S * self.xscale, ry * self.S * self.yscale, col)

    def line(self, pts, col, width=1):
        super().line(pts, col, max(1, round(width * self.S)))

    def ball(self, x, y, rx, ry, ramp, ang=0.):
        # Clean light bands keep the small faces readable, with no checkerboard dither.
        px, py = self.pos(x, y)
        rx *= self.S * self.xscale
        ry *= self.S * self.yscale
        radius = max(rx, ry)
        c, s = math.cos(ang), math.sin(ang)
        for yy in range(max(0, math.floor(py - radius)), min(self.h, math.ceil(py + radius) + 1)):
            for xx in range(max(0, math.floor(px - radius)), min(self.w, math.ceil(px + radius) + 1)):
                dx, dy = xx - px, yy - py
                u, v = (dx * c - dy * s) / rx, (dx * s + dy * c) / ry
                rr = u * u + v * v
                if rr > 1:
                    continue
                nx, ny = u * c + v * s, -u * s + v * c
                value = max(0, min(.999, .23 + .71 * (-.40 * nx - .54 * ny + .74 * math.sqrt(max(0, 1 - rr)))))
                shade = min(len(ramp) - 1, round(value * (len(ramp) - 1)))
                if rr > .93 and nx + ny > .2:
                    shade = 0
                self.im.putpixel((xx, yy), ramp[shade])


def beats(clip, n):
    w = (.05, .58, 1., .38, 0, 0, 0, 0)[n] if clip == 'attack' else 0
    s = (0, 0, 0, .68, 1., .58, .20, .025)[n] if clip == 'attack' else 0
    d = (0, .08, .22, .40, .60, .78, .92, 1.)[n] if clip == 'die' else 0
    ph = n * math.pi / 4 + .31
    b = (1 - math.cos(n * math.pi / 3 + .3)) * .7 if clip == 'idle' else math.sin(ph) * 1.8 if clip == 'walk' else 0
    return w, s, d, ph, b


def setup(kind, clip, n, pivot, angle=0):
    a = Painter(kind)
    w, s, d, ph, b = beats(clip, n)
    r = L.Rig(a, *pivot, angle * d + ((-.10, -.04, .035, .01)[n] if clip == 'hurt' else 0))
    return a, r, w, s, d, ph, b


# Ship-specific corroded copper, navy sailcloth, drowned skin and salt-dark wood.
_palette_base = len(PALETTE)
PALETTE = PALETTE + ['#50352b','#916448','#c28c59','#e6b77c','#ffe0a8',
 '#101d2b','#1e324a','#36516e','#60819a','#a3bfd0',
 '#23494a','#3e7774','#72aaa0','#b0d5c0','#def0d4',
 '#302c27','#514435','#81694b','#b49a6c','#dfca98']
assert len(PALETTE) <= 256 and len(set(PALETTE)) == len(PALETTE)
import longship_slime_models as models
models.COPPER, models.NAVY, models.SEA, models.WOOD = [list(range(_palette_base+5*i,_palette_base+5*i+5)) for i in range(4)]

DRAW = {k: (lambda clip, n, fn=fn: fn(setup, clip, n)) for k, fn in zip(KINDS, [models.crab, models.deckhand, models.lantern, models.cargomaw, models.bosun, models.captain])}


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    clipped = bool(grid.any() and (grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any()))  # BEFORE the roll hides it
    if grid.any():
        LOWEST[kind] = max(LOWEST.get(kind, -999), int(np.nonzero(grid.any(axis=1))[0].max()) - kay)
    if kind in FLYING:
        grid = np.roll(grid, kay - 115, axis=0)
        # Flyers hover well above the ground while alive and settle onto kay smoothly through death.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and clip == 'die':
            low = int(rows.max())
            descent = (0, .03, .12, .28, .48, .69, .87, 1.)[n]
            shift = round((kay - low) * descent) if low <= kay else kay - low
            grid = np.roll(grid, shift, axis=0)
    else:
        # Grounded kinds rest their lowest pixel exactly on the anchor row in every living and death frame.
        while grid.any() and int((grid[int(np.nonzero(grid.any(axis=1))[0].max())] != 0).sum()) <= 2:
            grid[int(np.nonzero(grid.any(axis=1))[0].max())] = 0
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (clip == 'die' or int(rows.max()) != kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    problem = 'drawn past the canvas edge before the ground roll (clipped)' if clipped else None
    low = int(np.nonzero(grid.any(axis=1))[0].max()) if grid.any() else -1
    if not grid.any() or grid[0].any() or grid[-1].any() or grid[:, 0].any() or grid[:, -1].any():
        problem = 'empty or touches the border'
    elif kind in FLYING:
        if clip != 'die' and low > kay - 12:
            problem = f'flying kind should hover well above anchor row {kay} (lowest row {low})'
        elif clip == 'die' and low > kay:
            problem = f'flying death frame {n} sinks below anchor row {kay} (lowest row {low})'
    elif low != kay:
        problem = f'lowest row {low} != anchor row {kay}'
    if problem:
        BAD.append((kind, clip, n, problem))
        assert not STRICT, (kind, clip, n, problem)
    return grid


def rgba(grid, palette=PALETTE):
    return old.rgba(grid, palette)


def frames(kind):
    data = {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}
    for clip, grids in data.items():
        distinct = len({g.tobytes() for g in grids})
        assert distinct >= min(4, len(grids)), (kind, clip, 'static animation')
        if clip in ('attack', 'die'):
            assert distinct == 8, (kind, clip, 'eight distinct poses required')
    return data


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def save_registry(data):
    REGISTRY.write_text(json.dumps({k: data[k] for k in KINDS if k in data}, indent=2) + '\n')


def api_draw(sid, offset, data):
    for clip, (_, count) in CLIPS.items():
        for n, grid in enumerate(data[clip]):
            old.api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [{'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
        offset += count
    return offset


def build(kinds=None):
    assert '--replace' not in sys.argv, '--replace is refused; use refresh KIND to overwrite named frames'
    saved = registry()
    suffix = os.environ.get('SOURCE_SUFFIX', '')
    target_kinds = [k for k in (kinds or KINDS) if k in KINDS]
    for kind in target_kinds:
        kw, kh, _, _ = kind_frame(kind)
        if kind in saved:
            sp = old.api('get?sprite_id=' + saved[kind])['sprite']
            assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34), f'existing source {kind} is not {kw}x{kh}x34'
            print(kind, saved[kind], 'existing source preserved', flush=True)
            continue
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/longship_slime_{kind}_raw.npz', **data)
        sid = old.api('create', {
            'name': f'{PREFIX}{kind}{suffix}_all', 'width': kw, 'height': kh, 'frames': 34, 'layers': 1,
            'fps': 10, 'palette': PALETTE, 'persist': True, 'ops': [{'op': 'set_layer', 'layer': 0, 'name': kind}],
        })['sprite_id']
        try:
            total = api_draw(sid, 0, data)
        except Exception:
            old.api('delete', {'sprite_id': sid})
            raise
        saved[kind] = sid
        save_registry(saved)
        print(kind, sid, total, 'frames saved', flush=True)


def refresh():
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/longship_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def atlas_path(kind):
    return ASSETS / f'cathedral_{kind}.png'


def export(kinds=None):
    saved = registry()
    assert set(saved) == set(KINDS)
    live = json.loads(MANIFEST.read_text())
    unrelated = [k for k in live['kinds'] if k not in KINDS]
    assert len(unrelated) == 140
    villagers = {k: (live['sprites'].get(k), live['tops'].get(k), live.get('kindFrames', {}).get(k)) for k in unrelated}
    meta = json.loads(json.dumps(live))
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            assert meta['clips'][clip] == dict(fps=fps, n=count, row=row, editorStart=offset), clip
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['sprites'][kind] = saved[kind]
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for k in unrelated:
        assert (meta['sprites'].get(k), meta['tops'].get(k), meta.get('kindFrames', {}).get(k)) == villagers[k]
    for kind, atlas in atlases.items():
        path = atlas_path(kind)
        atlas.save(path, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.')


def verify(kinds=None):
    saved = registry()
    meta = json.loads(MANIFEST.read_text())
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        assert kindframe.frame_of(meta, kind) == (kw, kh, kax, kay)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        atlas = Image.open(atlas_path(kind)).convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh)
        offset = 0
        for row, (_, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                expected = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                actual = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert np.array_equal(np.array(expected), np.array(actual)), (kind, row, n)
            offset += count
        print(kind, '34 saved editor frames equal exported atlas')


def preview():
    OUT.mkdir(parents=True, exist_ok=True)
    cols = [('idle', 0), ('attack', 2), ('attack', 4), ('die', 4), ('die', 7)]
    sheet = Image.new('RGBA', (len(cols) * 192, len(KINDS) * 184), '#212b3d')
    d = ImageDraw.Draw(sheet)
    for r, kind in enumerate(KINDS):
        data = frames(kind)
        for c, (clip, n) in enumerate(cols):
            sheet.alpha_composite(rgba(data[clip][n]), (c * 192, r * 184))
        d.text((8, r * 184 + 170), NAMES[kind], fill='white')
    sheet.save(OUT / 'poses.png')
    print(OUT / 'poses.png')


def extents():
    global STRICT
    STRICT = False
    for kind in KINDS:
        data = frames(kind)
        idle_b = rgba(data['idle'][0]).getbbox()
        print(kind, 'idle', idle_b, 'wxh:', idle_b[2]-idle_b[0], 'x', idle_b[3]-idle_b[1], 'raw lowest vs anchor', LOWEST[kind])
    if BAD:
        print('BAD', BAD)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export, 'verify': verify}[cmd]()
