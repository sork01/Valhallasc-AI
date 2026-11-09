"""Guaranteed, class-neutral gear for one-time quests at each quest hub.

Generators use reward_for() when rebuilding a zone. Run --apply after changing
the table to update the existing world/map.txt without regenerating terrain.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def green(level, slot):
    if level == 5 and slot == 'pants':
        return 'pants_upgrade'  # the pre-existing level-5 set uses this legacy ID
    stem = {'pants': 'pants_wayfarer', 'necklace': 'necklace_moonstone',
            'accessory': 'accessory_amber'}[slot]
    return f'{stem}_l{level}_green'


def blue(level, slot):
    stem = {'pants': 'pants_wayfarer', 'necklace': 'necklace_moonstone',
            'accessory': 'accessory_amber'}[slot]
    return f'{stem}_l{level}_blue'


REWARDS = {
    'null_bell': 'null_pants',
    'null_current': 'null_accessory',
    'keel_cargo': 'pants_wayfarer_l35_keel',
    'keel_rigging': 'accessory_amber_l35_keel',
    'barrow_amber': 'pants_wayfarer_l25_norn',
    'barrow_threads': 'accessory_amber_l25_norn',
    'slime_patrol': green(1, 'necklace'),
    'ironhide_hunt': green(5, 'pants'),
    'king_challenge': blue(5, 'accessory'),
    # Greenmeadow's hamlets (pilot): two greens each where the levels allow, blue for the group elites
    'fold_strays': green(5, 'accessory'),
    'fold_watch': green(5, 'necklace'),
    'fold_tusker': blue(5, 'necklace'),
    'salt_strand': green(1, 'pants'),
    'salt_wreck': green(1, 'accessory'),
    'salt_claw': blue(5, 'pants'),
    'apple_mill': green(10, 'accessory'),
    'hollow_chapel': green(10, 'pants'),
    # The Crags' outposts (pilot): two greens each where the levels allow, blue for the group elite
    'anvil_cut': green(5, 'accessory'),
    'anvil_props': green(10, 'necklace'),
    'anvil_slagmaw': blue(10, 'pants'),
    'ford_cart': green(10, 'pants'),
    'ford_crown': green(10, 'accessory'),
    'hearth_horns': green(10, 'necklace'),
    'hearth_stair': green(5, 'necklace'),
    'crags_wisps': green(5, 'necklace'),
    'crags_spiders': green(5, 'pants'),
    'crags_cinderlord': blue(10, 'necklace'),
    'crags_expedition': blue(10, 'accessory'),
    # Rimeveil's outposts (pilot): two greens each where the levels allow, blue for the group elites
    'rime_dw_gap': green(10, 'accessory'),
    'rime_dw_sledge': green(10, 'necklace'),
    'rime_sw_cairn': green(10, 'pants'),
    'rime_sw_signal': green(10, 'accessory'),
    'rime_sw_hoarhorn': blue(15, 'necklace'),
    'rime_pk_ridge': green(10, 'necklace'),
    'rime_pk_chart': green(10, 'pants'),
    'rime_pk_whitewail': blue(15, 'accessory'),
    'rime_spiral': green(10, 'accessory'),
    'rime_heart': green(15, 'necklace'),
    'rime_crabs': green(10, 'necklace'),
    'rime_wolves': green(10, 'pants'),
    'rime_wyrm_hunt': blue(15, 'accessory'),
    'rime_vanguard': blue(15, 'pants'),
    'fen_toads': green(15, 'necklace'),
    'fen_crocs': green(15, 'pants'),
    'fen_vanguard': blue(20, 'pants'),
    # Gloamfen's outposts (pilot): two greens each where the levels allow, blue for the group elite
    'fen_rh_wicks': green(15, 'accessory'),
    'fen_rh_pike': green(15, 'necklace'),
    'fen_rh_bellow': blue(20, 'pants'),
    'fen_dk_breach': green(15, 'pants'),
    'fen_dk_wreck': green(15, 'accessory'),
    'fen_gr_fort': green(15, 'necklace'),
    'fen_gr_chart': green(15, 'pants'),
    'fen_gr_fangs': green(20, 'accessory'),
    'fen_walk': green(15, 'accessory'),
    'fen_culvert': green(15, 'necklace'),
    'city_gel': green(10, 'necklace'),
    'city_pelts': green(15, 'pants'),
    'city_tribute': blue(20, 'accessory'),
    'wyrd_boars': green(20, 'necklace'),
    'wyrd_crows': green(25, 'pants'),
    'wyrd_seal': blue(25, 'accessory'),
    'wyrd_trolls': green(25, 'necklace'),
    'wyrd_weavers': green(30, 'pants'),
    'wyrd_vanguard': blue(30, 'accessory'),
    # the Wyrdwood's outposts (pilot): a green or blue at the end of each outpost chain
    'wyrd_h_wood': green(20, 'accessory'),
    'wyrd_s_bridge': green(25, 'accessory'),
    'wyrd_gf_vigil': green(25, 'pants'),
    'wyrd_gf_mill': green(25, 'accessory'),
    'wyrd_rw_gap': green(30, 'necklace'),
    'wyrd_rw_fire': green(30, 'accessory'),
    'wyrd_hm_ring': green(30, 'pants'),
    'wyrd_hm_gale': blue(30, 'necklace'),
    # Bifrost Reach's outposts (pilot): a green or blue at the end of each outpost chain
    'sky_h_shardfield': green(30, 'pants'),
    'sky_h_shardking': blue(30, 'accessory'),
    'sky_h_ledger': green(30, 'accessory'),
    'sky_wr_alpha': green(30, 'necklace'),
    'sky_wr_beacon': green(30, 'pants'),
    'sky_ss_tally': green(30, 'accessory'),
    'sky_ss_rod': green(35, 'pants'),
    'sky_hl_bell': green(35, 'accessory'),
    'sky_el_nests': green(35, 'necklace'),
    'sky_el_rod': blue(35, 'accessory'),
    'sky_hounds': green(30, 'necklace'),
    'sky_golems': green(30, 'pants'),
    'sky_vanguard': blue(35, 'necklace'),
    # Rán's Deep's outposts (pilot): a green or blue at the end of each outpost chain
    'deep_kh_ledger': green(35, 'accessory'),
    'deep_lr_lamp': green(35, 'accessory'),
    'deep_lr_sirens': green(35, 'necklace'),
    'deep_gw_vents': green(40, 'pants'),
    'deep_gw_gate': blue(40, 'accessory'),
    'deep_dw_stones': green(35, 'pants'),
    'deep_draugr': green(35, 'necklace'),
    'deep_anglers': green(35, 'pants'),
    'deep_ghostmaw': blue(40, 'necklace'),
    'deep_vanguard': blue(40, 'accessory'),
    'nacre_tideway': green(35, 'accessory'),
    'nacre_five_ways': green(35, 'pants'),
    'nacre_rim_gardens': green(35, 'necklace'),
    'nacre_gardens': green(35, 'necklace'),
    'nacre_history': green(35, 'pants'),
    'nacre_cathedral': blue(40, 'accessory'),
    'nacre_smithwork': blue(40, 'necklace'),
    'astral_moths': green(40, 'necklace'),
    'astral_wyrms': green(40, 'pants'),
    'astral_golems': blue(45, 'necklace'),
    'astral_survey': blue(45, 'accessory'),
    # Astralhollow's outposts (pilot): a green or blue at the end of each outpost chain, a blue for each elite quest
    'astral_h_lamps': green(40, 'accessory'),
    'astral_h_rounds': green(40, 'pants'),
    'astral_cr_chord': green(40, 'necklace'),
    'astral_cr_ring': green(40, 'accessory'),
    'astral_cw_fire': green(40, 'pants'),
    'astral_cometmaw': blue(40, 'accessory'),
    'astral_fh_line': green(40, 'necklace'),
    'astral_fh_cores': green(45, 'accessory'),
    'astral_eclipsequeen': blue(45, 'pants'),
    'prism_jackals': green(45, 'necklace'),
    'prism_scarabs': green(45, 'pants'),
    'prism_queen': blue(50, 'accessory'),
    'prism_sunshard': blue(50, 'necklace'),
    'prism_survey': blue(50, 'pants'),
    'orrery_mantises': green(50, 'necklace'),
    'orrery_gearlings': green(50, 'pants'),
    'orrery_matron': blue(55, 'accessory'),
    'orrery_engine': blue(55, 'necklace'),
    'orrery_survey': blue(55, 'pants'),
    # the Orrery's outposts (pilot): a green at the end of each chain
    'orrery_h_hold': green(50, 'accessory'),
    'orrery_h_rounds': green(55, 'pants'),
    'orrery_bc_hold': green(50, 'necklace'),
    'orrery_bc_axis': green(50, 'accessory'),
    'orrery_cn_hold': green(55, 'necklace'),
    'orrery_cn_lens': green(55, 'accessory'),
    'orrery_sw_hold': green(55, 'pants'),
    'orrery_sw_south': green(55, 'necklace'),
    # the Prismwaste's outposts (pilot): a green at the end of each chain
    'prism_h_hold': green(45, 'accessory'),
    'prism_h_rounds': green(50, 'pants'),
    'prism_mf_hold': green(45, 'necklace'),
    'prism_mf_glass': green(45, 'accessory'),
    'prism_ws_hold': green(50, 'necklace'),
    'prism_ws_watch': green(50, 'accessory'),
    'prism_cf_hold': green(50, 'pants'),
    'prism_cf_south': green(50, 'necklace'),
    'moonspore_grazers': green(55, 'necklace'),
    'moonspore_silkwings': green(55, 'pants'),
    'moonspore_mireheart': blue(60, 'accessory'),
    'moonspore_widow': blue(60, 'necklace'),
    'moonspore_bloom': blue(60, 'pants'),
    'moonspore_survey': blue(60, 'accessory'),
    'asterion_lamps': green(60, 'necklace'),
    'asterion_roots': green(60, 'pants'),
    'asterion_charts': blue(60, 'necklace'),
    'asterion_descent': blue(60, 'accessory'),
    'stormglass_crabs': green(60, 'necklace'),
    'stormglass_gulls': green(60, 'pants'),
    'stormglass_guards': blue(65, 'necklace'),
    'stormglass_heart': blue(65, 'accessory'),
    # the Stormglass Flats' outposts (pilot): a green at the end of each chain, a blue for the group elite
    'storm_h_hold': green(60, 'accessory'),
    'storm_h_rounds': green(65, 'pants'),
    'stormglass_hermit': blue(65, 'pants'),
    'storm_rs_hold': green(60, 'necklace'),
    'storm_rs_pans': green(60, 'accessory'),
    'storm_fp_hold': green(65, 'necklace'),
    'storm_fp_drift': green(65, 'accessory'),
    'storm_bh_hold': green(65, 'pants'),
    'storm_bh_shards': green(65, 'necklace'),
    # Emberwake Caldera's hubs (pilot): a green at the end of each chain
    'ew_h_hold': green(95, 'accessory'),
    'ew_h_rounds': green(95, 'pants'),
    'ew_cw_hold': green(95, 'necklace'),
    'ew_cw_links': green(95, 'accessory'),
    'ew_cq_hold': green(95, 'pants'),
    'ew_cq_quench': green(95, 'necklace'),
    'ew_gh_hold': green(95, 'accessory'),
    'ew_gh_crater': green(95, 'pants'),
    'sun_hares': green(65, 'necklace'),
    'sun_snails': green(65, 'pants'),
    'sun_honeyjaw': blue(70, 'accessory'),
    'sun_warden': blue(70, 'necklace'),
    # The Ribbonwild's hubs (pilot): a green at the end of each chain
    'ribbon_jc_hold': green(70, 'accessory'),
    'ribbon_rounds': green(70, 'pants'),
    'ribbon_bp_hold': green(70, 'necklace'),
    'ribbon_bp_dance': green(70, 'accessory'),
    'ribbon_tp_hold': green(70, 'pants'),
    'ribbon_tp_rosette': green(70, 'necklace'),
    'ribbon_gr_hold': green(70, 'accessory'),
    'ribbon_gr_stair': green(75, 'pants'),
    'ribbon_geckos': green(70, 'necklace'),
    'ribbon_beetles': green(70, 'pants'),
    'ribbon_gryphon': blue(75, 'accessory'),
    'ribbon_colossus': blue(75, 'necklace'),
    'ribbon_folds': blue(75, 'pants'),
    'ribbon_final': blue(75, 'accessory'),
    'tangle_mantises': green(75, 'necklace'),
    'tangle_gliders': green(75, 'pants'),
    # The Tanglecrown's hubs (pilot): a green at the end of each chain
    'tangle_lh_hold': green(75, 'accessory'),
    'tangle_rounds': green(75, 'pants'),
    'tangle_rg_hold': green(75, 'necklace'),
    'tangle_rg_glide': green(75, 'accessory'),
    'tangle_sp_hold': green(75, 'pants'),
    'tangle_sp_water': green(75, 'necklace'),
    'tangle_dr_hold': green(80, 'accessory'),
    'tangle_dr_stair': green(80, 'pants'),
    'tangle_anaconda': blue(80, 'accessory'),
    'tangle_jaguar': blue(80, 'necklace'),
    'heart_walkways': green(80, 'necklace'),
    'heart_lanterns': green(80, 'pants'),
    'heart_market': blue(80, 'accessory'),
    'lapis_hoppers': green(80, 'necklace'),
    'lapis_fennecs': green(80, 'pants'),
    # The Lapis Erg's hubs (pilot): a green at the end of each chain
    'lapis_wl_hold': green(80, 'accessory'),
    'lapis_rounds': green(80, 'pants'),
    'lapis_ww_hold': green(80, 'necklace'),
    'lapis_ww_dune': green(80, 'accessory'),
    'lapis_sp_hold': green(85, 'pants'),
    'lapis_sp_glare': green(85, 'necklace'),
    'lapis_ew_hold': green(85, 'accessory'),
    'lapis_ew_crag': green(85, 'pants'),
    # The Veyrroot's hubs (pilot): a green at the end of each chain
    'veyr_rf_hold': green(80, 'accessory'),
    'veyr_rounds': green(80, 'pants'),
    'veyr_gw_hold': green(80, 'necklace'),
    'veyr_gw_flats': green(80, 'accessory'),
    'veyr_rs_hold': green(80, 'pants'),
    'veyr_rs_hive': green(80, 'necklace'),
    'veyr_eb_hold': green(80, 'accessory'),
    'veyr_eb_grove': green(80, 'pants'),
    # Heartwood's city quests (pilot): a green at the end of each chain
    'hw_hollows': green(80, 'accessory'),
    'hw_resin': green(80, 'pants'),
    'hw_panes': green(80, 'necklace'),
    'hw_blankets': green(80, 'pants'),
    'hw_stools': green(80, 'accessory'),
    'hw_watch': green(80, 'necklace'),
    'lapis_colossus': blue(85, 'accessory'),
    'lapis_roc': blue(85, 'necklace'),
    'frostwake_hares': green(85, 'necklace'),
    'frostwake_otters': green(85, 'pants'),
    'frostwake_mammoth': blue(90, 'accessory'),
    'frostwake_manta': blue(90, 'necklace'),
    'frostwake_leviathan': blue(90, 'pants'),
    'cairn_ferrets': green(90, 'necklace'),
    'cairn_ibex': green(90, 'pants'),
    'cairn_behemoth': blue(95, 'accessory'),
    'cairn_titan': blue(95, 'necklace'),
    'cairn_condor': blue(95, 'pants'),
    'yr_sp_intro': green(95, 'necklace'),
    'yr_su_intro': green(95, 'pants'),
    'yr_au_intro': green(95, 'accessory'),
    'yr_wi_intro': green(95, 'necklace'),
    'cairn_thunder_final': blue(95, 'accessory'),
    # Sunward Vale's hubs (pilot): a green at the end of each chain (the ladder has levels 65 and 70)
    'svs_mb_hold': green(65, 'accessory'),
    'svs_rounds': green(65, 'pants'),
    'svs_hw_hold': green(65, 'necklace'),
    'svs_hw_ridge': green(70, 'accessory'),
    'svs_wf_hold': green(70, 'pants'),
    'svs_wf_barrow': green(70, 'necklace'),
    'svs_er_hold': green(70, 'accessory'),
    'svs_er_springs': green(70, 'pants'),
    # Cairnspine's hubs (pilot): a green at the end of each chain
    'crn_bw_hold': green(90, 'accessory'),
    'crn_rounds': green(90, 'pants'),
    'crn_sc_hold': green(90, 'necklace'),
    'crn_sc_adders': green(90, 'accessory'),
    'crn_wb_hold': green(90, 'pants'),
    'crn_wb_wood': green(90, 'necklace'),
    'crn_sg_hold': green(90, 'accessory'),
    'crn_sg_spires': green(90, 'pants'),
    # The Frostwake Shelf's hubs (pilot): a green at the end of each chain
    'fws_st_hold': green(85, 'accessory'),
    'fws_rounds': green(85, 'pants'),
    'fws_bw_hold': green(85, 'necklace'),
    'fws_bw_fissures': green(85, 'accessory'),
    'fws_au_hold': green(85, 'pants'),
    'fws_au_pools': green(85, 'necklace'),
    'fws_rw_hold': green(85, 'accessory'),
    'fws_rw_crabs': green(85, 'pants'),
    'yr_sp_bloom_final': blue(95, 'necklace'),
    'yr_su_solar_final': blue(95, 'accessory'),
    'yr_au_amber_final': blue(95, 'necklace'),
    'yr_wi_sols_final': blue(95, 'accessory'),
}


def reward_for(quest_id):
    return REWARDS.get(quest_id)


def add_reward(quest):
    reward = reward_for(quest['id'])
    if reward:
        quest['rewardItem'] = reward
    return quest


def apply_to_map():
    path = ROOT / 'world/map.txt'
    world = json.loads(path.read_text())
    items = {i['id']: i for i in json.loads((ROOT / 'world/items.txt').read_text())}
    seen = set()
    for zone in [world, *world['zones']]:
        for quest in zone.get('quests', []):
            quest_id = quest['id']
            if quest_id not in REWARDS:
                continue
            reward = REWARDS[quest_id]
            piece = items.get(reward)
            if not piece or piece['rarity'] not in ('uncommon', 'rare') or piece.get('class') or piece.get('source'):
                raise ValueError(f'{quest_id}: invalid class-neutral reward {reward}')
            if piece['requiredLevel'] > quest['level'] + 5 or quest['repeatable']:
                raise ValueError(f'{quest_id}: reward level or repeatability is invalid')
            quest['rewardItem'] = reward
            seen.add(quest_id)
    if seen != REWARDS.keys():
        raise ValueError(f'quests missing from map: {REWARDS.keys() - seen}')
    path.write_text(json.dumps(world, indent=2) + '\n')


if __name__ == '__main__' and sys.argv[1:] == ['--apply']:
    apply_to_map()
