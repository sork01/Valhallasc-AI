#!/usr/bin/env python3
"""Bounded checks for the player-style NPC atlases (client/assets/npcp_*.png + npcp.txt): contract, borders, animation,
recolour table, head sockets (a Python port of NpcArt.head), 24 distinct looks. No browser, no PixelFlow.
usage: python3 tests/npcp-art.py [--mutate]      (--mutate blanks one skin tone in a copy and must fail the socket/recolour checks)
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / 'client/assets'
META = json.loads((A / 'npcp.txt').read_text())
OLD = json.loads((A / 'npc.txt').read_text())
W = H = 96
AX, AY = META['anchor']
MUTATE = '--mutate' in sys.argv
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


def hexint(c):
    return int(c[1:], 16)


def frames(key):
    im = np.array(Image.open(A / f'npcp_{key}.png').convert('RGBA'))
    assert im.shape == (288, 768, 4), (key, im.shape)
    for row, clip in enumerate(('idle', 'walk', 'talk')):
        for n in range(META['clips'][clip]['n']):
            yield clip, n, im[row * H:(row + 1) * H, n * W:(n + 1) * W]


def socket(frame, skin):
    """Port of NpcArt.head: biggest skin-coloured component within 20 px of the anchor column and above the anchor row."""
    rgb = (frame[..., 0].astype(int) << 16) | (frame[..., 1].astype(int) << 8) | frame[..., 2].astype(int)
    mask = np.zeros((H, W), bool)
    for y in range(AY):
        for x in range(max(0, AX - 20), min(W, AX + 21)):
            if frame[y, x, 3] and rgb[y, x] in skin:
                mask[y, x] = True
    best = []
    seen = np.zeros_like(mask)
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        comp, stack = [], [(y, x)]
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            comp.append((cy, cx))
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        if len(comp) > len(best):
            best = comp
    if len(best) < 12:
        return None
    ys = [p[0] for p in best]
    xs = [p[1] for p in best]
    left, right = min(xs), max(xs)
    cx = (left + right) / 2
    half = max(5, (right - left) * .3)
    crown = min(ys)
    for y in range(crown - 1, -1, -1):
        if not frame[y, int(np.ceil(cx - half)):int(np.floor(cx + half)) + 1, 3].any():
            break
        crown = y
    return dict(x=cx - AX, y=crown + 1 - AY, face_top=min(ys), face_bottom=max(ys), cy=sum(ys) / len(ys), width=max(10, (right - left + 1) / 2 + 1), area=len(best))


idle_masks = {}
for key, spec in META['sprites'].items():
    mats = META['designs'][key]['materials']
    skin = {hexint(c) for k, c in mats.items() if k.startswith('skin')}
    if MUTATE:
        skin = {hexint('#010203')}
    img = np.array(Image.open(A / f'npcp_{key}.png').convert('RGBA'))
    colours = {(int(p[0]) << 16) | (int(p[1]) << 8) | int(p[2]) for p in img.reshape(-1, 4) if p[3]}
    general = META['designs'][key]['general']
    for group, need in (('cloth', 2), ('skin', 2), ('hair', 0 if key in ('pilgrim', 'lamplighter') else 1)) if general else (('skin', 1),):
        present = [n for n in range(4) if hexint(mats[f'{group}{n}']) in colours]
        check(MUTATE or len(present) >= need, f'{key}: only tones {present} of {group} are in the atlas (the per-person remap needs them)')
        designs = META['designs'][key]
    check(not general or set(designs['amounts']) == {'skin', 'hair', 'cloth'}, f'{key}: amounts missing')
    sigs = {}
    for clip, n, fr in frames(key):
        a = fr[..., 3] > 0
        ys, xs = np.nonzero(a)
        check(len(xs) > 0 and xs.min() >= 1 and xs.max() <= 94 and ys.min() >= 1 and ys.max() <= 94, f'{key} {clip} {n}: touches the border')
        check(a.any(0)[0] == False and a.any(0)[-1] == False, f'{key} {clip} {n}: opaque edge column')
        sigs.setdefault(clip, set()).add(fr.tobytes())
        if clip == 'idle' and n == 0 and general:
            idle_masks[key] = a
        # feet: the lowest opaque row must sit near the anchor (walk may lift a foot)
        slack = 10 if designs.get('species') == 'merfolk' else 6      # a merfolk tail flicks up on one walk frame
        check(ys.max() <= 94 and ys.max() >= AY - slack, f'{key} {clip} {n}: feet at row {ys.max()}, anchor {AY}')
        s = socket(fr, skin)
        check(s is not None, f'{key} {clip} {n}: no head socket (skin face not found)')
        if s:
            check(s['cy'] < 56 and s['face_top'] > 4, f'{key} {clip} {n}: face component at y {s["cy"]:.0f}, not the head')
            check(s['y'] + AY <= s['face_top'], f'{key} {clip} {n}: crown below the face top')
            check(s['y'] + AY >= 0, f'{key} {clip} {n}: crown above the frame')
            check(s['width'] >= 10 and s['width'] <= 30, f'{key} {clip} {n}: socket width {s["width"]}')
    for clip, v in sigs.items():
        check(len(v) >= 3, f'{key} {clip}: static ({len(v)} distinct frames)')
    # walk legs: the lower half must differ between walk frames
    lows = {np.array(Image.open(A / f'npcp_{key}.png').convert('RGBA'))[H + 58:2 * H, n * W:(n + 1) * W].tobytes() for n in range(8)}
    check(len(lows) >= 4, f'{key}: walk legs barely change ({len(lows)})')
    check(META['tops'][key] == 90 - min(int(np.nonzero(f[..., 3])[0].min()) for _, _, f in frames(key)), f'{key}: tops disagree with the atlas')

keys = sorted(idle_masks)
worst = (10 ** 9, None)
for i, k1 in enumerate(keys):
    for k2 in keys[i + 1:]:
        d = int((idle_masks[k1] ^ idle_masks[k2]).sum())
        if d < worst[0]:
            worst = (d, (k1, k2))
check(len(keys) == 24, f'{len(keys)} general designs, want 24')
check(len(META['sprites']) == 164, f"{len(META['sprites'])} designs in total, want 164 (24 general + 140 special)")
for sp, kind in (('special_heart_oracle', 'treefolk'), ('special_sky_warden', 'winged'), ('special_nacre_envoy', 'merfolk')):
    check(META['designs'].get(sp, {}).get('species') == kind, f'{sp}: species {kind} missing from the manifest')
check(worst[0] >= 120, f'two designs have near-identical silhouettes: {worst}')
print(f'designs {len(keys)}, closest silhouette pair {worst}')
print('FAIL' if fails else 'PASS', len(fails), 'problems')
for f in fails[:40]:
    print(' -', f)
sys.exit(1 if fails else 0)
