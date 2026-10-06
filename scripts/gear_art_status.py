"""Persistent, per-piece checklist for the level-25–50 gear artwork redesign.

init creates the 252 base-piece tasks without replacing an existing state. render refreshes the Markdown checklist.
update JOB --phase PHASE --note TEXT records partial work. finish JOB --evidence FILE... checks off a completed piece
only when its preview, worn atlas and matching icon have been produced and checked. Neither command deploys anything.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'docs/gear-redesign-state.txt'
TODO = ROOT / 'GEAR_REDESIGN_TODO.md'
CLASSES = ('assassin', 'warrior', 'mage', 'priest', 'hunter')
KINDS = ('armor', 'headgear', 'shoulders', 'gloves', 'weapon')
SHARED = ('pants', 'necklace', 'accessory')


def initial():
    items = json.loads((ROOT / 'world/items.txt').read_text())
    tasks = []
    for label, predicate in [(f'L{n}', lambda i, n=n: i.get('requiredLevel') == n and i['rarity'] == 'common' and not i.get('source')) for n in range(25, 51, 5)] + [
        (wing, lambda i, wing=wing: i.get('source') == f'cathedral_{wing}') for wing in ('cloister', 'reliquary', 'nave')
    ]:
        for cls, kinds in [(c, KINDS) for c in CLASSES] + [(None, SHARED)]:
            for kind in kinds:
                matches = [i for i in items if i.get('class') == cls and i['kind'] == kind and predicate(i)]
                assert len(matches) == 1, (label, cls, kind)
                item = matches[0]
                tasks.append(dict(id=f'{label}-{cls or "shared"}-{kind}', group=label,
                                  className=cls, kind=kind, item=item['id'], name=item['name'],
                                  done=False, phase='not started', note='', evidence=[]))
    assert len(tasks) == 252
    return dict(updated=datetime.now().isoformat(timespec='seconds'), active='L50-assassin-armor',
                tasks=tasks, integration=dict(renderer=False, catalog=False, icons=False, tests=False, filedrop=False))


def render(state):
    count = sum(t['done'] for t in state['tasks'])
    text = f'''# Gear redesign: levels 25–50 and the Drowned Cathedral

**Completed base pieces: {count}/{len(state['tasks'])}.** Updated {state['updated']}.
**Active/next piece:** `{state['active']}`.

## User's final scope

Create genuinely new armor and weapon shapes for each level: 25, 30, 35, 40, 45 and 50, for all five classes.
Green, blue and purple variants may recolor that level's base gear. Purple stays at the catalog's existing levels
30/40/50. Include matching worn layers and inventory icons, both bodies and every animation/facing.
Three Cathedral wings also need their own designs at levels 40/45/50 (28 pieces each).
Keep existing item IDs, stats, class/level restrictions, loot sources and saves. Preserve level-1–20 and GM artwork.
Do not commit, push, deploy or restart the production server unless the user asks.

The previous implementation added the item catalog and loot rules but reused starter silhouettes; the user rejected
that visual approach. **The old recolor previews are not evidence of completed redesign work.**

## Handoff and completion rules

1. Read `AGENTS.md` and the skills at `/home/serveperry/.claude/skills/createarmors/SKILL.md`,
   `/home/serveperry/.claude/skills/createweapons/SKILL.md` and `/home/serveperry/.claude/skills/makesprites/SKILL.md`.
2. Inspect `docs/gear-redesign-state.txt` before work. Resume the active piece or the first unchecked piece.
   Preserve all existing uncommitted changes: the gear catalog and Cathedral loot work already passed tests.
3. Draw new source layers through the existing cel rig; existing atlases and PixelFlow editor edits stay intact.
   `scripts/cel_common.py` supplies poses, depth, palette, preview/build/export helpers; each class's source is
   `scripts/make_<class>_cel_sprites.py` (Priest: `make_priest_sprites.py`). Assassin male body/blades are legacy.
4. Mark partial progress immediately: `python3 scripts/gear_art_status.py update JOB --phase PHASE --note TEXT`.
5. A checked piece means new source art, both-body all-pose worn exports, a matching icon, wiring and a visually
   inspected preview exist. Check it off **immediately after finishing that individual piece**, not after a whole set:
   `python3 scripts/gear_art_status.py finish JOB --evidence relative/file ... --note TEXT`.
   Include the preview, male/female atlas and icon artifact paths; use the note for PixelFlow IDs and checks.
6. Keep the active piece and a concrete next command current. Scratch work under `.tools/` and `test-results/`
   is local-only. Put reusable drawing source and the state here in the repo so another agent can take over.
7. New art must visibly differ from the starter and adjacent levels; hue changes alone do not complete a piece.
   Preview the level-50 assassin first, then work through all six levels and the three wings.

## Integration checkpoints

'''
    for key, label in [('renderer', 'New layer loading and allowed variants'), ('catalog', 'Catalog maps each level/tier to its new base art'),
                       ('icons', 'Matching inventory icons exported and wired'), ('tests', 'Generator, Rust, actual MCP and browser/art checks'),
                       ('filedrop', 'Updated level-50 assassin preview saved to Sork’s Filedrop')]:
        text += f'- [{"x" if state["integration"][key] else " "}] {label}\n'
    if state.get('preview'):
        text += '\nLatest full-set preview: [Level-50 assassin on Filedrop](' + state['preview']['url'] + ').\n'
        text += 'All eight ordinary level-50 pieces are redesigned; Cathedral and other levels remain tracked below.\n'
    for group in dict.fromkeys(t['group'] for t in state['tasks']):
        text += f'\n## {group}\n\n'
        for task in (t for t in state['tasks'] if t['group'] == group):
            text += f'- [{"x" if task["done"] else " "}] `{task["id"]}` — {task["name"]}'
            if task['phase'] != 'not started':
                text += f' — {task["phase"]}'
            if task['note']:
                text += f' ({task["note"]})'
            text += '\n'
    TODO.write_text(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['init', 'render', 'update', 'reopen', 'finish'])
    p.add_argument('job', nargs='?')
    p.add_argument('--phase', default='in progress')
    p.add_argument('--note', default='')
    p.add_argument('--evidence', nargs='+', default=[])
    args = p.parse_args()
    if args.command == 'init' and not STATE.exists():
        STATE.parent.mkdir(exist_ok=True)
        STATE.write_text(json.dumps(initial(), indent=2) + '\n')
    state = json.loads(STATE.read_text())
    if args.command in ('update', 'reopen', 'finish'):
        task = next(t for t in state['tasks'] if t['id'] == args.job)
        if args.command == 'reopen':
            assert task['done'], 'Only a completed piece can be reopened'
            task.update(done=False, phase=args.phase, evidence=[])
            state['active'] = task['id']
        elif args.command == 'finish':
            assert args.evidence and all((ROOT / f).is_file() for f in args.evidence), 'Completed pieces need existing evidence files'
            task.update(done=True, phase='complete', evidence=args.evidence)
            remaining = [t for t in state['tasks'] if not t['done']]
            state['active'] = remaining[0]['id'] if remaining else 'integration checks'
        else:
            assert not task['done'], 'Finished tasks need an explicit review before reopening'
            task['phase'] = args.phase
            state['active'] = task['id']
        task['note'] = args.note
        state['updated'] = datetime.now().isoformat(timespec='seconds')
        STATE.write_text(json.dumps(state, indent=2) + '\n')
    render(state)
    print(f'{sum(t["done"] for t in state["tasks"])}/{len(state["tasks"])} pieces complete; active: {state["active"]}')


if __name__ == '__main__':
    main()
