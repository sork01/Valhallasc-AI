"""Pure loot-table model: 1,500 runs, no game-world simulation or grinding.

Humans Need missing usable slots; each eligible human has an equal roll. Others
Greed. Includes the cloak and TWO accessory copies. Does not model better stat
rolls on duplicate items. No demand-aware selection or bad-luck protection.
"""
import json
import random
import statistics
from pathlib import Path
from raid_rewards import CLASSES, build

ROOT=Path(__file__).resolve().parents[1]

def simulate(humans,runs=1500):
    rng=random.Random(20261022+humans)
    rules=build();first=[];all_done=[]
    kinds=('armor','headgear','shoulders','gloves','pants','necklace','accessory','cloak','weapon')
    for _ in range(runs):
        have=[dict.fromkeys(kinds,0) for _ in range(humans)]
        full=lambda h: all(h[k]>=(2 if k=='accessory' else 1) for k in kinds)
        first_at=None
        for clear in range(1,301):
            for boss in rules['bosses']:
                slots=rng.sample(boss['slots'],2)+['weapon']*boss['weapons']
                for slot in slots:
                    cls=rng.choice(CLASSES) if slot in ('armor','headgear','shoulders','gloves','weapon') else None
                    need=[n for n,h in enumerate(have) if (cls is None or CLASSES[n%5]==cls)
                          and h[slot]<(2 if slot=='accessory' else 1)]
                    if need:have[rng.choice(need)][slot]+=1
            if first_at is None and any(map(full,have)):first_at=clear
            if all(map(full,have)):
                first.append(first_at);all_done.append(clear);break
        else:raise AssertionError('model exceeds 300 clears')
    return dict(humans=humans,runs=runs,firstMedian=statistics.median(first),
                allMedian=statistics.median(all_done),allP95=sorted(all_done)[int(runs*.95)],
                allWorst=max(all_done))

if __name__=='__main__':
    rules=build();result=dict(model=[simulate(n) for n in (1,5,10)],stats={})
    for cls in CLASSES:
        chosen=[p for p in rules['pieces'] if p['class'] in (None,cls)]
        result['stats'][cls]={stat:[sum(p['rolls'][stat][n]*(2 if p['slot']=='accessory' else 1)
                                    for p in chosen) for n in (0,1)]
                              for stat in ('attack','defense','stamina','accuracy','dexterity')}
    target=ROOT/'test-results/raid-rewards/loot-model.txt';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
