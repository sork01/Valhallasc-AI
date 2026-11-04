#!/usr/bin/env python3
"""The Obsidian Orrery: six native PixelFlow slime-style sources, per-kind frames and fitting motion.

preview | extents | build | refresh <kinds> | export | verify
All attacks have eight distinct wind-up/strike/recovery poses. Rigid materials retain their shape;
the jointed mantis stays grounded; the Orbit Seer falls to the ground on death.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw
import make_crag_sprites as old
import kindframe
from astral_slime_redraw import (
    Painter as BasePainter, PALETTE, OUTLINE, WHITE, EYE_WHITE, BLUSH,
    PLATE, TEAL, GOLD, FUR, BLUE, BROWN, PINK, PEARL, VIOLET, AMBER,
    AZURE, SLATE, mix, mixp, rot, sm, bez, taper, foot, spark, motion, atk, arm_ik, biped_legs,
)

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
OUT = ROOT / 'test-results/orrery-slime'
REGISTRY = ROOT / 'scripts/orrery_slime_sources.txt'
MANIFEST = ASSETS / 'orrery.txt'
PREFIX = 'valhallasc_orrery_slime_style_'
KINDS = ['bronzemantis', 'gearling', 'orbitseer', 'chronoguard', 'pendulummatron', 'epochengine']
NAMES = dict(zip(KINDS, ['Bronze Mantis', 'Gearling', 'Orbit Seer', 'Chronoguard', 'Pendulum Matron', 'Epoch Engine']))
W = H = 96
AX, AY = 48, 90
KIND_FRAMES = {k: (192, 154, 70, 148) for k in KINDS}
CLIPS = {'idle': (10, 6), 'walk': (10, 8), 'attack': (10, 8), 'hurt': (10, 4), 'die': (10, 8)}
FLYING = ('orbitseer',)
PALETTE = PALETTE[:] + ['#583d4a', '#926451', '#c99771', '#efc29b', '#ffe6bd']
SAND = list(range(len(PALETTE)-5, len(PALETTE)))
RAINBOW = [PINK[3], GOLD[3], TEAL[3], VIOLET[3]]


def kind_frame(kind):
    return kindframe.check_frame(*KIND_FRAMES.get(kind, (W, H, AX, AY)))


class Painter(BasePainter):
    def __init__(self, kind, dx=0.):
        self.w, self.h, self.ax, self.ay = kind_frame(kind)
        self.im = Image.new('P', (self.w, self.h), 0)
        self.d = ImageDraw.Draw(self.im)
        self.cx = self.ax - 2 + dx


def curves(clip, n):
    """Explicit animation beats: ready, anticipate, wind-up, release, impact, follow, recoil, recover."""
    wind = [0, .48, 1, .35, 0, 0, .08, 0][n] if clip == 'attack' else 0
    strike = [0, 0, 0, .50, 1, .72, .28, 0][n] if clip == 'attack' else 0
    dead = sm(n / 7) if clip == 'die' else 0
    phase = n * math.pi / (3 if clip == 'idle' else 4)
    bob = math.sin(phase) * (1.2 if clip == 'idle' else 2 if clip == 'walk' else 0)
    recoil = [-3, -2, 1, 0][n] if clip == 'hurt' else 0
    return wind, strike, dead, phase, bob, recoil


def diamond(a, x, y, rx, ry, ramp):
    a.poly([(x-rx,y),(x,y+ry),(x+rx,y),(x,y-ry)], ramp[2], outline=ramp[0])
    a.poly([(x-rx+1,y),(x,y+ry-1),(x,y)], ramp[3])
    a.line([(x,y+ry-2),(x,y-ry+2)], ramp[-1])



def gear(a, x, y, r, ramp, angle=0):
    points=[]
    for i in range(32):
        t=angle+i*math.pi/16
        radius=r*(1 if i%4 in (0,1) else .80)
        points.append((x+math.cos(t)*radius,y+math.sin(t)*radius))
    a.poly(points,ramp[2],outline=ramp[0])
    a.ball(x,y,r*.69,r*.69,ramp)
    a.ellipse(x-r*.22,y+r*.25,r*.22,r*.11,ramp[4])


def bronzemantis(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('bronzemantis',recoil+st*12-w*5)
    by=28+bob*.4+w*10-d*10
    for far in (True,False):
        for i,x in enumerate((-18,0,13)):
            fx=x+(-10 if i==0 else 7)+(6 if far else 0)
            swing=math.sin(ph+i*math.pi+(math.pi if far else 0)) if clip=='walk' else 0
            lift=max(0,swing)*4
            knee=(mix(fx,fx*.7,d),mix(15,by+9,d))
            end=(mix(fx+swing*3,fx*.5,d),mix(3+lift,by+10,d))
            a.limb([(x,by-4),knee,end],BROWN if far else AMBER,4)
            if not d: foot(a,end[0],lift,3,2,AMBER)
        if far:
            a.ball(-13,by,23,14,AMBER,ang=d*.9)
            gear(a,-20,by+8,8,PLATE,ph*.12)
            a.ball(7,by+5,12,16,AMBER)
    hx=12+st*8; hy=mix(by+27+w*6,by+8,d)
    a.ball(hx,hy,14,12,AMBER)
    a.face(hx+1,hy,clip,n,.8,sep=5,pupil=TEAL[0])
    for sg in (-1,1):
        a.limb([(hx+sg*6,hy+9),(hx+sg*10,hy+23)],BROWN,2)
        a.ball(hx+sg*10,hy+24,2.5,2.5,TEAL)
    # Two jointed scythes swing from above the head into a forward cut.
    for far in (True,False):
        sh=(8,by+13); elbow=(mix(18,10,w)+st*9,by+20+w*21-st*11)
        tip=(mix(26,15,w)+st*24,by+14+w*30-st*19)
        if far: elbow=(elbow[0]-8,elbow[1]-6); tip=(tip[0]-8,tip[1]-6)
        if d: elbow=mixp(elbow,(12,11),d);tip=mixp(tip,(28,5),d)
        a.limb([sh,elbow,tip],AMBER if not far else BROWN,5)
        a.poly([tip,(tip[0]+7,tip[1]+15),(tip[0]+21,tip[1]+12),(tip[0]+25,tip[1]+5),(tip[0]+13,tip[1]+9)],PLATE[3],outline=PLATE[0])
    if d>.12:
        a.line([(-26,by+7),(-19,by+1),(-22,by-4),(-10,by-8)],OUTLINE,2)
        spark(a,32,7,GOLD[3],3)
    return a


def gearling(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('gearling',recoil+st*26-w*10)
    cy=mix(30+bob*.5+w*7,15,d)
    for sg in (-1,1):
        lift=max(0,math.sin(ph+(sg<0)*math.pi))*4 if clip=='walk' else 0
        a.limb([(sg*11,cy-12),(sg*14,8+lift)],PLATE,5)
        foot(a,sg*14,lift,5,3,PLATE)
    gear(a,0,cy,26,AMBER,(ph*.15 if clip in ('idle','walk') else st*.7)+d*.8)
    a.ball(0,cy,17,17,PLATE)
    a.face(1,cy+2,clip,n,.92,sep=6,pupil=TEAL[0])
    for sg in (-1,1):
        a.limb([(sg*5,cy+24),(sg*9,cy+36)],BROWN,3)
        a.ball(sg*9,cy+37,4,4,GOLD)
    if st>.25:
        spark(a,38,cy,GOLD[4],4)
    if d>.1:
        a.line([(-10,cy+13),(-4,cy+5),(-8,cy-2),(2,cy-10)],OUTLINE,2)
        for i in range(3): gear(a,-29+i*26,4,4+i%2,PLATE,d+i)
    return a


def orbitseer(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('orbitseer',recoil+st*10-w*5)
    cy=mix(60+bob+w*8,19,d)
    angle=ph*.25 if clip in ('idle','walk') else -w*.8+st*.9
    # Two brass orbital rings remain around the eye and fall into fragments on death.
    for sg in (-1,1):
        points=[]
        for j in range(25):
            t=j*math.pi/12
            points.append((math.cos(t)*40,cy+math.sin(t)*10+sg*math.cos(t)*5))
        if d<.85: a.line(points,GOLD[2],3)
    for j in range(4):
        t=angle+j*math.pi/2
        x=mix(math.cos(t)*39,-32+j*21,d); y=mix(cy+math.sin(t)*10,4,d)
        a.ball(x,y,4,4,VIOLET if j%2 else GOLD)
    a.ball(0,cy,23,22,BLUE)
    a.ball(0,cy+1,16,17,PEARL)
    a.eye(0,cy+1,clip,n,1.7,pupil=TEAL[0])
    a.ellipse(-16,cy-8,3,2,BLUSH);a.ellipse(16,cy-8,3,2,BLUSH)
    if st>.3:
        a.poly([(14,cy+4),(67,cy+11),(67,cy-8),(14,cy-3)],TEAL[3],outline=TEAL[0])
        a.poly([(15,cy+1),(67,cy+4),(67,cy-2),(15,cy-1)],WHITE)
    if d>.1:
        a.line([(-13,cy+15),(-5,cy+5),(-9,cy-3),(3,cy-15)],OUTLINE,2)
    return a


def chronoguard(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('chronoguard',recoil+st*7-w*3)
    by=mix(38+bob*.4,15,d)
    biped_legs(a,PLATE,ph,clip,11,by-7,6,3,6,st,w,d)
    a.ball(0,by,18,20,PLATE)
    a.poly([(-14,by+8),(14,by+8),(12,by-9),(-12,by-9)],BLUE[2],outline=BLUE[0])
    gear(a,0,by,10,GOLD,0)
    a.ball(0,by,6,6,PEARL)
    a.line([(0,by),(0,by+4),(3,by+5)],OUTLINE,2)
    a.ball(0,by+25,16,14,PLATE)
    a.poly([(-13,by+27),(13,by+27),(12,by+17),(-12,by+17)],SLATE[0],outline=OUTLINE)
    a.face(0,by+23,clip,n,.75,sep=5,mouth=False,pupil=TEAL[0])
    a.poly([(-4,by+38),(1,by+54),(7,by+38)],GOLD[3],outline=GOLD[0])
    a.limb([(-13,by+11),(-24,by+3),(-28,by-2)],PLATE,7)
    a.poly([(-36,by+6),(-18,by+7),(-18,by-10),(-27,by-19),(-37,by-10)],BLUE[2],outline=GOLD[2])
    hand=(mix(26,10,w)+st*27,mix(by+9,by+31,w)-st*11)
    if d: hand=mixp(hand,(25,6),d)
    a.limb([(13,by+11),(20,by+16),hand],PLATE,6)
    a.ball(*hand,5,5,PLATE)
    ang=mix(1.25,.1,st)-d*.9
    tip=(hand[0]+math.cos(ang)*37,hand[1]+math.sin(ang)*37)
    a.line([(hand[0]-math.cos(ang)*16,hand[1]-math.sin(ang)*16),tip],BROWN[2],4)
    a.poly([tip,(tip[0]+5,tip[1]+8),(tip[0]+10,tip[1]),(tip[0]+4,tip[1]-4)],GOLD[3],outline=GOLD[0])
    if d>.15: a.line([(-10,by+14),(-2,by+5),(-5,by-4),(5,by-12)],OUTLINE,2)
    return a


def pendulummatron(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('pendulummatron',recoil)
    by=mix(39+bob*.4,12,d);hy=mix(69+bob*.4,22,d)
    hem=29+d*10
    a.poly([(-11,by+4),(11,by+4),(hem,3),(hem-10,1),(0,3),(-hem+8,1),(-hem,3)],VIOLET[2],outline=VIOLET[0])
    for x in (-18,-8,3,14): a.line([(x*.4,by),(x,4)],VIOLET[3],2)
    a.poly([(-10,by+1),(10,by+1),(18,6),(-18,6)],PEARL[3],outline=PEARL[0])
    a.ball(0,by+5,13,10,VIOLET)
    a.ball(0,hy,15,14,PEARL)
    a.ball(-6,hy+10,12,8,PLATE)
    a.ball(4,hy+12,9,7,PLATE)
    a.face(1,hy,clip,n,.85,sep=5.5,pupil=VIOLET[0])
    a.limb([(10,by+8),(22,by+5),(26,by+1)],VIOLET,5)
    a.ball(26,by+1,4,4,PEARL)
    hand=(mix(-22,-5,w)+st*18,mix(by+6,by+27,w))
    if d: hand=mixp(hand,(-23,7),d)
    a.limb([(-10,by+8),(-17,by+12),hand],VIOLET,5)
    a.ball(*hand,4,4,PEARL)
    angle=mix(mix(-1.55,1.25,w),-.25,st)-d*.4
    end=(hand[0]+math.cos(angle)*34,max(6,hand[1]+math.sin(angle)*34))
    a.line([hand,end],GOLD[1],3)
    gear(a,*end,10,GOLD,st*.4)
    a.ball(*end,4,4,PEARL)
    if d>.12:
        for i in range(3): spark(a,22+i*5,5+i%2*3,GOLD[3],2)
    return a


def epochengine(clip,n):
    w,st,d,ph,bob,recoil=curves(clip,n)
    a=Painter('epochengine',recoil+st*6-w*3)
    cy=mix(51+bob*.5+w*4,24,d)
    for sg in (-1,1):
        lift=max(0,math.sin(ph+(sg<0)*math.pi))*3 if clip=='walk' else 0
        a.limb([(sg*18,cy-20),(sg*23,10+lift)],BROWN,8)
        gear(a,sg*23,7+lift,8,AMBER,ph*.12)
    gear(a,0,cy,34,AMBER,ph*.10+d*.5)
    a.ball(0,cy,26,26,PEARL)
    a.face(0,cy+4,clip,n,1.05,sep=7,pupil=CRIMSON[0] if 'CRIMSON' in globals() else BROWN[0])
    a.line([(0,cy),(0,cy-12),(9,cy-18)],GOLD[1],3)
    for sg in (-1,1):
        sh=(sg*25,cy+5)
        hand=(sg*41+(st*22 if sg>0 else -w*8),cy+2+w*28-st*12)
        if d: hand=mixp(hand,(sg*43,8),d)
        a.limb([sh,(sg*35,cy+12),hand],BROWN,8)
        gear(a,*hand,11,PLATE,st*.5)
    a.limb([(-14,cy+28),(-14,cy+42)],PLATE,6)
    a.ellipse(-14,cy+47,8+w*3,5+w*2,PEARL[2])
    if st>.3:
        for i in range(3): spark(a,70+i*7,cy-5+i*6,GOLD[4],4)
    if d>.1:
        a.line([(-19,cy+18),(-7,cy+8),(-12,cy),(2,cy-11),(-1,cy-23)],OUTLINE,2)
        for i in range(4): gear(a,-35+i*23,5,5,AMBER,d+i)
    return a


DRAW = {k: globals()[k] for k in KINDS}


STRICT = True
BAD = []


def frame(kind, clip, n):
    kw, kh, kax, kay = kind_frame(kind)
    grid = np.array(DRAW[kind](clip, n).im)
    if kind in FLYING:
        # Flying Orbit Seer stays well above the ground in living clips and settles onto kay at the end of death.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and clip == 'die' and (n == 7 or int(rows.max()) > kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    else:
        # Grounded kinds rest their lowest pixel exactly on the anchor row in every living and death frame.
        rows = np.nonzero(grid.any(axis=1))[0]
        if rows.size and (clip == 'die' or int(rows.max()) != kay):
            grid = np.roll(grid, kay - int(rows.max()), axis=0)
    if clip == 'hurt' and n == 0:
        grid[grid > 0] = EYE_WHITE
    problem = None
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
    return {clip: np.array([frame(kind, clip, n) for n in range(count)]) for clip, (_, count) in CLIPS.items()}


def registry():
    return json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}


def api_draw(sid, offset, data):
    for clip, grids in data.items():
        for n, grid in enumerate(grids):
            old.api('draw', dict(sprite_id=sid, frame=offset + n, ops=[dict(op='grid', rows=grid.tolist(), x=0, y=0, layer=0)]))
        offset += len(grids)
    return offset


def build():
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    saved = registry()
    existing = {s['name']: s['sprite_id'] for s in old.api('list')['sprites']}
    data = {kind: frames(kind) for kind in KINDS}
    for kind in KINDS:
        if kind in saved:
            print('Preserving saved source', kind, saved[kind], flush=True)
            continue
        name = PREFIX + kind + '_all'
        assert name not in existing, 'Unregistered source already exists: ' + name
        np.savez_compressed(ROOT / f'scripts/orrery_slime_{kind}_raw.npz', **data[kind])
        kw, kh, _, _ = kind_frame(kind)
        sid = old.api('create', dict(
            name=name, width=kw, height=kh, frames=34, layers=1, fps=10,
            palette=PALETTE, persist=True, ops=[dict(op='set_layer', layer=0, name=kind)]
        ))['sprite_id']
        saved[kind] = sid
        REGISTRY.write_text(json.dumps(saved, indent=2) + '\n')
        print(kind, sid, api_draw(sid, 0, data[kind]), 'frames saved', flush=True)


def refresh():
    names = [k for k in sys.argv[2:] if k in KINDS]
    assert names, 'name the kinds to refresh'
    saved = registry()
    for kind in names:
        data = frames(kind)
        np.savez_compressed(ROOT / f'scripts/orrery_slime_{kind}_raw.npz', **data)
        print('Refreshed', kind, saved[kind], api_draw(saved[kind], 0, data), 'frames', flush=True)


def cel_grid(cel, w=W, h=H):
    if 'rle' in cel:
        runs = cel['rle']
        return np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(h, w)
    return np.array(cel['grid'], dtype=np.uint8)


def export():
    saved = registry()
    assert set(saved) == set(KINDS)
    meta = dict(frame=[W, H], anchor=[AX, AY], kinds=KINDS, clips={}, sprites=saved, tops={}, artStyle='greenmeadow-slime')
    proof, atlases = {}, {}
    for kind in KINDS:
        kw, kh, kax, kay = kind_frame(kind)
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        assert (sp['width'], sp['height'], len(sp['frames'])) == (kw, kh, 34)
        atlas = Image.new('RGBA', kindframe.atlas_size(kw, kh))
        offset, rows = 0, []
        for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
            meta['clips'][clip] = dict(fps=fps, n=count, row=row, editorStart=offset)
            for n in range(count):
                im = rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette'])
                bounds = im.getbbox()
                kindframe.check_bounds(bounds, kw, kh)
                atlas.alpha_composite(im, (n * kw, row * kh))
                rows.append(dict(clip=clip, n=n, sha256=hashlib.sha256(im.tobytes()).hexdigest(), bounds=bounds))
            offset += count
        meta['tops'][kind] = kindframe.top_of([r['bounds'] for r in rows if r['clip'] == 'idle'], kay)
        kindframe.set_kind_frame(meta, kind, kw, kh, kax, kay)
        atlases[kind] = atlas
        proof[kind] = dict(source=saved[kind], frames=rows)
    for kind, atlas in atlases.items():
        dest = ASSETS / f'orrery_{kind}.png'
        atlas.save(dest, optimize=True)
        proof[kind]['atlasSha256'] = hashlib.sha256(dest.read_bytes()).hexdigest()
    MANIFEST.write_text(json.dumps(meta, indent=2) + '\n')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'editor-export-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print('Exported 204 saved PixelFlow frames and derived health-bar tops.', flush=True)


def verify():
    meta = json.loads(MANIFEST.read_text())
    saved = registry()
    for kind in KINDS:
        assert meta['sprites'][kind] == saved[kind]
        sp = old.api('get?sprite_id=' + saved[kind])['sprite']
        kw, kh, _, _ = kindframe.frame_of(meta, kind)
        atlas = Image.open(ASSETS / f'orrery_{kind}.png').convert('RGBA')
        assert atlas.size == kindframe.atlas_size(kw, kh), (kind, atlas.size)
        offset = 0
        for row, (clip, (_, count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cell = atlas.crop((n * kw, row * kh, (n + 1) * kw, (row + 1) * kh))
                assert cell.tobytes() == rgba(cel_grid(sp['frames'][offset + n]['cels'][0], kw, kh), sp['palette']).tobytes(), (kind, clip, n, 'editor mismatch')
            offset += count
        print(kind, '34 saved editor frames equal exported atlas', flush=True)


def extents():
    global STRICT
    STRICT = False
    for kind in [k for k in KINDS if k in DRAW]:
        old_kf = KIND_FRAMES.get(kind)
        KIND_FRAMES[kind] = (192, 192, 96, 160)
        left = right = up = 0
        for clip, grids in frames(kind).items():
            for grid in grids:
                ys, xs = np.nonzero(grid)
                if xs.size:
                    left = max(left, 94 - int(xs.min()) + 2)
                    right = max(right, int(xs.max()) - 94 + 2)
                    up = max(up, 158 - int(ys.min()))
        print(f'{kind}: left {left} right {right} up {up}  ->  suggested ax {left+4}, w {left+4+right+5}, ay {up+4}, h {up+4+6}')
        if old_kf:
            KIND_FRAMES[kind] = old_kf
        else:
            del KIND_FRAMES[kind]


def preview():
    global STRICT
    STRICT = False
    OUT.mkdir(parents=True, exist_ok=True)
    only = [k for k in sys.argv[2:] if k in KINDS] or [k for k in KINDS if k in DRAW]
    for kind in only:
        kw, kh, _, kay = kind_frame(kind)
        data = frames(kind)
        sheet = Image.new('RGB', (8 * kw * 2, 5 * (kh * 2 + 26)), '#221f33')
        sd = ImageDraw.Draw(sheet)
        for row, (clip, grids) in enumerate(data.items()):
            for n, grid in enumerate(grids):
                im = rgba(grid).resize((kw * 2, kh * 2), Image.Resampling.NEAREST)
                sheet.paste(im, (n * kw * 2, row * (kh * 2 + 26)), im)
                sd.text((n * kw * 2 + 8, row * (kh * 2 + 26) + kh * 2 + 4), f'{clip} {n}', fill='white')
                gy = row * (kh * 2 + 26) + kay * 2 + 2
                sd.line([(n * kw * 2, gy), (n * kw * 2 + kw * 2, gy)], fill='#5c5284')
        sheet.save(OUT / f'preview-{kind}.png')
        print(OUT / f'preview-{kind}.png')
    print('Frame problems:', BAD or 'none')


if __name__ == '__main__':
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh, 'export': export,
     'verify': verify}[sys.argv[1] if len(sys.argv) > 1 else 'preview']()
