"""Add the high-level rank rotation without changing skill IDs or base effects."""
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
    for skill in skills:
        base = skill["level"]
        ranks = [r for r in skill["ranks"] if r["level"] <= base + 40]
        travel = skill["id"] in ("blink", "rollaway")
        ranks.append({"level": base + 60,
                      "power": 1 if travel else 1.6,
                      "cooldown": 0.55 if travel else 1,
                      "description": "45% shorter cooldown." if travel
                      else "60% stronger damage, healing or buff effect."})
        if base <= 18:
            ranks.append({"level": base + 80,
                          "power": 1 if travel else 1.8,
                          "cooldown": 0.4 if travel else 1,
                          "description": "60% shorter cooldown." if travel
                          else "80% stronger damage, healing or buff effect."})
        else:
            ranks.append({"level": 99, "power": 2, "cooldown": 1,
                          "capstone": True, "description": CAPSTONES[skill["class"]]})
        skill["ranks"] = ranks
    PATH.write_text("[\n" + ",\n".join("  " + json.dumps(s, ensure_ascii=False, separators=(",", ":")) for s in skills) + "\n]\n")


if __name__ == "__main__":
    main()
