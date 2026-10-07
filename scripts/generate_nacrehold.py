#!/usr/bin/env python3
"""Nacrehold, a safe 192-tile merfolk city (zone 9). Rebuild, then sync-world and rebuild Rust.

The Drowned Cathedral is a sealed entrance reserved for the NEXT five-player instance,
not a portal into an unfinished dungeon. --plot writes a planning image. All people,
house doors, places, gates and swimmers are checked against the real collision grid.
"""
import argparse
import json
import math
import random
from quest_gear_rewards import add_reward
from pathlib import Path

import generate_gloamfen as fen
import mercenary_offers as merc
import spark_travel
from skaldholm_content import HEALER_OFFERS, GUILD_OFFERS, SMITH_OFFERS

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'world/map.txt'
NAME, ZONE, SIZE = 'Nacrehold', 9, 192
ARRIVAL, GATE, DEEP_GATE, DEEP_RETURN = (96, 171), (96, 178), (108, 170), (108, 165)
STONE = (89, 31)
XP = json.loads((ROOT / 'world/levels.txt').read_text())
COLORS = ['#e9acc8', '#81d6cc', '#b2b4ef', '#eccb89', '#8dbedc', '#ecb395']


def obj(kind, x, y, r=.4, **kw):
    return dict(kind=kind, x=x, y=y, r=r, v=0, **kw)


def npc(id_, name, role, x, y, female=False, offers=None, buys=False, dialogue='', **kw):
    i = sum(map(ord, id_))
    return dict(id='nacre_' + id_, name=name, role=role, x=x, y=y,
                color=COLORS[i % 6], offers=offers or [], buys=buys,
                look=dict(species='merfolk', female=female, tail=COLORS[i % 6],
                          skin=['#a4dbc9', '#abd4e4', '#cdbfea'][i % 3],
                          hair=['#243e62', '#ebdbbd', '#b96289', '#43827a'][i % 4],
                          style='long' if female else 'short'), dialogue=dialogue, **kw)


def objective(kind, target, label, count=1):
    return dict(kind=kind, target=target, label=label, count=count)


def quest(id_, title, giver, description, objectives, level=35, gold=100, requires='welcome', **kw):
    return add_reward(dict(id='nacre_' + id_, title=title, npc='nacre_' + giver,
                description=description, objectives=objectives, level=level,
                rewardXp=XP[level - 1] // 10, rewardGold=gold,
                requires='nacre_' + requires if requires else None, repeatable=False, **kw))


def content():
    people = [
        npc('envoy', 'Lyris Pearlvoice', 'Mermaid · City envoy', 92, 166, True,
            dialogue='Welcome, air-breather. The tide grants you breath beneath these waters. Nacrehold is a city, not a wreck: six neighbourhoods, a hundred and twenty homes, and a thousand stories. Meet our people; let the sea teach you to walk slowly.'),
        npc('healer', 'Nerissa Stillwater', 'Mermaid · Tide healer', 144, 36, True, HEALER_OFFERS,
            dialogue='Rest beneath the pearl lanterns. My blessing is free; my potions are prepared for your level. Nothing hunts you inside Nacrehold.'),
        npc('trader', 'Orin Shellweaver', 'Merman · Market keeper', 102, 130, False, GUILD_OFFERS, True,
            'We trade in memories as well as shells. I buy spare equipment and materials, and sell hot stew and satchels. The kettle is sealed. Do not ask how.'),
        npc('smith', 'Thalos Reefhammer', 'Merman · Coral smith', 90, 130, False, SMITH_OFFERS,
            dialogue='Coral grows slowly; a good blade lasts longer. Bring your starter gear for a free fitting. My hammer rings softly out of respect for the sleeping reef.'),
        npc('archivist', 'Vaela Inkfin', 'Mermaid · Keeper of tides', 140, 64, True,
            dialogue='We carved our histories on mother-of-pearl. The Drowned Cathedral once kept the Heart of the Tide. Now its bells ring without hands. Its doors are sealed; read our memorials before you ask why.'),
        npc('gardener', 'Pelar Kelpbraid', 'Merman · Reef gardener', 42, 36,
            dialogue='The Lantern Gardens are tended, never harvested. A reef is a neighbourhood too: the coral builds homes, the little fish pay rent in gossip.'),
        npc('singer', 'Syllene Softsong', 'Mermaid · Conch singer', 104, 92, True,
            dialogue='Our fountain does not splash. It remembers the surface, and hums. Walk the six districts and bring me their voices; the city needs a new lullaby.'),
        npc('warden', 'Captain Namar Deepwatch', 'Merman · Cathedral warden', 96, 31,
            dialogue='Beyond this sealed arch lies the Drowned Cathedral, the next level-40 five-player instance: flooded cloisters, a choir bound to a stolen bell, and the drowned hierophant who guards the Heart of the Tide. Gather at the Meeting Stone. The seal will open in a future expedition.'),
        npc('innkeeper', 'Maera Warmcurrent', 'Mermaid · The Sleeping Nautilus', 52, 136, True,
            [dict(id='rest', label='Rest in the warm current · restores HP', cost=5, heal=10000)],
            dialogue='The nautilus never hurries. Neither should you. I have a warm current and a bed of soft sea grass, if you need to rest.'),
        npc('lamplighter', 'Ilo Glowfin', 'Merman · Pearl lamplighter', 156, 112,
            dialogue='The lamps are living pearls; I sing them awake. A little siren pearl helps a tired lamp remember its light.'),
        npc('stone', 'The Nacre Meeting Stone', 'Gather your party', STONE[0] + 1.7, STONE[1] + 1.7,
            offers=merc.offers(open_=True), dialogue='The sea-blue runes offer companions of every calling for 250 gold each, up to five in your party. The sealed Drowned Cathedral stands beside you. Its expedition has not opened yet.', art='stone'),
    ]
    # Quiet swimmers on the clear street grid; quest givers and shopkeepers stay still.
    names = ['Aren', 'Miriel', 'Kovar', 'Oceane', 'Tethis', 'Luma', 'Soren', 'Elyra', 'Brin', 'Coralie', 'Damar', 'Iselle', 'Kelp', 'Pearl', 'Finn', 'Nori', 'Reef', 'Mira']
    for i, name in enumerate(names):
        x = [48, 72, 120, 144, 168, 24][i % 6]
        y = [72, 120, 144][i // 6]
        route = [[x, y], [x + 24, y], [x + 24, y + 24], [x, y + 24]]
        # The eastmost and westmost walks go along vertical boulevards instead.
        if x == 168 or (x == 72 and y == 72):
            route = [[x, y], [x, y + 20]]
        people.append(npc('resident_' + str(i), name, 'Mermaid · Resident' if i % 2 else 'Merman · Resident', *route[0], bool(i % 2),
                          dialogue=['The roof of my home is older than my grandmother.', 'Surface stars are beautiful. We have lanternfish.', 'Listen: the whole reef is breathing.', 'The Cathedral bells sound different lately.'][i % 4],
                          route=route, speed=1.25 + (i % 3) * .15, pause=3, phase=i * 7.3))
    places = [dict(id='nacre_' + id_, name=name, x=x, y=y, r=3) for id_, name, x, y in [
        ('garden', 'Lantern Gardens', 48, 28), ('sanctuary', 'Palace of the Gentle Tide', 144, 32),
        ('archive', 'The Pearl Archive', 144, 72), ('memorial', 'Memorial of the Lost Choir', 120, 36),
        ('cathedral', 'The Sealed Drowned Cathedral', 96, 36),
        ('rose', 'Rosecoral Quarter', 48, 72), ('azure', 'Azure Shells', 144, 72),
        ('violet', 'Violet Reach', 48, 120), ('gold', 'Gilded Shoals', 144, 120),
        ('mint', 'Jade Current', 48, 168), ('amber', 'Amberwake', 144, 168)]]
    talk = lambda id_, label: objective('talk', 'nacre_' + id_, 'Speak to ' + label)
    visit = lambda id_, label: objective('visit', 'nacre_' + id_, label)
    bring = lambda id_, label, n: objective('bring', id_, label, n)
    quests = [
        quest('welcome', 'A City Beneath the Waves', 'envoy', 'Meet the healer, market keeper, gardener and Cathedral warden, then return to Lyris.',
              [talk('healer', 'Nerissa'), talk('trader', 'Orin'), talk('gardener', 'Pelar'), talk('warden', 'Captain Namar')], requires=None),
        quest('gardens', 'Where the Lanternfish Sleep', 'gardener', 'Visit the Lantern Gardens and the gentle tide sanctuary. Take only memories.',
              [visit('garden', 'Visit the Lantern Gardens'), visit('sanctuary', 'Visit the tide sanctuary')]),
        quest('districts', 'Six Verses for the Sea', 'singer', 'Learn the rhythm of all six residential districts for Syllene’s lullaby.',
              [visit(k, 'Visit ' + label) for k, label in [('rose', 'Rosecoral Quarter'), ('azure', 'Azure Shells'), ('violet', 'Violet Reach'), ('gold', 'Gilded Shoals'), ('mint', 'Jade Current'), ('amber', 'Amberwake')]], gold=150),
        quest('history', 'Names the Sea Has Kept', 'archivist', 'Read the Pearl Archive and stand beside the memorial of the choir that never returned.',
              [visit('archive', 'Read the Pearl Archive'), visit('memorial', 'Visit the Lost Choir memorial')], level=38),
        quest('cathedral', 'The Bell Behind the Seal', 'warden', 'Study the sealed Cathedral, speak to its archivist, and gather beside the Meeting Stone. This is preparation; the expedition itself is still sealed.',
              [visit('cathedral', 'Inspect the sealed Cathedral'), talk('archivist', 'Vaela'), talk('stone', 'the Nacre Meeting Stone')], level=40, gold=200, requires='history'),
        quest('lamps', 'A Pearl for Every Window', 'lamplighter', 'Bring three Siren Pearls from Ran’s Deep to refresh the city’s lamps. No creature is hunted inside the city.',
              [bring('siren_pearl', 'Bring Siren Pearls', 3)], level=38, gold=700),
        quest('smithwork', 'Coral That Remembers Iron', 'smith', 'Bring Shellback Plates from Ran’s Deep for Thalos’s patient craft.',
              [bring('shellback_plate', 'Bring Shellback Plates', 3)], level=39, gold=700),
        quest('letters', 'A Letter in a Shell', 'innkeeper', 'Carry Maera’s greetings to the city envoy and its gardener, then return for a warm welcome.',
              [talk('envoy', 'Lyris'), talk('gardener', 'Pelar')], gold=80),
        quest('supplies', 'The Tide’s Standing Order', 'trader', 'Orin always needs Drowned Coins from Ran’s Deep. This order can be repeated.',
              [bring('drowned_coin', 'Bring Drowned Coins', 4)], gold=800),
    ]
    quests[-1]['repeatable'] = True
    return people, places, quests


def build():
    rng = random.Random(20261020)
    people, places, quests = content()
    roads = [dict(x0=x - (3 if x == 96 else 2.4), x1=x + (3 if x == 96 else 2.4), y0=12, y1=180, t=2 if x == 96 else 1) for x in [24, 48, 72, 96, 120, 144, 168]]
    roads += [dict(x0=16, x1=176, y0=y - 2.4, y1=y + 2.4, t=1) for y in [48, 72, 96, 120, 144, 168]]
    roads += [dict(x=96, y=96, r=18, t=2), dict(x0=76, x1=124, y0=32, y1=41, t=2), dict(x0=24, x1=168, y0=25, y1=33, t=1)]
    objects = [obj('nacrefountain', 96, 96, 2.2), obj('nacrecathedral', 96, 24, width=7, depth=6),
               obj('nacrepalace', 144, 24, width=7, depth=5), obj('nacrearchive', 144, 59, width=5, depth=4),
               obj('nacregarden', 40, 24, 2.2), obj('nacrememorial', 120, 28, 1.2),
               obj('meetingstone', *STONE, 1.7), obj('nacreinn', 52, 130, width=5, depth=4)]
    for x, color in [(90, '#b2b4ef'), (102, '#eccb89')]:
        objects.append(obj('nacrestall', x, 126, width=2.5, depth=1.8, color=color))
    def reserved(x, y):
        return math.hypot(x - 96, y - 96) < 21 or any(math.hypot(x - n['x'], y - n['y']) < 4 for n in people if not n.get('route')) or any(abs(x - o['x']) < o.get('width', o['r'] * 2) / 2 + 3 and abs(y - o['y']) < o.get('depth', o['r'] * 2) / 2 + 3 for o in objects)
    lots = [(x, y) for y in [41, 55, 64, 79, 88, 103, 112, 127, 136, 151, 160, 175] for x in [32, 40, 56, 64, 80, 88, 104, 112, 128, 136, 152, 160]]
    houses = []
    for x, y in lots:
        if len(houses) == 120 or reserved(x, y):
            continue
        district = (0 if y < 96 else 2 if y < 144 else 4) + (x > 96)
        label = ['Rosecoral', 'Azure Shells', 'Violet Reach', 'Gilded Shoals', 'Jade Current', 'Amberwake'][district]
        houses.append(obj('nacrehouse', x, y, width=3.4, depth=2.6, color=COLORS[district], v_=rng.randrange(4), label=f'{label} {len(houses) + 1}', sign='live'))
    assert len(houses) == 120, len(houses)
    objects += houses
    # Pearl lamps beside street corners, living gardens in the verges. Keep roads and every doorway clear.
    for y in [48, 72, 96, 120, 144, 168]:
        for x in [24, 48, 72, 120, 144, 168]:
            if math.hypot(x - 96, y - 96) < 22:
                continue
            objects.append(obj('pearllamp', x + 3.4, y - 3.4, .18, v_=int(x + y) % 3))
    for x, y in [(30, 18), (38, 16), (48, 18), (54, 22), (32, 34), (54, 34), (132, 18), (158, 18), (134, 36), (158, 36)]:
        objects.append(obj('coral', x, y, .55, v_=rng.randrange(4)))
    for x in [12, 180]:
        for y in range(16, 180, 8):
            objects.append(obj('kelp' if y % 16 else 'coral', x, y, .4, v_=rng.randrange(4)))
    for o in objects:
        o['v'] = o.pop('v_', o['v'])
    return dict(name=NAME, theme='nacre', tagline='A hundred and twenty shell-roofed homes beneath a quiet tide', size=SIZE,
                spawn=dict(x=ARRIVAL[0], y=ARRIVAL[1]), city=dict(name=NAME, x0=8, x1=184, y0=8, y1=184, plaza=dict(x=96, y=96), radius=18, entry=dict(x=96, y=168)),
                roads=roads, paths=[], objects=objects, slimes=[], npcs=people, places=places, quests=quests,
                futureInstance=dict(name='The Drowned Cathedral', level=40, players=5, status='sealed', x=96, y=24,
                                    story='Recover the Heart of the Tide from the drowned hierophant and free the bound choir.'),
                portals=[dict(id='nacre_deep_gate', name='The Keelhaven Tideway', x=GATE[0], y=GATE[1], r=1.1, to=8, tx=DEEP_RETURN[0], ty=DEEP_RETURN[1])])


def open_tideway(deep):
    deep['portals'] = [p for p in deep['portals'] if p['id'] != 'nacre_gate'] + [dict(id='nacre_gate', name='The Nacrehold Tideway', x=DEEP_GATE[0], y=DEEP_GATE[1], r=1.1, to=ZONE, tx=ARRIVAL[0], ty=ARRIVAL[1])]
    # Remove ONLY decoration clipping the tideway and its approach, deterministically on every rebuild.
    deep['objects'] = [o for o in deep['objects'] if not (o['kind'] in ['coral', 'kelp', 'deeprock', 'clam', 'anemone'] and any(math.hypot(o['x'] - x, o['y'] - y) < o['r'] + 2 for x, y in [DEEP_GATE, DEEP_RETURN]))]


def check(zone):
    seen, _ = fen.flood(zone, ARRIVAL)
    probes = [(n['id'], n['x'], n['y']) for n in zone['npcs']]
    probes += [(p['id'], p['x'], p['y']) for p in zone['places']]
    probes += [(o['label'], o['x'], o['y'] + o['depth'] / 2 + .8) for o in zone['objects'] if o['kind'] == 'nacrehouse']
    probes += [('return gate', *GATE)]
    missing = [name for name, x, y in probes if not seen[int(y / .5), int(x / .5)]]
    for n in zone['npcs']:
        route = n.get('route', [])
        for a, b in zip(route, route[1:] + route[:1]):
            steps = max(1, int(math.dist(a, b) * 4))
            for i in range(steps + 1):
                x, y = (a[j] + (b[j] - a[j]) * i / steps for j in [0, 1])
                if not seen[int(y / .5), int(x / .5)]:
                    missing.append(n['id'] + ' route')
                    break
    assert not missing, missing


def plot(zone, path):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (768, 768), '#194d5f')
    d = ImageDraw.Draw(im)
    for r in zone['roads']:
        if 'x0' in r:
            d.rectangle([r['x0'] * 4, r['y0'] * 4, r['x1'] * 4, r['y1'] * 4], fill='#a5d9d5')
        else:
            d.ellipse([(r['x'] - r['r']) * 4, (r['y'] - r['r']) * 4, (r['x'] + r['r']) * 4, (r['y'] + r['r']) * 4], fill='#bde4df')
    for o in zone['objects']:
        w, h = o.get('width', o['r'] * 2), o.get('depth', o['r'] * 2)
        d.rectangle([(o['x'] - w / 2) * 4, (o['y'] - h / 2) * 4, (o['x'] + w / 2) * 4, (o['y'] + h / 2) * 4], fill=o.get('color', '#6380af'))
    for n in zone['npcs']:
        x, y = n['x'] * 4, n['y'] * 4
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill='#ffe698')
    im.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot')
    args = parser.parse_args()
    zone = build()
    world = json.loads(PATH.read_text())
    spark_travel.ensure(dict(zones=[zone]))
    check(zone)
    if args.plot:
        plot(zone, args.plot)
    assert world['zones'][7]['name'] == "Rán's Deep"
    later = world['zones'][9:]
    world['zones'] = world['zones'][:8] + [zone] + later
    from generate_cathedral import open_cathedral
    open_cathedral(zone, world)
    open_tideway(world['zones'][7])
    spark_travel.ensure(world)
    PATH.write_text(json.dumps(world, indent=2) + '\n')
    print(f'Wrote {NAME}: 120 homes, {len(zone["npcs"])} people, {len(zone["quests"])} quests; every door and route reachable.')


if __name__ == '__main__':
    main()
