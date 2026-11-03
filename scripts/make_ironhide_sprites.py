#!/usr/bin/env python3
"""makesprites workflow: preview | build [--replace] | export.

Build saves a NEW valhallasc_ironhide_slime_style_all sprite in PixelFlow (34 frames),
preserving the original a3f8837048d1098c. It refuses
existing names unless --replace is given; --replace discards their hand edits.
Export reads editor frames back so edits survive. No original Valhalla art is touched.
Needs numpy/Pillow; build/export also need PixelFlow and its local agent key.
"""
import json
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
PREFIX = 'valhallasc_ironhide_slime_style_'
PALETTE = ['#00000000','#25364c','#3b5571','#6084a4','#8bb4cb','#bfdee2','#e8f5e9',
           '#5b4031','#8a5e3c','#bd8b50','#ebc879','#fff1bd','#edf5e8','#ffffff','#d9a177']
CLIPS = {'idle': (6, 6), 'walk': (10, 8), 'attack': (12, 8),
         'hurt': (10, 4), 'die': (8, 8)}


def frame(clip, n):
    """Chunky chibi beetle: the slimes' soft glossy pixels, eyes and squash/stretch."""
    im=Image.new('P',(W,H),0);d=ImageDraw.Draw(im)
    lean,lift,sx,sy=0,0,1.,1.
    if clip=='idle':lift=[0,1,2,1,0,0][n];sx=[1,1,.98,1.04,1,1][n]
    elif clip=='walk':
        lift=[0,0,3,6,4,0,0,0][n];sx=[1.04,1.1,.94,.9,.96,1.12,1.06,1.][n];sy=[.97,.87,1.08,1.12,1.04,.83,.94,1.][n]
    elif clip=='attack':
        lean=[-1,-3,-4,1,4,4,2,0][n];lift=[0,0,0,3,5,0,0,0][n];sx=[1.04,1.1,1.14,.92,.94,1.06,1.04,1][n];sy=[.97,.88,.82,1.12,1.08,.86,.95,1][n]
    elif clip=='hurt':lean=[-3,-2,-1,0][n];sx=[1.12,1.06,.97,1][n];sy=[.83,.93,1.04,1][n]
    elif clip=='die':sx=1+min(n,4)*.035;sy=max(.25,1-max(0,n-1)*.21);lift=-max(0,n-1)*1.1
    cx,cy=31+lean,AY-18-lift
    def pos(x,y):return (round(cx+(x-31)*sx),round(cy+(y-42)*sy))
    def ellipse(x,y,rx,ry,index):
        px,py=pos(x,y);rx=max(1,round(rx*sx));ry=max(1,round(ry*sy));d.ellipse((px-rx,py-ry,px+rx,py+ry),fill=index)
    def line(points,index,width=1):d.line([pos(x,y) for x,y in points],fill=index,width=width)
    def ball(x,y,rx,ry,ramp):
        px,py=pos(x,y);rx*=sx;ry*=sy
        for yy in range(max(1,math.floor(py-ry)),min(H-1,math.ceil(py+ry)+1)):
            for xx in range(max(1,math.floor(px-rx)),min(W-1,math.ceil(px+rx)+1)):
                u,v=(xx-px)/rx,(yy-py)/ry;rr=u*u+v*v
                if rr>1:continue
                z=math.sqrt(max(0,1-rr));light=max(0,min(.999,.24+.70*(-.40*u-.54*v+.74*z)))
                value=light*(len(ramp)-1);lo=int(value);fraction=value-lo
                threshold=((xx%4)*5+(yy%4)*3)%16/16
                shade=min(len(ramp)-1,lo+int(fraction>threshold))
                if rr>.91 and (u+v)>.2:shade=0
                im.putpixel((xx,yy),ramp[shade])
    dead=clip=='die' and n>=2
    # Three far and three near feet: short, chunky limbs tuck beneath the shell.
    stride=math.sin(n*math.pi/2)*2.5 if clip=='walk' else 0
    for k in range(3):
        x=20+k*11;phase=stride*(-1 if k==1 else 1)
        line([(x,45),(x-5,49),(x-7+phase,53)],1,4);ellipse(x-7+phase,53,3,2,8)
    ball(30,40,21,16,[1,2,3,4,5,6])
    # Soft underside and wing-plate crease retain the iron shell without thin mechanical detail.
    line([(17,48),(23,53),(32,55),(41,51)],2,3)
    line([(30,25),(34,30),(37,37),(37,45),(34,51)],2,2)
    line([(28,26),(32,31),(35,37)],5,1)
    for x,y in [(21,30),(18,33),(24,28)]:ellipse(x,y,2,1,6)
    for k in range(3):
        x=19+k*10;phase=stride*(-1 if k==1 else 1)
        if dead:line([(x,48),(x+2,51),(x+6,49)],8,3)
        else:
            line([(x,47),(x-3,53),(x-1+phase,57)],1,5)
            line([(x,47),(x-3,53),(x-1+phase,56)],9,3);ellipse(x-1+phase,57,3,2,8)
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
    if clip=='die' and n>=4:
        # Collapse into a low shell with a few bouncing pixels, like the slime's breakup.
        arr=np.array(im);arr[:AY-10]=0;im=Image.fromarray(arr,'P');d=ImageDraw.Draw(im)
        for k in range(5):
            x=20+k*8+(n-4)*(k-2);y=AY-12-(n-4)*(5-abs(k-2))
            if 1<x<W-2 and 1<y<H-2:d.rectangle((x,y,x+1,y+1),fill=5 if k%2 else 10)
        if n>=6:
            arr=np.array(im);arr[AY-8:]=0;im=Image.fromarray(arr,'P');d=ImageDraw.Draw(im);d.ellipse((16,AY-3,56,AY-1),fill=3);d.line([(54,AY-2),(61,AY-4)],fill=9,width=2)
    arr=np.array(im)
    if clip in ('hurt','die') and n==0:arr[arr>0]=12
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
    if existing and not replace:
        raise SystemExit('Sprites already exist. Use export to preserve edits; --replace discards them.')
    if replace:
        for sid in existing.values():
            api('delete', {'sprite_id': sid})
    frames = {clip: np.array([frame(clip, n) for n in range(count)])
              for clip, (_, count) in CLIPS.items()}
    np.savez_compressed(ROOT / 'scripts/ironhide_raw.npz', **frames)
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


def export():
    saved, clips = ids(), {}
    packet = api('get?sprite_id=' + saved[PREFIX + 'all'])
    sp = packet.get('sprite', packet)
    assert (sp['width'], sp['height'], len(sp['frames'])) == (W, H, sum(n for _, n in CLIPS.values()))
    atlas = Image.new('RGBA', (8 * W, len(CLIPS) * H))
    offset = 0
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
            atlas.alpha_composite(image, (n * W, row * H))
            sheet.alpha_composite(image, (n * W, 0))
        clips[clip] = {'fps': fps, 'n': count, 'row': row, 'editorStart': offset}
        offset += count
        dest = ROOT / 'test-results/ironhide-export'
        dest.mkdir(parents=True, exist_ok=True)
        sheet.resize((sheet.width * 2, H * 2), Image.Resampling.NEAREST).save(dest / f'{clip}.png')
    atlas.save(ASSETS / 'ironhide.png', optimize=True)
    (ASSETS / 'ironhide.txt').write_text(json.dumps({'frame': [W, H], 'anchor': [AX, AY],
        'kinds': ['beetle'], 'clips': clips, 'sprites': saved}, indent=2) + '\n')
    print('Exported client/assets/ironhide.png and ironhide.txt from PixelFlow')


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
        raise SystemExit('Usage: make_ironhide_sprites.py preview [directory] | build [--replace] | export')
