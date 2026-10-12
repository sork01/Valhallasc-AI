"""Write the class milestone catalog. Names and stat grants live together here."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = {
    "warrior": [
        ("Iron Constitution", {"stamina": 4}),
        ("Veteran's Edge", {"strength": 5}),
        ("Guarded Footwork", {"stamina": 4, "dexterity": 2}),
        ("Fortress Heart", {"stamina": 8}),
        ("Battle Insight", {"strength": 7, "accuracy": 2}),
        ("Titan's Grip", {"strength": 12}),
        ("Unbroken March", {"stamina": 14}),
        ("War Tempo", {"strength": 10, "agility": 5}),
        ("Last Bastion", {"strength": 18, "stamina": 12}),
    ],
    "mage": [
        ("Arcane Study", {"intellect": 4}),
        ("Steady Conduit", {"intellect": 5, "stamina": 2}),
        ("Mana Lattice", {"intellect": 7}),
        ("Runic Shelter", {"stamina": 7, "intellect": 3}),
        ("Spellweaver", {"intellect": 10}),
        ("Astral Reservoir", {"intellect": 10, "stamina": 5}),
        ("Star Reader", {"intellect": 14}),
        ("Eldritch Focus", {"intellect": 13, "agility": 5}),
        ("Infinite Thesis", {"intellect": 22, "stamina": 8}),
    ],
    "assassin": [
        ("Knife Discipline", {"agility": 4}),
        ("Silent Steps", {"dexterity": 3, "agility": 2}),
        ("Keen Edge", {"agility": 7}),
        ("Shadow Poise", {"dexterity": 5, "stamina": 4}),
        ("Death's Measure", {"agility": 9, "accuracy": 2}),
        ("Ghost's Reach", {"agility": 12}),
        ("Unseen Guard", {"dexterity": 8, "stamina": 6}),
        ("Perfect Cut", {"agility": 15}),
        ("Night Sovereign", {"agility": 18, "dexterity": 9}),
    ],
    "priest": [
        ("Quiet Prayer", {"intellect": 4}),
        ("Merciful Hands", {"intellect": 4, "stamina": 3}),
        ("Steadfast Faith", {"stamina": 6, "intellect": 3}),
        ("Radiant Wisdom", {"intellect": 9}),
        ("Guardian Vow", {"stamina": 9, "intellect": 4}),
        ("Hallowed Voice", {"intellect": 12}),
        ("Sacred Endurance", {"stamina": 13, "intellect": 5}),
        ("Dawn's Counsel", {"intellect": 16}),
        ("Eternal Benediction", {"intellect": 19, "stamina": 11}),
    ],
    "hunter": [
        ("Sure Draw", {"agility": 4}),
        ("Trail Sense", {"agility": 3, "stamina": 3}),
        ("Hawk's Eye", {"agility": 6, "accuracy": 2}),
        ("Wilderness Heart", {"stamina": 8, "agility": 3}),
        ("Longbow Craft", {"agility": 10}),
        ("Pathfinder's Step", {"agility": 9, "dexterity": 5}),
        ("Far Horizon", {"agility": 14}),
        ("Storm Tracker", {"agility": 13, "stamina": 7}),
        ("Master of the Hunt", {"agility": 20, "dexterity": 8}),
    ],
}


def main():
    entries = []
    for cls, rows in ROWS.items():
        for index, (name, bonus) in enumerate(rows, 1):
            level = index * 10
            description = "Always active: " + ", ".join(
                f"+{amount} {stat.capitalize()}" for stat, amount in bonus.items()
            ) + "."
            entries.append({"id": f"{cls}_milestone_{level}", "name": name,
                            "class": cls, "level": level, "description": description,
                            "bonus": bonus})
    (ROOT / "world/passives.txt").write_text(json.dumps(entries, indent=2) + "\n")


if __name__ == "__main__":
    main()
