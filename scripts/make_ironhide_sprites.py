#!/usr/bin/env python3
"""Ironhide Beetle sprite plumbing. The CLI delegates to meadow_slime_redraw (preview | build | refresh | export | verify).

The Greenmeadow slimes are the style reference and are not touched here.  --replace is refused.
"""
import sys

if __name__ == '__main__':
    import meadow_slime_redraw as redraw
    command = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused. Edit the saved source and export to preserve it.')
    if command not in ('preview', 'build', 'refresh', 'export', 'verify'):
        raise SystemExit('Usage: make_ironhide_sprites.py preview | build | refresh | export | verify')
    getattr(redraw, command)()
