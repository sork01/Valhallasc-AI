#!/usr/bin/env python3
"""Leg removal must not change pixels inside an opaque, closed skirt or robe.

Uses the actual pose/cloth geometry and a no-leg control render, rather than a
border or frame-count check. The exported-atlas mode also guards saved pixels.
"""
import json
import hashlib
import os
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from scipy.ndimage import binary_erosion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import npcp_general as G

keys = G.pick(os.environ.get('NPC_SKIRT_KINDS', 'named').split(','))
keys = [k for k in keys if not G.DESIGNS[k].get('tail')]
assert keys
mode = os.environ.get('NPC_SKIRT_MODE', 'atlas')
mutate = bool(os.environ.get('NPC_SKIRT_MUTATE'))
original_panels, original_body = G.skirt_panels, G.core.body_layer
captures = []


def capture(ink, xf, p, o):
    probe = G.cc.Ink(0, ink.color)
    probe.turn = ink.turn
    original_panels(probe, xf, p, o)
    index, _ = probe.resolve()
    captures.append(binary_erosion(index > 0, iterations=1))
    original_panels(ink, xf, p, o)


def no_legs(*args, **kwargs):
    kwargs['legs'] = False
    return original_body(*args, **kwargs)


def legacy_surface(ink, vertices, material, tone=2, bias=3, outline=True):
    ink.plate(vertices, material, tone, not outline)


failures, poses, covered_pixels = [], 0, 0
uncovered_leg_pixels = {}
for key in keys:
    uncovered_leg_pixels[key] = 0
    atlas = np.array(Image.open(ROOT / f'client/assets/npcp_{key}.png').convert('RGBA')) if mode == 'atlas' else None
    for row, (clip, count) in enumerate(G.CLIPS):
        for frame in range(count):
            captures.clear()
            with patch.object(G, 'skirt_panels', capture), patch.object(G, 'lower_body', lambda *a, **kw: None), patch.object(G.core, 'body_layer', no_legs), patch.object(G.core, 'boots', lambda *a, **kw: None):
                control = np.array(G.render(key, clip, frame)[0])
            mask = captures[0]
            assert mask.sum() > 5, (key, 'no garment coverage')
            if mode == 'atlas':
                actual = atlas[row*96:(row+1)*96, frame*96:(frame+1)*96]
            elif mutate:
                def uncovered(ink, xf, joints, R, p, o):
                    G.lower_body(ink, joints, R, o.get('pants', 'pants'), o.get('boots', 'leather'))
                with patch.object(G, 'garment_surface', legacy_surface), patch.object(G, 'covered_lower_body', uncovered):
                    actual = np.array(G.render(key, clip, frame)[0])
            else:
                actual = np.array(G.render(key, clip, frame)[0])
            leaks = int((mask & np.any(actual != control, axis=2)).sum())
            uncovered_leg_pixels[key] += int((~mask & np.any(actual != control, axis=2)).sum())
            if leaks:
                failures.append(dict(kind=key, clip=clip, frame=frame, exposedPixels=leaks))
            poses += 1
            covered_pixels += int(mask.sum())
    print(key, 'checked', flush=True)
    assert uncovered_leg_pixels[key] > 0, (key, 'legs were removed rather than hidden behind the garment')

result = dict(mode=mode, designs=len(keys), poses=poses, coveredPixels=covered_pixels,
              uncoveredLegPixels=uncovered_leg_pixels, failures=failures)
out = ROOT / 'test-results/npc-named/robes'
out.mkdir(exist_ok=True, parents=True)
suffix = '' if os.environ.get('NPC_SKIRT_KINDS', 'named') == 'named' else '-' + hashlib.sha256(os.environ['NPC_SKIRT_KINDS'].encode()).hexdigest()[:8]
(out / ('mutation-proof.json' if mutate else mode + '-occlusion-proof' + suffix + '.json')).write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(designs=len(keys), poses=poses, failures=len(failures))))
for failure in failures[:30]:
    print(failure)
sys.exit(1 if failures else 0)
