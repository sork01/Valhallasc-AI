"""Greenmeadow's landing dock (zone shapes pilot, 2026-11-07).

Owner: "make a dock in greenmeadow with a ship. when starting a new character, you should start there on the dock next to the
ship. and automatically get a quest to guide you to the beginner quests", then "the quest should be given when you step of the dock".

A pier runs from the Saltgrass Strand below Saltby out over the shallows; a ship lies moored along its west side. Runs LAST in
`zone_shapes.py apply` (after every pass that rebuilds zone 0's voids), so nothing of the approved Greenmeadow design moves:
  * the pier cells become land (`shapeFloor`), the outside band round them is coast (`shapeEdge` 'c'), and the voids are cut
    again from the same mask (void rectangles are a pure function of floor + seam margin, see skaldholm_rebuild.wing_gate);
  * Saltby's sanctuary reaches down over the pier; a trail joins the pier to Saltby's plaza;
  * zone 0 gets `dock`: the pier box (stepping out of it grants the quest), the start point of a new character, the ship;
  * the quest `meadow_landing` is added: `autoLevel` 1 so no giver offers it and no one can accept it, `landing` so the
    level sync never hands it out either (server/src/world/landing.rs grants it).

`unshape` restores the pre-shape view, so all of this goes with it.
"""
import numpy as np

import zone_shapes as zs

# The pier: cells x 199..201, from the beach (y 282) out over the shallows to y 298 (the land ends at y 287 here).
PIER = dict(x0=199, x1=202, y0=282, y1=299)
# A new character stands on the pier beside the gangplank.
START = dict(x=200.5, y=293.5)
# The ship lies west of the pier (behind it on screen), bow towards the beach.
SHIP = dict(x=195.4, y0=288.6, y1=299.4, beam=3.5, plank=293.5)
QUEST_ID = 'meadow_landing'
TRAIL = [[200.5, 282.6], [196.2, 281.0], [190.5, 276.4]]
# The ship's skipper stands at the foot of the gangplank and greets every new arrival (world/landing.rs sends the line once).
SKIPPER = dict(id='dock_skipper', name='Skipper Halvard', role='Master of the Grey Gull', x=199.9, y=292.1, color='#4f6d8a',
               dialogue=('Mind the gangplank, the Gull bucks like a goat. Saltby is up the beach, and the road north runs straight '
                         'to Alderhaven. Ask for Wren at the fountain.'),
               offers=[], buys=False, look=dict(skin='#c08a66', hair='#d8d2c4', style='short', hat='cap', hatColor='#2f4560'))
GREETING = 'Land ho! Welcome to Greenmeadow, friend. Follow the road north to Alderhaven and ask for Wren.'


def quest(levels):
    return {
        'id': QUEST_ID,
        'title': 'Ashore at Saltby',
        'npc': 'guide',
        'description': ('The ship that carried you over the sea has tied up at Saltby. Follow the road north to Alderhaven and find '
                        'Wren by the fountain. She helps every newcomer find their feet, and she knows who needs a hand.'),
        'objectives': [{'kind': 'talk', 'target': 'guide', 'label': 'Find Wren in Alderhaven', 'count': 1}],
        'level': 1,
        'rewardXp': levels[0] // 10,
        'rewardGold': 5,
        'requires': None,
        'autoLevel': 1,
        'landing': True,
        'repeatable': False,
    }


def build(world, levels):
    z = world
    n = z['size']
    floor = np.array([[c == '#' for c in row] for row in z['shapeFloor']])
    # what the voids cover now (the cells that are neither land nor seam margin)
    blocked = np.zeros((n, n), bool)
    for o in z['objects']:
        if o['kind'] == 'void':
            x0, y0 = round(o['x'] - o['width'] / 2), round(o['y'] - o['depth'] / 2)
            blocked[y0:y0 + round(o['depth']), x0:x0 + round(o['width'])] = True
    key = lambda vs: sorted((o['x'], o['y'], o['width'], o['depth']) for o in vs)
    assert key(o for o in z['objects'] if o['kind'] == 'void') == key(zs.void_pieces(~blocked)), 'the voids do not rasterise exactly'
    assert not (blocked & floor).any(), 'a void covers land'
    pier = np.zeros_like(floor)
    pier[PIER['y0']:PIER['y1'], PIER['x0']:PIER['x1']] = True
    assert floor[PIER['y0'], PIER['x0']:PIER['x1']].all(), 'the pier must start on the beach'
    assert not floor[PIER['y1'] - 1, PIER['x0']:PIER['x1']].any(), 'the pier must end over the water'
    floor |= pier
    blocked &= ~pier
    z['shapeFloor'] = [''.join('#' if v else ' ' for v in row) for row in floor]
    band = zs.dilate(pier, 3) & ~floor
    z['shapeEdge'] = [''.join('c' if band[y, x] and row[x] == ' ' else row[x] for x in range(n)) for y, row in enumerate(z['shapeEdge'])]
    z['objects'] = [o for o in z['objects'] if o['kind'] != 'void'] + zs.void_pieces(~blocked)
    # sand under the planks (hidden, but the minimap and the gaps between the piles show it)
    z['groundSpans'] = z['groundSpans'] + [[y, PIER['x0'], PIER['x1'] - 1, 1] for y in range(PIER['y0'], PIER['y1']) if not any(
        s[0] == y and s[1] <= PIER['x0'] and s[2] >= PIER['x1'] - 1 for s in z['groundSpans'])]
    for c in z['camps']:
        if c['name'] == 'Saltby':
            c['y1'] = PIER['y1']
            break
    else:
        raise AssertionError('no Saltby camp')
    z['paths'] = z['paths'] + [TRAIL]
    z['dock'] = dict(x0=PIER['x0'], x1=PIER['x1'], y0=PIER['y0'], y1=PIER['y1'], start=START, quest=QUEST_ID, ship=SHIP,
                     greeter=SKIPPER['id'], greeting=GREETING)
    assert not any(n['id'] == SKIPPER['id'] for n in z['npcs'])
    z['npcs'].append(dict(SKIPPER))
    assert not any(q['id'] == QUEST_ID for q in z['quests'])
    z['quests'].append(quest(levels))
    # nothing solid on the pier or the trail, no monster near the landing
    for o in z['objects']:
        if o['kind'] != 'void' and (o.get('r') or o.get('width')):
            assert not (PIER['x0'] - 1 <= o['x'] <= PIER['x1'] + 1 and PIER['y0'] - 1 <= o['y'] <= PIER['y1']), f'{o["kind"]} on the pier'
    for s in z['slimes']:
        assert np.hypot(s['x'] - START['x'], s['y'] - START['y']) > 20, f'{s} next to the landing'
    return dict(pier_cells=int(pier.sum()), voids=sum(o['kind'] == 'void' for o in z['objects']))
