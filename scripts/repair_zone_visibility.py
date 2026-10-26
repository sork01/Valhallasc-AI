#!/usr/bin/env python3
"""Apply the owning generators' visibility repairs without rebuilding released content."""
import json
from generate_worldheart import MAP, add_meeting_stone, check as check_canopy
from generate_lapis_erg import repair_oases, check as check_lapis

def main():
    world = json.loads(MAP.read_text())
    canopy, lapis = world['zones'][22], world['zones'][24]
    add_meeting_stone(canopy['objects'])
    repair_oases(lapis)
    check_canopy(canopy)
    check_lapis(lapis)
    MAP.write_text(json.dumps(world, indent=2, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    main()
