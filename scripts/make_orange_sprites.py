#!/usr/bin/env python3
"""Create/export orange gear drawings through PixelFlow.

`preview` renders local drafts. `build` creates editable PixelFlow sprites once;
`export` reads PixelFlow's saved cels, preserving later editor changes.
"""
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw
from make_crag_sprites import api

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / 'client/assets/orange.txt'
ASSETS = ROOT / 'client/assets'
RULES = json.loads((ROOT / 'world/orange_rules.txt').read_text())['pieces']
SIZE = 64
PALETTES = [('#33191b', '#89512f', '#f2a347', '#ffe39a', '#e7652d'),
            ('#183424', '#426d38', '#84b95b', '#dbf4a2', '#3fa87d'),
            ('#182842', '#396f9a', '#83c9e0', '#ecfaff', '#f8d958'),
            ('#162536', '#2d6380', '#65b5b6', '#d2fbef', '#b990e9'),
            ('#14172d', '#363b70', '#7c88c7', '#e6eaff', '#e6b5ff'),
            ('#44301c', '#bc7931', '#f6c55f', '#fff2b2', '#f6e7c1'),
            ('#391b25', '#8e3537', '#e67842', '#ffe2a2', '#f4b16a')]


def render(n):
    piece = RULES[n]
    slot = piece['slot']
    family = n // 5
    dark, base, light, glint, gem = PALETTES[family]
    im = Image.new('RGBA', (SIZE, SIZE))
    d = ImageDraw.Draw(im)
    kw = dict(outline=dark, width=2)
    if slot == 'armor':
        d.polygon([(17,15),(25,11),(32,16),(39,11),(47,15),(51,25),(44,30),
                   (43,48),(33,54),(21,48),(20,30),(13,25)], fill=base)
        d.polygon([(20,17),(27,15),(32,20),(37,15),(44,17),(43,43),(32,50),(21,43)], fill=light, **kw)
        d.line([(32,21),(32,49)], fill=dark, width=2)
        d.polygon([(25,27),(32,24),(39,27),(32,36)], fill=gem, **kw)
        d.line([(22,20),(26,18),(29,21)], fill=glint, width=2)
    elif slot == 'weapon':
        d.polygon([(14,51),(18,47),(39,14),(49,8),(46,20),(23,53)], fill=light, **kw)
        d.line([(18,48),(45,13)], fill=glint, width=3)
        d.line([(13,43),(27,50)], fill=base, width=6)
        d.line([(13,43),(27,50)], fill=dark, width=2)
        d.ellipse((10,51,18,59), fill=gem, **kw)
    elif slot == 'headgear':
        d.polygon([(14,43),(17,24),(23,19),(29,23),(33,14),(39,23),(46,19),(50,25),(51,43)], fill=base, **kw)
        d.polygon([(19,32),(25,28),(33,34),(40,28),(46,32),(45,43),(20,43)], fill=light, **kw)
        d.polygon([(29,31),(33,26),(37,31),(33,38)], fill=gem, **kw)
        d.line([(20,25),(23,22)], fill=glint, width=2)
    elif slot == 'shoulders':
        for x, sign in [(12,1),(52,-1)]:
            d.polygon([(x,22),(x+sign*15,17),(x+sign*22,30),(x+sign*16,42),(x+sign*3,39)], fill=base, **kw)
            d.polygon([(x+sign*2,25),(x+sign*14,21),(x+sign*18,30),(x+sign*14,36),(x+sign*4,34)], fill=light, **kw)
            d.ellipse((x+sign*8-3,27,x+sign*8+3,33), fill=gem)
        d.line([(28,21),(36,21)], fill=glint, width=3)
    else:  # two gauntlets
        for x in (13,37):
            d.polygon([(x+3,18),(x+14,18),(x+18,26),(x+15,42),(x+5,47),(x,41),(x+1,26)], fill=base, **kw)
            d.polygon([(x+4,22),(x+13,22),(x+14,33),(x+6,37),(x+3,32)], fill=light, **kw)
            d.polygon([(x+6,27),(x+10,24),(x+14,27),(x+10,33)], fill=gem)
            d.line([(x+4,20),(x+13,20)], fill=glint, width=2)
    if family == 1:
        # Verdant Crown grows leaves and thorn tips; the outline differs from the brass family.
        for x,y in [(10,14),(49,11),(7,43),(52,47)]:
            d.polygon([(x,y),(x+5,y-4),(x+4,y+4)], fill=gem, **kw)
    elif family == 2:  # Storm Oracle: lightning forks and charged points.
        d.line([(29,7),(34,13),(31,18),(38,22),(34,30)], fill=gem, width=2)
        d.line([(10,35),(15,29),(13,24),(19,19)], fill=glint, width=2)
        d.line([(51,45),(47,40),(49,35),(44,31)], fill=gem, width=2)
    elif family == 3:  # Abyss Singer: pearl bubbles and wave crests.
        d.arc((6,7,56,59), 195, 345, fill=gem, width=2)
        d.arc((12,11,52,53), 205, 345, fill=glint, width=2)
        for x,y in [(12,16),(48,15),(8,48),(55,43)]:
            d.ellipse((x-2,y-2,x+2,y+2), fill=glint, outline=dark)
    elif family == 4:  # Starforged: small constellations connected in dark metal.
        stars = [(9,13),(16,10),(48,11),(55,20),(7,45),(51,52)]
        d.line(stars[:4], fill=gem, width=1)
        d.line(stars[4:], fill=gem, width=1)
        for x,y in stars:
            d.line([(x-2,y),(x+2,y)], fill=glint, width=1)
            d.line([(x,y-2),(x,y+2)], fill=glint, width=1)
    elif family == 5:  # Solar Regent: sun discs and radiating rays.
        d.ellipse((27,3,37,13), fill=gem, outline=dark, width=2)
        for x0,y0,x1,y1 in [(32,0,32,3),(19,8,24,11),(40,11,45,8),
                              (5,36,11,36),(53,36,59,36),(25,56,21,61),(39,56,43,61)]:
            d.line([(x0,y0),(x1,y1)], fill=glint, width=2)
    elif family == 6:  # Ash Phoenix: hooked feathers and small embers.
        for x,y,sign in [(7,19,1),(49,18,-1),(5,43,1),(52,45,-1)]:
            d.polygon([(x,y+9),(x+sign*3,y),(x+sign*8,y+6),(x+sign*5,y+4)],
                      fill=gem, outline=dark)
        for x,y in [(20,7),(43,10),(31,56)]:
            d.ellipse((x,y,x+2,y+2), fill=glint)
    return im


def grid(image, colors):
    index = {tuple(bytes.fromhex(c[1:]))+(255,): n for n,c in enumerate(colors) if n}
    return [[index.get(image.getpixel((x,y)), 0) for x in range(SIZE)] for y in range(SIZE)]


def image_from_pixel_flow(sprite):
    assert (sprite['width'], sprite['height'], len(sprite['frames'])) == (SIZE, SIZE, 1)
    cel = sprite['frames'][0]['cels'][0]
    if 'rle' in cel:
        data = [value for count, value in zip(cel['rle'][::2], cel['rle'][1::2]) for _ in range(count)]
        pixels = [data[i*SIZE:(i+1)*SIZE] for i in range(SIZE)]
    else:
        pixels = cel['grid']
    palette = [tuple(bytes.fromhex(c[1:]))+(255,) if len(c)==7 else (0,0,0,0) for c in sprite['palette']]
    out = Image.new('RGBA', (SIZE,SIZE))
    out.putdata([palette[p] for row in pixels for p in row])
    return out


def main():
    mode = sys.argv[1] if len(sys.argv)>1 else 'preview'
    first = int(sys.argv[2]) if len(sys.argv)>2 else 1
    last = int(sys.argv[3]) if len(sys.argv)>3 else len(PALETTES) * 5
    assert 1 <= first <= last <= min(len(RULES), len(PALETTES) * 5)
    selected = range(first-1, last)
    meta = json.loads(META.read_text()) if META.exists() else {'version':1,'sprites':{}}
    if mode == 'preview':
        dest = ROOT/'test-results/orange-preview'; dest.mkdir(parents=True,exist_ok=True)
        for n in selected: render(n).resize((256,256),Image.Resampling.NEAREST).save(dest/f'orange_{n+1:02}.png')
        print(dest)
    elif mode == 'build':
        for n in selected:
            name = RULES[n]['id']
            if name in meta['sprites']: continue
            colors = ['#00000000', *PALETTES[n//5]]
            sprite_id = api('create', {'name':'valhallasc_'+name,'width':SIZE,'height':SIZE,
                                       'frames':1,'layers':1,'fps':1,'palette':colors,'persist':True,
                                       'ops':[{'op':'set_layer','layer':0,'name':name}]})['sprite_id']
            try:
                api('draw',{'sprite_id':sprite_id,'frame':0,'ops':[{'op':'grid','rows':grid(render(n),colors),'x':0,'y':0,'layer':0}]})
            except Exception:
                api('delete',{'sprite_id':sprite_id})
                raise
            meta['sprites'][name]=sprite_id
            META.write_text(json.dumps(meta,indent=2)+'\n')
            print(name,sprite_id,flush=True)
    elif mode == 'export':
        for n in selected:
            name = RULES[n]['id']
            sprite = api('get?sprite_id='+meta['sprites'][name])
            image_from_pixel_flow(sprite.get('sprite',sprite)).save(ASSETS/f'{name}.png')
            print(name,'exported',flush=True)
    else:
        raise SystemExit('Use preview, build, or export')


if __name__ == '__main__': main()
