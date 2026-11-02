"""Street-centred entrances for the four main cities; final atlas overlay.

Keep landmarks/services in place. The northern Nacrehold route goes around its
cathedral forecourt; Skaldholm's northern street is Lark Lane because the
Steward's Hall closes the Grand Avenue. No file zones or instance IDs change.
"""
import math

# (portal, destination, direction, route from crossing onto an existing street,
#  street centre, street width, optional wall aperture)
ENTRIES = {
    4: [
        ('glacier_gate', 2, (0, -1), [(48., 5.5), (48., 34.)], 48., 4., (48., 12., False, 4.5, False)),
        ('path_4_0', 0, (0, 1), [(80., 154.5), (80., 130.)], 80., 7., (80., 140., False, 5.9, True)),
        ('path_4_1', 1, (1, 0), [(154.5, 76.), (128., 76.)], 76., 7., (144., 76., True, 5.9, True)),
        ('path_4_3', 3, (-1, 0), [(5.5, 76.), (34., 76.)], 76., 7., (16., 76., True, 4.5, False)),
    ],
    9: [
        ('nacre_deep_gate', 8, (0, -1), [(96., 5.5), (96., 17.), (104., 17.), (104., 35.), (96., 35.), (96., 50.)], 96., 6., None),
        ('nacre_astral_gate', 13, (1, 0), [(186.5, 48.), (168., 48.)], 48., 4.8, None),
        ('path_9_1', 1, (0, 1), [(96., 186.5), (96., 168.)], 96., 6., None),
        ('path_9_7', 7, (-1, 0), [(5.5, 48.), (24., 48.)], 48., 4.8, None),
        ('path_9_15', 15, (1, 0), [(186.5, 120.), (168., 120.)], 120., 4.8, None),
    ],
    17: [
        ('asterion_stormglass_gate', 19, (0, -1), [(90., 5.5), (90., 30.)], 90., 6., None),
    ],
}


def entry(zone, to):
    return next((e for e in ENTRIES.get(zone, []) if e[1] == to), None)


def landing(spec):
    _, _, (dx, dy), points, *_ = spec
    x, y = points[0]
    return (x, y), (x - dx * 6, y - dy * 6)


def near_route(o, points, margin):
    for a, b in zip(points, points[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = max(0, min(1, ((o['x'] - a[0]) * dx + (o['y'] - a[1]) * dy) / (dx * dx + dy * dy)))
        if math.hypot(o['x'] - a[0] - dx * t, o['y'] - a[1] - dy * t) < o.get('r', 0) + margin:
            return True
    return False


def cut_wall(z, arch):
    x, y, vertical, half = arch['x'], arch['y'], arch['vertical'], arch['halfWidth']
    wall, along = (x, y) if vertical else (y, x)
    out = []
    for o in z['objects']:
        cross = o['x'] if vertical else o['y']
        middle = o['y'] if vertical else o['x']
        length = o.get('depth' if vertical else 'width', 0)
        if o['kind'] != 'rampart' or abs(cross - wall) > 1 or not length or middle + length / 2 <= along - half or middle - length / 2 >= along + half:
            out.append(o)
            continue
        for lo, hi in [(middle - length / 2, min(middle + length / 2, along - half)),
                       (max(middle - length / 2, along + half), middle + length / 2)]:
            if hi - lo <= .05:
                continue
            part = dict(o)
            part['y' if vertical else 'x'] = (lo + hi) / 2
            part['depth' if vertical else 'width'] = hi - lo
            out.append(part)
    z['objects'] = out


def prepare(zones, clear):
    for zone in [0, 4, 9, 17]:
        z = zones[zone]
        # Retire only paths/paving owned by this overlay or the earlier arch fix.
        for key in ['archPaths', 'cityEntryPaths']:
            for path in z.pop(key, []):
                if path in z.get('paths', []):
                    z['paths'].remove(path)
        z['roads'] = [r for r in z.get('roads', []) if not r.get('cityEntry')]
        z['cityEntrances'] = []
        if zone == 0:
            # Alderhaven already has aligned north/south gates on its central
            # avenue. Keep the meadow's distant adventure crossings in place.
            for name, points, y in [('alderhaven_north', [(36., 65.), (36., 78.)], 72.),
                                    ('alderhaven_south', [(36., 95.), (36., 89.)], 94.)]:
                assert all(clear(z, a, b, 1.2) for a, b in zip(points, points[1:]))
                z['cityEntrances'].append(dict(id=name, points=points, axis='y', street=36., width=3.2,
                                              opening=dict(x=36., y=y, vertical=False, halfWidth=2.)))
            continue
        previous = z.get('exitArches', [])
        specs = ENTRIES[zone]
        arches = [dict(x=a[0], y=a[1], vertical=a[2], halfWidth=a[3], towers=a[4],
                       portal=id_, name=zones[to].get('name','Greenmeadow'))
                  for id_, to, _, _, _, _, a in specs if a]
        # Close obsolete apertures before opening their street-centred replacements.
        for old in previous:
            if any(abs(old['x']-a['x']) < .01 and abs(old['y']-a['y']) < .01 for a in arches):
                continue
            vertical = old['vertical']
            template = next(o for o in z['objects'] if o['kind'] == 'rampart' and
                            abs((o['x'] if vertical else o['y']) - (old['x'] if vertical else old['y'])) < 1)
            half = old.get('halfWidth', 4.5)
            z['objects'].append(dict(template, x=old['x'], y=old['y'], width=1.8 if vertical else half*2,
                                     depth=half*2 if vertical else 1.8))
        if zone == 4:
            # The unused west tower occupied the Trade Road's centre. The four
            # old portal posts were invisible colliders in the major avenues.
            z['objects'] = [o for o in z['objects'] if not
                            (o['kind'] == 'tower' and (o['x'], o['y']) == (16., 76.)) and not
                            (o['kind'] == 'post' and (o['x'], o['y']) in [(78.5,155.),(81.5,155.),(152.,74.5),(152.,77.5)])]
        for arch in arches:
            cut_wall(z, arch)
        if arches:
            z['exitArches'] = arches
        foliage = {'tree', 'bush', 'rock', 'flowers', 'coral', 'kelp'}
        for id_, to, direction, points, street, width, aperture in specs:
            z['objects'] = [o for o in z['objects'] if o['kind'] not in foliage or
                            not near_route(o, points, width/2+.4)]
            assert all(clear(z, a, b, 1.2) for a, b in zip(points, points[1:])), f'{zone}: blocked street approach {id_}'
            entrance = dict(id=id_, portal=id_, points=points, axis='x' if direction[0] else 'y', street=street, width=width)
            if aperture:
                entrance['opening'] = next(a for a in arches if a['portal'] == id_)
            z['cityEntrances'].append(entrance)
            # Extend the city's own paving through the approach rather than
            # leaving a dirt line over grass beside a parallel city street.
            for a, b in zip(points, points[1:]):
                across = width / 2
                vertical = a[0] == b[0]
                z['roads'].append(dict(t=1, x0=min(a[0],b[0])-(across if vertical else 0),
                                       x1=max(a[0],b[0])+(across if vertical else 0),
                                       y0=min(a[1],b[1])-(0 if vertical else across),
                                       y1=max(a[1],b[1])+(0 if vertical else across), cityEntry=id_))
