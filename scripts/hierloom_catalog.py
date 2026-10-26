"""Four level-scaling, indestructible Chained Forge XP pieces. Idempotent overlay."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'raid_hierlooms'
PIECES = (
    ('hierloom_dawn_ring', 'Dawnkeeper Ring', 'accessory', 'chainforged_accessory'),
    ('hierloom_ember_ring', 'Everember Ring', 'accessory', 'chainforged_accessory'),
    ('hierloom_necklace', 'Legacy of the Forge', 'necklace', 'chainforged_necklace'),
    ('hierloom_cloak', 'Mantle of Generations', 'cloak', 'cloak_l99_epic'),
)


def apply():
    path = ROOT / 'world/items.txt'
    items = json.loads(path.read_text())
    items = [i for i in items if i.get('source') != SOURCE]
    for id_, name, kind, variant in PIECES:
        items.append(dict(id=id_, name=name, kind=kind, rarity='hierloom', requiredLevel=1,
                          sell=9152, attack=0, defense=0,
                          bonusStats=dict(strength=1, agility=1, intellect=1, stamina=2),
                          **{'class': None}, variant=variant, source=SOURCE))
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    apply()
