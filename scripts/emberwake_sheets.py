#!/usr/bin/env python3
"""Readable full animation sheets and a cast sheet from exported PixelFlow art."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from emberwake_content import ENEMIES
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'test-results/emberwake'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',19)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    meta=json.loads((ROOT/'client/assets/cathedral.txt').read_text())
    cast=Image.new('RGB',(7*215+20,320),'#282631');cd=ImageDraw.Draw(cast)
    cd.text((20,15),'EMBERWAKE CALDERA  /  Levels 95-99',fill='#f2d2a6',font=font)
    for i,e in enumerate(ENEMIES):
        atlas=Image.open(ROOT/f"client/assets/cathedral_{e['kind']}.png").convert('RGBA')
        sheet=Image.new('RGB',(8*192+130,5*202+100),'#282631');d=ImageDraw.Draw(sheet)
        d.text((20,15),e['name']+('  /  ELITE' if e['elite'] else '')+f"  /  Level {e['level']}",font=font,fill='#f2d2a6')
        for row,(clip,spec) in enumerate(meta['clips'].items()):
            d.text((12,60+row*202+85),clip.upper(),font=small,fill='#c7bec6')
            for n in range(spec['n']):
                frame=atlas.crop((n*96,row*96,n*96+96,row*96+96)).resize((192,192),Image.Resampling.NEAREST)
                sheet.paste(frame,(120+n*192,60+row*202),frame)
        sheet.save(OUT/f"emberwake-sheet-{e['kind']}.png")
        frame=atlas.crop((0,0,96,96)).resize((192,192),Image.Resampling.NEAREST)
        cast.paste(frame,(20+i*215,55),frame)
        words=e['name'].replace(',','').split();line='';y=255
        for word in words:
            trial=(line+' '+word).strip()
            if d.textlength(trial,font=small)>203:
                cd.text((20+i*215,y),line,font=small,fill='#f2d2a6');y+=18;line=word
            else:line=trial
        cd.text((20+i*215,y),line,font=small,fill='#f2d2a6')
    cast.save(OUT/'emberwake-enemy-cast.png')
    print('Seven full 34-frame sheets and one cast sheet:',OUT)
if __name__=='__main__':main()
