#!/usr/bin/env python3
"""The test suite holds only tests that run: an #[ignore]d Rust test is a tool and sits behind the `tools` switch, and every
script that runs a tool builds with it (a filter that matches nothing would otherwise succeed in silence). MUTATE=ungated|script must fail."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CFG = '#[cfg(feature = "tools")]'
assert re.search(r'^\[features\]\n(?:#.*\n)*tools = \[\]$', (ROOT / 'server/Cargo.toml').read_text(), re.M), 'the tools switch'
found = 0
for path in sorted((ROOT / 'server/src').rglob('*.rs')):
    text = path.read_text()
    if os.getenv('MUTATE') == 'ungated' and path.name == 'vault_tests.rs':
        text = text.replace(CFG, '', 1)
    lines = text.split('\n')
    for i, line in enumerate(lines):
        if not re.match(r'\s*#\[ignore', line):
            continue
        # The attributes of this one test: the unbroken run of attribute and comment lines around the #[ignore].
        start = i
        while start > 0 and re.match(r'\s*(#\[|//)', lines[start - 1]):
            start -= 1
        assert any(CFG in l for l in lines[start:i]), f'{path.relative_to(ROOT)}:{i + 1}: an ignored test is not behind the tools switch'
        found += 1
assert found >= 40, f'only {found} tools found'
runners = sorted(p for p in (ROOT / 'scripts').iterdir() if p.suffix in ('.sh', '.py') and '--ignored' in p.read_text()
                 and re.search(r'cargo(\.sh)?"?,? "?test', p.read_text()))
assert len(runners) >= 8, [p.name for p in runners]
for path in runners:
    text = path.read_text()
    if os.getenv('MUTATE') == 'script' and path.name == 'ttk.sh':
        text = text.replace('valhalla-server/tools', '')
    for line in text.split('\n'):
        if re.search(r'cargo(\.sh)?"?,? "?test', line) and not line.lstrip().startswith('#'):
            assert 'valhalla-server/tools' in line, f'{path.name} builds tests without the tools switch: {line.strip()}'
# The scripts under tests/tools sit one level deeper than the suites: every relative path they name must still resolve.
scripts = sorted((ROOT / 'tests/tools').glob('*.cjs'))
assert len(scripts) >= 8 and not [p.name for p in scripts if (ROOT / 'tests' / p.name).exists()], 'tools stay out of tests/'
for path in scripts:
    text = path.read_text()
    if os.getenv('MUTATE') == 'path' and path.name == 'gear-sheet.cjs':
        text = text.replace("'../../client'", "'../client'")
    for target in re.findall(r"require\('(\.[^']*)'\)", text):
        assert (path.parent / target).exists(), f'{path.name} requires a missing {target}'
    for target in re.findall(r"__dirname,\s*'([^']*)'", text):
        top = (path.parent / target).resolve()
        assert top == ROOT or (top.relative_to(ROOT).parts[0] in ('client', 'world', 'scripts', 'test-results')), f'{path.name} points at {target}'
print(f'{found} tools are behind the switch; {len(runners)} runners build with it')
