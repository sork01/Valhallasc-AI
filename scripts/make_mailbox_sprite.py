#!/usr/bin/env python3
"""Native editable PixelFlow mailbox. build once; export preserves source edits."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'client/assets'
sys.path.insert(0,str(Path.home()/'.claude/skills/makesprites'))
import pf

PALETTE = ['#00000000','#211e2c','#4b3540','#76503c','#ac7950','#e1b777',
           '#233f51','#315f77','#538b9a','#8abfc0','#9b683e','#d4a354','#ffe3a3',
           '#b3484d','#ee7c6d','#fff1ce','#d6c3a3','#8b7869']


def draw():
    im = Image.new('P',(96,112),0)
    d = ImageDraw.Draw(im)
    # Grounded oak pedestal, stone foot and brass-rimmed blue postal cabinet.
    d.polygon([(36,100),(54,96),(66,101),(48,108),(32,103)],fill=1)
    d.polygon([(36,96),(54,92),(64,97),(47,103),(34,100)],fill=17)
    d.polygon([(43,61),(54,58),(54,97),(43,101)],fill=2)
    d.polygon([(44,63),(48,62),(48,98),(44,99)],fill=4)
    d.line([(50,62),(50,97)],fill=5,width=1)
    d.polygon([(23,29),(54,18),(75,31),(75,63),(43,77),(23,62)],fill=1)
    d.polygon([(25,32),(44,43),(44,73),(25,61)],fill=6)
    d.polygon([(46,43),(72,33),(72,62),(46,73)],fill=7)
    d.polygon([(25,29),(54,20),(72,31),(44,41)],fill=8)
    d.line([(25,29),(44,41),(72,31)],fill=12,width=2)
    d.line([(25,61),(44,73),(72,62)],fill=11,width=2)
    d.line([(44,42),(44,71)],fill=10,width=2)
    d.polygon([(30,38),(39,43),(39,48),(30,43)],fill=1)
    d.line([(30,38),(39,43)],fill=9,width=1)
    # Sealed cream envelope on the face: recognizable at world scale.
    d.polygon([(50,49),(67,43),(67,57),(50,64)],fill=1)
    d.polygon([(51,50),(66,45),(66,56),(51,62)],fill=15)
    d.line([(51,51),(58,54),(66,46)],fill=10,width=1)
    d.line([(51,61),(56,55)],fill=16,width=1)
    d.line([(66,55),(61,52)],fill=16,width=1)
    d.ellipse((57,53,60,56),fill=13)
    # Raised red collection flag with gold finial.
    d.line([(77,18),(77,55)],fill=1,width=4)
    d.line([(77,18),(77,55)],fill=11,width=2)
    d.polygon([(78,19),(91,14),(91,26),(78,31)],fill=1)
    d.polygon([(79,20),(89,17),(89,25),(79,28)],fill=13)
    d.line([(80,20),(88,18)],fill=14,width=1)
    d.ellipse((75,14,79,18),fill=12)
    return np.array(im,dtype=np.uint8)


def main():
    mode = sys.argv[1] if len(sys.argv)>1 else 'export'
    path = ASSETS/'mailbox.txt'
    if mode == 'build':
        if path.exists(): raise SystemExit('Mailbox source exists; export preserves edits.')
        sid = pf.create('valhallasc_mailbox',96,112,1,PALETTE,fps=1)
        pf.draw_grid(sid,0,0,draw())
        path.write_text(json.dumps(dict(sprite=sid,frame=[96,112],anchor=[48,104]),indent=2)+'\n')
        print('mailbox PixelFlow source',sid)
    meta = json.loads(path.read_text())
    sp, frames = pf.load(meta['sprite'])
    assert (sp['width'],sp['height'],len(frames)) == (96,112,1)
    image = Image.fromarray(pf.to_rgba(frames[0][0],sp['palette']),'RGBA')
    target = ASSETS/'mailbox.png'
    if mode == 'verify':
        assert image.tobytes() == Image.open(target).convert('RGBA').tobytes()
        print('Mailbox PixelFlow export verified')
    else:
        image.save(target,optimize=True)
        print('exported',target)


if __name__ == '__main__': main()
