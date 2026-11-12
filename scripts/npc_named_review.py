#!/usr/bin/env python3
"""Local review sheets of saved named-NPC exports. No uploads or world edits."""
import collections
import json
import math
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test-results/npc-named'
PLAN = json.loads((ROOT / 'docs/npc-named-plan.txt').read_text())
PEOPLE = [p for p in PLAN['people'] if p['classification'] == 'named']
META = json.loads((ROOT / 'client/assets/npcp.txt').read_text())


def cell(person, clip='idle', frame=0):
    atlas = Image.open(ROOT / f'client/assets/npcp_{person["designKey"]}.png').convert('RGBA')
    row = META['clips'][clip]['row']
    return atlas.crop((frame*96, row*96, (frame+1)*96, (row+1)*96)).resize((192, 192), Image.Resampling.NEAREST)


def board(people, columns, poses, title):
    width, height = 192 * len(poses), 228
    sheet = Image.new('RGBA', (columns * width, math.ceil(len(people)/columns)*height+32), '#253343')
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 8), title, fill='#fff0d8')
    for i, person in enumerate(people):
        x, y = (i % columns)*width, (i//columns)*height+32
        for j,(clip,frame) in enumerate(poses):
            sheet.alpha_composite(cell(person, clip, frame), (x+j*192, y))
        draw.text((x+4,y+190),person['name'],fill='#fff0d8')
        draw.text((x+4,y+207),person['id'],fill='#9bb9c9')
    return sheet


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    board(PEOPLE, 12, [('idle',0)], '148 named NPC designs - saved PixelFlow exports').save(OUT/'roster.png')
    by_zone = collections.defaultdict(list)
    for person in PEOPLE:
        by_zone[person['zone']].append(person)
    for zone,people in by_zone.items():
        board(people, 2, [('idle',0),('walk',2),('talk',1)],
              f'{people[0]["zoneName"]}: idle / walk / talk').save(OUT/f'zone-{zone:02}.png')
    names = ['fold_hild','dock_skipper','apple_maren','apple_sten','tg_dr_kessa','nacre_harbourmaster','hw_smith','hw_kid_pip']
    highlights = [next(p for p in PEOPLE if p['id']==name) for name in names]
    frames, durations = [], []
    for clip,count,ms in [('idle',6,167),('walk',8,100),('talk',6,167)]:
        for frame in range(count):
            frames.append(board(highlights,4,[(clip,frame)],f'Named NPCs: {clip}'))
            durations.append(ms)
    frames[0].save(OUT/'highlights.gif', save_all=True, append_images=frames[1:], loop=0, duration=durations, disposal=2)
    if '--robes-before' in sys.argv:
        before = Path(sys.argv[sys.argv.index('--robes-before') + 1])
        robe_comparison(before)
    print('Saved roster,',len(by_zone),'zone sheets and highlight animation to',OUT)


def robe_comparison(before):
    names = ['fold_hild', 'hw_steward', 'hw_pilgrim', 'deep_dw_ottilia', 'prism_ws_ottilie', 'hw_innkeeper']
    selected = [next(p for p in PEOPLE if p['id'] == name) for name in names]
    old_meta = json.loads((before/'client/assets/npcp.txt').read_text())

    def comparison(clip, frame):
        out = Image.new('RGBA', (len(selected)*192, 460), '#253343')
        d = ImageDraw.Draw(out)
        d.text((4,4), 'BEFORE: legs through cloth', fill='#ffad9c')
        d.text((4,234), 'CORRECTED: closed cloth covers legs', fill='#aeefb3')
        for i,p in enumerate(selected):
            row = old_meta['clips'][clip]['row']
            old = Image.open(before/f'client/assets/npcp_{p["designKey"]}.png').convert('RGBA')
            old = old.crop((frame*96,row*96,(frame+1)*96,(row+1)*96)).resize((192,192),Image.Resampling.NEAREST)
            out.alpha_composite(old,(i*192,26))
            out.alpha_composite(cell(p,clip,frame),(i*192,256))
            d.text((i*192+3,216),p['name'],fill='#fff0d8')
        return out

    comparison('idle',0).save(OUT/'robe-fix-before-after.png')
    frames = [comparison('walk',frame) for frame in range(8)]
    frames[0].save(OUT/'robe-fix-walk.gif',save_all=True,append_images=frames[1:],duration=140,loop=0,disposal=2)


if __name__ == '__main__':
    main()
