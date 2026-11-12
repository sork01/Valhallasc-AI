#!/usr/bin/env python3
"""Inventory missing people without changing the legacy NPC plan or world."""
import collections
import json
import re
from pathlib import Path
import npc_art_catalog as legacy
import npcp_named

ROOT = Path(__file__).resolve().parents[1]
INDIVIDUAL_CUTS = {'astral_cw_brisa': 5, 'ew_gh_ivar': 7}
FEMALE = set('''fold_hild salt_ragna apple_maren apple_lotta anvil_ingrid ford_tora
hearth_sigrid rime_dw_hild rime_sw_runa rime_pk_sif fen_rh_brid fen_dk_linnea
fen_gr_ysolde wyrd_gf_hild wyrd_gf_trader wyrd_rw_dagny wyrd_rw_trader
wyrd_hm_sunniva sky_wr_vigdis sky_wr_trader sky_ss_ingrid sky_ss_trader
sky_el_hallveig deep_lr_solveig deep_lr_trader deep_gw_bergljot deep_gw_trader
deep_dw_ottilia deep_dw_trader nacre_harbourmaster nacre_gatewarden astral_cr_ide
astral_cr_trader astral_cw_brisa prism_mf_ilsa prism_ws_ottilie prism_cf_runa
orrery_bc_tolla orrery_cn_isolde orrery_sw_kestrel storm_rs_edda storm_fp_ingrid
storm_bh_sigrid sv_hw_marit sv_wf_greta sv_er_ingrid rw_bp_aldis rw_bp_pernille
rw_tp_ysolde rw_gr_lisbet tg_dr_kessa tg_sp_odile ve_gw_ilsa ve_gw_nuri ve_eb_dessa
hw_healer hw_innkeeper hw_captain hw_weaver hw_bellringer hw_storyteller hw_tapper
hw_glassblower hw_kid_mina hw_kid_tove lp_ww_hesper lp_ww_yeva lp_sp_soraya
lp_ew_lunet fw_bw_brynja fw_au_sigrun cn_wb_ingrid cn_sg_ragna yo_wm_ingrid
yo_th_sunniva yo_lf_tove ew_cw_ragna ew_cq_tove ew_gh_sunniva'''.split())


def inventory():
    world = json.loads((ROOT / 'world/map.txt').read_text())
    assigned = json.loads((ROOT / 'client/assets/npc.txt').read_text())['npcs']
    authored = {s['id']: s for s in npcp_named.catalog()}
    assert len(authored) == len(npcp_named.catalog())
    quests = collections.defaultdict(list)
    for zone in [world] + world['zones']:
        for quest in zone.get('quests', []):
            quests[quest['npc']].append(quest['id'])
    people, excluded, present = [], [], set()
    for zi, zone in [(0, world)] + list(enumerate(world['zones'], 1)):
        for npc in zone.get('npcs', []):
            if npc['id'] in assigned:
                continue
            if npc.get('art') in ('stone', 'scenery', 'mailbox') or 'meeting stone' in npc['name'].lower():
                excluded.append(npc['id'])
                continue
            ident = npc.get('look', {})
            role = npc.get('role', '')
            family = next((k for k, pattern in legacy.MATCH if re.search(pattern, role.lower())), 'pilgrim')
            row = dict(id=npc['id'], name=npc['name'], role=role, zone=zi,
                       zoneName='Greenmeadow' if zi == 0 else zone['name'],
                       identity=ident, color=npc.get('color', '#8899aa'),
                       quests=quests[npc['id']], moving=bool(npc.get('route')))
            if npc['id'] in authored:
                design = dict(authored[npc['id']])
                design['female'] = bool(ident.get('female', npc['id'] in FEMALE))
                # Vary cuts within each held-prop group; the concrete result is saved in the plan.
                peers = [p for p in people if p.get('design', {}).get('prop') == design['prop']]
                design['cut'] = INDIVIDUAL_CUTS.get(npc['id'], len(peers) % 7 - 3)
                design['bark'] = ['#ad8057', '#926a49', '#b58e65', '#8f7357'][len(people) % 4]
                design['leaf'] = ['#507a43', '#658a52', '#397c60', '#7a934d'][len(people) % 4]
                row.update(classification='named', designKey='named_' + npc['id'], design=design,
                           reason='Named quest giver' if quests[npc['id']] else 'Individual resident or story trait')
                present.add(npc['id'])
            else:
                assert not quests[npc['id']], f'Unplanned named quest giver: {npc["id"]}'
                row.update(classification='generic', reuse=family,
                           reason='Reuse an existing role with personal colours in the separate assignment task')
                if zi in (23, 24):
                    row.update(requiredSpecies='treefolk',
                               reuseNote='Reuse a treefolk design of the appropriate role; never assign the human general sprite here.')
            people.append(row)
    assert present == authored.keys(), authored.keys() - present
    return dict(baseline='8e982701', counts=dict(missingPeople=len(people),
                namedDesigns=len(present), genericReuse=len(people)-len(present),
                excludedScenery=len(excluded), namedQuestGivers=sum(bool(p['quests']) for p in people)),
                people=people, excludedScenery=excluded)


if __name__ == '__main__':
    plan = inventory()
    (ROOT / 'docs/npc-named-plan.txt').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(plan['counts']))
