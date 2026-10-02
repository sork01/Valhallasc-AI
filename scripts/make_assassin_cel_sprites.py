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
import generic_gear as gg
from cel_common import V, unit, rig
import make_assassin_sprites as old   # ../Valhalla/tools, read-only: the existing artwork's poses and palette

SLOTS = {'armor': ('shadow', 'moon'), 'shoulders': ('shadow', 'moon', 'ironhide'), 'gloves': ('shadow', 'moon', 'duelist'),
         'head': ('shadow', 'moon', 'ironhide'), 'weapon': ('daggers', 'moonfang'),
         'pants': ('wayfarer',), 'necklace': ('moonstone',), 'accessory': ('amber',)}
LEGACY = ['body', 'armor_shadow', 'armor_moon', 'weapon_daggers', 'weapon_moonfang']
if cc.FEMALE:      # the woman's body and outfits are drawn here; her blades are the existing assassin_weapon_* atlases
    LEGACY = ['weapon_daggers', 'weapon_moonfang']
MATS = {**old.MATS, **gg.GEAR_MATS}
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


def female_layers(inks, p, psi, R, xf, joints):
    """The woman's body and both outfits, after the original body/outfit drawing in ../Valhalla/tools/make_assassin_sprites.py
    on the shared female body: an hourglass torso, long sleek hair, the same angular fringe and the same garments."""
    torso = lambda ink, mat, *a: cc.torso(ink, xf, mat, *a)
    body = inks['body']
    cc.base_body(body, xf, joints, R)
    head = cc.head_frame(body, xf, psi, p, turn=1.0)
    H, hd, front = head['H'], head['hd'], head['front']
    sw = p['sway']
    # Long straight hair to the hips (the back sheet), then the legacy angular crown and fringe wedges.
    body.plate([xf(q) for q in [(-6, -5, 84), (6, -5, 84), (9 + sw * .8, -8.4, 62), (9.6 + sw * 1.4, -10, 40), (6 + sw * 2, -11, 27), (1 + sw * 2.2, -10.6, 33), (-4 + sw * 2, -11, 26), (-9.4 + sw * 1.4, -10, 40), (-9 + sw * .8, -8.4, 62)]], 'hair', 1)
    body.plate([xf(q) for q in [(-2.4, -5.4, 82), (2.8, -5.4, 82), (4 + sw, -9.6, 60), (3 + sw * 1.8, -10.8, 40), (0 + sw * 2, -10.4, 44), (-2 + sw, -9.6, 60)]], 'hair', 2, True)
    if not cc.face(body, head, p):
        body.poly([H(*q) for q in [(-9, 8), (-10, 0), (-8, -8), (-4, -10), (5, -9), (9, -5), (10, 4), (6, 12), (-3, 13)]], COLOR['hair'][1], hd - 5)
    crown = [(-10, 2), (-11, 8), (-8, 12), (-9, 15), (-3, 13), (1, 16), (3, 13),
             (8, 14), (8, 11), (11, 8), (10, 2), (8, -3), (6, 2), (4, -1), (1, 6), (-2, 1), (-5, 6), (-8, -2)]
    body.poly([H(*q) for q in crown], COLOR['hair'][1], hd - 6)
    for wedge in [[(-8, 10), (-2, 12), (-4, 6), (-8, 3)], [(-1, 12), (3, 13), (6, 7), (2, 7)], [(6, 11), (9, 8), (8, 3)]]:
        body.poly([H(*q) for q in wedge], COLOR['hair'][2], hd - 6.1, False)
    body.poly([H(*q) for q in [(-6, 11), (-2, 12), (-3, 10), (-6, 8)]], COLOR['hair'][3], hd - 6.2, False)
    for sx_ in (-1, 1):
        body.plate([xf(q) for q in [(sx_ * 9.4, -1.2, 86), (sx_ * 11.2, -1.2, 80), (sx_ * 11, .8, 64), (sx_ * 9.2, .6, 62), (sx_ * 8.6, -.4, 74)]], 'hair', 2 if sx_ > 0 else 1, True)

    for key, mat, scarf in [('armor_shadow', 'night', 'scarf'), ('armor_moon', 'moon', 'ribbon')]:
        ink = inks[key]
        torso(ink, mat, 8.6, 4.3, 36, 69)
        ink.plate([xf(q) for q in [(-8, 4.5, 66), (1, 4.5, 67), (7, 4.5, 43), (-1, 4.5, 40)]], mat, 1)
        ink.plate([xf(q) for q in [(-7, 4.7, 66), (-6, 4.7, 66), (3, 4.7, 44), (2, 4.7, 44)]], 'silver', 1, True)
        ink.plate([xf(q) for q in [(-8, 4.8, 43), (8, 4.8, 43), (8, 4.8, 39), (-8, 4.8, 39)]], 'leather', 1)
        for sx, name in ((-1, 'L'), (1, 'R')):
            j = joints[name]
            ink.bone(j['shoulder'], j['elbow'], 3.6, 2.8, mat, -.8)
            ink.bone(j['elbow'] + (j['hand'] - j['elbow']) * .45, j['elbow'] + (j['hand'] - j['elbow']) * .82, 2.9, 2.3, 'leather', -.6)
            ink.bone(j['knee'] + (j['ankle'] - j['knee']) * .2, j['ankle'], 3.1, 2.5, 'leather', -.8)
            ink.bone(j['ankle'] + V(0, -1, -1), j['ankle'] + V(0, 4.5, -2), 2.5, 2.5, 'leather', -.8)
            if mat == 'moon':
                ink.plate([xf(q) for q in [(sx * 6, -4, 40), (sx * 10, -4, 40), (sx * (14 + sw), -7, 23), (sx * 9, -5, 18), (sx * 6, -4, 31)]], mat, 2)
                ink.bone(j['shoulder'], j['shoulder'] + R @ V(sx * 3, 0, -3), 3.1, 2, 'silver', -1)
        ink.plate([xf(q) for q in [(-5, 4.8, 76), (5, 4.8, 76), (6, 4.8, 70), (0, 5, 67), (-6, 4.8, 70)]], scarf, 2)
        for sx, length in [(-1, 18), (1, 24)]:
            wind = sw * 1.4
            ink.plate([xf(q) for q in [(sx * 3, -5, 74), (sx * 7, -5, 74), (sx * 13 + wind, -12, 66), (sx * length + wind, -19, 57),
                      (sx * (length - 7) + wind, -18, 56), (sx * 10 + wind, -12, 62)]], scarf, 2)
        if mat == 'moon':
            ink.plate([xf(q) for q in [(-1.8, 4.9, 54), (0, 5, 58), (1.8, 4.9, 54), (0, 5, 50)]], 'rune', 2)


def render_frame(clip, facing, k):
    p = {**DEFAULT, **CLIPS[clip][2](k)}
    psi = rig.psi_for(facing)
    R, xf, joints = cc.skeleton(p)
    inks = {part: cc.Ink(psi, COLOR) for part in SHEET.parts}
    if cc.FEMALE:
        female_layers(inks, p, psi, R, xf, joints)
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
    gg.draw(inks, R, xf, joints, head)
    flash = clip in ('hurt', 'die') and k == 0
    return {part: ink.resolve(flash) for part, ink in inks.items()}


NAKED = {slot: 'none' for slot in SLOTS}
SHADOW = {'armor': 'shadow', 'shoulders': 'shadow', 'gloves': 'shadow', 'head': 'shadow', 'weapon': 'daggers'}
MOON = {'armor': 'moon', 'shoulders': 'moon', 'gloves': 'moon', 'head': 'moon', 'weapon': 'moonfang'}
GENERIC = {'armor': 'shadow', 'shoulders': 'ironhide', 'gloves': 'duelist', 'head': 'ironhide', 'pants': 'wayfarer',
           'necklace': 'moonstone', 'accessory': 'amber', 'weapon': 'daggers'}
SHEET = cc.Sheet(
    'assassin', files='assassin', pixel='assassin_cel_', mats=MATS, clips=CLIPS, slots=SLOTS, gear=GEAR, render=render_frame,
    revision=cc.revision_of([open(__file__).read(), open(gg.__file__).read()]), legacy=LEGACY, legacy_files='assassin',
    # Explicit groups, so the class-independent layers are listed here (Sheet only adds them when it picks the groups itself).
    groups=({'shadow': ['body', 'armor_shadow', 'shoulders_shadow', 'gloves_shadow', 'head_shadow'],
             'moon': ['ref_body', 'armor_moon', 'shoulders_moon', 'gloves_moon', 'head_moon'],
             'generic': ['ref_body', 'head_ironhide', 'shoulders_ironhide', 'gloves_duelist', 'pants_wayfarer'],
             'trinkets': ['ref_body', 'necklace_moonstone', 'accessory_amber']} if cc.FEMALE else
            {'shadow': ['shoulders_shadow', 'gloves_shadow', 'head_shadow'], 'moon': ['shoulders_moon', 'gloves_moon', 'head_moon'],
             'generic': ['head_ironhide', 'shoulders_ironhide', 'gloves_duelist', 'pants_wayfarer'],
             'trinkets': ['necklace_moonstone', 'accessory_amber']}),
    default_equip={'armor': 'shadow', 'shoulders': 'none', 'gloves': 'none', 'head': 'none', 'weapon': 'daggers'},
    meta={'attack': {'duration': .4, 'impact': .2}, 'portrait': [57, 15, 46, 46]},
    combos=[('naked', NAKED), ('shadow', SHADOW), ('moon', MOON), ('generic', GENERIC)])

if __name__ == '__main__':
    SHEET.cli()
