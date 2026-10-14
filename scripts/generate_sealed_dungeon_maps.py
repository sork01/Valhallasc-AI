#!/usr/bin/env python3
"""Build open private dungeons and their reserved sealed floor plans.

The maps reserve stable public zone IDs 29–39. Future parent landmarks remain sealed until their opening tasks.
Run after the outdoor zone generators, then sync-world.cjs and rebuild Rust.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_gloamfen as fen
import generate_undervault as vault
from eye_below_content import BOSSES as EYE_BOSSES
from elder_hollow_content import BOSSES as ELDER_BOSSES
from thousandfold_content import BOSSES as PAVILION_BOSSES
from rain_crown_content import BOSSES as RAIN_BOSSES
from seed_vault_content import BOSSES as SEED_BOSSES
from sunken_astrolabe_content import BOSSES as ASTRO_BOSSES
from thunderheart_gate_content import BOSSES as THUNDER_BOSSES
from blooming_labyrinth_content import BOSSES as BLOOM_BOSSES
from solar_crucible_content import BOSSES as SOLAR_BOSSES
from yearwheel_dungeon_content import bosses as yearwheel_bosses

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'
SIZE = 96
FIRST = 29
OPEN_IDS = {'eye_below', 'elder_hollow', 'thousandfold', 'rain_crown', 'seed_vault', 'sunken_astrolabe', 'thunderheart_gate', 'blooming_labyrinth', 'solar_crucible', 'amber_archive', 'silent_solstice'}

# Centre lines are also the future encounter route. Branches and loops are
# deliberate: the five floors do not share a rotated copy of one plan.
PLANS = [
    dict(id='eye_below', name='The Eye Below', parent=19, level=65,
         landing=(105, 30), spawn=(48, 82), rooms=[(48, 82), (48, 65), (27, 62), (28, 38),
         (48, 25), (68, 38), (68, 62), (48, 48)],
         links=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 1), (3, 7), (7, 5)]),
    dict(id='elder_hollow', name='The Elder Hollow', parent=20, level=70,
         landing=(106, 27), spawn=(48, 83), rooms=[(48, 83), (48, 65), (28, 53), (68, 53),
         (48, 38), (27, 23), (69, 23), (48, 17)],
         links=[(0, 1), (1, 2), (1, 3), (2, 4), (3, 4), (4, 5), (4, 6),
                (5, 7), (6, 7)]),
    dict(id='thousandfold', name='The Thousandfold Pavilion', parent=21, level=75,
         landing=(113, 65), spawn=(48, 83), rooms=[(48, 83), (22, 69), (72, 58),
         (24, 46), (70, 32), (48, 17)],
         links=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]),
    dict(id='rain_crown', name='Temple of the Rain Crown', parent=22, level=80,
         landing=(120, 30), spawn=(48, 83), rooms=[(48, 83), (48, 69), (32, 56),
         (64, 44), (48, 31), (48, 17)],
         links=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]),
    dict(id='seed_vault', name='The Seed Vault', parent=24, level=80,
         landing=(48, 22), spawn=(48, 82), rooms=[(48, 82), (48, 51), (25, 45),
         (71, 45), (34, 24), (62, 24), (48, 17)],
         links=[(0, 1), (1, 2), (1, 3), (2, 4), (3, 5), (4, 6), (5, 6)]),
    dict(id='sunken_astrolabe', name='The Sunken Astrolabe', parent=25, level=85,
         landing=(140, 17), spawn=(48, 82), rooms=[(48, 82), (25, 69), (71, 69),
         (48, 53), (26, 38), (70, 38), (48, 19)],
         links=[(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (3, 5), (4, 6), (5, 6)]),
    dict(id='thunderheart_gate', name='The Thunderheart Gate', parent=27, level=95,
         landing=(151, 20), spawn=(48, 82), rooms=[(48, 82), (24, 70), (24, 52),
         (65, 53), (67, 34), (41, 23), (70, 18)],
         links=[(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (2, 5)]),
    dict(id='blooming_labyrinth', name='The Blooming Labyrinth', parent=28, level=97,
         landing=(48, 235), spawn=(48, 82), rooms=[(48, 82), (25, 69), (71, 68),
         (47, 54), (22, 38), (73, 36), (49, 18)],
         links=[(0, 1), (0, 2), (1, 3), (2, 3), (1, 4), (2, 5),
                (3, 4), (3, 5), (4, 6), (5, 6)]),
    dict(id='solar_crucible', name='The Solar Crucible', parent=28, level=98,
         landing=(346, 248), spawn=(48, 82), rooms=[(48, 82), (48, 65), (25, 53),
         (71, 53), (48, 40), (27, 24), (69, 24), (48, 17)],
         links=[(0, 1), (1, 2), (1, 3), (2, 4), (3, 4), (4, 5),
                (4, 6), (5, 7), (6, 7)]),
    dict(id='amber_archive', name='The Amber Archive', parent=28, level=99,
         landing=(358, 151), spawn=(48, 82), rooms=[(48, 82), (20, 68), (48, 68),
         (76, 68), (20, 45), (48, 45), (76, 45), (20, 22), (48, 22), (76, 22)],
         links=[(0, 2), (1, 2), (2, 3), (1, 4), (2, 5), (3, 6),
                (4, 5), (5, 6), (4, 7), (5, 8), (6, 9),
                (7, 8), (8, 9)]),
    dict(id='silent_solstice', name='The Silent Solstice', parent=28, level=99,
         landing=(47, 144), spawn=(48, 82), rooms=[(48, 82), (27, 72), (69, 72),
         (27, 53), (69, 53), (48, 43), (24, 25), (72, 25), (48, 17)],
         links=[(0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 5),
                (3, 6), (4, 7), (5, 8), (6, 8), (7, 8)]),
]


def rectangle(cx, cy, width, depth):
    return [cx - width // 2, cy - depth // 2, cx + (width + 1) // 2, cy + (depth + 1) // 2]


def build(plan):
    floor = np.zeros((SIZE, SIZE), bool)
    rooms = []

    def carve(box):
        x0, y0, x1, y1 = box
        assert 2 <= x0 < x1 <= SIZE - 2 and 2 <= y0 < y1 <= SIZE - 2
        floor[y0:y1, x0:x1] = True
        rooms.append(box)

    for n, (x, y) in enumerate(plan['rooms']):
        # Wider arrival and destination halls; intervening halls vary by plan.
        width = 20 if n in (0, len(plan['rooms']) - 1) else 16
        depth = 18 if n in (0, len(plan['rooms']) - 1) else 16
        if plan['id'] == 'thousandfold' and n not in (0, len(plan['rooms']) - 1):
            width, depth = 23, 14
        if plan['id'] == 'rain_crown' and n not in (0, len(plan['rooms']) - 1):
            width, depth = 18, 14
        carve(rectangle(x, y, width, depth))
    paths = []
    for a, b in plan['links']:
        x0, y0 = plan['rooms'][a]
        x1, y1 = plan['rooms'][b]
        bend = (x1, y0)
        for (ax, ay), (bx, by) in (((x0, y0), bend), (bend, (x1, y1))):
            if ax == bx and ay == by:
                continue
            carve([min(ax, bx) - 3, min(ay, by) - 3,
                   max(ax, bx) + 4, max(ay, by) + 4])
        paths.append([[x0, y0], list(bend), [x1, y1]])

    vault.SIZE = SIZE
    wall, _ = vault.wall_pieces(floor)
    wall_kind = {'eye_below': 'eye_wall', 'elder_hollow': 'elder_wall',
                 'thousandfold': 'pavilion_wall', 'rain_crown': 'rain_wall',
                 'seed_vault': 'seed_wall', 'sunken_astrolabe': 'astro_wall', 'thunderheart_gate': 'thunder_wall', 'blooming_labyrinth':'bloom_wall', 'solar_crucible':'solar_wall', 'amber_archive':'amber_wall', 'silent_solstice':'solstice_wall'}.get(plan['id'], 'vaultwall')
    objects = [dict(kind=wall_kind, x=round(x, 2), y=round(y, 2),
                    r=round(max(w, d) / 2, 2), width=round(w, 2),
                    depth=round(d, 2), v=(i + plan['parent']) % 4)
               for i, (x, y, w, d) in enumerate(wall)]
    # Solid void covers all non-floor cells, including the unrendered rock
    # beyond the wall. This also blocks Shadowstep and knockback shortcuts.
    used = floor.copy()
    for y in range(SIZE):
        for x in range(SIZE):
            if used[y, x]:
                continue
            x1 = x
            while x1 < min(x + 8, SIZE) and not used[y, x1]:
                x1 += 1
            y1 = y
            while y1 < min(y + 8, SIZE) and not used[y1, x:x1].any():
                y1 += 1
            used[y:y1, x:x1] = True
            objects.append(dict(kind='void', x=(x + x1) / 2, y=(y + y1) / 2,
                                r=max(x1 - x, y1 - y) / 2,
                                width=x1 - x, depth=y1 - y, v=0))
    sx, sy = plan['spawn']
    eye = plan['id'] == 'eye_below'
    elder = plan['id'] == 'elder_hollow'
    pavilion = plan['id'] == 'thousandfold'
    rain = plan['id'] == 'rain_crown'
    seed = plan['id'] == 'seed_vault'
    astro = plan['id'] == 'sunken_astrolabe'
    thunder = plan['id'] == 'thunderheart_gate'
    bloom = plan['id'] == 'blooming_labyrinth'
    solar = plan['id'] == 'solar_crucible'
    amber = plan['id'] == 'amber_archive'
    solstice = plan['id'] == 'silent_solstice'
    if eye:
        # Every arena is on the real walkable floor. The boss courts have no
        # overlapping trash, and arrivals remain more than eight units clear.
        points = [(48, 65), (42, 64), (27, 62), (28, 54),
                  (68, 62), (61, 62), (48, 48), (54, 47), (49, 36)]
        kinds = ['eye_drifter', 'eye_adept', 'eye_lurker', 'eye_drifter',
                 'eye_lurker', 'eye_adept', 'eye_adept', 'eye_drifter', 'eye_lurker']
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='eye_lenswarden', x=28, y=38),
                   dict(kind='eye_undertide', x=68, y=38),
                   dict(kind='eye_unblinking', x=48, y=25)]
        for n, (x, y) in enumerate(plan['rooms']):
            if n:
                objects += [dict(kind='eye_lamp', x=x-6, y=y-6, r=0, v=n%3),
                            dict(kind='eye_lamp', x=x+6, y=y-6, r=0, v=(n+1)%3)]
        objects += [dict(kind='eye_lens', x=48, y=21, r=0, v=0),
                    dict(kind='eye_rune', x=48, y=79, r=0, v=0)]
    elif elder:
        points = [(48, 65), (42, 64), (28, 53), (68, 53), (48, 38),
                  (32, 39), (64, 39), (37, 25), (59, 25)]
        kinds = ['elder_thornling', 'elder_moth', 'elder_barkguard',
                 'elder_barkguard', 'elder_moth', 'elder_thornling',
                 'elder_thornling', 'elder_moth', 'elder_barkguard']
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='elder_gatekeeper', x=27, y=23),
                   dict(kind='elder_matron', x=69, y=23),
                   dict(kind='elder_heart', x=48, y=17)]
        for n, (x, y) in enumerate(plan['rooms']):
            if n:
                objects += [dict(kind='elder_lantern', x=x-6, y=y-6, r=0, v=n%3),
                            dict(kind='elder_lantern', x=x+6, y=y-6, r=0, v=(n+1)%3)]
        objects += [dict(kind='elder_crown', x=48, y=11, r=0, v=0),
                    dict(kind='elder_seed', x=48, y=79, r=0, v=0)]
    elif pavilion:
        points = [(30, 69), (24, 65), (44, 69), (62, 58), (72, 60),
                  (80, 58), (24, 54), (71, 40), (48, 26)]
        kinds = ['pavilion_foldling', 'pavilion_inkmoth', 'pavilion_silkguard',
                 'pavilion_foldling', 'pavilion_inkmoth', 'pavilion_silkguard',
                 'pavilion_silkguard', 'pavilion_foldling', 'pavilion_inkmoth']
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='pavilion_mirror', x=24, y=46),
                   dict(kind='pavilion_weaver', x=70, y=32),
                   dict(kind='pavilion_sovereign', x=48, y=17)]
        for n, (x, y) in enumerate(plan['rooms']):
            if n:
                objects += [dict(kind='pavilion_lantern', x=x-6, y=y-5, r=0, v=n%3),
                            dict(kind='pavilion_lantern', x=x+6, y=y-5, r=0, v=(n+1)%3)]
        objects += [dict(kind='pavilion_throne', x=48, y=11, r=0, v=0),
                    dict(kind='pavilion_seal', x=48, y=79, r=0, v=0)]
    elif rain:
        points = [(48, 69), (42, 67), (55, 67), (25, 56), (28, 51),
                  (39, 55), (64, 44), (59, 40), (70, 43)]
        kinds = ['rain_crown_droplet', 'rain_crown_oracle', 'rain_crown_guard'] * 3
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='rain_crown_gatekeeper', x=32, y=56),
                   dict(kind='rain_crown_sibyl', x=48, y=31),
                   dict(kind='rain_crown_sovereign', x=48, y=17)]
        for n, (x, y) in enumerate(plan['rooms']):
            if n:
                objects += [dict(kind='rain_brazier', x=x-6, y=y-5, r=0, v=n%3),
                            dict(kind='rain_brazier', x=x+6, y=y-5, r=0, v=(n+1)%3)]
        objects += [dict(kind='rain_crown_altar', x=48, y=11, r=0, v=0),
                    dict(kind='rain_crown_glyph', x=48, y=79, r=0, v=0)]
    elif seed:
        points = [(48, 62), (48, 58), (54, 57), (19, 45), (31, 45),
                  (71, 51), (65, 45), (34, 32), (62, 32)]
        kinds = ['seed_mote', 'seed_amberwing', 'seed_rootguard'] * 3
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='seed_warden', x=25, y=45),
                   dict(kind='seed_germinator', x=71, y=45),
                   dict(kind='seed_worldseed', x=48, y=17)]
        for n, (x, y) in enumerate(plan['rooms']):
            if n:
                objects += [dict(kind='seed_lamp', x=x-6, y=y-5, r=0, v=n%3),
                            dict(kind='seed_lamp', x=x+6, y=y-5, r=0, v=(n+1)%3)]
        objects += [dict(kind='seed_altar', x=48, y=11, r=0, v=0),
                    dict(kind='seed_glyph', x=48, y=78, r=0, v=0)]
    elif astro:
        points = [(48, 65), (42, 68), (25, 69), (71, 69), (48, 53),
                  (43, 47), (26, 47), (70, 47), (48, 30)]
        kinds = ['astro_gearling', 'astro_starling', 'astro_sentinel'] * 3
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='astro_warden', x=26, y=38),
                   dict(kind='astro_navigator', x=70, y=38),
                   dict(kind='astro_axis', x=48, y=19)]
        for n, (x, y) in enumerate(plan['rooms']):
            if n:
                objects += [dict(kind='astro_lamp', x=x-6, y=y-5, r=0, v=n%3),
                            dict(kind='astro_lamp', x=x+6, y=y-5, r=0, v=(n+1)%3)]
        objects += [dict(kind='astro_orrery', x=48, y=11, r=0, v=0),
                    dict(kind='astro_seal', x=48, y=78, r=0, v=0)]
    elif thunder:
        points = [(36, 82), (24, 70), (29, 69), (24, 60), (24, 52),
                  (65, 53), (60, 50), (67, 43), (41, 32)]
        kinds = ['thunder_spark', 'thunder_ray', 'thunder_guard'] * 3
        spawns = [dict(kind=k, x=x, y=y) for k, (x, y) in zip(kinds, points)]
        spawns += [dict(kind='thunder_conductor', x=67, y=34),
                   dict(kind='thunder_bastion', x=41, y=23),
                   dict(kind='thunder_heart', x=70, y=18)]
        for n,(x,y) in enumerate(plan['rooms'][1:]):
            objects += [dict(kind='thunder_pylon',x=x-6,y=y-5,r=0,v=n%3),dict(kind='thunder_pylon',x=x+6,y=y-5,r=0,v=(n+1)%3)]
        objects += [dict(kind='thunder_altar',x=70,y=11,r=0,v=0),dict(kind='thunder_seal',x=48,y=78,r=0,v=0)]
    elif bloom:
        points=[(48,65),(43,68),(25,69),(71,68),(47,54),(42,48),(22,47),(73,46),(49,31)]
        kinds=['bloom_spore','bloom_moth','bloom_guard']*3
        spawns=[dict(kind=k,x=x,y=y) for k,(x,y) in zip(kinds,points)]
        spawns += [dict(kind='bloom_thornkeeper',x=22,y=38),dict(kind='bloom_mirror',x=73,y=36),dict(kind='bloom_heart',x=49,y=18)]
        for n,(x,y) in enumerate(plan['rooms'][1:]):
            objects += [dict(kind='bloom_lamp',x=x-6,y=y-5,r=0,v=n%3),dict(kind='bloom_lamp',x=x+6,y=y-5,r=0,v=(n+1)%3)]
        objects += [dict(kind='bloom_altar',x=49,y=11,r=0,v=0),dict(kind='bloom_seal',x=48,y=78,r=0,v=0)]
    elif solar:
        points=[(48,65),(42,65),(54,65),(25,53),(71,53),(42,40),(54,40),(27,32),(69,32)]
        kinds=['solar_emberling','solar_sunmoth','solar_crucible_guard']*3
        spawns=[dict(kind=k,x=x,y=y) for k,(x,y) in zip(kinds,points)]
        spawns += [dict(kind='solar_ashwarden',x=27,y=24),dict(kind='solar_heliomancer',x=69,y=24),dict(kind='solar_heart',x=48,y=17)]
        for n,(x,y) in enumerate(plan['rooms'][1:]):
            objects += [dict(kind='solar_brazier',x=x-6,y=y-5,r=0,v=n%3),dict(kind='solar_brazier',x=x+6,y=y-5,r=0,v=(n+1)%3)]
        objects += [dict(kind='solar_forge',x=48,y=11,r=0,v=0),dict(kind='solar_seal',x=48,y=78,r=0,v=0)]
    elif amber:
        points=[(48,68),(40,68),(56,68),(20,58),(76,58),(28,45),(68,45),(20,34),(76,34)]
        kinds=['amber_page','amber_moth','amber_sentinel']*3
        spawns=[dict(kind=k,x=x,y=y) for k,(x,y) in zip(kinds,points)]
        spawns += [dict(kind='amber_curator',x=20,y=22),dict(kind='amber_chronicle',x=76,y=22),dict(kind='amber_memory',x=48,y=22)]
        for n,(x,y) in enumerate(plan['rooms'][1:]):
            objects += [dict(kind='amber_lantern',x=x-6,y=y-5,r=0,v=n%3),dict(kind='amber_lantern',x=x+6,y=y-5,r=0,v=(n+1)%3)]
        objects += [dict(kind='amber_lectern',x=48,y=12,r=0,v=0),dict(kind='amber_seal',x=48,y=78,r=0,v=0)]
    elif solstice:
        points=[(32,72),(27,72),(69,72),(27,53),(69,53),(42,43),(54,43),(24,34),(72,34)]
        kinds=['solstice_flurry','solstice_owl','solstice_guard']*3
        spawns=[dict(kind=k,x=x,y=y) for k,(x,y) in zip(kinds,points)]
        spawns += [dict(kind='solstice_watcher',x=24,y=25),dict(kind='solstice_harbinger',x=72,y=25),dict(kind='solstice_heart',x=48,y=17)]
        for n,(x,y) in enumerate(plan['rooms'][1:]):
            objects += [dict(kind='solstice_lantern',x=x-6,y=y-5,r=0,v=n%3),dict(kind='solstice_lantern',x=x+6,y=y-5,r=0,v=(n+1)%3)]
        objects += [dict(kind='solstice_altar',x=48,y=11,r=0,v=0),dict(kind='solstice_seal',x=48,y=78,r=0,v=0)]
    else:
        spawns = []
    return dict(name=plan['name'], theme='eye_below' if eye else 'elder_hollow' if elder else
                'thousandfold' if pavilion else 'rain_crown' if rain else 'seed_vault' if seed else 'sunken_astrolabe' if astro else 'thunderheart_gate' if thunder else 'blooming_labyrinth' if bloom else 'solar_crucible' if solar else 'amber_archive' if amber else 'silent_solstice' if solstice else 'vault',
                tagline='A living lens beneath the stormglass sea' if eye else
                'The first oak remembers every spring' if elder else
                'A palace of silk, ink and living paper' if pavilion else
                'Jade rain falls through the forgotten temple' if rain else
                'Roots cradle a sleeping heart of amber and green' if seed else
                'Brass skies turn beneath blue desert sand' if astro else
                'Stormlight gathers around a heart of thunder' if thunder else
                'A living maze of glass petals and spring roots' if bloom else
                'An ember forge beneath the summer sun' if solar else
                'Living records guard the last memory of autumn' if amber else
                'A frozen court beneath the longest night' if solstice else
                'A sealed expedition beneath ' + plan['name'],
                sealedTemplate=plan['id'] not in OPEN_IDS, size=SIZE, levels=[plan['level']] * 2,
                min_level=plan['level'], players=5, copies=4,
                spawn=dict(x=sx, y=sy), rooms=rooms, paths=paths,
                objects=objects, slimes=spawns, npcs=[], quests=[], city=None,
                **({'final_boss': EYE_BOSSES[-1]} if eye else
                   {'final_boss': ELDER_BOSSES[-1]} if elder else
                   {'final_boss': PAVILION_BOSSES[-1]} if pavilion else
                   {'final_boss': RAIN_BOSSES[-1]} if rain else
                   {'final_boss': SEED_BOSSES[-1]} if seed else
                   {'final_boss': ASTRO_BOSSES[-1]} if astro else
                   {'final_boss': THUNDER_BOSSES[-1]} if thunder else
                   {'final_boss': BLOOM_BOSSES[-1]} if bloom else
                   {'final_boss': SOLAR_BOSSES[-1]} if solar else
                   {'final_boss': yearwheel_bosses('amber_archive')[-1]} if amber else
                   {'final_boss': yearwheel_bosses('silent_solstice')[-1]} if solstice else {}),
                portals=[dict(id=plan['id'] + '_return', name='Return to ' + plan['name'] + ' entrance',
                              x=sx - 6, y=sy, r=1.1, to=plan['parent'],
                              tx=plan['landing'][0], ty=plan['landing'][1])] +
                        ([dict(id='eye_below_exit', name='The Unblinking Way Home',
                               x=48, y=19, r=1.2, to=19, tx=105, ty=30,
                               after_clear=True, look='exit')] if eye else
                         [dict(id='elder_hollow_exit', name='The Crownway Home',
                               x=48, y=12, r=1.2, to=20, tx=106, ty=27,
                               after_clear=True, look='exit')] if elder else
                         [dict(id='thousandfold_exit', name='The Last Fold Home',
                               x=48, y=12, r=1.2, to=21, tx=113, ty=65,
                               after_clear=True, look='exit')] if pavilion else
                         [dict(id='rain_crown_exit', name='The Crownwater Way Home',
                               x=48, y=12, r=1.2, to=22, tx=120, ty=30,
                               after_clear=True, look='exit')] if rain else
                         [dict(id='seed_vault_exit', name='The Heartroot Way Home',
                               x=48, y=12, r=1.2, to=24, tx=48, ty=22,
                               after_clear=True, look='exit')] if seed else
                         [dict(id='sunken_astrolabe_exit', name='The Meridian Way Home',
                               x=48, y=12, r=1.2, to=25, tx=140, ty=17,
                               after_clear=True, look='exit')] if astro else
                         [dict(id='thunderheart_gate_exit',name='The Stormway Home',x=70,y=12,r=1.2,to=27,tx=151,ty=20,after_clear=True,look='exit')] if thunder else
                         [dict(id='blooming_labyrinth_exit',name='The Springway Home',x=49,y=12,r=1.2,to=28,tx=48,ty=235,after_clear=True,look='exit')] if bloom else
                         [dict(id='solar_crucible_exit',name='The Daybreak Way Home',x=48,y=12,r=1.2,to=28,tx=346,ty=248,after_clear=True,look='exit')] if solar else
                         [dict(id='amber_archive_exit',name='The Turning Page Home',x=48,y=17,r=1.2,to=28,tx=358,ty=151,after_clear=True,look='exit')] if amber else
                         [dict(id='silent_solstice_exit',name='The Dawnway Home',x=48,y=14,r=1.2,to=28,tx=47,ty=144,after_clear=True,look='exit')] if solstice else []))


def check(zone, plan, parent):
    sx, sy = plan['spawn']
    seen, blocked = fen.flood(zone, (sx, sy))
    for x, y in [*plan['rooms'], *((p['x'], p['y']) for p in zone['portals']),
                 *((s['x'], s['y']) for s in zone['slimes'])]:
        assert seen[int(y * 2), int(x * 2)], (zone['name'], 'unreachable', x, y)
    assert not blocked[int(sy * 2), int(sx * 2)]
    gate = zone['portals'][0]
    assert abs(sx - gate['x']) > gate['r'] + 2
    landing = plan['landing']
    seen_parent, blocked_parent = fen.flood(parent, (parent['spawn']['x'], parent['spawn']['y']))
    x, y = landing
    assert seen_parent[int(y * 2), int(x * 2)] and not blocked_parent[int(y * 2), int(x * 2)]
    assert min((np.hypot(x - s['x'], y - s['y']) for s in parent['slimes']), default=999) >= 8
    landmarks = ([parent['futureInstance']] if parent.get('futureInstance') else parent.get('futureInstances', []))
    landmark = next(mark for mark in landmarks if mark['name'] == plan['name'])
    assert np.hypot(x - landmark['x'], y - landmark['y']) >= 5
    assert landmark['status'] == ('open' if plan['id'] in OPEN_IDS else 'sealed')


def preview(zone, plan, directory):
    """A labeled plan for review and FileDrop; no raster art enters the game."""
    from PIL import Image, ImageDraw, ImageFont

    directory.mkdir(parents=True, exist_ok=True)
    scale, left, top = 7, 64, 112
    image = Image.new('RGB', (800, 900), '#101723')
    draw = ImageDraw.Draw(image)
    font_file = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title = ImageFont.truetype(font_file, 31)
    label = ImageFont.truetype(font_file, 17)
    small = ImageFont.truetype(font_file, 14)
    draw.text((64, 32), plan['name'], font=title, fill='#f7e9c1')
    state = 'OPEN PRIVATE INSTANCE' if plan['id'] in OPEN_IDS else 'SEALED FLOOR PLAN'
    draw.text((65, 75), f"LEVEL {plan['level']}  ·  FIVE PLAYERS  ·  {state}",
              font=label, fill='#aac3d3')
    draw.rectangle((left, top, left + SIZE * scale, top + SIZE * scale), fill='#17212b', outline='#648093', width=2)
    colors = {
        'eye_below': ('#397586', '#6ec1ce'),
        'elder_hollow': ('#56805b', '#b4d29a'),
        'thousandfold': ('#915f89', '#f5b7d8'),
        'rain_crown': ('#4d8273', '#8bd3b0'),
        'seed_vault': ('#756845', '#e9d290'),
        'sunken_astrolabe': ('#857043', '#efda9e'),
        'thunderheart_gate': ('#586d83', '#b5d1ed'),
        'blooming_labyrinth': ('#657d5f', '#e4b7d0'),
        'solar_crucible': ('#9f6444', '#f7d393'),
        'amber_archive': ('#886a48', '#f4cf86'),
        'silent_solstice': ('#5d7186', '#d9e5f3'),
    }
    floor, edge = colors[plan['id']]
    for x0, y0, x1, y1 in zone['rooms']:
        draw.rectangle((left + x0 * scale, top + y0 * scale,
                        left + x1 * scale, top + y1 * scale), fill=floor)
    for n, (x, y) in enumerate(plan['rooms']):
        cx, cy = left + x * scale, top + y * scale
        draw.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), fill='#17212b', outline=edge, width=3)
        draw.text((cx, cy), str(n + 1), font=small, fill='#ffffff', anchor='mm')
    for x, y, letter, color in [(*plan['spawn'], 'A', '#92f0bc'),
                                 (zone['portals'][0]['x'], zone['portals'][0]['y'], 'R', '#8ae8f6')]:
        cx, cy = left + x * scale, top + y * scale
        draw.ellipse((cx - 13, cy - 13, cx + 13, cy + 13), fill=color, outline='#15202a', width=2)
        draw.text((cx, cy), letter, font=small, fill='#10222a', anchor='mm')
    draw.text((64, 805), 'A  Safe party arrival     R  Return portal', font=label, fill='#e6edf0')
    draw.text((64, 834), f"Returns to public zone {plan['parent']} at {plan['landing']}.", font=small, fill='#aabfca')
    note = ('Entrance is open; this floor has encounters and unique scenery.'
            if plan['id'] in OPEN_IDS else
            'Entrance remains sealed; encounters are staged for a future release.'
            if plan['id'] == 'thunderheart_gate' else
            'Entrance remains sealed; encounters and scenery are future tasks.')
    draw.text((64, 857), note, font=small, fill='#aabfca')
    filename = 'Valhalla_' + '_'.join(plan['name'].replace('The ', '').split()) + ('_Open_Map.png' if plan['id'] in OPEN_IDS else '_Sealed_Map.png')
    path = directory / filename
    image.save(path, optimize=True)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previews', type=Path, help='Render labeled map images in this directory')
    args = parser.parse_args()
    world = json.loads(MAP.read_text())
    assert len(world['zones']) >= FIRST - 1
    existing = world['zones'][FIRST - 1:]
    if existing:
        assert [z.get('name') for z in existing[:min(len(existing), len(PLANS))]] == [p['name'] for p in PLANS[:len(existing)]], \
            'The reserved dungeon zone IDs have changed'
        existing = existing[len(PLANS):]
    zones = [build(p) for p in PLANS]
    for zone, plan in zip(zones, PLANS):
        check(zone, plan, world['zones'][plan['parent'] - 1])
    world['zones'] = world['zones'][:FIRST - 1] + zones + existing
    MAP.write_text(json.dumps(world, indent=2) + '\n')
    if args.previews:
        for zone, plan in zip(zones, PLANS):
            print(preview(zone, plan, args.previews))
    print(f'{sum(not z["sealedTemplate"] for z in zones)} open and {sum(z["sealedTemplate"] for z in zones)} sealed private maps at zones 29–39:',
          ', '.join(f"{z['name']} ({len(z['objects'])} obstacles)" for z in zones))


if __name__ == '__main__':
    main()
