#!/usr/bin/env python3
"""Original human-sized grave cross; PixelFlow is the editable source. build | export."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from make_crag_sprites import api,rgba
ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'client/assets/raid_cross.txt'
PALETTE=['#00000000','#221c26','#504750','#81757c','#b5a6a0','#e4d3bb','#d37c3e','#ffdc89','#42574b','#78966b']
def build():
    if META.exists(): raise SystemExit('Cross already exists; export preserves PixelFlow edits.')
    im=Image.new('P',(96,128),0);d=ImageDraw.Draw(im)
    d.ellipse((12,107,85,124),fill=1);d.ellipse((17,106,80,120),fill=2)
    d.polygon([(22,109),(29,100),(68,100),(78,110),(76,116),(22,116)],fill=1)
    d.polygon([(26,108),(33,103),(65,103),(73,109),(68,113),(28,112)],fill=3)
    outline=[(37,105),(35,62),(12,61),(10,39),(34,38),(34,10),(56,6),(63,12),(62,38),(85,40),(86,60),(62,63),(65,105),(54,112)]
    d.polygon(outline,fill=1)
    d.polygon([(40,103),(39,57),(16,56),(15,43),(39,42),(39,13),(54,10),(57,15),(56,43),(80,44),(81,55),(57,58),(60,103),(53,107)],fill=3)
    d.polygon([(40,14),(52,12),(52,46),(17,46),(17,44),(40,43)],fill=5)
    d.polygon([(41,54),(53,54),(54,102),(43,101)],fill=4)
    d.polygon([(57,44),(80,45),(80,53),(57,55)],fill=2)
    d.line([(44,19),(48,23),(44,28),(50,32)],fill=2,width=2)
    d.line([(22,50),(30,48),(35,52)],fill=4,width=2)
    d.polygon([(44,65),(53,65),(55,76),(48,82),(42,75)],fill=1)
    d.polygon([(46,67),(51,67),(52,74),(48,78),(45,74)],fill=6)
    d.line([(48,68),(48,75)],fill=7,width=2)
    for x,y in [(24,109),(65,107),(72,112),(34,114)]:
        d.line([(x,y+3),(x+2,y-4),(x+5,y-5)],fill=8,width=2);d.ellipse((x+2,y-6,x+6,y-2),fill=9)
    sid=api('create',dict(name='valhallasc_ember_grave_cross',width=96,height=128,frames=1,layers=1,fps=1,palette=PALETTE,persist=True))['sprite_id']
    api('draw',dict(sprite_id=sid,frame=0,ops=[dict(op='grid',rows=np.array(im).tolist(),x=0,y=0,layer=0)]))
    META.write_text(json.dumps(dict(sprite=sid,frame=[96,128],anchor=[48,120]),indent=2)+'\n')
def export():
    meta=json.loads(META.read_text());packet=api('get?sprite_id='+meta['sprite']);sp=packet.get('sprite',packet);cel=sp['frames'][0]['cels'][0]
    if 'rle' in cel:
        r=cel['rle'];grid=np.repeat(np.array(r[1::2],dtype=np.uint8),r[0::2]).reshape(128,96)
    else:grid=np.array(cel['grid'],dtype=np.uint8)
    rgba(grid,sp['palette']).save(ROOT/'client/assets/raid_cross.png')
    print('Exported original PixelFlow cross',meta['sprite'])
if __name__=='__main__':
    if sys.argv[1]=='build':build()
    export()
