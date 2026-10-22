"""Preview, build in PixelFlow, and export five cloak bases on all ten rigs.

New builds resume saved IDs and never replace editable sprites. Export reads
both male and female cels back from PixelFlow. Only cloak atlases are written.
"""
import argparse
import base64
import importlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import cel_common as cc
import cloak_shapes as shape
import make_progression_gear as pipeline
import sprite_bounds

ROOT=Path(__file__).resolve().parents[1]; ASSETS=ROOT/'client/assets'
STATE=ROOT/'docs/cloak-gear-state.txt'; MANIFEST=ROOT/'world/gear-art.txt'
RAW=ROOT/'scripts/cloak_raw'; OUT=ROOT/'test-results/cloaks'
META=pipeline.META
pipeline.PALETTE_HEX=shape.PALETTE
pipeline.PALETTE=np.array([[int(c[i:i+2],16) for i in (1,3,5)]+[255 if n else 0] for n,c in enumerate(shape.PALETTE)],np.uint8)

def frames(cls,gender,style):
    module=importlib.import_module(shape.rigs.MODULES[cls]);result={}
    import hashlib
    revision=hashlib.sha256(Path(shape.__file__).read_bytes()+Path(cc.__file__).read_bytes()+Path(module.__file__).read_bytes()).hexdigest()
    cache=RAW/style/f'{cls}-{gender}';cache.mkdir(parents=True,exist_ok=True)
    for clip,(_,n,_) in module.CLIPS.items():
        for facing in cc.DIRS:
            for k in range(n):
                key=(clip,facing,k);path=cache/f'{clip}-{facing}-{k}.npz'
                if path.exists():
                    with np.load(path) as d:
                        if str(d['revision']) == revision:
                            result[key]=(d['index'],d['depth']);continue
                idx,z=shape.render(cls,gender,style,*key)
                assert idx.any(),(cls,gender,style,key,'blank')
                assert not idx[[0,-1],:].any() and not idx[:,[0,-1]].any(),(cls,gender,style,key,'clipped')
                np.savez_compressed(path,index=idx,depth=z,revision=revision);result[key]=(idx,z)
    return result

def preview(style):
    OUT.mkdir(parents=True,exist_ok=True)
    keys=[('idle','S',0),('idle','N',0),('walk','SE',1),('walk','SE',5),('attack','W',4),('die','NE',7)]
    sheet=Image.new('RGBA',(6*240,10*255),'#293d45');draw=ImageDraw.Draw(sheet)
    for ci,cls in enumerate(META):
        for gi,gender in enumerate(('male','female')):
            raw=frames(cls,gender,style)
            for col,key in enumerate(keys):
                rgba,z=pipeline.body(cls,gender,key);idx,dep=raw[key]
                take=(idx>0)&((rgba[...,3]==0)|(dep<z));rgba[take]=pipeline.PALETTE[idx[take]]
                x,y=col*240,(ci*2+gi)*255
                sheet.alpha_composite(Image.fromarray(rgba).resize((240,240),Image.Resampling.NEAREST),(x,y))
                draw.text((x+4,y+237),f'{cls} {gender} {key[0]} {key[1]} {key[2]}',fill='white')
    path=OUT/f'{style}.png';sheet.save(path);print(path,flush=True)

def build(style):
    state=json.loads(STATE.read_text()) if STATE.exists() else {}
    record=state.setdefault(style,dict(variant=style,kind='cloak',classes={}))
    def save(): STATE.write_text(json.dumps(state,indent=2)+'\n')
    save()
    for cls in META:
        for gender in ('male','female'):
            raw=frames(cls,gender,style);module=importlib.import_module(shape.rigs.MODULES[cls])
            clips=record['classes'].setdefault(cls+'-'+gender,{})
            for clip,(fps,n,_) in module.CLIPS.items():
                if clip in clips: continue
                indices=[raw[(clip,d,k)][0] for d in cc.DIRS for k in range(n)]
                clips[clip]=pipeline.save_sprite(f'cloak_{style}_{cls}_{gender}_{clip}',indices,fps);save()
            print(f'{style}: {cls}/{gender} saved',flush=True)
    if 'icon' not in record:
        idx,_=frames('warrior','male',style)[('idle','N',0)]
        image=Image.fromarray(pipeline.PALETTE[idx]);image=image.crop(image.getbbox());image.thumbnail((38,40),Image.Resampling.NEAREST)
        icon=Image.new('RGBA',(48,48));icon.alpha_composite(image,((48-image.width)//2,(48-image.height)//2))
        rgba=np.array(icon);grid=np.zeros((48,48),np.uint8)
        for n,c in enumerate(pipeline.PALETTE[1:],1):grid[np.all(rgba==c,axis=2)]=n
        record['icon']=pipeline.save_sprite(f'cloak_{style}_icon',[grid],1);save()
    export(style)

def export(style):
    state=json.loads(STATE.read_text());record=state[style];files=[]
    for cls,stem in META.items():
        for gender in ('male','female'):
            prefix=stem+('_f' if gender=='female' else '');meta_path=ASSETS/(prefix+'_sprites.txt');meta=json.loads(meta_path.read_text())
            raw=frames(cls,gender,style);atlas=Image.new('RGBA',(1280,6400));depth_atlas=Image.new('RGB',atlas.size,(255,255,0))
            for clip,C in meta['clips'].items():
                saved=record['classes'][cls+'-'+gender][clip];sprite,grids=pipeline.load_sprite(saved)
                assert sprite['palette']==shape.PALETTE
                for di,d in enumerate(cc.DIRS):
                    for k in range(C['n']):
                        _,dep=raw[(clip,d,k)];dep=dep.copy();x,y=saved['offset'];patch=pipeline.PALETTE[grids[di*C['n']+k]];h,w=patch.shape[:2]
                        rgba=np.zeros((160,160,4),np.uint8);rgba[y:y+h,x:x+w]=patch
                        added=(rgba[...,3]>0)&~np.isfinite(dep)
                        if added.any():
                            nearest=ndi.distance_transform_edt(~np.isfinite(dep),return_distances=False,return_indices=True);dep[added]=dep[tuple(nearest)][added]
                        enc=np.full((160,160),65535,np.uint16);opaque=rgba[...,3]>0
                        enc[opaque]=np.clip(np.round((dep[opaque]+512)*64),0,65534).astype(np.uint16)
                        depth=np.zeros((160,160,3),np.uint8);depth[...,0]=enc>>8;depth[...,1]=enc&255
                        at=(k*160,(C['row0']+di)*160);atlas.paste(Image.fromarray(rgba),at);depth_atlas.paste(Image.fromarray(depth),at)
            part='cloak_'+style;name=prefix+'_'+part
            for suffix,picture in (('',atlas),('_depth',depth_atlas)):
                path=ASSETS/(name+suffix+'.png');picture.save(path,optimize=True);files.append(str(path.relative_to(ROOT)))
            meta['parts'][part]=dict(png=name+'.png',depth=name+'_depth.png');meta['lazyParts']=sorted(set(meta.get('lazyParts',[]))|{part})
            meta.setdefault('gearSprites',{})[part]=record['classes'][cls+'-'+gender];meta_path.write_text(json.dumps(meta,indent=2)+'\n')
            # Only the changed cloak bound is recomputed; preserve existing part bounds.
            bp=sprite_bounds.bounds_name(meta_path);bounds=json.loads(bp.read_text())
            bounds['parts'][part]=base64.b64encode(sprite_bounds.part_bounds(ASSETS/(name+'.png'),meta)).decode();bp.write_text(json.dumps(bounds,separators=(',',':'))+'\n')
    sprite,grids=pipeline.load_sprite(record['icon']);icon=Image.new('RGBA',(48,48));icon.paste(Image.fromarray(pipeline.PALETTE[grids[0]]),tuple(record['icon']['offset']))
    path=ASSETS/('gear_icon_cloak_'+style+'.png');icon.save(path);files.append(str(path.relative_to(ROOT)))
    record['files']=files;STATE.write_text(json.dumps(state,indent=2)+'\n')
    manifest=json.loads(MANIFEST.read_text());manifest['CLOAK-'+style.upper()]=record;MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    import cloak_catalog
    cloak_catalog.append_icons()
    print(style,'exported',len(files),'files',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('preview','build','export'));p.add_argument('styles',nargs='*',default=list(shape.STYLES));args=p.parse_args()
    import fcntl
    lock_path=ROOT/'.tools/cloak-art.lock';lock_path.parent.mkdir(exist_ok=True)
    with lock_path.open('w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        for style in args.styles:
            assert style in shape.STYLES
            globals()[args.command](style)
