#!/usr/bin/env python3
"""Fishing icons: preview, build, export, verify. Build preserves saved editor work.

The original frames come from two native PixelFlow sources. Expert frames are
authored below and appended locally without changing the original pixels.
Preview never writes production assets.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(os.environ.get('FISH_ART_ROOT', Path(__file__).resolve().parents[1]))
ASSETS = ROOT / 'client/assets'
META = ASSETS / 'fishing-icons.txt'
NAME = 'valhallasc_fishing_items_v2'
SIZE, COLS = 48, 13
INK = '#242236'
RAMPS = {
    'silver': ['#485d79', '#819bad', '#bfd4db', '#f0f8e8'],
    'blue': ['#283b6b', '#3869a0', '#65b4d0', '#b7f4ec'],
    'green': ['#274b48', '#3e7961', '#7bb580', '#d5e9a5'],
    'gold': ['#794638', '#bd803d', '#e8bd65', '#fff0a8'],
    'pink': ['#633a69', '#a95c8a', '#e29bae', '#ffe0cf'],
    'purple': ['#403866', '#7262a4', '#b29bcf', '#e6d6ff'],
    'fire': ['#702e39', '#be4937', '#f28c45', '#ffdc79'],
    'coal': ['#29283a', '#45485c', '#76798b', '#b6b2ba'],
    'wood': ['#49302d', '#815139', '#b87e4b', '#e5bc7a'],
    'storm': ['#2c3a67', '#416b91', '#7bd7de', '#c4ffe3'],
    'opal': ['#385361', '#4fa996', '#9ee0bb', '#edffcb'],
    'moon': ['#463d72', '#825cc0', '#c9b6ff', '#f9e7f2'],
}
# Authored body, fin and colour choices; roster order never controls a silhouette.
# width/height refer to the body (tail and occupational details are separate).
SPECS = {
 'pier_sprat': ('fish','silver',27,10,0), 'saltby_herring': ('fish','blue',29,13,1),
 'sand_dab': ('flat','gold',26,18,0), 'copper_mackerel': ('fish','gold',30,12,3),
 'tide_flounder': ('flat','blue',28,22,2), 'glass_eel': ('eel','silver',30,7,0),
 'moonscale_carp': ('koi','purple',28,21,2), 'snow_minnow': ('fish','silver',25,8,2),
 'frost_char': ('fish','pink',30,14,1), 'ice_perch': ('perch','blue',26,17,3),
 'silver_smelt': ('fish','silver',32,9,3), 'blue_grayling': ('perch','purple',29,13,1),
 'aurora_trout': ('fish','green',31,15,2), 'frostwake_pike': ('gar','blue',33,10,1),
 'mud_loach': ('eel','wood',29,10,3), 'reed_bream': ('flat','green',25,20,1),
 'bog_dace': ('fish','wood',26,12,2), 'moss_catfish': ('cat','green',28,18,0),
 'peat_eel': ('eel','green',32,8,2), 'lantern_gar': ('gar','gold',31,12,3),
 'fen_crownfin': ('crown','green',27,20,3), 'alder_trout': ('fish','gold',30,14,1),
 'brook_dace': ('fish','blue',25,11,0), 'willow_chub': ('fish','green',28,16,1),
 'fern_perch': ('perch','green',25,18,3), 'root_barb': ('fish','wood',28,14,0),
 'amber_salmon': ('fish','fire',32,15,2), 'antler_sturgeon': ('sturgeon','wood',32,13,3),
 'jade_barb': ('fish','green',26,13,2), 'vine_tetra': ('flat','blue',22,18,1),
 'rain_guppy': ('guppy','pink',22,12,3), 'orchid_gourami': ('flat','pink',25,23,2),
 'parrot_perch': ('perch','gold',25,20,2), 'canopy_arowana': ('gar','green',33,14,2),
 'jade_dragonfish': ('dragon','green',31,17,3), 'sand_tilapia': ('flat','gold',27,20,3),
 'palm_minnow': ('fish','green',24,9,0), 'dune_carp': ('koi','gold',28,20,1),
 'lapis_bream': ('flat','blue',27,21,3), 'dusk_catfish': ('cat','purple',30,19,1),
 'mirage_eel': ('eel','blue',33,9,1), 'sapphire_lungfish': ('cat','blue',31,15,3),
 'blossom_dace': ('fish','pink',27,12,0), 'thaw_minnow': ('fish','blue',24,10,2),
 'petal_chub': ('fish','purple',27,17,1), 'vernal_trout': ('fish','green',30,15,1),
 'equinox_perch': ('perch','purple',26,18,2), 'wheel_koi': ('koi','pink',29,21,3),
 'yearling_crownray': ('ray','purple',32,26,3), 'cinder_fry': ('fish','fire',24,10,0),
 'slag_sucker': ('cat','coal',27,17,2), 'ash_barb': ('fish','coal',28,13,3),
 'basalt_eel': ('eel','coal',32,9,3), 'furnace_bass': ('perch','fire',28,20,1),
 'obsidian_gar': ('gar','coal',33,12,3), 'phoenix_koi': ('dragon','fire',29,20,2),
 'sunfire_ray': ('ray','fire',34,25,2),
 'cloud_minnow': ('fish','silver',23,8,1), 'storm_barb': ('fish','blue',27,12,2),
 'gale_eel': ('eel','storm',32,9,1), 'thundercrest_ray': ('ray','blue',33,23,3),
 'star_dace': ('fish','purple',25,10,0), 'comet_perch': ('perch','gold',27,18,2),
 'nebula_gar': ('gar','purple',33,13,0), 'prism_gudgeon': ('fish','pink',23,10,1),
 'glass_spindlefish': ('gar','silver',30,8,2), 'suncut_carp': ('koi','gold',30,18,1),
 'prismatic_mirrorfish': ('crown','purple',26,20,2), 'clockwork_chub': ('fish','gold',24,13,3),
 'obsidian_bream': ('flat','coal',29,21,1), 'orrery_sturgeon': ('sturgeon','coal',33,16,2),
 'spore_rasbora': ('fish','pink',22,9,2), 'veil_catfish': ('cat','purple',25,20,1),
 'dreamfin_pike': ('gar','pink',34,10,0), 'moonwake_dragonfish': ('dragon','purple',32,20,0),
 'crescent_bleak': ('fish','silver',31,9,0), 'silver_crescent_eel': ('eel','purple',30,8,2),
 'ringwater_koi': ('koi','blue',28,23,3), 'ribbon_shiner': ('fish','pink',27,10,3),
 'jubilee_guppy': ('guppy','gold',22,13,0), 'parade_gourami': ('flat','pink',29,23,3),
 'festival_crownfin': ('crown','pink',29,21,1), 'rootfoot_dace': ('fish','green',25,10,3),
 'nectar_perch': ('perch','pink',26,19,0), 'canopy_lungfish': ('cat','green',31,21,2),
 'heartwood_whitefish': ('fish','silver',28,13,1), 'pithscale_char': ('fish','wood',31,13,2),
 'amberroot_gar': ('gar','gold',34,11,0), 'mountainheart_paddlefish': ('sturgeon','gold',34,14,1),
 'cairn_minnow': ('fish','coal',23,9,0), 'tarn_grayling': ('perch','silver',27,16,3),
 'graniteback_sturgeon': ('sturgeon','silver',33,17,0),
}


def roster():
    sys.path.insert(0, str(ROOT / 'scripts'))
    from fish_catalog import pieces
    return pieces()


def fish_image(key):
    shape, colour, width, height, pattern = SPECS[key]
    dark, mid, light, shine = RAMPS[colour]
    accent = RAMPS['fire' if colour == 'coal' else 'gold'][2]
    image = Image.new('RGBA', (SIZE, SIZE))
    d = ImageDraw.Draw(image)
    cx, cy = 26, 25
    left, right = cx-width//2, cx+width//2
    top, bottom = cy-height//2, cy+height//2
    if shape == 'eel':
        pts = [(6,15),(11,12),(18,15),(18,23),(12,30),(15,35),(26,34),(34,24),(41,23)]
        d.line(pts, fill=INK, width=9, joint='curve')
        d.line(pts, fill=dark, width=7, joint='curve')
        d.line([(x,y-1) for x,y in pts], fill=light, width=3, joint='curve')
        d.ellipse((35,19,44,27), fill=mid, outline=INK)
        d.point((41,21), fill=shine); d.point((42,22), fill=INK)
        for x,y in pts[2:-2]: d.point((x+1,y+2), fill=accent)
        return image
    if shape == 'ray':
        pts = [(24,10),(31,18),(43,26),(34,30),(26,29),(21,39),(19,29),(5,27),(15,18)]
        d.polygon(pts, fill=dark, outline=INK)
        d.polygon([(24,12),(29,20),(40,26),(28,25),(23,29),(16,25),(8,26),(18,19)], fill=mid)
        d.polygon([(24,14),(26,22),(12,25),(19,19)], fill=light)
        d.line([(21,33),(24,40),(31,43)], fill=INK, width=3)
        d.line([(21,33),(24,40),(31,43)], fill=accent, width=1)
        for x in (21,27): d.ellipse((x,18,x+2,20), fill=shine); d.point((x+1,19),fill=INK)
        for x,y in [(14,24),(33,24),(23,25)]: d.point((x,y),fill=shine)
        return image
    tail_w = 12 if shape in ('guppy','koi','dragon') else 8
    d.polygon([(left+3,cy),(left-tail_w+3,cy-9),(left-tail_w+4,cy+8)], fill=dark, outline=INK)
    d.line([(left-tail_w+5,cy-6),(left+2,cy),(left-tail_w+5,cy+5)],fill=light)
    fin_top = top - (8 if shape in ('perch','crown','dragon') else 5)
    if shape in ('perch','crown','dragon'):
        pts=[(left+5,top+3)]
        for x in range(left+6,right-5,4): pts.extend([(x,fin_top+(x%3)),(x+2,top)])
        pts += [(right-4,top+4)]
    else: pts=[(left+6,top+3),(cx,fin_top),(cx+4,top+3)]
    d.polygon(pts,fill=accent if shape in ('crown','dragon') else mid,outline=INK)
    if shape == 'gar':
        d.polygon([(right-6,cy-3),(45,cy-1),(45,cy+2),(right-5,cy+4)],fill=mid,outline=INK)
    d.ellipse((left,top,right,bottom),fill=dark,outline=INK)
    d.ellipse((left+1,top+1,right-1,bottom-3),fill=mid)
    d.ellipse((left+3,top+2,right-5,cy),fill=light)
    d.line([(left+5,top+3),(cx,top+2),(right-9,top+4)],fill=shine,width=1)
    if pattern == 0:
        d.line([(left+3,cy+2),(right-5,cy+2)],fill=light)
    elif pattern == 1:
        for x in range(left+5,right-6,6):
            d.line([(x,top+4),(x+2,cy+3)],fill=dark,width=2)
    elif pattern == 2:
        for x in range(left+5,right-6,5):
            for y in (cy-1,cy+3): d.point((x,y),fill=accent)
    else:
        for x in range(left+4,right-6,5):
            d.line([(x,cy-2),(x+2,cy),(x,cy+2)],fill=dark)
    d.polygon([(cx-3,cy+1),(cx+4,cy+3),(cx-1,bottom+4)],fill=dark,outline=INK)
    d.line([(cx-1,cy+3),(cx,bottom+1)],fill=light)
    d.arc((right-12,top+3,right-5,bottom-1),270,90,fill=dark)
    ex,ey=right-5,cy-3
    d.ellipse((ex-2,ey-2,ex+2,ey+2),fill=shine,outline=INK)
    d.point((ex+1,ey),fill=INK)
    d.line([(right-2,cy+2),(right,cy+1)],fill=INK)
    if shape in ('cat','dragon','sturgeon','koi'):
        for sign in (-1,1): d.line([(right-2,cy+2),(right+2,cy+sign*6),(right-1,cy+sign*8)],fill=accent)
    if shape == 'sturgeon':
        for x in range(left+5,right-5,5): d.polygon([(x,top+1),(x+2,top-4),(x+4,top+1)],fill=light,outline=INK)
    if shape == 'dragon':
        d.line([(cx+3,top),(cx+1,top-5),(cx+5,top-7)],fill=accent,width=2)
    if shape == 'crown':
        d.polygon([(cx-6,top),(cx-7,top-6),(cx-2,top-3),(cx+1,top-8),(cx+4,top-3),(cx+8,top-6),(cx+7,top)],fill=accent,outline=INK)
    return image


def render(item):
    key = item['id']
    if item['kind'] == 'fish': return fish_image(key.removeprefix('fish_'))
    im = Image.new('RGBA',(SIZE,SIZE)); d = ImageDraw.Draw(im)
    wood, gold, silver, blue = [RAMPS[k] for k in ('wood','gold','silver','blue')]
    if item['kind'] == 'rod':
        tier=item['fishing']['tier']; lava=item['fishing']['lava']
        palette = {9: 'green', 10: 'coal'}.get(tier)
        c = RAMPS[palette or ('fire' if lava else 'wood')]
        d.line([(9,40),(15,31),(24,19),(31,9),(36,6)],fill=INK,width=5)
        d.line([(9,40),(15,31),(24,19),(31,9),(36,6)],fill=c[2],width=3)
        d.line([(11,38),(16,31)],fill=wood[0],width=4)
        for y in (33,36,39):d.line([(10+(40-y)//2,y),(13+(40-y)//2,y+1)],fill=gold[2])
        d.line([(36,6),(39,13),(40,25),(38,31)],fill=silver[2])
        if lava and tier == 2:
            d.ellipse((14,26,26,38),fill=INK,outline=gold[2]);d.ellipse((17,29,23,35),fill=c[2])
        d.ellipse((16,28,24,36),fill=INK);d.ellipse((18,29,23,34),fill=c[0],outline=gold[2])
        d.ellipse((35,29,41,37),fill=INK);d.rectangle((36,31,40,34),fill=RAMPS['fire' if lava else 'pink'][2]);d.line([(37,30),(39,30)],fill=silver[3])
        for k in range(tier):d.point((22+k*2,24-k*2),fill=gold[3])
    elif item['kind'] == 'food':
        habitat=key.split('_')[1]; feast=key.endswith('feast')
        c=RAMPS[{'shore':'blue','cold':'silver','swamp':'green','forest':'wood','jungle':'green','oasis':'gold',
                 'spring':'pink','lava':'fire','cloudwater':'purple','glasswater':'opal','moonwater':'moon',
                 'greenwater':'green','deep':'coal'}[habitat]]
        d.ellipse((4,19,44,41),fill=INK);d.ellipse((5,19,43,38),fill=silver[1],outline=silver[3]);d.ellipse((9,22,39,35),fill=wood[0])
        d.polygon([(12,25),(8,21),(8,30)],fill=gold[1],outline=INK)
        d.ellipse((12,21,36,32),fill=gold[1],outline=INK);d.ellipse((14,22,34,28),fill=gold[2])
        for x in (18,23,28):d.line([(x,23),(x+2,28)],fill=wood[0])
        d.point((33,25),fill=INK)
        for x,y in ((13,33),(35,30),(32,34)):
            d.ellipse((x-2,y-1,x+2,y+1),fill=RAMPS['green'][2])
        d.arc((7,28,17,37),170,350,fill=gold[3],width=2)
        if feast:
            d.ellipse((10,15,23,22),fill=c[1],outline=INK)
            d.ellipse((24,16,38,23),fill=c[2],outline=INK)
            d.line([(14,16),(19,20)],fill=c[3]);d.line([(28,17),(33,21)],fill=c[3])
        else:
            for x in (20,28):d.line([(x,18),(x-2,15),(x,12)],fill=silver[2])
        if habitat == 'swamp':
            d.ellipse((7,27,16,32),fill=RAMPS['wood'][2],outline=INK);d.rectangle((11,31,13,35),fill=RAMPS['silver'][2])
        elif habitat == 'jungle':
            d.polygon([(7,30),(11,25),(17,30),(12,35)],fill=RAMPS['green'][2],outline=INK);d.line([(9,30),(15,30)],fill=RAMPS['green'][3])
        # Every habitat has a recognisable garnish colour, independent of rarity.
        d.ellipse((35,21,41,27),fill=c[2],outline=INK);d.point((38,23),fill=c[3])
    elif key.endswith('old_boot'):
        d.polygon([(14,9),(29,10),(27,29),(38,33),(40,39),(9,39),(10,32)],fill=wood[1],outline=INK)
        d.polygon([(17,13),(25,13),(22,30),(14,33)],fill=wood[2]);d.line([(10,38),(39,38)],fill=wood[0],width=3)
        for y in (20,24,28):d.line([(23,y),(28,y)],fill=gold[2])
        d.line([(16,12),(28,13)],fill=INK,width=3)
    elif key.endswith(('driftwood','charred_branch')):
        c=RAMPS['coal'] if key.endswith('charred_branch') else wood
        d.line([(9,37),(19,27),(28,18),(38,10)],fill=INK,width=9)
        d.line([(9,36),(19,26),(28,17),(38,10)],fill=c[1],width=6)
        d.line([(11,34),(29,16),(37,10)],fill=c[3],width=2)
        d.line([(22,23),(18,12)],fill=INK,width=5);d.line([(22,23),(18,12)],fill=c[2],width=3)
        d.ellipse((6,33,12,39),fill=c[2],outline=INK)
    elif key.endswith('tangled_line'):
        for box in ((9,14,35,34),(14,9,39,33),(10,20,34,38)):
            d.ellipse(box,outline=INK,width=4);d.ellipse(box,outline=silver[2],width=2)
        d.line([(26,29),(38,37),(40,33)],fill=gold[2],width=2)
    elif key.endswith('cracked_shell'):
        d.polygon([(24,10),(34,12),(40,21),(37,30),(25,39),(10,30),(7,21),(13,13)],fill=RAMPS['pink'][1],outline=INK)
        for x in (12,18,25,32,38):d.line([(25,36),(x,17 if x<35 else 22)],fill=RAMPS['pink'][3])
        d.line([(26,10),(21,20),(28,25),(22,30)],fill=INK,width=2)
    elif key.endswith('cooled_slag'):
        d.polygon([(9,21),(17,12),(33,11),(40,23),(34,36),(16,39),(7,30)],fill=RAMPS['coal'][0],outline=INK)
        d.polygon([(10,22),(18,14),(31,13),(25,23)],fill=RAMPS['coal'][2]);d.polygon([(25,24),(37,24),(32,33),(20,34)],fill=RAMPS['coal'][1])
        d.line([(17,17),(21,24),(18,30),(27,34)],fill=RAMPS['fire'][1],width=2)
    elif key.endswith('sunken_coffer'):
        d.polygon([(8,22),(28,16),(41,23),(41,37),(21,43),(8,35)],fill=wood[1],outline=INK)
        d.polygon([(8,22),(8,16),(27,10),(41,16),(41,23),(21,29)],fill=wood[2],outline=INK)
        for x in (13,32):d.line([(x,16),(x+5,19),(x+5,38)],fill=gold[2],width=3)
        d.line([(21,29),(21,42)],fill=wood[0]);d.rectangle((24,25,29,32),fill=gold[2],outline=INK)
        d.line([(6,31),(11,27),(13,32),(10,36)],fill=RAMPS['green'][1],width=2)
    elif key.endswith('message_bottle'):
        d.polygon([(23,7),(31,11),(28,19),(34,27),(30,38),(21,42),(10,35),(11,27),(21,15)],fill=blue[1],outline=INK)
        d.polygon([(19,24),(26,20),(30,28),(25,35),(17,36),(14,31)],fill=gold[3],outline=wood[1])
        d.line([(18,29),(25,25)],fill=wood[2]);d.line([(17,32),(24,28)],fill=wood[2]);d.line([(13,28),(12,33),(19,39)],fill=blue[3],width=2)
        d.polygon([(23,6),(32,10),(30,15),(21,11)],fill=wood[2],outline=INK)
    elif key.endswith('lost_purse'):
        d.polygon([(19,13),(15,7),(31,8),(28,14),(36,22),(39,34),(32,40),(14,40),(8,33),(12,22)],fill=wood[1],outline=INK)
        d.ellipse((12,20,33,36),fill=wood[2]);d.line([(18,15),(30,15),(35,21)],fill=gold[2],width=2)
        d.ellipse((22,24,31,33),fill=gold[2],outline=gold[0]);d.line([(26,26),(26,31)],fill=gold[3])
    elif key.endswith('rod_charm'):
        d.arc((11,6,37,33),180,540,fill=gold[1],width=3)
        d.line([(24,24),(24,33),(30,39),(36,33),(35,29)],fill=INK,width=5)
        d.line([(24,24),(24,33),(30,39),(36,33),(35,29)],fill=gold[2],width=3)
        d.polygon([(24,14),(30,21),(24,28),(18,21)],fill=blue[2],outline=INK);d.line([(24,16),(21,21),(24,24)],fill=blue[3])
    else: raise ValueError(key)
    return im


def contact(frames, items, output):
    sheet=Image.new('RGB',(7*170,math.ceil(len(items)/7)*128),'#263344'); d=ImageDraw.Draw(sheet)
    for n,(im,item) in enumerate(zip(frames,items)):
        x,y=n%7*170,n//7*128
        sheet.paste(im.resize((96,96),Image.Resampling.NEAREST),(x+35,y),im.resize((96,96),Image.Resampling.NEAREST))
        name=item['id'].removeprefix('fish_').removeprefix('fishing_').removeprefix('rod_')
        d.text((x+3,y+98),name[:24],fill='white')
    Path(output).parent.mkdir(parents=True,exist_ok=True);sheet.save(output)


def api():
    from make_npcp_sprites import pf_api
    return pf_api()


def save_atlas(atlas, meta):
    atlas.save(ASSETS/'fishing-icons.png', optimize=True)
    data = {key: meta[key] for key in ('size', 'cols', 'rows', 'at')}
    (ROOT/'client/fishingicons.js').write_text(
        "'use strict';\n// Generated from assets/fishing-icons.txt.\nwindow.FISHING_ICONS = "
        + json.dumps(data, separators=(',', ':')) + ';\n')


def extend(items, output):
    """Rebuild the expert cells using the already exported original frames."""
    meta = json.loads(META.read_text())
    original = [key for source in meta['sources'] for key in source['order']]
    by_id = {item['id']: item for item in items}
    added = [key for key in by_id if key not in original]
    previous = Image.open(ASSETS/'fishing-icons.png').convert('RGBA')
    ids = original + added
    meta.update(order=ids, rows=math.ceil(len(ids)/COLS), local=added)
    atlas = Image.new('RGBA', (COLS*SIZE, meta['rows']*SIZE))
    frames = []
    for key in original:
        x, y = meta['at'][key]
        frames.append(previous.crop((x*SIZE, y*SIZE, (x+1)*SIZE, (y+1)*SIZE)))
    frames.extend(render(by_id[key]) for key in added)
    meta['at'] = {key: [n % COLS, n // COLS] for n, key in enumerate(ids)}
    for n, frame in enumerate(frames):
        atlas.alpha_composite(frame, (n % COLS*SIZE, n // COLS*SIZE))
    META.write_text(json.dumps(meta, indent=2) + '\n')
    save_atlas(atlas, meta)
    contact(frames[len(original):], [by_id[key] for key in added], output)
    print(f'Expert fishing art: {len(added)} new icons, {len(original)} original cells preserved')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['preview','build','export','verify','extend'])
    p.add_argument('--output',default=str(ROOT/'test-results/fishing-art/contact.png'))
    args=p.parse_args(); items=roster();ids=[i['id'] for i in items]
    if args.action=='preview':
        contact([render(i) for i in items],items,args.output);print(args.output);return
    if args.action == 'extend':
        extend(items, args.output)
        return
    if META.exists():
        meta = json.loads(META.read_text())
        order = {key: i for i, key in enumerate(meta['order'])}
        items.sort(key=lambda item: order.get(item['id'], len(order)))
        ids = [i['id'] for i in items]
    pf=api()
    if args.action=='build':
        previous=json.loads(META.read_text()) if META.exists() else None
        if previous and previous.get('version')==NAME:
            assert json.loads(META.read_text())['order']==ids,'Roster changed; preserve old source and author a new version'
            print('Saved fishing source preserved');return
        from make_item_sprites import palette_of,index_frames
        images=[np.array(render(i)) for i in items];palette,colours=palette_of(images)
        assert len(palette)<=256
        existing=pf.ids(NAME); sources=[]
        groups=[[i for i in items if i['kind']=='fish'],[i for i in items if i['kind']!='fish']]
        assert all(len(group)<=64 for group in groups),'PixelFlow frame cap'
        offset=0
        for group, suffix in zip(groups,('fish','tackle')):
            name=NAME+'_'+suffix;sid=existing.get(name)
            selected=images[offset:offset+len(group)]
            if not sid:
                ops=[dict(op='grid',frame=n,layer=0,x=0,y=0,rows=g.tolist()) for n,g in enumerate(index_frames(selected,colours))]
                result=pf.api('create',dict(name=name,width=SIZE,height=SIZE,frames=len(group),layers=1,fps=1,palette=palette,persist=True,ops=ops))
                assert result.get('ok'),result.get('errors');sid=result['sprite_id']
            sources.append(dict(sprite=sid,order=ids[offset:offset+len(group)]));offset+=len(group)
        META.write_text(json.dumps(dict(version=NAME,sourceHistory=([*previous.get('sourceHistory',[]),previous['sources']] if previous else []),size=SIZE,cols=COLS,rows=math.ceil(len(ids)/COLS),sources=sources,order=ids,at={k:[n%COLS,n//COLS] for n,k in enumerate(ids)}),indent=2)+'\n')
        print('Saved PixelFlow sources', [source['sprite'] for source in sources])
    meta=json.loads(META.read_text())
    assert meta['order']==ids
    atlas=Image.new('RGBA',(COLS*SIZE,meta['rows']*SIZE));frames=[]
    for source in meta['sources']:
        sp,grids=pf.load(source['sprite'])
        assert (sp['width'],sp['height'],len(grids))==(SIZE,SIZE,len(source['order']))
        for data in grids:
            n=len(frames);im=Image.fromarray(pf.to_rgba(data[0],sp['palette']));frames.append(im)
            atlas.alpha_composite(im,(n%COLS*SIZE,n//COLS*SIZE))
    by_id = {i['id']: i for i in items}
    for key in meta.get('local', []):
        n = len(frames)
        im = render(by_id[key])
        frames.append(im)
        atlas.alpha_composite(im, (n%COLS*SIZE, n//COLS*SIZE))
    target=ASSETS/'fishing-icons.png'
    if args.action=='verify':
        assert atlas.tobytes()==Image.open(target).convert('RGBA').tobytes(),'Editor export differs'
        print('Verified',len(ids),'editor frames against production atlas');return
    save_atlas(atlas, meta)
    contact(frames,items,args.output);print('Exported',len(ids),'icons;',args.output)


if __name__=='__main__': main()
