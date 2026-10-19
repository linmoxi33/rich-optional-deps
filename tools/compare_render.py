"""Compare two render matrices produced by ``render_matrix.py``.

Exits non-zero if anything differs, so it can gate CI.

    python tools/compare_render.py base.json new.json
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)

    base_path, new_path = sys.argv[1], sys.argv[2]
    with open(base_path, encoding="utf-8") as fh:
        base = json.load(fh)
    with open(new_path, encoding="utf-8") as fh:
        new = json.load(fh)

    only_base = sorted(set(base) - set(new))
    only_new = sorted(set(new) - set(base))
    shared = sorted(set(base) & set(new))
    diffs = [key for key in shared if base[key] != new[key]]

    print(f"captures: base={len(base)} new={len(new)} shared={len(shared)}")
    if only_base:
        print(f"only in base ({len(only_base)}): {only_base}")
    if only_new:
        print(f"only in new ({len(only_new)}): {only_new}")

    identical = len(shared) - len(diffs)
    print(f"identical: {identical}/{len(shared)}")

    if diffs:
        print(f"DIFFERENT: {len(diffs)}")
        for key in diffs:
            print(f"  - {key}")
            old, cur = base[key], new[key]
            # Show the first differing position so the diff is actionable.
            limit = min(len(old), len(cur))
            pos = next((i for i in range(limit) if old[i] != cur[i]), limit)
            lo = max(0, pos - 40)
            print(f"      base: {old[lo:pos + 40]!r}")
            print(f"      new : {cur[lo:pos + 40]!r}")
        return 1

    if only_base or only_new:
        return 1

    print("OK: all captures are byte-identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
