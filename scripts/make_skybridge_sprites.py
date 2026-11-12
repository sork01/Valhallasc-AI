#!/usr/bin/env python3
"""Shattered Span native PixelFlow entry points; saved editor frames survive export."""
import sys
import span_slime_redraw as native
KINDS = native.KINDS


def build(kinds=None, replace=False):
    assert not replace, '--replace is refused; use span_slime_redraw.py refresh KIND'
    return native.build(kinds)


def export(kinds=None):
    return native.export(kinds)


def verify(kinds=None):
    return native.verify(kinds)


def preview(kinds=None):
    return native.preview()


if __name__ == '__main__':
    action = sys.argv[1] if len(sys.argv) > 1 else 'preview'
    kinds = [k for k in sys.argv[2:] if k in KINDS] or KINDS
    if action == 'build': build(kinds, replace='--replace' in sys.argv[2:])
    else: globals()[action](kinds)
