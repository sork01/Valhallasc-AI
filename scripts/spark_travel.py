"""Persistent Spark Travel masters. Called by zone generators before writing map.txt."""
import json
from pathlib import Path

# The glacier connects to both Lanternmere and Skaldholm: neither branch is a stop on the other.
STOPS = [
    ('Alderhaven', 'travel_alderhaven', 36, 85, ['travel_cinderwatch']),
    ('Cinderwatch Camp', 'travel_cinderwatch', 48, 83.5, ['travel_alderhaven', 'travel_rimeward']),
    ('Rimeward Camp', 'travel_rimeward', 64, 115.5, ['travel_cinderwatch', 'travel_lanternmere', 'travel_skaldholm']),
    ('Lanternmere', 'travel_lanternmere', 64, 20.5, ['travel_rimeward']),
    ('Skaldholm', 'travel_skaldholm', 80, 128, ['travel_rimeward', 'travel_hollowmoot']),
    # The Wyrdwood has two stops in one zone: the flight between them crosses the river in a straight line.
    ('Hollowmoot', 'travel_hollowmoot', 23, 153, ['travel_skaldholm', 'travel_skuldwatch']),
    ('Skuldwatch', 'travel_skuldwatch', 88, 89, ['travel_hollowmoot', 'travel_perch']),
    # Bifrost Reach: the flight from Skuldwatch crosses the Highmoor to the Stormrift and climbs the rift.
    ("Heimdall's Perch", 'travel_perch', 86, 135, ['travel_skuldwatch', 'travel_keelhaven']),
    # Ran's Deep: the flight from the Perch dives off the Eyrie's storm and down the Maelstrom.
    ('Keelhaven', 'travel_keelhaven', 86, 154, ['travel_perch', 'travel_nacrehold']),
    ('Nacrehold', 'travel_nacrehold', 100, 164, ['travel_keelhaven', 'travel_astralhollow']),
    ('Astralhollow', 'travel_astralhollow', 76, 119, ['travel_nacrehold', 'travel_last_shade']),
    ('The Last Shade', 'travel_last_shade', 76, 119, ['travel_astralhollow', 'travel_stillpoint']),
    ('The Stillpoint', 'travel_stillpoint', 44, 119, ['travel_last_shade', 'travel_lamplight']),
    ('Lamplight Refuge', 'travel_lamplight', 44, 119, ['travel_stillpoint', 'travel_asterion']),
    ('Asterion', 'travel_asterion', 90, 114, ['travel_lamplight', 'travel_breakwater']),
    ('Breakwater Camp', 'travel_breakwater', 42, 119, ['travel_asterion', 'travel_millbridge']),
    ('Millbridge', 'travel_millbridge', 46, 118, ['travel_breakwater', 'travel_jubilee']),
    ('Jubilee Crossroads', 'travel_jubilee', 42, 85, ['travel_millbridge', 'travel_banyan']),
    ('Banyan Landing', 'travel_banyan', 36, 124, ['travel_jubilee', 'travel_veyrroot']),
    ('Veyrroot Canopy', 'travel_veyrroot', 82, 96, ['travel_banyan', 'travel_azure_wells']),
    ('Azure Wells', 'travel_azure_wells', 44, 135, ['travel_veyrroot', 'travel_frostwake']),
    ('Frostwake Station', 'travel_frostwake', 46, 143, ['travel_azure_wells', 'travel_boulderwatch']),
    ('Boulderwatch', 'travel_boulderwatch', 47, 153, ['travel_frostwake', 'travel_springmere']),
    ('Springmere', 'travel_springmere', 84, 326, ['travel_boulderwatch', 'travel_solhaven', 'travel_rimehold']),
    ('Solhaven', 'travel_solhaven', 328, 318, ['travel_springmere', 'travel_harvestwatch']),
    ('Harvestwatch', 'travel_harvestwatch', 329, 80, ['travel_solhaven', 'travel_rimehold']),
    ('Rimehold', 'travel_rimehold', 86, 80, ['travel_harvestwatch', 'travel_springmere']),
]


def ensure(world):
    for area in [world] + world.get('zones', []):
        # A zone may have several hubs: `city` is the first, `camps` the rest.
        for city in [c for c in [area.get('city')] + area.get('camps', []) if c]:
            for name, id_, x, y, links in STOPS:
                if city['name'] != name:
                    continue
                master = dict(id=id_, name='Travel Master', role='Spark Travel', x=x, y=y,
                              color='#74d7d0', travelStop=name, travelLinks=links,
                              look=dict(hair='#e4edf4', skin='#edc5a1', style='long', hat='hood', hatColor='#328e97'),
                              dialogue='This stop is now yours to visit by Spark Travel. Become a sparkling spark and fly for 20 gold per leg, at three times walking speed. Talk to every travel master along a route before you can use it.',
                              offers=[], buys=False)
                if name == 'Nacrehold':
                    master.update(name='Travel Master Auralis', role='Mermaid · Spark Travel')
                    master['look'].update(species='merfolk', female=True, tail='#81d6cc', skin='#abd4e4')
                if name == 'Millbridge':
                    master.update(name='Travel Master Jori', role='Millbridge courier · Spark Travel', art='sun_travel')
                if name == 'Jubilee Crossroads':
                    master.update(name='Travel Master Luma', role='Festival courier · Spark Travel', art='ribbon_travel')
                if name == 'Banyan Landing':
                    master.update(name='Travel Master Suri', role='Canopy courier · Spark Travel', art='tangle_travel')
                if name == 'Veyrroot Canopy':
                    master.update(name='Travel Master Lio', role='Branchwing courier · Spark Travel', art='heart_travel')
                if name == 'Azure Wells':
                    master.update(name='Travel Master Nadir', role='Caravan courier · Spark Travel', art='lapis_travel')
                if name == 'Frostwake Station':
                    master.update(name='Travel Master Eira', role='Aurora courier · Spark Travel', art='frostwake_travel')
                if name == 'Boulderwatch':
                    master.update(name='Travel Master Asta', role='High pass courier · Spark Travel', art='cairn_travel')
                for stop, person, season in [('Springmere','Linn','sp'),('Solhaven','Taro','su'),('Harvestwatch','Maren','au'),('Rimehold','Eirik','wi')]:
                    if name == stop:
                        master.update(name='Travel Master '+person, role='Yearwheel courier · Spark Travel', art='year_'+season+'_travel')
                folk = area.setdefault('npcs', [])
                old = next((i for i, n in enumerate(folk) if n['id'] == id_), None)
                if old is None:
                    folk.append(master)
                else:
                    folk[old] = master


if __name__ == '__main__':
    path = Path(__file__).resolve().parents[1] / 'world/map.txt'
    world = json.loads(path.read_text())
    ensure(world)
    path.write_text(json.dumps(world, indent=2) + '\n')
