#!/usr/bin/env python3
"""KINDFRAME-EXPORT checks: the shared per-kind frame rules (scripts/kindframe.py). No PixelFlow, no server."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts'))
import kindframe as kf

n = 0
def check(ok, label):
    global n
    assert ok, label
    n += 1
    print(f'{n}: {label}')

def refused(*a):
    try: kf.check_frame(*a)
    except ValueError: return True
    return False

check(kf.check_frame(192, 192, 96, 190) == (192, 192, 96, 190), '192x192 maximum accepted')
check(refused(193, 96, 48, 90) and refused(96, 193, 48, 90), 'a 193 px frame is refused (both axes)')
check(refused(31, 96, 10, 20) and refused(96, 31, 48, 20), 'frames under the 32 px minimum are refused')
check(refused(96, 96, 96, 90) and refused(96, 96, 48, -1) and refused(96, 96, 48.5, 90) and refused(96, 96, True, 90), 'anchor outside the frame / non-integer is refused')
check(kf.atlas_size(64, 64) == (512, 320) and kf.atlas_size(192, 192) == (1536, 960), 'atlas is 8 columns by 5 rows of the kind\'s own frame')

# a manifest with no kindFrames behaves exactly as before
live = json.loads((ROOT/'client/assets/crags.txt').read_text())
check('kindFrames' not in live and kf.frame_of(live, 'wisp') == (96, 96, 48, 90), 'a live manifest has no kindFrames and falls back to the zone-wide frame')
same = json.loads(json.dumps(live)); kf.set_kind_frame(same, 'wisp', 96, 96, 48, 90)
check(json.dumps(same) == json.dumps(live), 'writing the zone-wide size for a kind adds nothing (byte-identical)')

# per-kind entries: written only for kinds that differ, others unaffected
m = json.loads(json.dumps(live))
kf.set_kind_frame(m, 'wisp', 64, 64, 32, 58); kf.set_kind_frame(m, 'golem', 192, 192, 96, 184)
check(m['kindFrames'] == {'wisp': {'frame': [64, 64], 'anchor': [32, 58]}, 'golem': {'frame': [192, 192], 'anchor': [96, 184]}}, 'only the differing kinds get entries')
check(kf.frame_of(m, 'spider') == (96, 96, 48, 90) and kf.frame_of(m, 'wisp') == (64, 64, 32, 58) and kf.frame_of(m, 'golem') == (192, 192, 96, 184), 'lookup: own entry, else zone-wide')
kf.set_kind_frame(m, 'wisp', 96, 96, 48, 90); kf.set_kind_frame(m, 'golem', 96, 96, 48, 90)
check(json.dumps(m) == json.dumps(live), 'returning every kind to the zone-wide size removes the map again')
check(kf.top_of([(10, 20, 30, 80), (10, 14, 30, 80)], 90) == 76 and kf.top_of([(0, 50, 9, 99)], 184) == 134, 'tops derive from the kind\'s own anchor')
try: kf.check_bounds((0, 5, 50, 60), 96, 96); touched = False
except AssertionError: touched = True
check(touched and (kf.check_bounds((1, 1, 95, 95), 96, 96) is None), 'border check: art touching the frame edge is refused')

# the SHARED Cathedral manifest: merging the Cloister kinds back as they are changes nothing, and only they change when resized
cath = json.loads((ROOT/'client/assets/cathedral.txt').read_text())
kinds = ['tidetemplar', 'tidecantor', 'tideleech', 'bellkeeper', 'mournsister', 'rootabbot', 'choirmother', 'choirsinger']
same = kf.merge_kind_entries(cath, kinds, {k: cath['sprites'][k] for k in kinds}, {k: cath['tops'][k] for k in kinds})
check(json.dumps(same) == json.dumps(cath), 'cathedral.txt: merging the eight kinds unchanged is byte-identical')
big = kf.merge_kind_entries(cath, kinds, {k: cath['sprites'][k] for k in kinds}, {k: cath['tops'][k] for k in kinds}, {'rootabbot': (160, 160, 80, 154)})
other = [k for k in cath['sprites'] if k not in kinds]
check(big['kindFrames'] == {'rootabbot': {'frame': [160, 160], 'anchor': [80, 154]}}, 'only the resized Cloister kind gets an entry')
check(all(big['sprites'][k] == cath['sprites'][k] and big['tops'][k] == cath['tops'][k] for k in other) and list(big['sprites']) == list(cath['sprites']), 'the other 138 kinds\' entries and key order are untouched')
back = kf.restore_kind_entries(big, kinds, {k: cath['sprites'][k] for k in kinds}, {k: cath['tops'][k] for k in kinds})
check(json.dumps(back) == json.dumps(cath), 'rollback with no saved frames returns the shared manifest byte-identically')

# rollback format: a backup stores oldFrames in the manifest shape; converting must not break and must round-trip
old_frames = {'rootabbot': {'frame': [160, 160], 'anchor': [80, 154]}}
check(kf.frames_from_manifest(old_frames) == {'rootabbot': (160, 160, 80, 154)} and kf.frames_from_manifest(None) == {}, 'backup oldFrames (manifest shape) convert to frame tuples')
there = kf.restore_kind_entries(cath, kinds, {k: cath['sprites'][k] for k in kinds}, {k: cath['tops'][k] for k in kinds}, kf.frames_from_manifest(old_frames))
check(there['kindFrames'] == old_frames, 'rollback restores a saved per-kind frame')
back = kf.restore_kind_entries(there, kinds, {k: cath['sprites'][k] for k in kinds}, {k: cath['tops'][k] for k in kinds}, kf.frames_from_manifest(None))
check(json.dumps(back) == json.dumps(cath), 'rollback with no oldFrames removes the entry again (byte-identical)')

# borrowed art: an alias kind takes the source kind's frame (what boss_add_art_aliases.py does)
al = json.loads(json.dumps(cath)); kf.set_kind_frame(al, 'cf_kettil', 160, 160, 80, 154)
kf.set_kind_frame(al, 'es_foe_x', *kf.frame_of(al, 'cf_kettil'))
check(al['kindFrames']['es_foe_x'] == al['kindFrames']['cf_kettil'], 'an alias kind copies the borrowed kind\'s frame')
kf.set_kind_frame(al, 'es_foe_y', *kf.frame_of(al, 'cf_brute'))
check('es_foe_y' not in al['kindFrames'], 'an alias of a zone-wide kind gets no entry')

# every live manifest still has the same frame and no kindFrames key
for p in sorted((ROOT/'client/assets').glob('*.txt')):
    try: d = json.loads(p.read_text())
    except Exception: continue
    if isinstance(d, dict) and 'kinds' in d and 'clips' in d and 'frame' in d:
        assert 'kindFrames' not in d, p.name
        kf.check_frame(*d['frame'], *d['anchor']) if d['frame'][0] >= kf.MIN_FRAME else None
        n += 1
print(f'{n}: every live enemy manifest has no kindFrames (backward compatible)')
