#!/usr/bin/env python3
"""A woman wearing a head piece must not have long hair hanging out of it.

Her long hair is baked into the body layer, so each female rig ships a second body (`body_hat`, drawn under a worn
head piece) made without the hair plates: scripts/export_character_body.py CLASS --female --hat-hair.
Checks the atlases and sidecars only (no browser): the part is wired into the metadata and bounds sidecar, no hair
colour is left below the chin in any of the 272 poses (while the ordinary body still has plenty), the head itself is
unchanged, and men have no such part.
"""
import base64
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'client' / 'assets'
sys.path.insert(0, str(ROOT / 'scripts'))
import sprite_bounds  # noqa: E402

STEMS = ['mage', 'priest', 'hunter', 'warrior_layered', 'assassin']
OUTLINE = (24, 24, 42)
CHIN = -9        # head-local v (up is positive): at and above this is face, scalp and fringe
HANG = -20       # the longest short lock (the priest's cheek locks) ends at -16; long hair runs 50+ below
failures = []


def check(ok, message):
    if not ok:
        failures.append(message)


def hair_mask(image, colours):
    return np.logical_or.reduce([(image[..., :3] == c).all(-1) for c in colours]) & (image[..., 3] > 0)


for stem in STEMS:
    meta = json.loads((ASSETS / f'{stem}_f_sprites.txt').read_text())
    bounds = json.loads((ASSETS / f'{stem}_f_bounds.txt').read_text())
    part = meta['parts'].get('body_hat')
    check(part is not None, f'{stem}_f: metadata has no body_hat part')
    check('body_hat' in meta.get('lazyParts', []), f'{stem}_f: body_hat must be lazy (most women never wear headgear)')
    check('body_hat' not in json.loads((ASSETS / f'{stem}_sprites.txt').read_text())['parts'], f'{stem}: a man has no body_hat')
    if part is None:
        continue
    check(part == {'png': f'{stem}_f_body_hat.png', 'depth': f'{stem}_f_body_hat_depth.png'}, f'{stem}_f: body_hat file names')
    body = np.asarray(Image.open(ASSETS / meta['parts']['body']['png']).convert('RGBA'))
    hat = np.asarray(Image.open(ASSETS / part['png']).convert('RGBA'))
    depth = Image.open(ASSETS / part['depth'])
    check(hat.shape == body.shape and depth.size == (body.shape[1], body.shape[0]), f'{stem}_f: body_hat atlas size')
    frames = sum(c['n'] for c in meta['clips'].values()) * 8
    sidecar = base64.b64decode(bounds['parts'].get('body_hat', ''))
    check(len(sidecar) == frames * 4 and sidecar == sprite_bounds.part_bounds(ASSETS / part['png'], meta), f'{stem}_f: body_hat bounds entry is missing or stale')
    colours = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in meta['ramps']['hair']]
    fw, fh = meta['frame']
    yy, xx = np.mgrid[0:fh, 0:fw]
    long_body = long_hat = head_diff = head_total = poses = 0
    for clip, spec in meta['clips'].items():
        for d in range(8):
            for i in range(spec['n']):
                cx, cy, rx, ry = meta['headFrames'][f'{clip}/{d}/{i}'][:4]
                cell = (slice((spec['row0'] + d) * fh, (spec['row0'] + d + 1) * fh), slice(i * fw, (i + 1) * fw))
                a, b = body[cell], hat[cell]
                v = (xx + .5 - cx) * ry - (yy + .5 - cy) * rx
                long_body += (hair_mask(a, colours) & (v < HANG)).sum()
                low_hat = hair_mask(b, colours) & (v < HANG)
                long_hat += low_hat.sum()
                check(not low_hat.any(), f'{stem}_f {clip}/{d}/{i}: long hair left in body_hat')
                check(b[..., 3].any() and not b[[0, -1], :, 3].any() and not b[:, [0, -1], 3].any(), f'{stem}_f {clip}/{d}/{i}: empty or clipped')
                region = (v >= CHIN) & (a[..., 3] > 0) & ~hair_mask(a, colours) & ~(a[..., :3] == OUTLINE).all(-1)
                head_diff += ((a != b).any(-1) & region).sum()
                head_total += region.sum()
                poses += 1
    check(poses == frames, f'{stem}_f: checked {poses} poses of {frames}')
    check(long_body > 10000, f'{stem}_f: the ordinary body should still carry long hair ({long_body}); is the check looking at the right place?')
    check(head_diff <= head_total * .02, f'{stem}_f: the head changed under headgear ({head_diff} of {head_total} pixels)')
    print(f'{stem}_f: {poses} poses, long hair {long_body} -> {long_hat} px, head pixels changed {head_diff}/{head_total}')

if failures:
    print('\n'.join(failures[:25]))
    sys.exit(1)
print('hat-hair-art: ok')
