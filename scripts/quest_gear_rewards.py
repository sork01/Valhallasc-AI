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
    'crags_wisps': green(5, 'necklace'),
    'crags_spiders': green(5, 'pants'),
    'crags_cinderlord': blue(10, 'necklace'),
    'crags_expedition': blue(10, 'accessory'),
    'rime_crabs': green(10, 'necklace'),
    'rime_wolves': green(10, 'pants'),
    'rime_wyrm_hunt': blue(15, 'accessory'),
    'rime_vanguard': blue(15, 'pants'),
    'fen_toads': green(15, 'necklace'),
    'fen_crocs': green(15, 'pants'),
    'fen_vanguard': blue(20, 'pants'),
    'city_gel': green(10, 'necklace'),
    'city_pelts': green(15, 'pants'),
    'city_tribute': blue(20, 'accessory'),
    'wyrd_boars': green(20, 'necklace'),
    'wyrd_crows': green(25, 'pants'),
    'wyrd_seal': blue(25, 'accessory'),
    'wyrd_trolls': green(25, 'necklace'),
    'wyrd_weavers': green(30, 'pants'),
    'wyrd_vanguard': blue(30, 'accessory'),
    'sky_hounds': green(30, 'necklace'),
    'sky_golems': green(30, 'pants'),
    'sky_vanguard': blue(35, 'necklace'),
    'deep_draugr': green(35, 'necklace'),
    'deep_anglers': green(35, 'pants'),
    'deep_ghostmaw': blue(40, 'necklace'),
    'deep_vanguard': blue(40, 'accessory'),
    'nacre_gardens': green(35, 'necklace'),
    'nacre_history': green(35, 'pants'),
    'nacre_cathedral': blue(40, 'accessory'),
    'nacre_smithwork': blue(40, 'necklace'),
    'astral_moths': green(40, 'necklace'),
    'astral_wyrms': green(40, 'pants'),
    'astral_golems': blue(45, 'necklace'),
    'astral_survey': blue(45, 'accessory'),
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
    'sun_hares': green(65, 'necklace'),
    'sun_snails': green(65, 'pants'),
    'sun_honeyjaw': blue(70, 'accessory'),
    'sun_warden': blue(70, 'necklace'),
    'ribbon_geckos': green(70, 'necklace'),
    'ribbon_beetles': green(70, 'pants'),
    'ribbon_gryphon': blue(75, 'accessory'),
    'ribbon_colossus': blue(75, 'necklace'),
    'ribbon_folds': blue(75, 'pants'),
    'ribbon_final': blue(75, 'accessory'),
    'tangle_mantises': green(75, 'necklace'),
    'tangle_gliders': green(75, 'pants'),
    'tangle_anaconda': blue(80, 'accessory'),
    'tangle_jaguar': blue(80, 'necklace'),
    'heart_walkways': green(80, 'necklace'),
    'heart_lanterns': green(80, 'pants'),
    'heart_market': blue(80, 'accessory'),
    'lapis_hoppers': green(80, 'necklace'),
    'lapis_fennecs': green(80, 'pants'),
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
