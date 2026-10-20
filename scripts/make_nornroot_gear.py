"""Build the 28 original Fatewoven pieces, both bodies, every pose and facing.

Usage: python3 scripts/make_nornroot_gear.py [--preview]
Source-drawn art, exported directly as editable PNG/depth layers; no PixelFlow
record is claimed. IDs/stats/variants stay stable. Rebuilds are deterministic.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib
import json
from pathlib import Path
import time
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import nornroot_gear_shapes as shape
import cel_common as cc

ROOT=Path(__file__).resolve().parents[1]; ASSETS=ROOT/'client/assets'
OUT=ROOT/'test-results/nornroot-redesign'; VARIANT='fatewoven'
RGBA=np.array([[int(h[i:i+2],16) for i in (1,3,5)]+[255 if n else 0] for n,h in enumerate(shape.PALETTE)],np.uint8)


def picture(cls,gender,key):
    stem=shape.META[cls]+('_f' if gender=='female' else '')
    meta=json.loads((ASSETS/f'{stem}_sprites.txt').read_text());clip,facing,k=key
    box=(k*160,(meta['clips'][clip]['row0']+cc.DIRS.index(facing))*160,(k+1)*160,(meta['clips'][clip]['row0']+cc.DIRS.index(facing)+1)*160)
    body=meta['parts']['body']
    with Image.open(ASSETS/body['png']) as im:rgba=np.array(im.crop(box).convert('RGBA'))
    with Image.open(ASSETS/body['depth']) as im:dep=np.array(im.crop(box).convert('RGB')).astype(np.uint32)
    depth=(dep[:,:,0]*256+dep[:,:,1])/64-512;depth[rgba[:,:,3]==0]=np.inf
    for slot in shape.SLOTS:
        idx,z=shape.render(cls,gender,*key,slot);take=(idx>0)&(z<=depth)
        rgba[take]=RGBA[idx[take]];depth[take]=z[take]
    return Image.fromarray(rgba)


def preview():
    OUT.mkdir(parents=True,exist_ok=True)
    sheet=Image.new('RGB',(1440,1810),'#152825');d=ImageDraw.Draw(sheet)
    font=lambda n:ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
    d.text((25,20),'NORNROOT — ORIGINAL FATEWOVEN EQUIPMENT',font=font(29),fill='#ffe1a0')
    d.text((25,67),'Root corslets • Pegged loom crowns • Funeral shuttles • Spindle weapons',font=font(20),fill='#c1d0bd')
    for row,cls in enumerate(shape.CLASSES):
        y=120+row*330
        d.rounded_rectangle((15,y,1425,y+315),radius=15,fill='#293b35',outline='#9e8e62',width=2)
        d.text((30,y+12),cls.upper(),font=font(22),fill='#edcb87')
        for sex,gender in enumerate(('male','female')):
            x=110+sex*650;d.text((x+220,y+12),gender.upper(),font=font(17),fill='#c1d0bd')
            for col,key in enumerate([('idle','S',0),('walk','SE',2),('attack','S',4)]):
                im=picture(cls,gender,key).resize((208,208),Image.Resampling.NEAREST)
                sheet.paste(im,(x+col*208,y+48),im)
                d.text((x+col*208+60,y+270),key[0].capitalize(),font=font(16),fill='#d6d2b7')
    file=OUT/'Nornroot_Fatewoven_Original_Heroes.png';sheet.save(file);print(file,flush=True)


def export_body(args):
    cls,gender=args;module=importlib.import_module(shape.rig.MODULES[cls]);stem=shape.META[cls]+('_f' if gender=='female' else '')
    meta=json.loads((ASSETS/f'{stem}_sprites.txt').read_text())
    files=[];parts={};icons={};bounds={};counts={}
    for slot in shape.SLOTS:
        atlas=Image.new('RGBA',(1280,6400));depth_atlas=Image.new('RGB',(1280,6400),(255,255,0));count=0;all_bounds=[]
        for clip,(_,n,_) in module.CLIPS.items():
            for di,facing in enumerate(cc.DIRS):
                for k in range(n):
                    idx,depth=shape.render(cls,gender,clip,facing,k,slot)
                    assert idx.any(),(cls,gender,slot,clip,facing,k,'blank')
                    assert not (idx[[0,-1],:].any() or idx[:,[0,-1]].any()),(cls,gender,slot,clip,facing,k,'clipped')
                    yy,xx=np.nonzero(idx);all_bounds.append([int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)])
                    encoded=np.full((160,160),65535,np.uint16);mask=idx>0
                    encoded[mask]=np.clip(np.round((depth[mask]+512)*64),0,65534).astype(np.uint16)
                    rgb=np.zeros((160,160,3),np.uint8);rgb[:,:,0]=encoded>>8;rgb[:,:,1]=encoded&255
                    at=(k*160,(meta['clips'][clip]['row0']+di)*160)
                    atlas.paste(Image.fromarray(RGBA[idx]),at);depth_atlas.paste(Image.fromarray(rgb),at);count+=1
                    if gender=='male' and clip=='idle' and facing=='S' and k==0:
                        im=Image.fromarray(RGBA[idx]);im=im.crop(im.getbbox());im.thumbnail((40,40),Image.Resampling.NEAREST)
                        icon=Image.new('RGBA',(48,48));icon.alpha_composite(im,((48-im.width)//2,(48-im.height)//2))
                        kind=shape.KINDS.get(slot,slot);job=f'nornroot-{"shared" if slot in ("pants","necklace","accessory") else cls}-{kind}'
                        if slot not in ('pants','necklace','accessory') or cls=='warrior':
                            path=ASSETS/f'gear_icon_{job}.png';icon.save(path);icons[job]=str(path.relative_to(ROOT))
        part=f'{slot}_{VARIANT}';prefix=f'{cls}_{"f_" if gender=="female" else ""}nornroot_{slot}'
        entry={}
        for key,suffix,im in [('png','',''),('depth','_depth','')]:
            path=ASSETS/f'{prefix}{suffix}.png';(atlas if key=='png' else depth_atlas).save(path,optimize=True)
            files.append(str(path.relative_to(ROOT)));entry[key]=path.name
        parts[part]=entry;bounds[part]=all_bounds;counts[slot]=count
        print(cls,gender,slot,count,'clear frames',flush=True)
    return dict(cls=cls,gender=gender,stem=stem,parts=parts,files=files,icons=icons,bounds=bounds,counts=counts)


def build():
    OUT.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(export_body,[(c,g) for c in shape.CLASSES for g in ('male','female')]))
    # Merge only our new parts into the latest metadata; preserve all other sets.
    for r in results:
        path=ASSETS/(r['stem']+'_sprites.txt');meta=json.loads(path.read_text())
        meta['parts'].update(r['parts']);meta['lazyParts']=sorted(set(meta.get('lazyParts',[]))|set(r['parts']))
        for part in r['parts']:meta.setdefault('gearSources',{})[part]='scripts/nornroot_gear_shapes.py'
        path.write_text(json.dumps(meta,indent=2)+'\n')
    items=[i for i in json.loads((ROOT/'world/items.txt').read_text()) if i.get('source')=='nornroot']
    assert len(items)==28
    path=ROOT/'world/gear-art.txt';manifest=json.loads(path.read_text());tasks=[]
    revision=hashlib.sha256(Path(shape.__file__).read_bytes()+Path(__file__).read_bytes()).hexdigest()
    for item in items:
        cls=item.get('class');kind=item['kind'];slot='head' if kind=='headgear' else kind;job=f'nornroot-{cls or "shared"}-{kind}'
        chosen=[r for r in results if cls is None or r['cls']==cls]
        files=[f for r in chosen for f in r['files'] if Path(f).stem.removesuffix('_depth').endswith('_'+slot)]
        icon=next(r['icons'][job] for r in chosen if job in r['icons']);files.append(icon)
        manifest[job]=dict(variant=VARIANT,kind=kind,classes={c:{} for c in (shape.CLASSES if cls is None else [cls])},revision=revision,files=files,icon={'source':icon},source='scripts/nornroot_gear_shapes.py')
        tasks.append(dict(id=job,group='nornroot',className=cls,kind=kind,item=item['id'],name=item['name'],done=False,phase='art exported; visual check pending',evidence=files))
    path.write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'docs/nornroot-gear-state.txt').write_text(json.dumps(dict(tasks=tasks),indent=2)+'\n')
    (OUT/'bounds.json').write_text(json.dumps([{k:v for k,v in r.items() if k in ('cls','gender','counts','bounds')} for r in results]))
    print('28 pieces exported; all ten rigs, all clips/facings; catalogue wiring is a separate step',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--preview',action='store_true');args=parser.parse_args()
    preview() if args.preview else build()
