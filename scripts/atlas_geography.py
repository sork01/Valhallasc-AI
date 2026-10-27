#!/usr/bin/env python3
"""Trace the owner's painted atlas without moving its coast or province borders.

Authored polygons share identical boundary chains. Those shared edges determine
walkable neighbours and route marks; the bitmap is only the presentation layer.
"""
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'world/atlas-geography.txt'
SCALE = 4


def generate():
    source = json.loads(SOURCE.read_text())
    regions = []
    owners = defaultdict(list)
    grid = np.full(((source['height']+SCALE-1)//SCALE,
                    (source['width']+SCALE-1)//SCALE), -1, dtype=np.int16)
    for r in source['regions']:
        poly = r['polygon']
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        regions.append(dict(r, outline=[poly], box=[min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys)]))
        image = Image.new('1', (grid.shape[1], grid.shape[0]))
        ImageDraw.Draw(image).polygon([(x/SCALE, y/SCALE) for x, y in poly], fill=1)
        grid[np.asarray(image, dtype=bool)] = r['zone']
        for a, b in zip(poly, poly[1:]+poly[:1]):
            owners[tuple(sorted((tuple(a), tuple(b))))].append(r['zone'])
    boundaries = defaultdict(list)
    for edge, zones in owners.items():
        assert len(zones) <= 2, (edge, zones)
        if len(zones) == 2:
            boundaries[tuple(sorted(zones))].append(edge)
    links = []
    for (a, b), edges in sorted(boundaries.items()):
        length = sum(math.dist(*edge) for edge in edges)
        # A tiny corner contact is not a route across a province boundary.
        if length < 24:
            continue
        middle = [sum((p[k]+q[k])/2*math.dist(p, q) for p, q in edges)/length for k in (0, 1)]
        p, q = min(edges, key=lambda e: math.dist([(e[0][k]+e[1][k])/2 for k in (0, 1)], middle))
        links.append(dict(a=a, b=b, at=[(p[k]+q[k])/2 for k in (0, 1)]))
    return dict(width=source['width'], height=source['height'], background=source['background'],
                regions=regions, cities=source['cities'], links=links), grid


if __name__ == '__main__':
    atlas, _ = generate()
    out = ROOT / 'test-results/organic-atlas'
    out.mkdir(parents=True, exist_ok=True)
    (out/'geometry.txt').write_text(json.dumps(atlas, indent=2, ensure_ascii=False)+'\n')
    print(f"{len(atlas['regions'])} painted regions, {len(atlas['links'])} shared-border routes")
