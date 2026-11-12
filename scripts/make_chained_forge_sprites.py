#!/usr/bin/env python3
"""Chained Forge native editable sources. Destructive legacy replacement is refused."""
import sys
import forge_slime_redraw as native
from chained_forge_content import ENEMIES
KINDS = [e['kind'] for e in ENEMIES]
PREFIX = native.PREFIX
PALETTES = {k: native.PALETTE for k in KINDS}

def draw(enemy, clip, n):
    return native.rgba(native.frame(enemy['kind'], clip, n))

def build(kinds=None, replace=False):
    assert not replace, '--replace is refused; use forge_slime_redraw.py refresh KIND'
    return native.build(kinds or KINDS)

def export(kinds=None):return native.export()
def verify(kinds=None):return native.verify()
def preview(kinds=None):return native.preview()

if __name__ == '__main__':
    assert '--replace' not in sys.argv, '--replace is refused; use refresh KIND explicitly'
    cmd = sys.argv[1] if len(sys.argv)>1 else 'preview'
    kinds = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    globals()[cmd](kinds)
