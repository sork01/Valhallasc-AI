"""Space new abilities through 40 and keep a rank reward at later even levels.

The first nine abilities unlock at 4, 8, ..., 36 and gain rank 2 two
levels later. The tenth unlocks at 40 and gains rank 2 at 42. Ranks 3 and
4 rotate at 42–60 and 62–80; rank 5 rotates at 82–98, with the final
ability's capstone at 99. Level 42 awards two ranks.
"""
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "world/skills.txt"
CAPSTONES = {
    "warrior": "Titan's Wrath reaches its final earthshaking rank: double base damage and healing from damage dealt.",
    "mage": "Starfall reaches its final celestial rank: double base damage across its full field.",
    "assassin": "Thousand Cuts reaches its final shadow rank: double base damage through its full blade fan.",
    "priest": "Heaven's Wrath reaches its final dawn rank: double base damage and healing pulse.",
    "hunter": "Arrow Storm reaches its final tempest rank: double base damage across its surrounding storm.",
}


def main():
    skills = json.loads(PATH.read_text())
    by_class = {}
    for skill in skills:
        index = by_class.get(skill["class"], 0)
        assert index < 10 and len(skill["ranks"]) == 4, skill["id"]
        by_class[skill["class"]] = index + 1
        skill["level"] = (index + 1) * 4
        levels = [skill["level"] + 2, 42 + index * 2,
                  62 + index * 2, 99 if index == 9 else 82 + index * 2]
        for rank, level in zip(skill["ranks"], levels):
            rank["level"] = level
        assert levels == sorted(levels), skill["id"]
    assert by_class == {key: 10 for key in CAPSTONES}
    PATH.write_text("[\n" + ",\n".join("  " + json.dumps(s, ensure_ascii=False, separators=(",", ":")) for s in skills) + "\n]\n")


if __name__ == "__main__":
    main()
