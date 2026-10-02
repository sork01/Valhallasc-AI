#!/usr/bin/env python3
"""Assassin: adds the shoulders, gloves and head layers to the existing Assassin atlas (see cel_common.py).

usage: make_assassin_cel_sprites.py preview [clip|all] [directory]   contact sheets (scratch), rows = facings
       make_assassin_cel_sprites.py build [--replace]                 render the six new layers, create the editable PixelFlow sprites assassin_cel_<clip>_<facing>_<shadow|moon>
       make_assassin_cel_sprites.py export [--local]                  PixelFlow (edits kept) -> client/assets/assassin_{shoulders,gloves,head}_*.png + assassin_sprites.txt

The body, both outfits and both blade sets are LEGACY parts: they stay exactly as they are in client/assets (never
redrawn, never in PixelFlow); export only writes the six new layers and the metadata that lists all eleven. The poses,
ramps and head transform come from the original project's tools/make_assassin_sprites.py, imported read-only, so
the new gear sits exactly on the old body. Shadow: a spiked leather pauldron, clawed fingerless gloves, a metal
forehead band with trailing cloth. Moon: silver crescent pauldrons, lavender gauntlets, a crescent circlet with a veil.
"""
import math

import cel_common as cc
from cel_common import V, unit, rig
import make_assassin_sprites as old   # ../Valhalla/tools, read-only: the existing artwork's poses and palette

SLOTS = {'armor': ('shadow', 'moon'), 'shoulders': ('shadow', 'moon'), 'gloves': ('shadow', 'moon'),
         'head': ('shadow', 'moon'), 'weapon': ('daggers', 'moonfang')}
LEGACY = ['body', 'armor_shadow', 'armor_moon', 'weapon_daggers', 'weapon_moonfang']
MATS = dict(old.MATS)
PALETTE, COLOR = cc.palette_of(MATS)
DEFAULT, CLIPS = old.DEFAULT, old.CLIPS
GEAR = {
    'armor': {'none': {'name': 'Simple cloth', 'defense': 0},
              'shadow': {'name': 'Nightweave', 'defense': 2}, 'moon': {'name': 'Moonveil', 'defense': 4}},
    'shoulders': {'none': {'name': 'Bare shoulders', 'defense': 0},
                  'shadow': {'name': 'Nightweave Spaulders', 'defense': 1}, 'moon': {'name': 'Moonveil Crescents', 'defense': 2}},
    'gloves': {'none': {'name': 'Bare hands', 'defense': 0},
               'shadow': {'name': 'Nightweave Claws', 'defense': 1}, 'moon': {'name': 'Moonveil Gauntlets', 'defense': 2}},
    'head': {'none': {'name': 'Bare head', 'defense': 0},
             'shadow': {'name': 'Shadow Brow Band', 'defense': 1}, 'moon': {'name': 'Moonveil Circlet', 'defense': 2}},
    'weapon': {'none': {'name': 'Empty hands', 'attack': 0},
               'daggers': {'name': 'Twin daggers', 'attack': 4}, 'moonfang': {'name': 'Moonfang blades', 'attack': 8}},
}


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R, xf, joints = cc.skeleton(p)
    inks = {part: cc.Ink(psi, COLOR) for part in SHEET.parts}
    head = cc.head_frame(inks['head_shadow'], xf, psi, p, turn=1.0)
    H, hd, front = head['H'], head['hd'], head['front']
    sw = p['sway']
    cuff = lambda j, f: j['hand'] + (j['elbow'] - j['hand']) * f

    for tier in ('shadow', 'moon'):
        ink = inks['shoulders_' + tier]
        moon = tier == 'moon'
        for key in 'LR':
            j = joints[key]
            sh = j['shoulder']
            sx = -1 if key == 'L' else 1
            out, upv = R @ V(sx, 0, 0), R @ V(0, 0, 1)
            if moon:
                # A silver crescent riding each shoulder with a lavender rune in the hollow.
                ink.bone(sh - out * .4 + upv * 2.4, sh + out * 5 - upv * 1.4, 4.4, 3.9, 'silver', -1.0, 2)
                ink.plate([sh + out * 1 + upv * 3, sh + out * 3.4 + upv * 11, sh + out * 6.6 + upv * 9, sh + out * 5 + upv * 3.4, sh + out * 3.8 + upv * 6.4], 'silver', 3)
                ink.plate([sh + out * 2.6 + upv * 4, sh + out * 3.6 + upv * 8.2, sh + out * 4.8 + upv * 6.6], 'rune', 3, True)
            elif sx < 0:
                # The leading shoulder: a layered dark pauldron with three steel spikes.
                ink.bone(sh - out * .6 + upv * 2.6, sh + out * 5.4 - upv * 1.2, 4.8, 4.2, 'night', -1.0, 2)
                ink.bone(sh + out * 2.6 + upv * .8, sh + out * 7 - upv * 3.6, 4.2, 3.6, 'leather', -1.15, 2)
                for off in (-1.6, 0, 1.6):
                    ink.plate([sh + out * (2 + off) + upv * 3.4, sh + out * (3.4 + off * 1.4) + upv * (9.6 - abs(off)), sh + out * (4.6 + off) + upv * 3.6], 'silver', 3 if off == 0 else 2)
            else:
                ink.bone(sh - out * .4 + upv * 2.2, sh + out * 4.4 - upv * 1.2, 3.8, 3.4, 'night', -1.0, 2)
                ink.bone(sh + out * 1.2 + upv * 3.4, sh + out * 3.6 + upv * 2.6, .9, .9, 'silver', -1.3, 2)

    for tier in ('shadow', 'moon'):
        ink = inks['gloves_' + tier]
        moon = tier == 'moon'
        for key in 'LR':
            j = joints[key]
            hand = j['hand']
            if moon:
                ink.bone(cuff(j, .44), hand + (j['elbow'] - hand) * .05, 2.9, 2.6, 'moon', -.85, 2)
                ink.bone(cuff(j, .44), cuff(j, .34), 3.3, 3.3, 'silver', -.95, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.5, 2.2, 'silver', -.9)
                ink.bone(hand + (j['elbow'] - hand) * .14, hand + (j['elbow'] - hand) * .1, 2.9, 2.9, 'rune', -1.05, 2)
            else:
                ink.bone(cuff(j, .4), hand + (j['elbow'] - hand) * .05, 2.7, 2.4, 'leather', -.85, 2)
                ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.4, 2.1, 'night', -.9)
                ink.bone(cuff(j, .4), cuff(j, .3), 3.0, 3.0, 'silver', -1.0, 1)
                # Three short steel claws over the knuckles, pointing along the blade.
                u = unit(hand - j['elbow'])
                for off in (-1.4, 0, 1.4):
                    base = hand + u * 1.4 + (R @ V(0, 0, 1)) * off * .6 + (R @ V(1, 0, 0)) * off * .7
                    ink.plate([base - u * .4, base + u * 4.6, base + u * .6 + (R @ V(0, 0, 1)) * .9], 'silver', 3, True)

    for tier in ('shadow', 'moon'):
        ink = inks['head_' + tier]
        moon = tier == 'moon'
        if not moon:
            # Metal forehead plate on a dark cloth band, knotted at the back with two long trailing tails.
            band = [(-10.9, 2.6), (-11.4, 7), (-7, 10.4), (0, 11.4), (7, 10.4), (11.4, 7), (10.9, 2.6), (7, 5.6), (0, 6.6), (-7, 5.6)]
            ink.poly([H(*q) for q in band], COLOR['night'][2], hd - 7)
            ink.poly([H(*q) for q in [(-10.9, 2.6), (-9.4, 3.4), (0, 6.6), (9.4, 3.4), (10.9, 2.6), (7, 5.6), (0, 6.6), (-7, 5.6)]], COLOR['night'][1], hd - 7.05, False)
            if front > -.4:
                ink.poly([H(*q) for q in [(-5, 6.2), (5, 6.2), (4.2, 10.8), (-4.2, 10.8)]], COLOR['silver'][2], hd - 7.3)
                ink.poly([H(*q) for q in [(-2.6, 8.4), (-.6, 10.2), (1.2, 10.2), (-.2, 8.4), (1.2, 6.8), (-.6, 6.8)]], COLOR['rune'][2], hd - 7.4, False)
            for sy, length in ((-1, 30), (1, 38)):
                ink.plate([xf(q) for q in [(sy * .8, -6.2, 88), (sy * 3.6, -6.2, 88), (sy * 8 + sw * 1.6, -11, 80 - length * .3), (sy * (7 + length * .12) + sw * 2.4, -15, 86 - length), (sy * 4 + sw * 2, -13.4, 88 - length * .8), (sy * 3 + sw * 1.4, -9.4, 80)]], 'scarf', 2)
        else:
            # Crescent circlet: two silver horns curving up from a thin band, a lavender gem, and a trailing veil.
            ink.poly([H(*q) for q in [(-10.8, 2.6), (-11.2, 6.6), (-7, 9.8), (0, 10.8), (7, 9.8), (11.2, 6.6), (10.8, 2.6), (7, 5.6), (0, 6.6), (-7, 5.6)]], COLOR['silver'][2], hd - 7)
            for sx in (-1, 1):
                horn = [(sx * 9.6, 7.6), (sx * 13.8, 12), (sx * 14.4, 19), (sx * 11, 24.6), (sx * 12, 18.6), (sx * 10.4, 13.4), (sx * 7, 9.4)]
                ink.poly([H(*q) for q in horn], COLOR['silver'][3], hd - 7.1)
                ink.poly([H(*q) for q in [(sx * 9.6, 7.6), (sx * 13.8, 12), (sx * 12.6, 14), (sx * 8.4, 9.6)]], COLOR['silver'][1], hd - 7.15, False)
            if front > -.4:
                ink.poly([H(*q) for q in [(-2, 8.6), (0, 12), (2, 8.6), (0, 6.2)]], COLOR['rune'][2], hd - 7.4)
                ink.poly([H(*q) for q in [(-.8, 8.6), (0, 10.6), (.8, 8.6), (0, 7.4)]], COLOR['rune'][3], hd - 7.45, False)
            for sy in (-1, 1):
                ink.plate([xf(q) for q in [(sy * .8, -6.2, 86), (sy * 4, -6.2, 86), (sy * 9 + sw * 1.6, -10.6, 74), (sy * 11 + sw * 2.2, -13.4, 54), (sy * 6 + sw * 2, -12.4, 58), (sy * 3.4 + sw * 1.4, -8.8, 74)]], 'ribbon', 2)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


NAKED = {slot: 'none' for slot in SLOTS}
SHADOW = {'armor': 'shadow', 'shoulders': 'shadow', 'gloves': 'shadow', 'head': 'shadow', 'weapon': 'daggers'}
MOON = {'armor': 'moon', 'shoulders': 'moon', 'gloves': 'moon', 'head': 'moon', 'weapon': 'moonfang'}
SHEET = cc.Sheet(
    'assassin', files='assassin', pixel='assassin_cel_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read()]), legacy=LEGACY,
    groups={'shadow': ['shoulders_shadow', 'gloves_shadow', 'head_shadow'], 'moon': ['shoulders_moon', 'gloves_moon', 'head_moon']},
    default_equip={'armor': 'shadow', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'daggers'},
    meta={'attack': {'duration': .4, 'impact': .2}, 'portrait': [57, 15, 46, 46]},
    combos=[('naked', NAKED), ('shadow', SHADOW), ('moon', MOON)])

if __name__ == '__main__':
    SHEET.cli()
