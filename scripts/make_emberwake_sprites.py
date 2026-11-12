#!/usr/bin/env python3
"""Emberwake native art pipeline. Saved editor sources survive build and export."""
import sys
import emberwake_slime_redraw as redraw
from emberwake_slime_redraw import KINDS, build, export, verify, preview

if __name__ == '__main__':
    if '--replace' in sys.argv:
        raise SystemExit('--replace is refused; use emberwake_slime_redraw.py refresh KIND')
    action = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    {'build': build, 'export': export, 'verify': verify, 'preview': preview}[action]()
