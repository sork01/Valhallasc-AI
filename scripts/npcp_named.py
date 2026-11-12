#!/usr/bin/env python3
"""Authored looks for missing named people; assignments and world data stay separate.

Each row: stable NPC id | player-rig archetype | held prop | headwear | hair |
individual garment/signature. Explicit choices preserve the person's occupation.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REUSE_NATIVE = {'reuse_courier': 'courier', 'reuse_merchant': 'merchant'}
REUSE_ALIASES = {
    'reuse_treefolk_merchant': 'named_hw_sorter',
    'reuse_treefolk_courier': 'named_hw_courier',
    'reuse_treefolk_sentinel': 'named_hw_captain',
    'reuse_treefolk_steward': 'named_hw_storyteller',
}
ROWS = '''
fold_hild|pilgrim|crook|straw|long|wool
fold_torvald|elder|tablet|hood|beard|runes
salt_ragna|steward|spool|band|braid|net
salt_odd|fisher|fish|beanie|beard|oilskin
apple_maren|gardener|apples|straw|bun|apples
apple_sten|gardener|honey|veil|crop|honey
dock_skipper|fisher|reins|cap|beard|captain
apple_lotta|baker|bread|ribbon|long|flour
anvil_ingrid|carpenter|hammer|hood|braid|stone
anvil_bror|smith|hammer|band|beard|coal
ford_tora|steward|tablet|band|long|lava
ford_olaf|stablehand|reins|straw|crop|harness
ford_ulf|stablehand|satchel|hood|crop|patched
hearth_sigrid|lamplighter|lantern|hood|long|embers
hearth_elof|scholar|telescope|cap|crop|stars
rime_dw_hild|sentinel|spear|hood|braid|fur
rime_dw_nils|stablehand|reins|beanie|beard|sled
rime_sw_runa|ranger|harpoon|band|long|rope
rime_sw_arne|ranger|bow|none|crop|fangs
rime_pk_gunnar|sentinel|staff|beanie|beard|snow
rime_pk_sif|scholar|scroll|hood|long|map
fen_rh_brid|steward|staff|band|braid|reeds
fen_rh_sten|fisher|fish|hood|crop|creel
fen_dk_magnus|carpenter|saw|cap|beard|dike
fen_dk_linnea|pilgrim|chest|band|long|salvage
fen_gr_ysolde|sentinel|spear|helm|crop|garrison
fen_gr_per|scholar|compass|hood|crop|survey
fen_gr_trader|merchant|key|hood|beard|grave
wyrd_gf_hild|pilgrim|staff|hood|braid|knots
wyrd_gf_orm|ranger|grain|feather|long|quills
wyrd_gf_trader|weaver|spool|ribbon|braid|stitches
wyrd_rw_dagny|sentinel|hammer|band|crop|storm
wyrd_rw_fenn|gardener|staff|beanie|beard|wool
wyrd_rw_trader|merchant|harpoon|turban|braid|horns
wyrd_hm_sunniva|steward|lantern|hood|long|hearth
wyrd_hm_loom|weaver|spool|cap|crop|threads
sky_wr_vigdis|ranger|reins|band|braid|hound
sky_wr_leif|lamplighter|lantern|feather|crop|beacon
sky_wr_trader|merchant|scales|cap|long|fangs
sky_ss_ingrid|sentinel|spear|helm|braid|lightning
sky_ss_bjorn|scholar|tablet|cap|beard|tally
sky_ss_trader|weaver|fan|ribbon|long|feathers
sky_el_gunnar|sentinel|staff|hood|crop|nest
sky_el_hallveig|bard|trumpet|circlet|long|song
sky_el_trader|merchant|spool|feather|crop|quills
deep_lr_solveig|lamplighter|lantern|cap|long|brass
deep_lr_torvald|ranger|reins|cap|crop|maze
deep_lr_trader|merchant|scales|turban|braid|teeth
deep_gw_bergljot|steward|key|circlet|long|tide
deep_gw_hallbjorn|smith|hammer|none|shaved|reef
deep_gw_trader|gardener|flowers|veil|long|kelp
deep_dw_ottilia|physician|bell|hood|long|chapel
deep_dw_skuli|carpenter|staff|beanie|beard|grave
deep_dw_trader|merchant|chest|band|braid|coins
nacre_harbourmaster|steward|harpoon|circlet|long|pearl
nacre_gatewarden|sentinel|key|crown|braid|fivekeys
astral_cr_mael|bard|bell|circlet|long|choir
astral_cr_ide|scholar|telescope|band|crop|comet
astral_cr_trader|lamplighter|lantern|veil|long|hollow
astral_cw_brisa|sentinel|spear|circlet|braid|tailfire
astral_cw_oren|smith|hammer|goggles|crop|shell
astral_fh_aurel|steward|orb|hood|long|starhearth
astral_fh_dov|carpenter|tablet|hood|crop|starline
prism_mf_ilsa|steward|orb|circlet|braid|mirror
prism_mf_dov|alchemist|compass|goggles|crop|lens
prism_ws_marek|lamplighter|lantern|band|beard|sun
prism_ws_ottilie|weaver|fan|veil|long|sunveil
prism_cf_runa|sentinel|tablet|hood|braid|greyflint
prism_cf_teo|carpenter|saw|band|crop|fangcarver
orrery_bc_tolla|herald|bell|beret|braid|brassbell
orrery_bc_fenn|smith|hammer|cap|crop|ratchet
orrery_cn_isolde|sentinel|spear|helm|long|crownwatch
orrery_cn_quill|scholar|scroll|cap|crop|hourglass
orrery_sw_kestrel|ranger|compass|hood|long|shards
orrery_sw_anselm|carpenter|saw|beret|crop|glass
storm_rs_edda|sentinel|spear|band|braid|ironrod
storm_rs_jorun|weaver|spool|none|crop|reedweave
storm_fp_halv|lamplighter|lantern|hood|beard|stormeye
storm_fp_ingrid|smith|hammer|goggles|long|fulgur
storm_bh_torvald|steward|tablet|cap|beard|seawall
storm_bh_sigrid|carpenter|hammer|cap|crop|masonry
sv_hw_marit|gardener|honey|veil|braid|honeycomb
sv_hw_ansgar|sentinel|staff|straw|crop|wax
sv_wf_greta|steward|scroll|straw|long|strawmark
sv_wf_ottar|carpenter|flail|straw|crop|thresh
sv_er_ingrid|pilgrim|seed|hood|long|oakstair
rw_bp_aldis|sentinel|key|beret|braid|frayed
rw_bp_pernille|weaver|spool|ribbon|long|spool
rw_tp_ysolde|steward|fan|circlet|waves|fringe
rw_tp_calder|bard|fan|feather|crop|plumes
rw_gr_ruben|innkeeper|mug|straw|beard|marigold
rw_gr_lisbet|herald|bell|band|long|jingles
tg_rg_ixel|sentinel|harpoon|band|braid|marrow
tg_rg_pomo|weaver|spool|none|long|barkcloth
tg_dr_kessa|bard|drum|ribbon|braid|drum
tg_dr_yarrow|carpenter|saw|hood|crop|hides
tg_sp_marek|ranger|staff|hood|long|stilts
tg_sp_odile|smith|hammer|goggles|long|scaleplates
ve_gw_ilsa|sentinel|spear|band|braid|glade
ve_gw_nuri|weaver|spool|ribbon|long|moss
ve_rs_corvin|ranger|staff|hood|crop|ashsteps
ve_eb_dessa|steward|tablet|circlet|long|barkguard
ve_eb_taro|carpenter|saw|band|long|splinters
hw_steward|steward|scroll|hood|long|veins
hw_smith|smith|hammer|hood|crop|pithfire
hw_healer|physician|bottle|veil|long|dewleaf
hw_innkeeper|innkeeper|mug|ribbon|bun|sapwell
hw_captain|sentinel|spear|helm|braid|barkshield
hw_lamplighter|lamplighter|lantern|cap|bun|glowpods
hw_weaver|weaver|spool|band|crop|threadroot
hw_logwarden|elder|cane|beanie|beard|growthrings
hw_bellringer|herald|bell|ribbon|crop|dewdrop
hw_sorter|gardener|grain|cap|crop|seeds
hw_storyteller|bard|book|circlet|long|stories
hw_baker|baker|bread|toque|bun|barkloaf
hw_tapper|carpenter|waterjug|band|crop|sap
hw_gardener|gardener|flowers|hood|long|fungus
hw_glassblower|alchemist|alembic|goggles|crop|amber
hw_courier|courier|satchel|feather|crop|branchpost
hw_pilgrim|pilgrim|staff|hood|long|treewalk
hw_kid_pip|child|kite|cap|bun|acorn
hw_kid_mina|child|flowers|ribbon|crop|fern
hw_kid_tove|child|seed|hood|long|burl
hw_kid_ake|child|staff|band|crop|twig
lp_ww_hesper|sentinel|spear|turban|braid|quillguard
lp_ww_yeva|weaver|spool|veil|long|pelt
lp_sp_soraya|steward|waterjug|veil|braid|saltpan
lp_sp_tomas|alchemist|alembic|goggles|crop|blueglass
lp_ew_karim|ranger|compass|turban|crop|basin
lp_ew_lunet|ranger|bow|feather|long|fletching
fw_bw_brynja|stablehand|reins|beanie|braid|bellsled
fw_au_sigrun|lamplighter|lantern|beanie|long|aurora
fw_rw_leif|fisher|reins|hood|beard|deeprope
cn_sc_halvar|scholar|tablet|hood|beard|slaterunes
cn_wb_ingrid|carpenter|saw|band|long|palebark
cn_sg_ragna|sentinel|spear|beanie|braid|thunder
yo_wm_ingrid|ranger|compass|beanie|long|wintercairn
yo_wm_orm|weaver|spool|hood|beard|silverpelt
yo_th_halvar|sentinel|harpoon|cap|crop|copperwave
yo_th_sunniva|gardener|grain|hood|long|acorns
yo_lf_tove|steward|orb|straw|braid|sunwheel
yo_lf_arvid|baker|waterjug|hood|crop|kiln
ew_cw_ragna|ranger|telescope|hood|braid|caldera
ew_cw_sten|smith|hammer|hood|crop|ash
ew_cq_brage|sentinel|harpoon|helm|beard|quayslag
ew_cq_tove|carpenter|saw|hood|long|kilnplates
ew_gh_sunniva|steward|key|circlet|long|glassbank
ew_gh_ivar|smith|hammer|cap|crop|slag
'''

# Signature material and garment cuts are independent of the player's body ratio.
CUTS = {
    'pilgrim': (15, 12.2, 8), 'elder': (18, 11.2, 7.8),
    'sentinel': (31, 10.2, 6), 'steward': (12, 11.4, 7.8),
    'fisher': (27, 11, 7), 'gardener': (29, 11.5, 7),
    'smith': (34, 10.2, 6), 'carpenter': (33, 10.6, 6.2),
    'scholar': (11, 12, 8), 'weaver': (17, 12.6, 8),
    'merchant': (13, 13.5, 8.8), 'ranger': (32, 10.4, 6.5),
    'stablehand': (35, 9.6, 5.8), 'bard': (32, 10.8, 6.8),
    'lamplighter': (12, 12.8, 8.2), 'herald': (29, 10.4, 7),
    'physician': (16, 12.8, 8.4), 'innkeeper': (15, 14, 9),
    'baker': (28, 11.2, 7), 'alchemist': (25, 12.4, 8),
    'courier': (33, 10.2, 6), 'child': (24, 11.4, 7.5),
}


def catalog():
    return [dict(zip(('id', 'arch', 'prop', 'hat', 'hair', 'signature'), line.split('|')))
            for line in ROWS.strip().splitlines()]


def install(designs, G):
    """Only add the authored keys; old designs and assignments are immutable."""
    for prop, held in [('crook', 'staff'), ('apples', 'flowers'), ('honey', 'waterjug'),
                       ('flail', 'staff'), ('drum', 'flowers')]:
        G.PROPS[prop] = lambda *args, prop=prop: held_prop(G, prop, *args)
        G.HOLD[prop] = dict(G.HOLD[held])
        G.WALK_HOLD += (prop,)
        if prop in ('apples', 'drum'):
            G.TWO.add(prop)
    plan = json.loads((ROOT / 'docs/npc-named-plan.txt').read_text())
    for person in plan['people']:
        if person['classification'] != 'named':
            continue
        s = person['design']
        base = dict(designs[s['arch']])
        look = person['identity']
        merfolk = look.get('species') == 'merfolk'
        tree = person['zone'] in (23, 24)
        base.update(name=person['name'], general=False, arch=s['arch'],
                    prop=s['prop'], hat=s['hat'], hair=s['hair'],
                    coat=person['color'], skin=look.get('skin', '#edc5a1'),
                    hairc=look.get('hair', '#755841'), hatc=look.get('hatColor'),
                    female=s['female'], ornament=None, tail=look.get('tail', '#59b3ab') if merfolk else None,
                    tree=tree, named=True, signature=s['signature'], cut=s['cut'])
        if tree:
            base.update(skin=s['bark'], hairc=s['leaf'])
        hem, width, depth = CUTS[s['arch']]
        # Explicit per-person cut changes coat length, side panel and shoulder detail.
        base['outfit'] = dict(skirt=(hem + s['cut'], width + .35 * s['cut'], depth), hem_trim='accent')
        designs[person['designKey']] = base
    for key, source in {**REUSE_NATIVE, **REUSE_ALIASES}.items():
        designs[key] = dict(designs[source], general=True, reuse=True,
                            name='Reused ' + key.removeprefix('reuse_').replace('_', ' '))


def held_prop(G, name, ink, xf, joints, R, p, c):
    h = joints['L']['hand']
    if name in ('crook', 'flail'):
        G.line3(ink, h + G.V(0, 0, -16), h + G.V(0, 0, 43), 1.4, 'wood')
        if name == 'crook':
            points = [(0,43),(1,48),(5,51),(10,50),(13,46),(12,42),(9,40)]
            ink.ribbon([h + G.V(x, 0, z) for x,z in points], 1.5, 1.5, 'wood', 2, -.5)
        else:
            G.line3(ink, h + G.V(0,0,43), h + G.V(9,0,37), .7, 'leather')
            G.line3(ink, h + G.V(9,0,37), h + G.V(13,0,17), 2.6, 'wood')
    elif name == 'honey':
        ink.plate([h+G.V(x,2,z) for x,z in [(-7,-4),(7,-4),(9,0),(8,13),(-8,13),(-9,0)]], 'gold', 2)
        ink.plate([h+G.V(x,2.5,z) for x,z in [(-8,12),(8,12),(8,16),(-8,16)]], 'wood', 2)
        for z in (1,6,10):
            G.line3(ink,h+G.V(-6,3,z),h+G.V(6,3,z),.6,'trim',tone=3)
    else:
        # The carried object rests between two animated hands, with visible supporting fingers.
        b = (h + joints['R']['hand']) / 2
        if name == 'apples':
            ink.plate([b+G.V(x,2,z) for x,z in [(-13,0),(13,0),(10,-12),(-10,-12)]], 'wood', 2)
            for x,z in [(-7,3),(0,5),(7,3)]:
                G._ball(ink,b+G.V(x,3,z),3.5,'accent',2)
                G.line3(ink,b+G.V(x,3,z+3),b+G.V(x+1,3,z+6),.5,'leaf')
        else:
            ink.plate([b+G.V(x,2,z) for x,z in [(-13,6),(13,6),(11,-13),(-11,-13)]], 'leather', 2)
            ink.plate([b+G.V(x,2.5,z) for x,z in [(-13,5),(13,5),(13,8),(-13,8)]], 'cream', 3)
            for x in (-9,-3,3,9):
                G.line3(ink,b+G.V(x,3,4),b+G.V(-x,3,-11),.5,'trim')
        G.hand_cover(ink,joints,R,'R')
    G.hand_cover(ink,joints,R)


def details(G, d, ink, xf, joints, R, p, c, head):
    """Individual shaped seams, mantle and occupational badge, attached to the rig."""
    cut = d['cut']
    # An asymmetric short mantle keeps faces and held props unobscured.
    points = [(-10, -4, 70), (8, -4, 70), (10 + cut * .5, -7, 52 - cut),
              (-12 - cut * .45, -7, 43 + cut)]
    ink.plate([xf(q) for q in points], 'accent', 2)
    # Distinctively cut shoulder tabs and a diagonal trim, rather than colour alone.
    ink.plate([xf(q) for q in [(-9, 2, 68), (-14 - cut * .3, 2, 65),
                                (-11 - cut * .3, 4, 61), (-8, 4, 64)]], 'trim', 2)
    ink.plate([xf(q) for q in [(-5, 5, 65), (-3, 5.2, 66),
                                (7, 5.2, 45 + cut), (5, 5, 44 + cut)]], 'accent', 3, True)
    signature = d['signature']
    if signature in ('wool', 'fur', 'snow', 'pelt', 'silverpelt', 'wintercairn'):
        for x in (-8, -4, 0, 4, 8):
            ink.plate([xf(q) for q in [(x - 2, 4.8, 65), (x + 2, 4.8, 65), (x + 1, 5, 58 - abs(x) * .2)]], 'cream', 2)
    elif signature in ('net', 'oilskin', 'creel', 'rope', 'deeprope', 'maze', 'captain', 'harness', 'knots'):
        for z in (49, 54, 59):
            G.line3(ink, xf((-6, 5.8, z)), xf((6, 5.8, z + 3)), .5, 'leather', tone=2)
        for x in (-4, 0, 4):
            G.line3(ink, xf((x, 5.8, 47)), xf((x, 5.8, 63)), .5, 'leather', tone=3)
    elif signature in ('runes', 'map', 'survey', 'tally', 'hourglass', 'slaterunes', 'growthrings', 'starline', 'stories'):
        for x,z in [(-5,56),(0,53),(5,50)]:
            G.line3(ink, xf((x,5.6,z-3)), xf((x,5.6,z+3)), .7, 'trim', tone=3)
            G.line3(ink, xf((x,5.6,z)), xf((x+3,5.6,z+2)), .6, 'trim', tone=2)
    else:
        # Occupational medallion with a visibly different number/shape of lobes.
        for i in range(3 + cut % 3):
            x = -5 + i * 2.3
            ink.plate([xf(q) for q in [(x,5.6,56),(x+1.4,5.6,58+cut*.3),
                                        (x+2.8,5.6,56),(x+1.4,5.6,52)]], 'trim', 2 + i % 2, True)


if __name__ == '__main__':
    print(len(catalog()), 'authored named looks')
