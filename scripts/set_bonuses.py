#!/usr/bin/env python3
"""Validate the dungeon set design and export one catalog for Rust and the client."""

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/set-bonuses.md"
CATALOG = ROOT / "world/set-bonuses.txt"
CLIENT = ROOT / "client/setbonuses.js"
CLASSES = ("warrior", "mage", "assassin", "priest", "hunter")


def build():
    document = DOC.read_text()
    items = json.loads((ROOT / "world/items.txt").read_text())
    skills = json.loads((ROOT / "world/skills.txt").read_text())
    sources = {i["source"] for i in items if i.get("source") not in (None, "orange_pool", "chained_forge_packs", "raid_hierlooms")}
    pieces = Counter(i.get("source") for i in items if i["kind"] != "cloak")
    assert all(pieces[source] == 28 for source in sources), "each dungeon set needs 28 catalog pieces"
    levels = {i["source"]: i["requiredLevel"] for i in items if i.get("source") in sources}
    signatures = {}
    section = document.split("## Signature effects at eight pieces\n", 1)[1].split("\n## ", 1)[0]
    for line in section.splitlines():
        if line.startswith("| `"):
            source, _, description = [s.strip() for s in line.strip("| ").split("|", 2)]
            source = source.strip("`")
            match = re.fullmatch(r"\*\*([^*]+):\*\* (.+)", description)
            assert match and source in sources and source not in signatures, source
            signatures[source] = {"name": match[1], "description": match[2]}
    assert signatures.keys() == sources
    assert len({v["name"] for v in signatures.values()}) == len(sources)
    entries = []
    for klass in CLASSES:
        section = document.split(f"## {klass.capitalize()} (`SET-{klass.upper()}`)\n", 1)[1].split("\n## ", 1)[0]
        known = {s["id"]: s["level"] for s in skills if s["class"] == klass}
        rows = []
        for line in section.splitlines():
            if not line.startswith("| `"):
                continue
            source, stat, cooldown, doubled, trigger = [s.strip().strip("`") for s in line.strip("| ").split("|")]
            assert source in sources and stat.startswith("+5% "), (klass, line)
            assert stat[4:] in ("attack", "defense", "health", "resource"), stat
            assert all(known.get(skill, 999) <= levels[source] for skill in (cooldown, doubled, trigger)), (klass, source)
            rows.append({"source": source, "class": klass, "stat": stat[4:], "cooldownSkill": cooldown,
                         "doubleSkill": doubled, "triggerSkill": trigger})
        assert len(rows) == len(sources) and {r["source"] for r in rows} == sources, klass
        assert len({(r["cooldownSkill"], r["doubleSkill"], r["triggerSkill"]) for r in rows}) == len(rows), klass
        entries.extend(rows)
    return {"signatures": signatures, "entries": entries}


if __name__ == "__main__":
    data = build()
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    js = "'use strict';\nwindow.WORLD_SET_BONUSES = " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";\n"
    CATALOG.write_text(content)
    CLIENT.write_text(js)
    print(f"Exported {len(data['entries'])} set bonus rows and {len(data['signatures'])} signatures")
