#!/usr/bin/env python3
"""Editable 34-frame PixelFlow sprites for the Elder Hollow encounters."""
import json
import math
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from elder_hollow_content import ENEMIES
from make_crag_sprites import AX, AY, CLIPS, H, W, Frame, Palette, api, capsule, ellipsoid, polygon, rgba
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client/assets'
META = ASSETS / 'cathedral.txt'
KINDS = [e['kind'] for e in ENEMIES]
PREFIX = 'valhallasc_elder_hollow_'

def palette(enemy):
    rgb=tuple(int(enemy['color'][i:i+2],16) for i in (1,3,5))
    names={f'c{n}':'#'+''.join(f'{min(250,round(v*factor)):02x}' for v in rgb)
           for n,factor in enumerate((.29,.49,.69,.88,1.1))}
    names.update(leaf='#a8d07f',pollen='#f1dda0',bark='#6c5035',dark='#243a30',white='#f1f2c6',root='#9b7855')
    return Palette(names)
PALETTES={e['kind']:palette(e) for e in ENEMIES}

def draw(enemy,clip,n):
    p=PALETTES[enemy['kind']];f=Frame(p);art=enemy['art']
    wave=math.sin(n*math.pi/4);sway=wave*(3 if clip=='walk' else 1)
    thrust=(0,1,3,8,12,9,4,0)[n] if clip=='attack' else 0
    collapse=(0,.05,.13,.24,.40,.58,.78,.94)[n] if clip=='die' else 0
    if clip=='hurt': sway-=(4,3,1,0)[n]
    def at(x,y):return (48+x+sway*y/48+thrust*y/110,89-y*(1-collapse*.83)-abs(wave)*(2 if clip=='walk' else .4))
    ramp=p.ramp('c0','c1','c2','c3','c4')
    bright=p.ramp('c1','c2','c3','c4')
    def oval(x,y,rx,ry,colors=ramp):
        xx,yy=at(x,y)
        f.paint(ellipsoid(xx,yy,rx*(1+collapse*.2),max(1,ry*(1-collapse*.7))),colors,dither=.3)
    def limb(a,b,w=3,t=1.5,colors=ramp): f.paint(capsule(at(*a),at(*b),w,t),colors,dither=.3)
    def shape(points,color):f.flat(polygon([at(x,y) for x,y in points]),color,outline=True)
    def line(a,b,color='leaf',width=2):f.line(at(*a),at(*b),color,width)
    if art=='thornling':
        for side in (-1,1):
            limb((side*12,29),(side*19,5+wave*2),4,2)
            limb((side*12,43),(side*(29+thrust*.2),32),4,2)
            shape([(side*17,45),(side*32,38),(side*21,33)],'leaf')
        oval(0,35,20,23);oval(0,51,15,17,bright)
        for x in (-12,0,12):shape([(x-5,61),(x,77),(x+7,58)],'leaf')
        for x in (-7,7):oval(x,51,3,4,p.ramp('dark','pollen','white'))
    elif art=='moth':
        for side in (-1,1):
            shape([(side*4,50),(side*25,70+wave*2),(side*34,47),(side*23,24)],'c3')
            oval(side*21,49,10,19,p.ramp('c1','c2','pollen'))
            for y in (43,57):oval(side*22,y,3,4,p.ramp('pollen','white','white'))
            line((side*7,62),(side*16,81),'bark',2)
        oval(0,41,10,23);oval(0,64,13,11,bright)
        for x in (-6,6):oval(x,65,3,3,p.ramp('dark','white','white'))
        for x in (-7,0,7):line((x,30),(x+wave*3,10),'pollen',1)
    elif art=='barkguard':
        for side in (-1,1):
            limb((side*13,27),(side*18,3),7,5)
            limb((side*20,56),(side*(31+thrust*.15),28),8,5)
            oval(side*(31+thrust*.15),27,8,10,p.ramp('bark','c2','c4'))
        shape([(-20,14),(-24,48),(-12,72),(10,74),(24,46),(19,13)],'bark')
        oval(0,43,20,27);shape([(-14,63),(-9,77),(0,71),(10,77),(15,61)],'leaf')
        for x in (-8,8):oval(x,56,3,5,p.ramp('dark','pollen','white'))
        for y in (23,33,43):line((-16,y),(16,y),'root',2)
    elif art=='gatekeeper':
        for side in (-1,1):
            limb((side*13,33),(side*20,3),8,5)
            limb((side*20,56),(side*(33+thrust*.12),31),9,5)
            shape([(side*20,69),(side*37,65),(side*25,50)],'leaf')
        shape([(-22,9),(-27,44),(-16,70),(0,83),(18,68),(27,43),(22,9)],'bark')
        oval(0,46,21,32);oval(0,54,12,15,bright)
        for x in (-9,9):oval(x,58,4,6,p.ramp('dark','pollen','white'))
        for x in (-17,-8,0,8,17):line((x,27),(x+3,45),'root',2)
    elif art=='matron':
        for side in (-1,1):
            shape([(side*8,35),(side*30,61),(side*26,79),(side*12,56)],'c3')
            limb((side*12,42),(side*(32+thrust*.13),29),5,2,bright)
            oval(side*30,30,6,7,p.ramp('c1','pollen','white'))
        shape([(-20,7),(-16,54),(-9,69),(10,69),(17,53),(20,7)],'c2')
        oval(0,62,17,16)
        for x in (-9,0,9):oval(x,63,3,4,p.ramp('dark','pollen','white'))
        for x in (-18,-9,0,9,18):line((x,69),(x+wave*4,81),'leaf',2)
    else:
        for k in range(8):
            a=math.tau*k/8+wave*.04
            limb((math.cos(a)*20,44+math.sin(a)*20),
                 (math.cos(a)*36,44+math.sin(a)*36),6,2,p.ramp('bark','c2','leaf'))
        for x in (-22,-11,0,11,22):limb((x,27),(x+wave*4,3+(abs(x)%3)*4),5,2)
        oval(0,46,26,29);oval(0,51,17,19,p.ramp('c1','c2','leaf','white'))
        oval(0,50,8,15,p.ramp('dark','pollen','white'))
        for x in (-14,14):shape([(x-8,73),(x,84),(x+8,72)],'leaf')
    if clip=='attack' and n in (3,4,5):
        for k in range(4):
            x,y=at(25+k*3+thrust*.3,38+k%2*7)
            f.dots([(x,y)],'pollen')
    if clip=='die' and n>=5:
        for k in range(5):oval(-18+k*9,2+k%2*2,2,1.5,p.ramp('leaf','pollen','white'))
    if clip in ('hurt','die') and n==0:f.whiten()
    return f.a

# The six enemies are the cel-shaded redraw in elder_hollow_cel_redraw.py (2026-10-18); the old drawer stays as `_old_draw`.
import dungeon_cel  # noqa: E402
dungeon_cel.install(globals(), 'elder_hollow_cel_redraw')


def render(kind):
    enemy = next(e for e in ENEMIES if e['kind'] == kind)
    return {clip: np.stack([draw(enemy, clip, n) for n in range(count)])
            for clip, (_, count) in CLIPS.items()}


def bounds(frames):
    bad = []
    for clip, rows in frames.items():
        for n, grid in enumerate(rows):
            yy, xx = np.nonzero(grid)
            if len(xx) and (xx.min() < 1 or yy.min() < 1 or xx.max() > W-2 or yy.max() > H-2):
                bad.append(f'{clip} {n}: x {xx.min()}-{xx.max()}, y {yy.min()}-{yy.max()}')
    return bad


def preview(kinds):
    out = ROOT / 'test-results/elder-hollow-preview'
    out.mkdir(parents=True, exist_ok=True)
    for kind in kinds:
        frames=render(kind)
        assert not bounds(frames), (kind,bounds(frames))
        sheet=Image.new('RGBA',(W*6,H*5),'#152638')
        for row,(clip,(_,count)) in enumerate(CLIPS.items()):
            for n in range(min(count,6)):
                sheet.alpha_composite(rgba(frames[clip][n],PALETTES[kind].hex),(n*W,row*H))
        sheet.resize((W*12,H*10),Image.Resampling.NEAREST).save(out/f'{kind}.png')
        print(out/f'{kind}.png')


def build(kinds, replace=False):
    meta=json.loads(META.read_text())
    known=meta.get('sprites',{})
    clash=[k for k in kinds if k in known]
    if clash and not replace:
        raise SystemExit(f'{clash} already exist; export preserves editor changes. --replace discards only these Elder Hollow sprites.')
    for kind in clash:
        api('delete',{'sprite_id':known[kind]})
    for kind in kinds:
        frames=render(kind)
        assert not bounds(frames),(kind,bounds(frames))
        np.savez_compressed(ROOT/f'scripts/elder_hollow_{kind}_raw.npz',**frames)
        sid=api('create',{'name':PREFIX+kind+'_all','width':W,'height':H,
                          'frames':34,'layers':1,'fps':10,'palette':PALETTES[kind].hex,
                          'persist':True,'ops':[{'op':'set_layer','layer':0,'name':kind}]})['sprite_id']
        offset=0
        try:
            for clip,(_,count) in CLIPS.items():
                for n,grid in enumerate(frames[clip]):
                    api('draw',{'sprite_id':sid,'frame':offset+n,
                                'ops':[{'op':'grid','rows':grid.tolist(),'x':0,'y':0,'layer':0}]})
                offset+=count
        except Exception:
            api('delete',{'sprite_id':sid})
            raise
        meta['sprites'][kind]=sid
        META.write_text(json.dumps(meta,indent=2)+'\n')
        print(kind,sid,'34 editable frames')


def export(kinds):
    meta=json.loads(META.read_text())
    for kind in kinds:
        packet=api('get?sprite_id='+meta['sprites'][kind]);sp=packet.get('sprite',packet)
        assert (sp['width'],sp['height'],len(sp['frames']))==(W,H,34)
        atlas=Image.new('RGBA',(8*W,5*H))
        offset=0
        for row,(clip,(fps,count)) in enumerate(CLIPS.items()):
            for n in range(count):
                cel=sp['frames'][offset+n]['cels'][0]
                if 'rle' in cel:
                    runs=cel['rle'];grid=np.repeat(np.array(runs[1::2],dtype=np.uint8),runs[0::2]).reshape(H,W)
                else: grid=np.array(cel['grid'],dtype=np.uint8)
                atlas.alpha_composite(rgba(grid,sp['palette']),(n*W,row*H))
            meta['clips'][clip]={'fps':fps,'n':count,'row':row,'editorStart':offset}
            offset+=count
        atlas.save(ASSETS/f'cathedral_{kind}.png',optimize=True)
        meta['tops'][kind]=AY-atlas.crop((0,0,6*W,H)).getbbox()[1]
        if kind not in meta['kinds']: meta['kinds'].append(kind)
        META.write_text(json.dumps(meta,indent=2)+'\n')
        print(ASSETS/f'cathedral_{kind}.png')


def verify(kinds):
    meta=json.loads(META.read_text())
    for kind in kinds:
        frames=render(kind)
        assert not bounds(frames),(kind,bounds(frames))
        atlas=Image.open(ASSETS/f'cathedral_{kind}.png').convert('RGBA')
        assert atlas.size==(8*W,5*H)
        for row,(clip,(_,count)) in enumerate(CLIPS.items()):
            for n in range(count):
                expected=rgba(frames[clip][n],PALETTES[kind].hex)
                actual=atlas.crop((n*W,row*H,(n+1)*W,(row+1)*H))
                assert np.array_equal(np.array(expected),np.array(actual)),(kind,clip,n)
        assert kind in meta['sprites'] and kind in meta['kinds']
        print(kind,'34 frames match indexed source')


if __name__=='__main__':
    action=sys.argv[1] if len(sys.argv)>1 else ''
    kinds=[k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action=='preview': preview(kinds)
    elif action=='build': build(kinds,'--replace' in sys.argv[2:])
    elif action=='export': export(kinds)
    elif action=='verify': verify(kinds)
    else: raise SystemExit('Usage: make_elder_hollow_sprites.py preview | build [--replace] | export | verify [kind...]')
