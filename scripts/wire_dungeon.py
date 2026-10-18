#!/usr/bin/env python3
"""python3 scripts/wire_dungeon.py <make_x_sprites.py> <redraw_module> <note>: add the dungeon_cel.install call before `def render`."""
import sys
p, mod, note = sys.argv[1:4]
s = open(p).read()
if f"dungeon_cel.install(globals(), '{mod}')" in s:
    raise SystemExit('already wired')
call = f"dungeon_cel.install(globals(), '{mod}')\n"
if 'import dungeon_cel' in s:
    s = s.replace("\n\ndef render(kind):", f"\n{call}\n\ndef render(kind):", 1)
else:
    s = s.replace("\n\ndef render(kind):", f"\n\n# {note}\nimport dungeon_cel  # noqa: E402\n{call}\n\ndef render(kind):", 1)
open(p, 'w').write(s)
