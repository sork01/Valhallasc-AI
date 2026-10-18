"""L-SWEDISH-REDO: the hand-written Swedish catalog is complete, consistent and free of machine output.

Checks (python3 tests/swedish-catalog.py):
  1. every player-facing English text and template the build harvests has a Swedish entry, is a listed name or loanword
     (scripts/sv-keep.txt), or is listed as not text (scripts/sv-ignore.txt);
  2. a template keeps its {0} placeholders (one listed exception drops a plural ending);
  3. no entry equals its English text, none is empty and none looks like code;
  4. no Swedish text contains an English function word (the, and, you, of ...), which is what a half-translated line looks like;
  5. client/sv-data.js is exactly what scripts/build_swedish.py writes from the hand-written files;
  6. spot checks of the words the old machine catalog got wrong (party is "grupp", never "fest"; a staff is a "stav").
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import build_swedish as build  # noqa: E402

text = json.loads(build.TEXT_FILE.read_text())
templates = json.loads(build.TEMPLATE_FILE.read_text())
keep = set(json.loads(build.KEEP_FILE.read_text()))
ignore = set(json.loads(build.IGNORE_FILE.read_text()))
texts, template_sources = build.harvest()

phrases = json.loads(build.PHRASE_FILE.read_text())
errors = build.problems(text, templates, keep, ignore, texts, template_sources, phrases)
assert not errors, '\n'.join(errors[:40]) + f'\n{len(errors)} problems'
assert len(texts) > 6000 and len(template_sources) > 200, f'harvest looks broken: {len(texts)} texts, {len(template_sources)} templates'

ENGLISH = re.compile(r'\b(the|and|you|your|with|from|for|of|this|that|are|have|will)\b')
# Names that contain an English function word and are kept as written in the Swedish text.
NAMES = ('Heart of the', 'Bag of')
half = [(k, v) for k, v in list(text.items()) + list(templates.items()) + list(phrases.items()) if ENGLISH.search(v) and not any(n in v for n in NAMES)]
assert not half, 'English words left in Swedish text:\n  ' + '\n  '.join(f'{k!r} -> {v!r}' for k, v in half[:30])

phrases = json.loads(build.PHRASE_FILE.read_text())
expected = build.assemble(text, templates, phrases)
assert (ROOT / 'client' / 'sv-data.js').read_text() == expected, 'client/sv-data.js is stale: run python3 scripts/build_swedish.py'

assert 'fest' not in ' '.join(re.findall(r'\bfest\w*', ' '.join(text.values()))).split(), 'party must be "grupp", not "fest"'
assert text['Invite to party'] == 'Bjud in till grupp'
assert text['Ash Staff'] == 'Askstav' and text['Crystal Staff'] == 'Kristallstav'
assert text['Gather a party and face the Glasslion.'].startswith('Samla en grupp')
print(f'Swedish catalog: {len(text)} texts + {len(templates)} templates, {len(keep)} kept names, {len(ignore)} ignored; all checks passed')
