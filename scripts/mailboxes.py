#!/usr/bin/env python3
"""Final seeded mailbox overlay. Covers every authored city, camp and Spark hub.

Run by sync-world after all geometry/content overlays; never rewrites existing services.
"""
import json
import math
import re
from pathlib import Path
from compact_atlas import connected

ROOT = Path(__file__).resolve().parents[1]
MAP = ROOT / 'world/map.txt'


def hubs(z):
    result = [c for c in [z.get('city'), *z.get('camps', [])] if c]
    for n in z.get('npcs', []):
        if n.get('travelStop') and not any(c['name'] == n['travelStop'] for c in result):
            result.append(dict(name=n['travelStop'], plaza=dict(x=n['x'], y=n['y'])))
    return result


def clear(z, x, y, margin=.65):
    if not (1 < x < z['size']-1 and 1 < y < z['size']-1):
        return False
    if z.get('sky') and z['sky'][int(y)][int(x)] == ' ':
        return False
    for o in z['objects']:
        dx, dy = abs(x-o['x']), abs(y-o['y'])
        if o.get('width', 0) and o.get('depth', 0):
            if dx < o['width']/2+margin and dy < o['depth']/2+margin:
                return False
        elif math.hypot(dx, dy) < o.get('r', 0)+margin:
            return False
    return True


def place(z, hub):
    anchor = next((n for n in z['npcs'] if n.get('travelStop') == hub['name']), hub['plaza'])
    # Some service anchors sit on a collision edge. Approach from adjacent clear ground.
    for _,ox,oy in sorted((math.hypot(dx,dy),int(anchor['x'])+dx+.5,int(anchor['y'])+dy+.5)
                           for dx in range(-2,3) for dy in range(-2,3)):
        if clear(z,ox,oy,.75):
            anchor = dict(x=ox,y=oy)
            break
    reachable = connected(z, origin=anchor)
    for radius in range(3, 15):
        for step in range(32):
            angle = step * math.tau / 32
            x, y = round(anchor['x']+math.cos(angle)*radius, 2), round(anchor['y']+math.sin(angle)*radius, 2)
            if 'x0' in hub and not (hub['x0']+1 < x < hub['x1']-1 and hub['y0']+1 < y < hub['y1']-1):
                continue
            if not clear(z,x,y,1.1) or int(y)*z['size']+int(x) not in reachable:
                continue
            if any(math.hypot(x-n['x'],y-n['y']) < 2.6 for n in z['npcs']):
                continue
            if any(math.hypot(x-p['x'],y-p['y']) < p['r']+2 for p in z.get('portals', [])):
                continue
            if any(math.hypot(x-s['x'],y-s['y']) < 8 for s in z.get('slimes', [])):
                continue
            # A clear, direct approach from the hub anchor supplies a reachable interaction spot.
            if not all(clear(z,anchor['x']+(x-anchor['x'])*t/40,anchor['y']+(y-anchor['y'])*t/40,.4) for t in range(41)):
                continue
            return x,y,anchor
    raise ValueError(f"No reachable mailbox location in {hub['name']}")


def main():
    w = json.loads(MAP.read_text())
    directory = []
    for index,z in enumerate([w,*w['zones']]):
        z['npcs'] = [n for n in z.get('npcs',[]) if not n['id'].startswith('mailbox_')]
        for hub in hubs(z):
            x,y,anchor = place(z,hub)
            slug = re.sub('[^a-z0-9]+','_',hub['name'].lower()).strip('_')
            ident = f'mailbox_{index}_{slug}'
            z['npcs'].append(dict(id=ident,name='Mailbox',role='Player mail',x=x,y=y,color='#cda75e',art='mailbox',buys=False,
                dialogue='Send letters, gold and unbound items to other characters. Delivery is free and instant.',
                offers=[dict(id='mail',label='Open mailbox',cost=0)]))
            directory.append(dict(id=ident,zone=index,hub=hub['name'],x=x,y=y,anchor=dict(x=anchor['x'],y=anchor['y'])))
    MAP.write_text(json.dumps(w,indent=2,ensure_ascii=False)+'\n')
    (ROOT/'world/mailboxes.txt').write_text(json.dumps(directory,indent=2,ensure_ascii=False)+'\n')
    print(f'Mailboxes in {len(directory)} cities and hubs')


if __name__ == '__main__':
    main()
