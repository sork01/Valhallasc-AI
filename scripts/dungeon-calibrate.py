#!/usr/bin/env python3
"""Try dungeon power multipliers without a rebuild and print what the lone and party checks say.

  python3 scripts/dungeon-calibrate.py undervault --kind thrall=1.5,2 --kind hollowking=1,2.5
  python3 scripts/dungeon-calibrate.py "flooded cloister,coral" --tests pack,boss --seeds 2
  python3 scripts/dungeon-calibrate.py undervault --table my-table.json     # a whole table instead of kind=hp,dmg

The multipliers are written over `world/elite-power.txt` into a temporary table read through ELITE_POWER_FILE (test
builds only), so a trial costs the fights and not a compile. `--kind` may repeat; a bare `kind=2` means damage only
(health 1). With `--write` the merged table replaces `world/elite-power.txt` (rebuild before shipping).
Tests: pack (lone player must die to every pack), boss (lone player must die to every boss, green/purple/purple+5),
party (five players in green must win every pack and boss).
"""
import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ["warrior", "mage", "assassin", "priest", "hunter"]
TESTS = {
    "pack": "dungeon_solo_tests::a_dungeon_pack_kills_a_lone_player",
    "boss": "dungeon_solo_tests::a_dungeon_boss_kills_a_lone_player",
    "party": "dungeon_solo_tests::a_party_of_five_beats_every_dungeon_pack_and_boss",
}


def test_binary():
    out = subprocess.run(["bash", "scripts/cargo.sh", "test", "--no-run", "--message-format=json"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    path = None
    for line in out.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("profile", {}).get("test") and m.get("executable"):
            path = m["executable"]
    if not path:
        sys.exit("no test binary found")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dungeons", help="comma-separated words of dungeon names (DUNGEON_SOLO_DUNGEONS)")
    ap.add_argument("--kind", action="append", default=[], help="kind=hp,damage or kind=damage")
    ap.add_argument("--table", help="JSON table merged over world/elite-power.txt")
    ap.add_argument("--kinds", default="", help="only these bosses/mobs and the packs holding them (DUNGEON_SOLO_KINDS)")
    ap.add_argument("--classes", default="", help="lone classes, comma-separated (default: all five)")
    ap.add_argument("--enrage-file", help="soft-enrage table kind -> [start, ramp] used instead of world/enrage.txt (ENRAGE_FILE)")
    ap.add_argument("--tests", default="pack,boss,party")
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--write", action="store_true", help="write the merged table to world/elite-power.txt")
    ap.add_argument("--verbose", action="store_true", help="print every violation line")
    a = ap.parse_args()

    table = json.loads((ROOT / "world/elite-power.txt").read_text())
    if a.table:
        table.update(json.loads(Path(a.table).read_text()))
    for item in a.kind:
        kind, vals = item.split("=")
        nums = [float(v) for v in vals.split(",")]
        table[kind] = [1.0, nums[0]] if len(nums) == 1 else nums[:2]
    work = Path(tempfile.mkdtemp(prefix="calibrate-", dir=ROOT / "test-results"))
    power = work / "power.json"
    power.write_text(json.dumps(table, indent=1))
    if a.write:
        (ROOT / "world/elite-power.txt").write_text(json.dumps(table, indent=2, sort_keys=True) + "\n")
    binary = test_binary()
    env = dict(os.environ, ELITE_POWER_FILE=str(power), DUNGEON_SOLO_DUNGEONS=a.dungeons,
               DUNGEON_SOLO_SEEDS=str(a.seeds), DUNGEON_SOLO_FAIL_FAST="0", DUNGEON_SOLO_KINDS=a.kinds)
    if a.enrage_file:
        env["ENRAGE_FILE"] = str(Path(a.enrage_file).resolve())
    wanted = a.tests.split(",")
    jobs = []  # (label, process, logfile)
    for name in wanted:
        if name == "party":
            shards = os.cpu_count() or 4  # the party control: one process per shard of dungeons
            for i in range(shards):
                jobs.append((f"party/{i}", [binary, TESTS[name], "--ignored", "--nocapture"], {"DUNGEON_PARTY_SHARD": f"{i}/{shards}"}))
        else:
            for c in (a.classes.split(",") if a.classes else CLASSES):
                jobs.append((f"{name}/{c}", [binary, TESTS[name], "--ignored", "--nocapture"], {"DUNGEON_SOLO_CLASS": c}))
    cores = os.cpu_count() or 4
    running, results = [], {}
    pending = list(jobs)
    while pending or running:
        while pending and len(running) < cores:
            label, cmd, extra = pending.pop(0)
            log = work / (label.replace("/", "-") + ".log")
            p = subprocess.Popen(cmd, cwd=ROOT, env=dict(env, **extra), stdout=open(log, "w"), stderr=subprocess.STDOUT)
            running.append((label, p, log))
        label, p, log = running.pop(0)
        p.wait()
        results[label] = log.read_text()
    summarize(results, a)
    print("logs:", work)


def summarize(results, a):
    for kind, marker in (("pack", "LONE PLAYER SURVIVED A PACK"), ("boss", "LONE PLAYER SURVIVED A BOSS")):
        if kind not in a.tests.split(","):
            continue
        total = survived = 0
        per = {}
        for label, text in results.items():
            if not label.startswith(kind + "/"):
                continue
            for line in text.splitlines():
                m = re.match(rf"\[{kind} \d+\] (.*?) L(\d+) (.*?) vs lone", line)
                if not m:
                    continue
                total += 1
                key = f"{m.group(1)} {m.group(3) if kind == 'boss' else ''}".strip()
                row = per.setdefault(key, [0, 0])
                row[0] += 1
                if marker in line:
                    survived += 1
                    row[1] += 1
                    if a.verbose:
                        print(line)
        print(f"== lone {kind}: {survived} survived of {total} fights")
        for key, (n, s) in sorted(per.items()):
            print(f"   {key}: lone player survived {s} of {n}" + ("" if s == 0 else "   <-- TOO EASY"))
    if any(k.startswith("party/") for k in results):
        text = "\n".join(t for k, t in results.items() if k.startswith("party/"))
        wins = [l for l in text.splitlines() if l.startswith("[party5")]
        bad = [l for l in wins if "CANNOT WIN" in l]
        print(f"== party of five: {len(wins) - len(bad)} of {len(wins)} groups beaten")
        for l in bad if not a.verbose else wins:
            print("  ", l)
    for label, text in results.items():
        if "panicked" in text and "must" not in text:
            print(f"!! {label} panicked unexpectedly:\n{text[-800:]}")


if __name__ == "__main__":
    main()
