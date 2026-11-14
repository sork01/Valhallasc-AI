#!/usr/bin/env python3
"""Write testfail.md from the logs of scripts/test-all.sh: python3 scripts/testfail_report.py [OUT] [notes.md]"""
import re, sys, os
from pathlib import Path
out = Path(sys.argv[1] if len(sys.argv) > 1 else 'test-results/all-tests')
notes = Path(sys.argv[2]).read_text() if len(sys.argv) > 2 else ''
L = ['# Test failures\n', notes]
cargo = out / 'cargo-test.log'
if cargo.exists():
    log = cargo.read_text(errors='replace')
    fails = re.findall(r'^test (\S+) \.\.\. FAILED$', log, re.M)
    m = re.findall(r'^test result: .*$', log, re.M)
    L.append(f"## Rust (`cargo test --no-fail-fast`): {len(fails)} failed ({'; '.join(m)})\n")
    blocks = re.split(r'^---- (\S+) stdout ----$', log, flags=re.M); msg = {}
    for i in range(1, len(blocks), 2):
        p = re.search(r"panicked at ([^\n]+):\n(.*?)(?:\n\n|\nnote:)", blocks[i + 1], re.S)
        msg[blocks[i]] = (p.group(1) + ' ' + p.group(2).replace('\n', ' | '))[:230] if p else ''
    L += [f"- [ ] `{f}` — {msg.get(f, '')}" for f in sorted(fails)]
py = out / 'py-results.tsv'
if py.exists():
    rows = [l.split('\t') for l in py.read_text().splitlines()]
    bad = [r for r in rows if r[1] != '0']
    L.append(f"\n## Python (`tests/*.py`): {len(bad)} failed of {len(rows)}\n")
    for n, rc in bad:
        t = (out / f'py-{n}.log').read_text(errors='replace').strip().splitlines()
        L.append(f"- [ ] `tests/{n}.py` (exit {rc}) — {t[-1][:200] if t else '(no output, timed out?)'}")
br = out / 'browser-results.tsv'
if br.exists():
    rows = [l.split('\t') for l in br.read_text().splitlines() if '\t' in l]
    bad = [r for r in rows if r[1] != '0']
    L.append(f"\n## Node/browser (`tests/*.cjs`, bounded runner): {len(bad)} failed of {len(rows)} run{'' if 'DONE' in br.read_text() else ' so far (run unfinished)'}\n")
    for n, rc, sec in bad:
        lg = [x for x in (out / 'browser' / f'{n}.log').read_text(errors='replace').splitlines()
              if re.search(r'error|assert|fail|timeout|not defined|cannot', x, re.I) and not x.lstrip().startswith('at ')]
        L.append(f"- [ ] `tests/{n}.cjs` (exit {rc}, {sec}s) — {lg[0].strip()[:200] if lg else ''}")
Path('testfail.md').write_text('\n'.join(L) + '\n')
