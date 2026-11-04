#!/usr/bin/env python3
"""Per-kind enemy frame sizes (docs/kind-frames.md): the one place the exporters and rollback scripts get the rules from.

A zone manifest has a zone-wide `frame` [w, h] and `anchor` [x, y].  A kind that needs another size gets an entry in the
optional `kindFrames` map: {kind: {"frame": [w, h], "anchor": [x, y]}}.  Kinds without an entry use the zone-wide values,
so a manifest with no `kindFrames` key is exactly what it was before this module existed.  An atlas is always 8 columns
by 5 rows of that kind's own frame size (34 frames, five clips, the same row order).
"""
from __future__ import annotations

MIN_FRAME = 32      # the border check needs room around the art
MAX_FRAME = 192     # owner decision 2026-11-04: a 34-frame atlas is 1536x960, about 6 MB of texture per kind
COLUMNS, ROWS = 8, 5


def check_frame(w, h, ax, ay):
    """Raise ValueError unless this frame size and anchor are allowed."""
    for name, v in (('width', w), ('height', h), ('anchor x', ax), ('anchor y', ay)):
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError(f'{name} must be an integer, got {v!r}')
    if not (MIN_FRAME <= w <= MAX_FRAME and MIN_FRAME <= h <= MAX_FRAME):
        raise ValueError(f'frame {w}x{h} is outside {MIN_FRAME}..{MAX_FRAME}')
    if not (0 <= ax < w and 0 <= ay < h):
        raise ValueError(f'anchor ({ax},{ay}) is outside the {w}x{h} frame')
    return w, h, ax, ay


def frame_of(meta, kind):
    """-> (w, h, ax, ay) for a kind: its own kindFrames entry, else the zone-wide values."""
    own = (meta.get('kindFrames') or {}).get(kind)
    if own:
        (w, h), (ax, ay) = own['frame'], own['anchor']
    else:
        (w, h), (ax, ay) = meta['frame'], meta['anchor']
    return check_frame(w, h, ax, ay)


def set_kind_frame(meta, kind, w, h, ax, ay):
    """Record a kind's frame in `meta`. Writes `kindFrames` only for a kind that differs from the zone-wide frame;
    a kind equal to it has any entry removed (and an empty map dropped), so unchanged zones stay byte-identical."""
    check_frame(w, h, ax, ay)
    zone = (tuple(meta['frame']), tuple(meta['anchor']))
    frames = meta.get('kindFrames') or {}
    if ((w, h), (ax, ay)) == zone:
        frames.pop(kind, None)
    else:
        frames[kind] = {'frame': [w, h], 'anchor': [ax, ay]}
    if frames:
        meta['kindFrames'] = frames
    else:
        meta.pop('kindFrames', None)
    return meta


def frames_from_manifest(entries):
    """{kind: {'frame': [w, h], 'anchor': [x, y]}} (the manifest shape, e.g. a backup's `oldFrames`) -> {kind: (w, h, ax, ay)}."""
    return {k: (*v['frame'], *v['anchor']) for k, v in (entries or {}).items()}


def atlas_size(w, h):
    return COLUMNS * w, ROWS * h


def check_bounds(bounds, w, h):
    """The art bounding box (l, t, r, b) must clear the frame border by at least one transparent pixel."""
    assert bounds and bounds[0] > 0 and bounds[1] > 0 and bounds[2] < w and bounds[3] < h, f'art touches the {w}x{h} border: {bounds}'


def top_of(idle_bounds, ay):
    """Health-bar `tops` entry: sprite pixels from the anchor up to the highest idle pixel, from this kind's own anchor."""
    return int(ay - min(b[1] for b in idle_bounds))


def merge_kind_entries(live, kinds, sprites, tops, frames=None):
    """Return a copy of a SHARED manifest (Cathedral) with only these kinds' `sprites`, `tops` and `kindFrames` entries
    replaced; every other kind's entries and every other key are kept, in the same order.  `frames` is
    {kind: (w, h, ax, ay)}; a kind not in it is put back on the zone-wide frame."""
    import json
    merged = json.loads(json.dumps(live))
    for kind in kinds:
        merged['sprites'][kind] = sprites[kind]
        merged['tops'][kind] = tops[kind]
        if frames and kind in frames:
            set_kind_frame(merged, kind, *frames[kind])
        else:
            set_kind_frame(merged, kind, *merged['frame'], *merged['anchor'])
    return merged


def restore_kind_entries(live, kinds, old_sprites, old_tops, old_frames=None):
    """Rollback twin of merge_kind_entries: puts the saved entries back (a kind with no saved frame returns to the zone-wide one)."""
    return merge_kind_entries(live, kinds, old_sprites, old_tops, old_frames)
