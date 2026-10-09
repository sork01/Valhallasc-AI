#!/usr/bin/env python3
"""Precompute the tight alpha bounding box of every frame of every part of every layered sprite set.

client/magesprite.js reads only that rectangle of each frame (colour and depth) instead of scanning the 160x160 cell.
Output: client/assets/<set>_bounds.txt beside <set>_sprites.txt (JSON in a .txt, because Apache blocks .json). Per part
one base64 string of 4 bytes per frame (x, y, w, h; w = 0 for an empty frame), frames in clip order (the order of
meta.clips), then direction 0-7, then index.

    python3 scripts/sprite_bounds.py            # (re)write every sidecar
    python3 scripts/sprite_bounds.py --check    # exit 1 if any sidecar is missing or differs from the PNGs

Run it after any script that rewrites a part PNG. The client falls back to a slower scan when a sidecar is missing,
but a STALE sidecar clips sprites, which is why --check exists (tests/sprite-loading.cjs runs it).
"""
import base64
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image

ASSETS = Path(__file__).resolve().parent.parent / "client" / "assets"
VERSION = 1


def bounds_name(meta_path: Path) -> Path:
    return meta_path.with_name(meta_path.name.replace("_sprites.txt", "_bounds.txt"))


def part_bounds(png: Path, meta: dict) -> bytes:
    fw, fh = meta["frame"]
    alpha = np.asarray(Image.open(png).convert("RGBA"))[:, :, 3] > 0
    out = bytearray()
    for clip in meta["clips"].values():
        for d in range(8):
            for i in range(clip["n"]):
                cell = alpha[(clip["row0"] + d) * fh:(clip["row0"] + d + 1) * fh, i * fw:(i + 1) * fw]
                ys, xs = np.nonzero(cell)
                if len(xs) == 0:
                    out += bytes([0, 0, 0, 0])
                else:
                    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
                    out += bytes([x0, y0, x1 - x0 + 1, y1 - y0 + 1])
    return bytes(out)


def build(meta_path: Path) -> dict | None:
    meta = json.loads(meta_path.read_text())
    if "parts" not in meta or "clips" not in meta or max(meta["frame"]) > 255:
        return None
    frames = sum(c["n"] for c in meta["clips"].values()) * 8
    names = list(meta["parts"])
    with Pool() as pool:
        results = pool.starmap(part_bounds, [(ASSETS / meta["parts"][n]["png"], meta) for n in names])
    parts = {}
    for name, data in zip(names, results):
        assert len(data) == frames * 4, (meta_path.name, name)
        parts[name] = base64.b64encode(data).decode()
    return {"version": VERSION, "frames": frames, "parts": parts}


def main() -> int:
    check = "--check" in sys.argv
    bad = 0
    for meta_path in sorted(ASSETS.glob("*_sprites.txt")):
        built = build(meta_path)
        if built is None:
            continue
        target = bounds_name(meta_path)
        text = json.dumps(built, separators=(",", ":")) + "\n"
        if check:
            if not target.exists() or target.read_text() != text:
                print("STALE" if target.exists() else "MISSING", target.name)
                bad += 1
        else:
            target.write_text(text)
            print("wrote", target.name, len(built["parts"]), "parts,", len(text) // 1024, "KB")
    if check:
        print("sprite bounds:", "FAILED" if bad else "ok")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
