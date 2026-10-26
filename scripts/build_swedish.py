#!/usr/bin/env python3
"""Assemble client/sv-data.js from the hand-written Swedish files. No translation service is used.

Hand-written files (all JSON, all written by hand; see docs/swedish-glossary.md for the word choices):
  scripts/sv-translations.txt           exact English text -> Swedish
  scripts/sv-template-translations.txt  English template with {0}, {1}... -> Swedish template
  scripts/sv-phrase-translations.txt    short English phrases with numbers ({0}) that the client replaces inside longer
                                        composed lines, as "Rank {0}:" or "{0}s cooldown." (numbers only, never names)
  scripts/sv-keep.txt                   texts that stay as they are (names, loanwords)
  scripts/sv-ignore.txt                 harvested strings that are not player-facing text

Run `python3 scripts/build_swedish.py` to write client/sv-data.js; it fails with a list when the harvested English
has no Swedish, a template changes its placeholders, a Swedish text is the English text, or a text looks like code.
`--check` runs the same checks without writing. New strings go into the hand-written files, never into sv-data.js.
"""
import glob
import html.parser
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEXT_FILE = ROOT / 'scripts' / 'sv-translations.txt'
TEMPLATE_FILE = ROOT / 'scripts' / 'sv-template-translations.txt'
PHRASE_FILE = ROOT / 'scripts' / 'sv-phrase-translations.txt'
KEEP_FILE = ROOT / 'scripts' / 'sv-keep.txt'
IGNORE_FILE = ROOT / 'scripts' / 'sv-ignore.txt'
OUTPUT = ROOT / 'client' / 'sv-data.js'
KEYS = {'name', 'title', 'description', 'label', 'dialogue', 'role', 'what', 'todo', 'tip'}
# Client modules whose strings reach the player. Art, music and the GM console are left out.
# whatsnew.js and release-notes.txt are deliberately English-only (owner, 2026-10-24).
CLIENT_FILES = ('game', 'account', 'city', 'quests', 'inventory', 'skillbar', 'quickuse', 'settings', 'online', 'social',
                'syslog', 'attributes', 'weather', 'daynight', 'bank', 'rebirth', 'bossmech', 'bosssign', 'mounts', 'trade', 'pvp',
                'rolls', 'shop', 'gearservices', 'worldmap', 'field', 'spark', 'keymap', 'raidkey', 'touch', 'dpsmeter', 'activity')
INTERNAL = ('INSERT ', 'ALTER ', 'PRAGMA ', 'SELECT ', 'CREATE ', 'UPDATE ', 'DELETE ', 'Bearer ', 'HTTP ', 'SIGTERM ', 'VALHALLA_')
# A template may leave out a placeholder only where Swedish needs no plural ending the English one builds.
MAY_DROP = {'A treasure chest has appeared! It will vanish in {0} minute{1}.': {'{1}'}}
CODE_WORDS = re.compile(r'\b(function|const|undefined|null|addEventListener|querySelector)\b|=>|\|\||&&|\?\.|\);')


def is_text(value):
    """Heuristic: the harvest also picks up ids, css, event names and message types; those are not text."""
    t = value.strip()
    if not re.search(r'[A-Za-z]{3}', t):
        return False
    if re.fullmatch(r'[a-z][A-Za-z0-9_.:\-]*', t):
        return False
    if re.match(r'(rgba?|hsla?|url|polygon|translate|hue-rotate)\(', t) or t.startswith(('--', '#', '.', '_', ',')):
        return False
    if re.fullmatch(r'[a-z0-9\-_ ]+', t) and '-' in t:
        return False
    if re.fullmatch(r'[a-z\-]+:\{?\d?\}?[:\d\{\}]*', t):
        return False
    return '{0}px' not in t and 'sans-serif' not in t


def rust_source(path):
    """The part of a Rust file that runs on the server (everything before its tests module)."""
    source = pathlib.Path(path).read_text()
    return re.split(r'#\[cfg\(test\)\]\s*(?:#\[[^\]]*\]\s*)*mod \w+\s*\{', source)[0]


def harvest():
    """Return (texts, templates): the English the player can see, as the build finds it."""
    found = set()

    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in KEYS and isinstance(child, str):
                    found.add(child)
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for filename in glob.glob(str(ROOT / 'world' / '*.txt')):
        try:
            walk(json.loads(pathlib.Path(filename).read_text()))
        except json.JSONDecodeError:
            pass

    class Text(html.parser.HTMLParser):
        def handle_data(self, data):
            data = data.strip()
            if re.search(r'[A-Za-z]{3}', data) and len(data) < 700:
                found.add(data)

        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in ('title', 'placeholder', 'aria-label') and value and re.search(r'[A-Za-z]{3}', value):
                    found.add(value)
    Text().feed((ROOT / 'client' / 'index.html').read_text())
    templates = set()

    def add_template(value, pattern):
        if not re.search(r'[A-Za-z]{3}', value) or re.search(r'[<>=;/\\]', value):
            return
        parts = re.split(pattern, value)
        if len(parts) < 2 or sum(len(x) for x in parts if not re.fullmatch(pattern, x)) < 8:
            return
        index = iter(range(20))
        normalized = re.sub(pattern, lambda _: '{' + str(next(index)) + '}', value)
        if '${' in normalized or normalized.count('{') != normalized.count('}'):
            return
        if normalized.startswith(('login:', 'register:', 'sso:', 'quest:', 'refinement_')):
            return
        templates.add(normalized)
    for name in CLIENT_FILES:
        source = (ROOT / 'client' / (name + '.js')).read_text()
        for match in re.finditer(r"(?<![\\\w])(['\"])((?:\\.|(?!\1)[^\\\n]){3,260})\1", source):
            value = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), re.sub(r"\\(['\"])", r'\1', match[2]))
            if not re.search(r'[A-Za-z]{3}', value) or re.search(r'[{}<>$]', value) or value.startswith(('#', '.', 'http', '--', '/')):
                continue
            # A string with code characters counts only when it reads as a sentence: it starts with a capital and has a space.
            if re.search(r'[=;+/]|\(\)|\.\w+\(', value) and not (re.match(r'[A-Z]', value) and ' ' in value):
                continue
            found.add(value)
        for value in re.findall(r'`([^`\n]{4,220})`', source):
            add_template(value, r'\$\{[^{}]*\}')
    for filename in glob.glob(str(ROOT / 'server' / 'src' / '**' / '*.rs'), recursive=True):
        if '_tests.rs' in filename:
            continue
        source = rust_source(filename)
        for value in re.findall(r'"([^"\\\n]{4,180})"', source):
            if re.match(r'[A-Z][A-Za-z ]{3}', value) and ' ' in value and not re.search(r'[{}\\/<>:=]', value) and not value.startswith(INTERNAL):
                found.add(value)
        for value in re.findall(r'"([^"\\\n]{4,220})"', source):
            add_template(value, r'\{[^{}]*\}')
    return sorted(v for v in found if v.strip() and is_text(v)), sorted(t for t in templates if is_text(t))


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def problems(text, templates, keep, ignore, texts, template_sources, phrases=None):
    """Every way the hand-written files can be wrong, as readable lines."""
    out = []
    covered = set(text) | set(templates) | keep | ignore
    for source in texts:
        if source not in covered:
            out.append(f'no Swedish for text: {source!r}')
    for source in template_sources:
        if source not in covered:
            out.append(f'no Swedish for template: {source!r}')
    for source, swedish in list(text.items()) + list(templates.items()):
        if source == swedish:
            out.append(f'Swedish equals English (list it in sv-keep.txt if it is a name): {source!r}')
        if not swedish.strip():
            out.append(f'empty Swedish: {source!r}')
        if CODE_WORDS.search(swedish):
            out.append(f'looks like code: {source!r}')
        want = set(re.findall(r'\{\d+\}', source))
        have = set(re.sub(r':t\}', '}', x) for x in re.findall(r'\{\d+(?::t)?\}', swedish))
        if have - want or (want - have - MAY_DROP.get(source, set())):
            out.append(f'placeholders differ: {source!r} -> {swedish!r}')
    for source, swedish in (phrases or {}).items():
        if source == swedish or not swedish.strip():
            out.append(f'bad phrase: {source!r} -> {swedish!r}')
        if sorted(re.findall(r'\{\d+\}', source)) != sorted(re.findall(r'\{\d+\}', swedish)):
            out.append(f'phrase placeholders differ: {source!r} -> {swedish!r}')
    for source in text:
        if re.search(r'\{\d+\}', source):
            out.append(f'a template is in sv-translations.txt: {source!r}')
    for source in templates:
        if not re.search(r'\{\d+\}', source):
            out.append(f'a plain text is in sv-template-translations.txt: {source!r}')
    for source in keep & (set(text) | set(templates)):
        out.append(f'listed as kept and translated: {source!r}')
    return out


def assemble(text, templates, phrases):
    """The text of client/sv-data.js for the hand-written files."""
    dump = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    longest_first = lambda table: sorted(table.items(), key=lambda pair: -len(pair[0]))
    return ("'use strict';\nwindow.SV_TEXT = " + json.dumps(text, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + ';\n'
            'window.SV_TEMPLATES = ' + dump(longest_first(templates)) + ';\n'
            'window.SV_PHRASES = ' + dump(longest_first(phrases)) + ';\n')


def main():
    check_only = '--check' in sys.argv
    text = load(TEXT_FILE, {})
    foundry_text = load(ROOT / 'scripts/sv-blackhour-translations.txt', {})
    assert not (text.keys() & foundry_text.keys()), 'duplicate Foundry translations'
    text.update(foundry_text)
    templates = load(TEMPLATE_FILE, {})
    phrases = load(PHRASE_FILE, {})
    keep = set(load(KEEP_FILE, []))
    ignore = set(load(IGNORE_FILE, []))
    texts, template_sources = harvest()
    errors = problems(text, templates, keep, ignore, texts, template_sources, phrases)
    if errors:
        print('\n'.join(errors[:200]))
        print(f'{len(errors)} problems; nothing written')
        return 1
    stale = [s for s in list(text) + list(templates) if s not in set(texts) | set(template_sources)]
    if check_only:
        # sv-data.js is generated: a hand edit, or a source file changed without a rebuild, is stale.
        if not OUTPUT.exists() or OUTPUT.read_text() != assemble(text, templates, phrases):
            print('client/sv-data.js is stale: run `python3 scripts/build_swedish.py` and commit it')
            return 1
        print(f'ok: {len(texts)} texts, {len(template_sources)} templates harvested; {len(text)} + {len(templates)} translated; '
              f'{len(stale)} entries the harvest does not see (kept: server and script strings)')
        return 0
    output = assemble(text, templates, phrases)
    OUTPUT.write_text(output)
    print(f'wrote {len(text)} texts and {len(templates)} templates to {OUTPUT.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
