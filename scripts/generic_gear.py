"""Worn art for the class-independent gear (world/items.txt, class = null), drawn on any cel class's rig.

Six layers, the same design on every class and gender (the shared skeleton, head billboard and torso do the fitting):
  head_ironhide       Ironhide Helm        bronze beetle-shell dome, steel ridge and brow band, cheek plates, nose guard
  shoulders_ironhide  Ironhide Pauldrons   layered bronze shell plates, a steel ridge, a spike
  gloves_duelist      Duelist Gloves       tan riding gloves, flared cream cuffs, a brass buckle
  pants_wayfarer      Wayfarer Pants       brown travelling trousers, cream knee patches and rolled cuffs
  necklace_moonstone  Moonstone Necklace   a steel chain and a pale moonstone in a silver bezel
  accessory_amber     Amber Ring           a gold band with an amber stone on the left hand

A class script adds GEAR_MATS to its MATS, lists VARIANTS under its slots, calls draw() from its render_frame and
passes this file's source to cc.revision_of so an edit here re-renders the class. The icons in make_item_sprites.py
are the design reference.
"""
import math

import numpy as np

import cel_common as cc
from cel_common import V, unit

# Hex values are nudged off the item icons' ramps so they never collide with a class's own materials
# (cc.palette_of refuses duplicates), and never use #ffffff / #18182a, which the palette reserves.
GEAR_MATS = {
    'ironhide': ['#3b2511', '#6f4721', '#a97530', '#dda961'],
    'ironsteel': ['#3b4759', '#6b7b93', '#afbed4', '#eff5fe'],
    'ironbrass': ['#6f4b13', '#b1811f', '#e9b941', '#fff1a1'],
    'dueltan': ['#3c2a1f', '#5d4030', '#876148', '#b98d6a'],
    'duelcream': ['#8d7d66', '#c7b79b', '#ebdfc3', '#fffaea'],
    'wayfarer': ['#3a2a1e', '#5c4330', '#84634a', '#ad8a69'],
    'moonstone': ['#5b5b83', '#9b9bc5', '#d5d5f3', '#fdfdfe'],
    'amberstone': ['#6b2b09', '#b9591b', '#f19b2d', '#ffe181'],
}
VARIANTS = {'head': 'ironhide', 'shoulders': 'ironhide', 'gloves': 'duelist', 'pants': 'wayfarer',
            'necklace': 'moonstone', 'accessory': 'amber'}
PARTS = [f'{slot}_{variant}' for slot, variant in VARIANTS.items()]
NAMES = {
    'head': ('Ironhide Helm', 2), 'shoulders': ('Ironhide Pauldrons', 2), 'gloves': ('Duelist Gloves', 1),
    'pants': ('Wayfarer Pants', 2), 'necklace': ('Moonstone Necklace', 0), 'accessory': ('Amber Ring', 0),
}


def helm(ink, head):
    H, hd, front, side = head['H'], head['hd'], head['front'], head['side']
    outer = [(-12.4, -7.5), (-13, 5), (-10.8, 14.4), (-5.2, 20), (0, 21.4), (5.2, 20), (10.8, 14.4), (13, 5), (12.4, -7.5)]
    inner = [(9.6, -5.6), (9.6, 5), (6.6, 9.4), (0, 10.4), (-6.6, 9.4), (-9.6, 5), (-9.6, -5.6)]
    backview = front < -.4
    hd = hd - 4 if backview else hd      # from behind the dome must clear the hair ribbon on the back of the head
    nape = [(-11.4, -1.5), (-12.4, 5), (-10.8, 14.4), (-5.2, 20), (0, 21.4), (5.2, 20), (10.8, 14.4), (12.4, 5), (11.4, -1.5), (10.4, -3.6), (6, -4.6), (0, -4.9), (-6, -4.6), (-10.4, -3.6)]
    ink.poly([H(*q) for q in (nape if backview else outer + inner)], cc_color(ink, 'ironhide', 2), hd - 7)
    # shell ribs running down from the crown, lit left, dark right
    for x_top, x_low in ((-6.6, -11.6), (-3.2, -7), (3.2, 7), (6.6, 11.6)):
        ink.poly([H(x_top - .7, 18.8), H(x_top + .7, 18.8), H(x_low + .8, 8), H(x_low - .8, 8)], cc_color(ink, 'ironhide', 1), hd - 7.05, False)
    ink.poly([H(*q) for q in [(-10.8, 14.4), (-5.2, 20), (0, 21.4), (-1, 18), (-6.5, 14.4), (-9.6, 8.5), (-13, 5)]], cc_color(ink, 'ironhide', 3), hd - 7.04, False)
    # steel ridge over the crown and a brow band
    ink.poly([H(*q) for q in [(-1.5, 21.6), (1.5, 21.6), (2, 12), (-2, 12)]], cc_color(ink, 'ironsteel', 2), hd - 7.2)
    ink.poly([H(*q) for q in [(-13.2, 6.4), (-13.2, 9.8), (-6.5, 11.8), (0, 12.4), (6.5, 11.8), (13.2, 9.8), (13.2, 6.4),
                              (6.5, 8.6), (0, 9), (-6.5, 8.6)]], cc_color(ink, 'ironsteel', 2), hd - 7.3)
    ink.poly([H(*q) for q in [(-13.2, 6.4), (-13.2, 8), (-6.5, 10), (0, 10.6), (-6.5, 8.6)]], cc_color(ink, 'ironsteel', 3), hd - 7.32, False)
    if backview:
        return
    for sx in (-1, 1):       # cheek plates beside the face with a rivet each
        ink.poly([H(sx * 9.6, 5), H(sx * 13, 5), H(sx * 13.4, -7), H(sx * 11.6, -11), H(sx * 9.6, -9)], cc_color(ink, 'ironhide', 2 if sx > 0 else 1), hd - 7.1)
        ink.poly([H(sx * 11.4, 2.6), H(sx * 12.4, 2.6), H(sx * 12.4, 3.6), H(sx * 11.4, 3.6)], cc_color(ink, 'ironbrass', 3), hd - 7.4, False)
    cx = side * 3
    ink.poly([H(cx - 1.1, 9), H(cx + 1.1, 9), H(side * 5 + .9, -3.6), H(side * 5, -5.2), H(side * 5 - .9, -3.6)], cc_color(ink, 'ironsteel', 2), hd - 7.35)


def cc_color(ink, mat, tone):
    return ink.color[mat][tone]


def shoulders(ink, joints, R):
    for key in 'LR':
        j = joints[key]
        sh = j['shoulder']
        sx = -1 if key == 'L' else 1
        out, upv = R @ V(sx, 0, 0), R @ V(0, 0, 1)
        ink.bone(sh - out * .8 + upv * 2.6, sh + out * 5.8 - upv * 1.4, 5.4, 4.8, 'ironhide', -1.0, 2)
        ink.bone(sh + out * 2.4 + upv * .8, sh + out * 7.2 - upv * 3.8, 4.6, 3.9, 'ironhide', -1.15, 1)
        ink.bone(sh + out * .2 + upv * 4.6, sh + out * 5.4 + upv * 1.6, 1.0, .9, 'ironsteel', -1.45, 2)
        ink.plate([sh + out * 1.0 + upv * 4, sh + out * 2.2 + upv * 10.6, sh + out * 3.6 + upv * 4.2], 'ironsteel', 3)
        ink.bone(sh + out * 4.4 + upv * 1.8, sh + out * 5 + upv * 1.4, .9, .9, 'ironbrass', -1.5, 3)


def gloves(ink, joints, R):
    for key in 'LR':
        j = joints[key]
        el, hand = j['elbow'], j['hand']
        ink.bone(hand + (el - hand) * .5, hand + (el - hand) * .06, 2.8, 2.5, 'dueltan', -.8)
        ink.bone(hand + (el - hand) * .52, hand + (el - hand) * .36, 3.5, 3.1, 'duelcream', -.95, 2)
        ink.bone(hand + (el - hand) * .44, hand + (el - hand) * .43, 1.0, 1.0, 'ironbrass', -1.3, 3)
        ink.bone(hand - R @ V(0, 0, 1), hand + R @ V(0, 0, 1.9), 2.5, 2.2, 'dueltan', -.9)
        ink.bone(hand + R @ V(0, 0, .5) + (el - hand) * .02, hand + R @ V(0, 0, 1) + (el - hand) * .02, 1.0, 1.0, 'dueltan', -1.2, 3)


def pants(ink, joints):
    for key in 'LR':
        j = joints[key]
        hip, knee, ankle = j['hip'], j['knee'], j['ankle']
        ink.bone(hip, knee, 3.9, 3.4, 'wayfarer', -.3, 2)
        ink.bone(knee, ankle, 3.3, 2.7, 'wayfarer', -.3, 2)
        ink.bone(knee + (hip - knee) * .08, knee + (ankle - knee) * .22, 3.5, 3.5, 'duelcream', -.5, 2)       # knee patch
        ink.bone(ankle + (knee - ankle) * .2, ankle + (knee - ankle) * .06, 3.0, 3.1, 'duelcream', -.5, 3)    # rolled cuff
        ink.bone(hip + (knee - hip) * .35, hip + (knee - hip) * .34, 1.2, 1.2, 'ironbrass', -.6, 3)           # a button


def necklace(ink, xf):
    chain = [(-3.6, 2.6, 70), (-3.9, 4.6, 66.4), (-2.6, 6.0, 63.2), (0, 6.3, 61.6), (2.6, 6.0, 63.2), (3.9, 4.6, 66.4), (3.6, 2.6, 70)]
    for a, b in zip(chain, chain[1:]):
        ink.bone(xf(a), xf(b), .75, .75, 'ironsteel', -1.6, 2)
    back = [(-3.6, 2.6, 70), (-4, -1, 70.4), (-3.2, -3.6, 70.4), (0, -4.4, 70.4), (3.2, -3.6, 70.4), (4, -1, 70.4), (3.6, 2.6, 70)]
    for a, b in zip(back, back[1:]):
        ink.bone(xf(a), xf(b), .5, .5, 'ironsteel', -1.2, 1)
    ink.plate([xf(q) for q in [(0, 6.6, 65), (2.9, 6.6, 61.2), (0, 6.6, 56.8), (-2.9, 6.6, 61.2)]], 'ironsteel', 2)
    ink.plate([xf(q) for q in [(0, 6.8, 63.8), (2.0, 6.8, 61.2), (0, 6.8, 58.2), (-2.0, 6.8, 61.2)]], 'moonstone', 2, True)
    ink.plate([xf(q) for q in [(0, 6.9, 63.8), (0, 6.9, 58.2), (-2.0, 6.9, 61.2)]], 'moonstone', 3, True)


def ring(ink, joints, R):
    j = joints['L']
    hand = j['hand']
    up = R @ V(0, 0, 1)
    ink.bone(hand + up * .8, hand + up * 1.5, 2.7, 2.6, 'ironbrass', -1.4, 2)
    ink.bone(hand + up * 1.5, hand + up * 2.1, 1.9, 1.5, 'amberstone', -1.6, 3)


def draw(inks, R, xf, joints, head):
    """Fill the six generic layers of `inks` (a dict of cc.Ink keyed by part name)."""
    helm(inks['head_ironhide'], head)
    shoulders(inks['shoulders_ironhide'], joints, R)
    gloves(inks['gloves_duelist'], joints, R)
    pants(inks['pants_wayfarer'], joints)
    necklace(inks['necklace_moonstone'], xf)
    ring(inks['accessory_amber'], joints, R)
