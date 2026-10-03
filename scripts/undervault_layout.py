"""The plan of the Undervault, the five-player dungeon under Skaldholm (zone 5): rooms, packs, bosses and the doors.

Pure data, shared by generate_undervault.py (which writes the zone) and generate_skaldholm.py (which writes the stairs
beside the Meeting Stone that lead here). Coordinates are tiles on a 128x128 map, y growing southwards.

The route is one long snake, so a party meets everything in order: Stair Hall, Barracks (trash), the Gatewarden's Court
(boss 1), the Ossuary (trash, archers and acolytes), the Choir Chapel (boss 2), the Cistern (trash), the Colossus Forge
(boss 3) and the Throne of the Hollow King (boss 4). A portal out opens in the throne room when the king falls.
"""
NAME = 'The Undervault'
SIZE = 128
COPIES = 4                                   # private copies of the dungeon: four parties can be inside at once
PLAYERS = 5
LEVEL = 20

STAIRS_DOWN = (104.4, 122.0)                 # in Skaldholm, beside the Meeting Stone court
STAIRS_RETURN = (104.2, 125.4)               # where the dungeon sets you down in Skaldholm
ARRIVAL = (15.0, 111.0)                      # at the foot of the stairs
STAIRS_UP = (9.6, 111.0)                     # the stairs back up: they climb west into the hall's wall
EXIT_PORTAL = (115.0, 29.0)                  # opens when the Hollow King falls

ROOMS = {
    'hall0': (6, 100, 32, 122),              # Stair Hall
    'c1': (32, 108, 48, 114),
    'barracks': (48, 94, 80, 124),
    'c2': (80, 107, 90, 113),
    'court': (90, 90, 122, 124),             # Gatewarden's Court
    'c3': (102, 66, 110, 90),
    'ossuary': (80, 44, 122, 66),
    'c4': (60, 52, 80, 58),
    'chapel': (22, 36, 60, 72),              # Choir Chapel
    'c5': (38, 22, 46, 36),
    'cistern': (8, 4, 58, 22),
    'c6': (58, 10, 68, 16),
    'forge': (68, 4, 100, 36),               # Colossus Forge
    'c7': (100, 16, 106, 22),
    'throne': (106, 4, 124, 40),             # Throne of the Hollow King
}
HALLS = ['hall0', 'barracks', 'court', 'ossuary', 'chapel', 'cistern', 'forge', 'throne']

# Packs: a centre and (kind, dx, dy) members. Archers and acolytes stand behind the thralls (larger dy / dx away
# from the way in), so the front line meets the melee first and the shooters open up from behind.
PACKS = [
    ('barracks', (57, 101), [('thrall', -1.8, -1.2), ('thrall', 1.8, -1.2), ('thrall', 0, 1.6), ('archer', -2.8, 4.2)]),
    ('barracks', (72, 108), [('thrall', -1.8, -1.2), ('thrall', 1.8, -1.2), ('thrall', 0, 1.6), ('archer', 2.8, 4.2)]),
    ('barracks', (60, 117), [('thrall', -1.8, -1.2), ('thrall', 1.8, -1.2), ('archer', -2.2, 3.4), ('archer', 2.2, 3.4)]),
    ('ossuary', (90, 55), [('thrall', 0, 2), ('thrall', 3.2, 0.6), ('acolyte', -1.8, -2.4), ('acolyte', 1.8, -3)]),
    ('ossuary', (104, 52), [('thrall', -1.8, 1.8), ('archer', -3.2, -1.8), ('archer', 3.2, -1.8), ('acolyte', 0, -3.6)]),
    ('ossuary', (116, 58), [('thrall', -2, 0), ('thrall', 0.6, 2.2), ('archer', 2.4, -1.6), ('acolyte', 0.4, -3.2)]),
    ('c4', (70, 55), [('thrall', 0, -1), ('thrall', 0, 1)]),
    ('chapel', (46, 61), [('acolyte', -1.8, 0), ('acolyte', 1.8, 0), ('archer', 0, -2.6)]),
    ('cistern', (16, 12), [('thrall', 1.8, 0), ('thrall', 1.8, 3.2), ('archer', -1.6, 0.8), ('acolyte', -1.6, 3.2)]),
    ('cistern', (30, 14), [('thrall', 0, 2), ('thrall', 3.2, 0.6), ('acolyte', -1.8, -2.4), ('archer', 1.8, -3)]),
    ('cistern', (49, 9), [('thrall', -1.4, 2), ('thrall', 1.8, 2.4), ('archer', -2.8, -1.6), ('acolyte', 2.8, -1.6)]),
    ('c6', (63, 13), [('thrall', 0, -1), ('thrall', 0, 1)]),
    ('forge', (76, 28), [('thrall', 0, -1.6), ('thrall', 2.6, 0.8), ('archer', -2.2, 2.6)]),
]
BOSSES = [
    ('court', 'gatewarden', (112, 104)),
    ('chapel', 'choir', (30, 54)),
    ('forge', 'colossus', (88, 20)),
    ('throne', 'hollowking', (116, 15)),
]
