#!/usr/bin/env python3
"""Rigid Ironhide: preview | build | export.

New PixelFlow prefix; old sources preserved. --replace is refused.
Export reads saved editor frames and derives health-bar tops.
"""
import json
import hashlib
import math
import os
from pathlib import Path
import re
import ssl
import sys
import urllib.request
import urllib.error

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
W, H, AX, AY = 72, 64, 36, 60
PREFIX = 'valhallasc_meadow_ironhide_rigid_'
PALETTE = ['#00000000','#25364c','#3b5571','#6084a4','#8bb4cb','#bfdee2','#e8f5e9',
           '#5b4031','#8a5e3c','#bd8b50','#ebc879','#fff1bd','#edf5e8','#ffffff','#d9a177']
CLIPS = {'idle': (6, 6), 'walk': (10, 8), 'attack': (12, 8),
         'hurt': (10, 4), 'die': (8, 8)}


def frame(clip, n):
    """Glossy steel beetle with fixed-size plates and articulated legs.

    Body motion is translation/rotation only. Death cracks the shell, folds
    the six knees and tips the intact shell/head onto its side; no scaling.
    """
    im=Image.new('P',(W,H),0);d=ImageDraw.Draw(im)
    lean,lift,angle=0,0,0
    if clip=='idle':
        # Tiny weight shift: rigid shell, antenna/horn and eyes move together.
        lean=[0,0,1,1,0,-1][n]
    elif clip=='walk':
        lean=[0,1,1,0,-1,-1,0,0][n]
        lift=[0,1,1,0,0,1,1,0][n]
    elif clip=='attack':
        lean=[-1,-3,-4,-1,3,4,2,0][n]
        lift=[0,0,0,1,1,0,0,0][n]
    elif clip=='hurt':
        lean=[-3,-2,-1,0][n];lift=[1,0,1,0][n]
    elif clip=='die':
        angle=[0,0,5,12,21,30,34,32][n]
        lean=[0,-1,-1,-2,-2,-2,-2,-2][n]
        lift=[0,0,0,1,3,5,6,5][n]
    def pos(x,y):
        # Every rigid component has a single rotation and unchanged dimensions.
        return (round(x+lean),round(y-lift))
    def ellipse(x,y,rx,ry,index):
        px,py=pos(x,y);rx=max(1,round(rx));ry=max(1,round(ry));d.ellipse((px-rx,py-ry,px+rx,py+ry),fill=index)
    def line(points,index,width=1):d.line([pos(x,y) for x,y in points],fill=index,width=width)
    def ball(x,y,rx,ry,ramp):
        for yy in range(math.floor(y-ry),math.ceil(y+ry)+1):
            for xx in range(math.floor(x-rx),math.ceil(x+rx)+1):
                u,v=(xx-x)/rx,(yy-y)/ry;rr=u*u+v*v
                if rr>1:continue
                z=math.sqrt(max(0,1-rr));light=max(0,min(.999,.24+.70*(-.40*u-.54*v+.74*z)))
                value=light*(len(ramp)-1);lo=int(value);fraction=value-lo
                threshold=((xx%4)*5+(yy%4)*3)%16/16
                shade=min(len(ramp)-1,lo+int(fraction>threshold))
                if rr>.91 and (u+v)>.2:shade=0
                px,py=pos(xx,yy)
                if 0<=px<W and 0<=py<H:im.putpixel((px,py),ramp[shade])
    dead=clip=='die' and n>=3
    # Three far and three near feet: short, chunky limbs tuck beneath the shell.
    stride=math.sin(n*math.pi/4)*3 if clip=='walk' else 0
    buckle=max(0,n-1) if clip=='die' else 0
    for k in range(3):
        x=20+k*11;phase=stride*(-1 if k==1 else 1)
        line([(x,45),(x-5+buckle,49),(x-7+phase+buckle*1.5,53-buckle)],1,4);ellipse(x-7+phase+buckle*1.5,53-buckle,3,2,8)
    ball(30,40,21,16,[1,2,3,4,5,6])
    # Soft underside and wing-plate crease retain the iron shell without thin mechanical detail.
    line([(17,48),(23,53),(32,55),(41,51)],2,3)
    line([(30,25),(34,30),(37,37),(37,45),(34,51)],2,2)
    line([(28,26),(32,31),(35,37)],5,1)
    for x,y in [(21,30),(18,33),(24,28)]:ellipse(x,y,2,1,6)
    for k in range(3):
        x=19+k*10;phase=stride*(-1 if k==1 else 1)
        if dead:line([(x,48),(x-2+buckle,52-buckle/2),(x+5+buckle/2,49-buckle/2)],8,3)
        else:
            line([(x,47),(x-3+buckle,53-buckle/2),(x-1+phase+buckle,57-buckle)],1,5)
            line([(x,47),(x-3+buckle,53-buckle/2),(x-1+phase+buckle,56-buckle)],9,3);ellipse(x-1+phase+buckle,57-buckle,3,2,8)
    ball(47,44,11,11,[1,7,8,9,10])
    # A blunt gold horn, leaning forward during the same charge impact frames.
    horn=[(53,38),(58,32),(63,26),(64,33),(60,41),(55,43)]
    if clip=='attack' and n<3:horn=[(x-1,y-3) for x,y in horn]
    d.polygon([pos(x,y) for x,y in horn],fill=7)
    d.polygon([pos(x,y) for x,y in [(55,38),(60,32),(62,29),(62,34),(58,40)]],fill=10)
    line([(57,36),(61,30)],11,1)
    # Large white eye ovals and off-centre dark pupils echo the green slime.
    for x,y in [(43,40),(52,42)]:
        if dead:
            line([(x-2,y-2),(x+2,y+2)],1,1);line([(x+2,y-2),(x-2,y+2)],1,1)
        elif clip=='idle' and n==3:line([(x-3,y+1),(x+3,y)],1,2)
        else:
            ellipse(x,y,4,6,1);ellipse(x,y-1,3,5,12)
            ellipse(x+1,y,1.5,3.5,1);ellipse(x+1,y-2,1,1,13)
            if clip=='attack' and n<3:line([(x-3,y-5),(x+3,y-2)],7,2)
    line([(46,50),(49,52),(52,50)],7,1)
    ellipse(41,48,2,1,14)
    if clip=='die' and n>=2:
        # Angular dark fractures expose bright metal edges, then shed small chips.
        for points in [[(24,28),(26,34),(23,39),(28,44)],[(39,33),(35,38),(39,44),(36,49)]]:
            visible=points[:min(len(points),n)]
            line(visible,1,2)
            line([(x+1,y) for x,y in visible],5,1)
        if n>=4:
            for k in range(3):
                x=15+k*14+(n-4)*(k-1);y=53+(k%2)*2+(n-4)//2
                d.polygon([(x,y),(x+2,y-2),(x+4,y),(x+2,y+1)],fill=3+k)
    if angle:
        # Nearest-neighbour rigid rotation keeps plates solid, without forward-map holes.
        im=im.rotate(-angle, resample=Image.Resampling.NEAREST,
                     center=(33+lean,43-lift))
    arr=np.array(im)
    if clip=='hurt' and n==0:arr[arr>0]=12
    assert arr.any() and not (arr[0].any() or arr[-1].any() or arr[:,0].any() or arr[:,-1].any()),(clip,n)
    return arr


def rgba(grid, palette=PALETTE):
    colors = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] +
                       [0 if n == 0 else 255] for n, c in enumerate(palette)], dtype=np.uint8)
    return Image.fromarray(colors[grid])


def preview(frames, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for clip, grids in frames.items():
        sheet = Image.new('RGBA', (8 * W, H + 12), '#466e46')
        d = ImageDraw.Draw(sheet)
        for n, grid in enumerate(grids):
            sheet.alpha_composite(rgba(grid), (n * W, 0))
            d.line([(n * W + AX - 2, AY), (n * W + AX + 2, AY)], fill='#eabce1')
            d.text((n * W + 2, H), f'{clip} {n}', fill='white')
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(out / f'{clip}.png')


def api(route, body=None):
    env = Path(os.environ.get('PIXELFLOW_ENV', '/home/serveperry/webserver/www/pixelflow/.env'))
    key = re.search(r'^PIXELFLOW_API_KEY=(\S+)', env.read_text(), re.M).group(1)
    base = os.environ.get('PIXELFLOW_API_URL', 'https://localhost/pixelflow/api/sprites/')
    req = urllib.request.Request(base + route, None if body is None else json.dumps(body).encode(),
                                 {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + key})
    try:
        with urllib.request.urlopen(req, context=ssl._create_unverified_context(), timeout=30) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        result = json.load(error)
        raise RuntimeError(result.get('errors', result.get('error', 'PixelFlow request failed'))) from None
    if result.get('ok') is False:
        raise RuntimeError(result.get('errors', 'PixelFlow request failed'))
    return result


def ids():
    return {s['name']: s['sprite_id'] for s in api('list')['sprites'] if s['name'].startswith(PREFIX)}


def build(replace=False):
    existing = ids()
    if replace:
        raise SystemExit('--replace is refused. Edit the saved source and export to preserve it.')
    if existing:
        print('Saved source exists; use export to preserve editor frames.')
        return
    frames = {clip: np.array([frame(clip, n) for n in range(count)])
              for clip, (_, count) in CLIPS.items()}
    np.savez_compressed(ROOT / 'scripts/meadow_slime_raw.npz', **frames)
    sid = api('create', {'name': PREFIX + 'all', 'width': W, 'height': H,
                        'frames': sum(count for _, count in CLIPS.values()),
                        'layers': 1, 'fps': 10, 'palette': PALETTE, 'persist': True,
                        'ops': [{'op': 'set_layer', 'layer': 0, 'name': 'ironhide'}]})['sprite_id']
    offset = 0
    try:
        for clip, (_, count) in CLIPS.items():
            for n, grid in enumerate(frames[clip]):
                api('draw', {'sprite_id': sid, 'frame': offset + n, 'ops': [
                    {'op': 'grid', 'rows': grid.tolist(), 'x': 0, 'y': 0, 'layer': 0}]})
            print(clip, sid, f'frames {offset}–{offset + count - 1}')
            offset += count
    except Exception:
        api('delete', {'sprite_id': sid})
        raise
    (ROOT/'scripts/meadow_slime_sources.txt').write_text(
        json.dumps({PREFIX+'all': sid}, indent=2)+'\n')


def export():
    saved, clips = ids(), {}
    (ROOT/'scripts/meadow_slime_sources.txt').write_text(json.dumps(saved, indent=2)+'\n')
    packet = api('get?sprite_id=' + saved[PREFIX + 'all'])
    sp = packet.get('sprite', packet)
    assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
    atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
    offset = 0
    proof = []
    for row, (clip, (fps, count)) in enumerate(CLIPS.items()):
        sheet = Image.new('RGBA', (8 * W, H), '#466e46')
        for n in range(count):
            cel = sp['frames'][offset + n]['cels'][0]
            if 'rle' in cel:
                runs = cel['rle']
                grid = np.repeat(np.array(runs[1::2], dtype=np.uint8), runs[0::2]).reshape(H, W)
            else:
                grid = np.array(cel['grid'], dtype=np.uint8)
            image = rgba(grid, sp['palette'])
            bounds=image.getbbox()
            assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<W and bounds[3]<H
            proof.append(dict(clip=clip,n=n,sha256=hashlib.sha256(image.tobytes()).hexdigest(),bounds=bounds))
            atlas.alpha_composite(image, (n * W, row * H))
            sheet.alpha_composite(image, (n * W, 0))
        clips[clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
        offset += count
        dest = ROOT / 'test-results/ironhide-export'
        dest.mkdir(parents=True, exist_ok=True)
        sheet.resize((sheet.width * 2, H * 2), Image.Resampling.NEAREST).save(dest / f'{clip}.png')
    atlas.save(ASSETS / 'ironhide.png', optimize=True)
    (ASSETS / 'ironhide.txt').write_text(json.dumps({'frame': [W, H], 'anchor': [AX, AY],
        'kinds': ['beetle'], 'clips': clips, 'sprites': saved, 'tops': {'beetle': AY-min(r['bounds'][1] for r in proof if r['clip']=='idle')},
        'artStyle': 'greenmeadow-slime-rigid-shell'}, indent=2) + '\n')
    out=ROOT/'test-results/meadow-slime';out.mkdir(parents=True,exist_ok=True)
    (out/'editor-export-proof.json').write_text(json.dumps(dict(source=saved[PREFIX+'all'],frames=proof),indent=2)+'\n')
    print('Exported client/assets/ironhide.png and ironhide.txt from saved PixelFlow frames')


if __name__ == '__main__':
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if command == 'build':
        build('--replace' in sys.argv)
    elif command == 'export':
        export()
    elif command == 'preview':
        preview({c: [frame(c, n) for n in range(count)] for c, (_, count) in CLIPS.items()},
                sys.argv[2] if len(sys.argv) > 2 else ROOT / 'test-results/ironhide-preview')
    else:
        raise SystemExit('Usage: make_ironhide_sprites.py preview [directory] | build | export')
