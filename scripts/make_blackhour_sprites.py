#!/usr/bin/env python3
"""Black Hour Foundry native PixelFlow pipeline; registered editor frames are preserved."""
import sys
from blackhour_content import ENEMIES
import foundry_slime_redraw as native
KINDS = native.KINDS


def preview(kinds=None):
    return native.preview()


def build(kinds=None, replace=False):
    assert not replace and '--replace' not in sys.argv, '--replace refused; use foundry_slime_redraw.py refresh KIND'
    return native.build(kinds)


def export(kinds=None):
    return native.export(kinds)


def verify(kinds=None):
    return native.verify(kinds)


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    assert '--replace' not in sys.argv, '--replace refused; use foundry_slime_redraw.py refresh KIND'
    kinds = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    {'preview': preview, 'build': build, 'export': export, 'verify': verify}[action](kinds)
