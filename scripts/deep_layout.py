"""The plan of Ran's Deep (zone 8, levels 35-40): pure geometry and constants shared by generate_deep.py (which writes the zone)
and generate_bifrost.py (which writes the Maelstrom that leads here).

176x176 tiles, y growing southwards. The sea floor under the storm that Bifrost Reach floats over. The Maelstrom sets you down in
Keelhaven (a camp of overturned longships in the south, inside a bell of air), with the open Shallows round it (west: the wreck
of Naglfar, east: the drowned chapel). North of them stands the Net: a labyrinth of living coral, 10 x 7 cells of 16 tiles with
walls 3 thick (corridors 13 wide), grown by Ran to catch what the sea drops. One door in its south wall; in its heart a 2 x 2
chamber, Ran's Court, which has exactly two doors and holds the Kraken. The monster kinds follow the maze's depth: the further
a cell is from the door, the stronger what lives in it.

The maze is a seeded depth-first labyrinth over the cells (the chamber counts as one node), braided so that some dead ends are
loops; `MAZE_SEED` was picked by `search_seed` so that the chamber lies deep and has two doors.
"""
import math
import random

NAME = "Rán's Deep"
SIZE = 176
LEVELS = [35, 40]

# --- gates -------------------------------------------------------------------------------------------------------------
GATE = (80.0, 170.5)                       # the Maelstrom's way back up, in Keelhaven
ARRIVAL = (80.0, 165.0)                    # where Bifrost Reach's Maelstrom sets you down
EYRIE_GATE = (98.5, 32.5)                  # the Maelstrom in Bifrost Reach (zone 7), on the Roc's Eyrie, beside the end of the long bridge
EYRIE_ARRIVAL = (103.5, 32.4)

# --- the maze -----------------------------------------------------------------------------------------------------------
COLS, ROWS, PITCH, THICK = 10, 7, 16, 3.0
OX, OY = 8, 8                              # the maze's north-west corner (the outer wall's centre line)
BLOCK = {(4, 2), (5, 2), (4, 3), (5, 3)}   # Ran's Court
ENTRY = (4, 6)                             # the cell behind the door in the south wall
SOUTH_WALL = OY + ROWS * PITCH             # y of the maze's south wall (120)
RING_S = 174                               # y of the outer ring's south wall
MAZE_SEED = 215
BRAID = .55                                # chance that a dead end is opened into a loop
PIECE = 4.0                                # longest wall rectangle

BOUNDS = dict(x0=OX, y0=OY, x1=OX + COLS * PITCH, y1=RING_S)   # the walkable box inside the outer ring


def cell_box(c, r):
    """(x0, y0, x1, y1) of a cell's floor, inside the walls."""
    h = THICK / 2
    return (OX + c * PITCH + h, OY + r * PITCH + h, OX + (c + 1) * PITCH - h, OY + (r + 1) * PITCH - h)


def cell_centre(c, r):
    return (OX + (c + .5) * PITCH, OY + (r + .5) * PITCH)


def cell_of(x, y):
    return int((x - OX) // PITCH), int((y - OY) // PITCH)


def neighbours(c, r):
    for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        a, b = c + dc, r + dr
        if 0 <= a < COLS and 0 <= b < ROWS:
            yield a, b


def key(a, b):
    return (a, b) if a <= b else (b, a)


def maze(seed=MAZE_SEED):
    """-> (doors, depth): `doors` is a set of key(cellA, cellB) pairs that are open (block-internal pairs excluded: they are
    always open), `depth` maps every cell to its number of steps from ENTRY."""
    rng = random.Random(seed)
    node = {(c, r): ('B' if (c, r) in BLOCK else (c, r)) for r in range(ROWS) for c in range(COLS)}
    adj = {}
    for a in node:
        for b in neighbours(*a):
            if node[a] != node[b]:
                adj.setdefault(node[a], []).append((node[b], key(a, b)))
    start = node[ENTRY]
    seen, stack, doors = {start}, [start], set()
    while stack:
        n = stack[-1]
        options = [(m, d) for m, d in adj[n] if m not in seen]
        if not options:
            stack.pop()
            continue
        m, d = rng.choice(options)
        doors.add(d)
        seen.add(m)
        stack.append(m)
    # braid: open some dead ends into a neighbour (never into the chamber, never a wall of it)
    degree = {}
    for a, b in doors:
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1
    ends = sorted(c for c in node if c not in BLOCK and degree.get(c, 0) == 1 and c != ENTRY)
    for c in ends:
        if rng.random() < BRAID:
            options = [n for n in neighbours(*c) if n not in BLOCK and key(c, n) not in doors]
            if options:
                doors.add(key(c, rng.choice(options)))
    return doors, depths(doors)


def open_pairs(doors):
    pairs = set(doors)
    for a in BLOCK:
        for b in neighbours(*a):
            if b in BLOCK:
                pairs.add(key(a, b))
    return pairs


def depths(doors):
    pairs = open_pairs(doors)
    d = {ENTRY: 0}
    queue = [ENTRY]
    for c in queue:
        for n in neighbours(*c):
            if n not in d and key(c, n) in pairs:
                d[n] = d[c] + 1
                queue.append(n)
    return d


def chamber_doors(doors):
    return sorted(d for d in doors if (d[0] in BLOCK) != (d[1] in BLOCK))


def search_seed(limit=400):
    """The seeds whose chamber has two doors and lies in the deepest part: [(score, seed)], best first."""
    out = []
    for seed in range(limit):
        doors, depth = maze(seed)
        if len(chamber_doors(doors)) != 2 or len(depth) != COLS * ROWS:
            continue
        ranked = sorted(v for c, v in depth.items() if c not in BLOCK)
        at = max(depth[c] for c in BLOCK)
        pct = sum(1 for v in ranked if v <= at) / len(ranked)
        out.append((pct + .02 * at, seed, at, max(ranked)))
    return sorted(out, reverse=True)


# --- walls ----------------------------------------------------------------------------------------------------------------
def wall_rects(doors):
    """Every wall as a list of (x, y, width, depth) rectangles no longer than PIECE (centre and full size)."""
    pairs = open_pairs(doors)
    segments = []                                  # (x0, y0, x1, y1) of the rectangle
    h = THICK / 2
    for r in range(ROWS):
        for c in range(COLS):
            if c + 1 < COLS and key((c, r), (c + 1, r)) not in pairs:                         # a wall to the east of this cell
                x = OX + (c + 1) * PITCH
                segments.append((x - h, OY + r * PITCH - h, x + h, OY + (r + 1) * PITCH + h))
            if r + 1 < ROWS and key((c, r), (c, r + 1)) not in pairs:                         # a wall to the south of it
                y = OY + (r + 1) * PITCH
                segments.append((OX + c * PITCH - h, y - h, OX + (c + 1) * PITCH + h, y + h))
    # the outer shell: the maze's north wall, the ring down both sides to RING_S, the ring's south wall, the maze's south wall
    xw, xe = OX, OX + COLS * PITCH
    segments.append((xw - h, OY - h, xe + h, OY + h))
    segments.append((xw - h, OY - h, xw + h, RING_S + h))
    segments.append((xe - h, OY - h, xe + h, RING_S + h))
    segments.append((xw - h, RING_S - h, xe + h, RING_S + h))
    door_x0 = OX + ENTRY[0] * PITCH + h
    door_x1 = OX + (ENTRY[0] + 1) * PITCH - h
    segments.append((xw - h, SOUTH_WALL - h, door_x0, SOUTH_WALL + h))
    segments.append((door_x1, SOUTH_WALL - h, xe + h, SOUTH_WALL + h))
    out = []
    for x0, y0, x1, y1 in segments:
        w, d = x1 - x0, y1 - y0
        if w >= d:
            n = max(1, math.ceil(w / PIECE))
            for k in range(n):
                a, b = x0 + w * k / n, x0 + w * (k + 1) / n
                out.append(((a + b) / 2, (y0 + y1) / 2, b - a, d))
        else:
            n = max(1, math.ceil(d / PIECE))
            for k in range(n):
                a, b = y0 + d * k / n, y0 + d * (k + 1) / n
                out.append(((x0 + x1) / 2, (a + b) / 2, w, b - a))
    return out


# --- the open water round Keelhaven -----------------------------------------------------------------------------------------
HUB_BOX = (62, 143, 98, 172)               # Keelhaven's sanctuary, shared with deep_content.HUB
WINGS = {'west': (9.5, 121.5, 60.0, 172.5), 'east': (100.0, 121.5, 166.5, 172.5)}

# --- named places ---------------------------------------------------------------------------------------------------------------
BELL_R = 2.6
# chain id -> (burn seconds, bells as (id suffix, name, x, y)); the generator moves the maze bells onto their cells' floor
CHAINS = {
    'deep_harbour': (35, [('a1', 'the West Buoy Bell', 34.0, 150.0), ('a2', 'the Pearl Gate Bell', 80.0, 127.0), ('a3', 'the East Buoy Bell', 126.0, 150.0)]),
    'deep_net': (45, []),                      # four cells of the maze, chosen by pick_bells
    'deep_rans': (50, []),                     # five cells round Ran's Court
}
PLACES = [
    dict(id='deep_longship', name='the Wreck of Naglfar', x=26.0, y=140.0, r=4.5),
    dict(id='deep_chapel', name='the Drowned Chapel', x=140.0, y=140.0, r=4.5),
    dict(id='deep_pearlgate', name='the Pearl Gate', x=80.0, y=122.5, r=3.5),
    dict(id='deep_garden', name='the Abyssal Garden', x=0.0, y=0.0, r=4.5),     # the deepest dead end: placed by pick_places
    dict(id='deep_courtdoor', name='the Court Door', x=0.0, y=0.0, r=4.0),         # outside the nearer door of Ran's Court: placed by the generator
]

# --- spawn bands ----------------------------------------------------------------------------------------------------------------
# kind, count, spacing, where: 'wings' (the open shallows) or a quartile of the maze's depth (0 = near the door, 3 = deepest)
BANDS = [
    ('draugr', 11, 9.0, 'wings'),
    ('angler', 10, 9.0, 0),
    ('moray', 10, 9.0, 1),
    ('siren', 10, 9.0, 2),
    ('shellback', 9, 9.5, 3),
]
HVITSERK = (14.0, 127.0)                   # the drowned captain, in the west Shallows north of the Wreck of Naglfar
BOSS = ('kraken', cell_centre(4, 2)[0] + PITCH / 2, cell_centre(4, 2)[1] + PITCH / 2)    # the middle of the 2 x 2 chamber


def band_of_cells(depth):
    """cell -> quartile 0..3 of the depth ranking of the maze's ordinary cells (ties broken by position)."""
    cells = sorted((c for c in depth if c not in BLOCK), key=lambda c: (depth[c], c[1], c[0]))
    return {c: min(3, k * 4 // len(cells)) for k, c in enumerate(cells)}


def trail(doors, depth, goal):
    """The shortest route of cells from ENTRY to `goal` (a cell), as a list of cells."""
    pairs = open_pairs(doors)
    path = [goal]
    while path[-1] != ENTRY:
        c = path[-1]
        path.append(min((n for n in neighbours(*c) if n in depth and key(c, n) in pairs and depth[n] < depth[c]), key=lambda n: (depth[n], n)))
    return path[::-1]
