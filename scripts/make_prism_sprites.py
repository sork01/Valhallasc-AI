#!/usr/bin/env python3
"""Makesprites workflow for six Prismwaste enemies.

preview checks and displays the procedural design; build uploads 34 editable
frames per kind to PixelFlow. export reads editor frames into game atlases.
Build --replace discards only these six sprites and any editor changes to them.
"""
import json
import math
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import prism_redraw as prism_art
from make_crag_sprites import AY, rgba

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'client/assets'
KINDS=['miragejackal','shardscarab','glassharrier','prismsentinel','mirrorqueen','sunshard']
CLIPS=[('idle',6),('walk',8),('attack',8),('hurt',4),('die',8)]
W=H=96
# The art is the cel-shaded redraw in prism_redraw.py (2026-10-18); this script only builds, exports and verifies it.
PALETTES=prism_art.PALETTES

def draw(kind,clip,n):
    return rgba(prism_art.draw(kind,clip,n),PALETTES[kind].hex)

def atlas(kind):
    out=Image.new('RGBA',(W*8,H*5))
    for row,(clip,count) in enumerate(CLIPS):
        for n in range(count):out.alpha_composite(draw(kind,clip,n),(n*W,row*H))
    return out

def _pf():
    sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
    import pf
    return pf

def _metadata(sprites):
    start=0;clips={}
    for row,(clip,count) in enumerate(CLIPS):
        clips[clip]=dict(fps=10,n=count,row=row,editorStart=start)
        start+=count
    tops={}
    for kind in KINDS:
        top=min(np.nonzero(np.array(draw(kind,'idle',n))[:,:,3])[0].min() for n in range(CLIPS[0][1]))
        tops[kind]=int(AY-top)
    return dict(frame=[W,H],anchor=[48,90],kinds=KINDS,clips=clips,sprites=sprites,tops=tops)

def _grids(kind):
    palette=PALETTES[kind].hex
    colors=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[0 if j==0 else 255]
                     for j,c in enumerate(palette)],dtype=np.uint8)
    out={}
    for clip,count in CLIPS:
        out[clip]=[]
        for n in range(count):
            image=np.array(draw(kind,clip,n))
            grid=np.zeros((H,W),dtype=np.uint8)
            for j,rgba in enumerate(colors[1:],1):
                grid[np.all(image==rgba,axis=2)]=j
            assert np.array_equal(colors[grid],image),(kind,clip,n,'palette mismatch')
            ys,xs=np.nonzero(grid)
            assert len(xs) and xs.min()>0 and xs.max()<W-1 and ys.min()>0 and ys.max()<H-1,(kind,clip,n,'edge')
            out[clip].append(grid)
        assert len({g.tobytes() for g in out[clip]})>=count-1,(kind,clip,'static')
    return out

def _build(replace=False):
    pf=_pf();path=ASSETS/'prism.txt'
    meta=json.loads(path.read_text()) if path.exists() else {}
    sprites=meta.get('sprites',{})
    if sprites and not replace:
        raise SystemExit('PixelFlow sprites already exist. Use export to preserve editor edits; build --replace discards them.')
    if replace:
        for sid in sprites.values():
            result=pf.api('delete',{'sprite_id':sid})
            assert result.get('ok'),result
        sprites={}
    for kind in KINDS:
        grids=_grids(kind)
        np.savez_compressed(ROOT/'scripts'/f'prism_{kind}_raw.npz',
                            **{clip:np.stack(rows) for clip,rows in grids.items()})
        sid=pf.create('valhallasc_prism_redraw_'+kind+'_all',W,H,34,PALETTES[kind].hex,fps=10)
        frame=0
        try:
            for clip,count in CLIPS:
                for grid in grids[clip]:
                    pf.draw_grid(sid,frame,0,grid)
                    frame+=1
        except Exception:
            pf.api('delete',{'sprite_id':sid})
            raise
        sprites[kind]=sid
        path.write_text(json.dumps(_metadata(sprites),indent=2)+'\n')
        print(kind,sid,'34 frames',flush=True)

def _export():
    pf=_pf();path=ASSETS/'prism.txt'
    sprites=json.loads(path.read_text())['sprites']
    for kind in KINDS:
        sp,frames=pf.load(sprites[kind])
        assert (sp['width'],sp['height'],len(frames))==(W,H,34),(kind,'editor dimensions')
        out=Image.new('RGBA',(W*8,H*len(CLIPS)))
        offset=0
        for row,(clip,count) in enumerate(CLIPS):
            for n in range(count):
                image=Image.fromarray(pf.to_rgba(frames[offset+n][0],sp['palette']),'RGBA')
                out.alpha_composite(image,(n*W,row*H))
            offset+=count
        out.save(ASSETS/f'prism_{kind}.png',optimize=True)
        print('exported',kind,flush=True)
    path.write_text(json.dumps(_metadata(sprites),indent=2)+'\n')

def _verify():
    pf=_pf();sprites=json.loads((ASSETS/'prism.txt').read_text())['sprites']
    for kind in KINDS:
        sp,frames=pf.load(sprites[kind])
        assert len(frames)==34
        out=Image.new('RGBA',(W*8,H*len(CLIPS)))
        offset=0
        for row,(clip,count) in enumerate(CLIPS):
            for n in range(count):
                out.alpha_composite(Image.fromarray(pf.to_rgba(frames[offset+n][0],sp['palette']),'RGBA'),
                                    (n*W,row*H))
            offset+=count
        assert out.tobytes()==Image.open(ASSETS/f'prism_{kind}.png').convert('RGBA').tobytes(),kind
    print('Six PixelFlow sprites, 204 frames and exported atlases verified')

def main():
    cmd=sys.argv[1] if len(sys.argv)>1 else 'preview'
    ASSETS.mkdir(exist_ok=True)
    if cmd=='build':_build('--replace' in sys.argv[2:])
    elif cmd=='export':_export()
    elif cmd=='verify':_verify()
    elif cmd=='preview':
        for kind in KINDS:_grids(kind)
        main_contact()
    elif cmd=='contact':main_contact()
    else:raise SystemExit('preview | build [--replace] | export | verify | contact')

def main_contact():
        sheet=Image.new('RGB',(6*205+12,4*220+40),'#211f2d');d=ImageDraw.Draw(sheet)
        for col,kind in enumerate(KINDS):
            for row,(clip,n) in enumerate([('idle',2),('attack',4),('hurt',0),('die',6)]):
                pose=draw(kind,clip,n).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(pose,(10+col*205,28+row*220),pose)
                d.text((10+col*205,8+row*220),f'{kind} {clip}',fill='#f9d99d')
        out=ROOT/'test-results/prism-enemies.png';out.parent.mkdir(exist_ok=True);sheet.save(out);print(out)
if __name__=='__main__':main()
