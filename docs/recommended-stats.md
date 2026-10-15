# Recommended stat allocation

The server spends **only unspent** points. It does not reset trained points and
costs no gold. Existing manual choices stay in place. Paid full resets are
documented in [stat-reset.md](stat-reset.md).

| Class | Strength | Agility | Intellect | Stamina | Dexterity | Accuracy | Reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Warrior | 40% | 5% | 0% | 30% | 10% | 15% | Strong strikes and enough health to hold the front line. |
| Mage | 0% | 5% | 45% | 25% | 10% | 15% | Spell power and mana first, with survival and reliable hits. |
| Assassin | 10% | 40% | 0% | 20% | 15% | 15% | Fast critical attacks and dodging without giving up all health. |
| Priest | 0% | 5% | 45% | 30% | 5% | 15% | Healing power and more health while casting near allies. |
| Hunter | 5% | 40% | 0% | 25% | 15% | 15% | Bow damage and mobility, with room to survive a close enemy. |

For each available point, the server compares the class percentages with the
character's **effective** attributes (trained points, worn gear and automatic
passives), then invests in the largest deficit. This makes an old manual spread
and current gear part of the recommendation without changing either. The same
rule works at every level; as the character grows, it naturally fills the
currently underweight stats. Accuracy receives no more recommended points once
its trained or effective total reaches 20; Dexterity stops at 70. Points then
flow to other eligible stats. Stamina training raises current HP by 8 per point,
as it does for manual training. Defeated characters and characters with no
unspent points are refused. The operation is computed on a copy and saved as
one server action.
