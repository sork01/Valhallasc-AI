#!/usr/bin/env python3
"""Mutation-check real fishing progression. Exclusive worktree access; sources restored in finally.

One instrumented test build, a clean control, then one independent mutation per assertion.
Rebuild clean tests/binary afterward. Does not touch any running service or saved character.
"""
import json
import os
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
CASE_PREFIX='world::fishing::progression_tests::'
CASES={
 'water':'fishing_progression_every_upgrade_keeps_earlier_waters_and_replaces_one_rod',
 'requirements':'fishing_progression_all_waters_name_the_required_rod_and_reject_its_predecessor',
 'consume':'fishing_progression_every_upgrade_keeps_earlier_waters_and_replaces_one_rod',
 'speed':'fishing_progression_rods_and_food_change_wait_and_rare_weight',
 'luck':'fishing_progression_rods_and_food_change_wait_and_rare_weight',
 'food':'fishing_progression_food_is_one_choice_at_full_health_with_stronger_feasts',
 'stack':'fishing_progression_food_is_one_choice_at_full_health_with_stronger_feasts',
 'skill':'fishing_progression_food_is_one_choice_at_full_health_with_stronger_feasts',
 'full':'fishing_progression_food_is_one_choice_at_full_health_with_stronger_feasts',
}
EDITS={
 'server/src/world/fishing.rs':[
  ('(!lava || r.lava)','((!lava || r.lava) && (!progression_mutant("water") || r.lava == lava))'),
  ('if rod.is_none_or(|r| r.tier < required.tier) {','if !progression_mutant("requirements") && rod.is_none_or(|r| r.tier < required.tier) {'),
  ('p.buff(BuffKind::FishingSpeed).min(0.5)','if progression_mutant("speed") { 0. } else { p.buff(BuffKind::FishingSpeed).min(0.5) }'),
  ('p.buff(BuffKind::FishingLuck)','if progression_mutant("luck") { 0. } else { p.buff(BuffKind::FishingLuck) }'),
 ],
 'server/src/world/fishing_workshop.rs':[
  ('if !next.consume_item(&id, count) {','if !progression_mutant("consume") && !next.consume_item(&id, count) {'),
 ],
 'server/src/world/consumables.rs':[
  ('if let Some(bonus) = &it.food_bonus {','if let Some(bonus) = &it.food_bonus && !progression_mutant("food") {'),
  ('p.buffs.retain(|b| !b.id.starts_with("meal:"));','p.buffs.retain(|b| !b.id.starts_with("meal:") || progression_mutant("stack"));'),
  ('&& it.food_bonus.is_none() {','&& (it.food_bonus.is_none() || progression_mutant("full")) {'),
 ],
 'server/src/world.rs':[
  ('b.id.starts_with("meal:") || (b.id != id','(b.id.starts_with("meal:") && !progression_mutant("skill")) || (b.id != id'),
 ],
}
def main():
 originals={name:(ROOT/name).read_text() for name in EDITS}
 reports=ROOT/'test-results/fishing-progression-mutations';reports.mkdir(parents=True,exist_ok=True)
 try:
  for name,edits in EDITS.items():
   s=originals[name]
   for old,new in edits:
    assert s.count(old)==1,(name,old);s=s.replace(old,new)
   if name=='server/src/world.rs':s+='\nfn progression_mutant(mode: &str) -> bool { std::env::var("FISH_PROGRESSION_MUTATION").as_deref() == Ok(mode) }\n'
   (ROOT/name).write_text(s)
  build=subprocess.run(['bash','scripts/cargo.sh','test','fishing_progression','--no-run','--message-format=json'],cwd=ROOT,text=True,stdout=subprocess.PIPE,check=True)
  artifacts=[json.loads(line) for line in build.stdout.splitlines() if line.startswith('{')]
  binary=next(e['executable'] for e in artifacts if e.get('reason')=='compiler-artifact' and e.get('profile',{}).get('test') and e.get('executable'))
  env=dict(os.environ);env.pop('FISH_PROGRESSION_MUTATION',None)
  subprocess.run([binary,CASE_PREFIX,'--test-threads=1'],cwd=ROOT,env=env,check=True)
  for mode,test in CASES.items():
   name=CASE_PREFIX+test
   result=subprocess.run([binary,name,'--exact','--test-threads=1'],cwd=ROOT,env={**env,'FISH_PROGRESSION_MUTATION':mode},text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   (reports/(mode+'.txt')).write_text(result.stdout)
   assert result.returncode==101 and name+' ... FAILED' in result.stdout,(mode,result.stdout)
   print(mode+': mutation caught',flush=True)
 finally:
  for name,s in originals.items():(ROOT/name).write_text(s)
if __name__=='__main__':main()
