"""The plan of the Wyrdwood (zone 6, levels 20-30): pure geometry and constants shared by generate_wyrdwood.py (which
writes the zone) and generate_skaldholm.py (which writes the East Gate that leads here).

192x192 tiles, y growing southwards. You step in at the west edge, into the root-town Hollowmoot (south-west); the
south forest holds the boars (west), the gallows hill with its crows (south-east) and the Oakhorn's grove; the river
Skuld cuts the whole map from west to east at y ~ 108 and the only dry crossing is the Troll Bridge in the middle,
which the trolls haunt. North of the bridge stands the hill-fort Stormwatch, and above it three terraces climb to the
Highmoor: weavers around the Norn Stones, storm rams along the ridge and, in the summit court, the giant Hrungnir.
"""
import math

NAME = 'Wyrdwood'
SIZE = 192
LEVELS = [20, 30]

# --- gates -------------------------------------------------------------------------------------------------------------
GATE = (4.5, 150.0)                         # the way back to Skaldholm (west edge)
ARRIVAL = (9.5, 150.0)                      # where the East Gate of Skaldholm drops you
SKALD_GATE = (152.0, 76.0)                  # the portal outside Skaldholm's east wall (zone 4)
SKALD_ARRIVAL = (147.6, 76.0)               # where the Wyrdwood sets you down in Skaldholm

# --- hubs --------------------------------------------------------------------------------------------------------------
HOLLOW = dict(name='Hollowmoot', x0=9, x1=57, y0=131, y1=170, plaza=dict(x=33, y=150), radius=3.5, entry=dict(x=33, y=156))
STORM = dict(name='Stormwatch', x0=67, x1=125, y0=75, y1=97, plaza=dict(x=96, y=86), radius=3.5, entry=dict(x=96, y=91))
STORM_WALL = dict(x0=66, x1=126, y0=74, y1=98)       # the fort's rampart (the gates are in the middle of the north and south sides)
GATE_HALF = 4.0                                      # half width of both fort gates

# --- the river and its bridge ------------------------------------------------------------------------------------------
BRIDGE_X = 96.0
WATER_R, WATER_STEP = 2.3, 2.5


def river_y(x):
    """The centre line of the Skuld: a gentle meander, y = 108 +- 4."""
    return 108 + 2.6 * math.sin(x / 19.) + 1.6 * math.sin(x / 7.3 + 1.)


BRIDGE = dict(x0=BRIDGE_X, y0=river_y(BRIDGE_X) - 9.5, x1=BRIDGE_X, y1=river_y(BRIDGE_X) + 9.5, w=5.0)

# --- the heights -------------------------------------------------------------------------------------------------------
R_A_Y, R_A_GAP = 44.0, (150.0, 44.0)         # first ridge: the way from the weavers' terrace to the rams' is far in the east
R_B_Y, R_B_GAP = 22.0, (42.0, 22.0)          # second ridge: the way up to the summit court is far in the west
CRAG_R, CRAG_STEP = 1.5, 1.9
RIDGE_GAP_HALF = 4.6

# --- named places a `visit` objective can name -------------------------------------------------------------------------
PLACES = [
    dict(id='wyrd_glade', name='Moonpetal Glade', x=44.0, y=184.0, r=4.5),
    dict(id='wyrd_gallows_rock', name='Gallows Rock', x=160.0, y=172.0, r=4.5),
    dict(id='wyrd_beacon_west', name='the West Beacon', x=26.0, y=58.0, r=3.8),
    dict(id='wyrd_beacon_ridge', name='the Ridge Beacon', x=150.0, y=36.0, r=3.8),
    dict(id='wyrd_beacon_storm', name='the Storm Beacon', x=46.0, y=31.0, r=3.8),
    dict(id='wyrd_norn_stones', name='the Norn Stones', x=96.0, y=57.0, r=6.0),
]
BEACONS = ['wyrd_beacon_west', 'wyrd_beacon_ridge', 'wyrd_beacon_storm']

# --- the elites --------------------------------------------------------------------------------------------------------
OAKHORN = (158.0, 140.0)                     # the grove, south-east of the bridge
HRUNGNIR = (104.0, 11.0)                     # the summit court

# --- the escort --------------------------------------------------------------------------------------------------------
EYDIS_START = (176.0, 174.0)                 # the ruined mill on the gallows hill
EYDIS_SPEED = 2.5                            # tiles per second: about half a hero's pace
EYDIS_ROUTE = [(176.0, 174.0), (181.0, 150.0), (181.0, 128.0), (150.0, 121.5), (112.0, 119.0), (96.0, 117.0), (96.0, 99.0), (96.0, 91.0)]
# the ambushers wake when the walk passes the trigger (point, radius)
AMBUSHES = [dict(at=(181.0, 150.0), r=11.0, tag='crow', kind='crow', n=3, near=(181.0, 150.0)),
            dict(at=(104.0, 119.0), r=11.0, tag='troll', kind='troll', n=2, near=(97.0, 121.0))]

# --- spawn bands -------------------------------------------------------------------------------------------------------
# kind, count, min spacing between spawns, region: (x0, y0, x1, y1) boxes the band may use
BANDS = [
    ('boar', 14, 7.0, [(14, 112, 112, 189)]),
    ('crow', 12, 7.5, [(120, 150, 189, 189)]),
    ('troll', 12, 9.0, [(62, 112, 189, 127)]),
    ('weaver', 12, 8.0, [(8, 48, 184, 70)]),
    ('ram', 10, 9.0, [(8, 26, 184, 41)]),
]

# --- landmarks (client-drawn kinds) --------------------------------------------------------------------------------------
# The Hanged King's gallows crowd Gallows Hill; the bones of an older giant lie on the Highmoor (x, y, variant).
GALLOWS = [(160.0, 166.0, 0), (151.0, 172.0, 1), (170.0, 168.0, 2), (146.0, 160.0, 3), (167.0, 180.0, 1), (134.0, 176.0, 2), (176.0, 156.0, 0)]
BONES = [(70.0, 36.0, 0), (126.0, 34.0, 1), (58.0, 60.0, 2), (140.0, 60.0, 3), (80.0, 12.0, 1), (128.0, 14.0, 2)]
