#!/usr/bin/env python3
"""Create/export the first ten orange gear drawings through PixelFlow.

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
RULES = json.loads((ROOT / 'world/orange_rules.txt').read_text())['pieces'][:10]
SIZE = 64
PALETTES = [('#33191b', '#89512f', '#f2a347', '#ffe39a', '#e7652d'),
            ('#183424', '#426d38', '#84b95b', '#dbf4a2', '#3fa87d')]


def render(n):
    piece = RULES[n]
    slot = piece['slot']
    dark, base, light, glint, gem = PALETTES[n // 5]
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
    if n >= 5:
        # Verdant Crown grows leaves and thorn tips; the outline differs from the brass family.
        for x,y in [(10,14),(49,11),(7,43),(52,47)]:
            d.polygon([(x,y),(x+5,y-4),(x+4,y+4)], fill=gem, **kw)
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
    meta = json.loads(META.read_text()) if META.exists() else {'version':1,'sprites':{}}
    if mode == 'preview':
        dest = ROOT/'test-results/orange-preview'; dest.mkdir(parents=True,exist_ok=True)
        for n in range(10): render(n).resize((256,256),Image.Resampling.NEAREST).save(dest/f'orange_{n+1:02}.png')
        print(dest)
    elif mode == 'build':
        for n in range(10):
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
        for n in range(10):
            name = RULES[n]['id']
            sprite = api('get?sprite_id='+meta['sprites'][name])
            image_from_pixel_flow(sprite.get('sprite',sprite)).save(ASSETS/f'{name}.png')
            print(name,'exported',flush=True)
    else:
        raise SystemExit('Use preview, build, or export')


if __name__ == '__main__': main()
