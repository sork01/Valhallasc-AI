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
    ('Keelhaven', 'travel_keelhaven', 86, 154, ['travel_perch']),
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
