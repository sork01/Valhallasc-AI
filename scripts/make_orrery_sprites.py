#!/usr/bin/env python3
"""Obsidian Orrery sprite commands use saved slime-style PixelFlow sources; old art stays backed up."""
from orrery_slime_redraw import build, export, verify, preview, extents, refresh
import sys
if __name__ == '__main__':
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; edit the saved sources and export.')
    {'preview': preview, 'extents': extents, 'build': build, 'refresh': refresh,
     'export': export, 'verify': verify}[sys.argv[1] if len(sys.argv)>1 else 'preview']()
