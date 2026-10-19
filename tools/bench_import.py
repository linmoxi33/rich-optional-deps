"""Interleaved A/B import-cost benchmark.

Compares import time between a pristine rich checkout and a patched one.

Two methodology details that materially change the result:

1. **Pre-warm both trees with compileall first.**  Otherwise the tree that has
   never been imported pays byte-compilation cost and looks slower for reasons
   that have nothing to do with the change.  An early run of this benchmark
   without pre-warming reported ``rich.console`` as 23% faster, which is
   impossible -- ``rich.console`` is not touched by the patch.

2. **Interleave A and B samples.**  Machine load drifts; measuring all of A then
   all of B attributes that drift to the change.  Each sample gets a fresh
   interpreter.

Usage:
    python tools/bench_import.py <pristine_dir> <patched_dir> [rounds]
"""

from __future__ import annotations

import json
import statistics
import subprocess
import sys

TARGETS = [
    "rich",
    "rich.console",
    "rich.table",
    "rich.panel",
    "rich.progress",
    "rich.logging",
    "rich.traceback",
    "rich.syntax",
    "rich.markdown",
    "rich.pretty",
    "rich.tree",
    "rich.live",
    "rich.prompt",
]

# Modules the patch does not touch.  Their deltas are the noise floor: if they
# move by more than a few percent, the measurement is not trustworthy.
CONTROLS = {"rich", "rich.console", "rich.table", "rich.panel", "rich.progress",
            "rich.pretty", "rich.tree", "rich.live", "rich.prompt"}

PROBE = (
    "import json,sys,time\n"
    "t0=time.perf_counter()\n"
    "__import__(sys.argv[1])\n"
    "dt=(time.perf_counter()-t0)*1000\n"
    "heavy=[m for m in ('pygments','markdown_it') if m in sys.modules]\n"
    "nsub=len([m for m in sys.modules if m.startswith('pygments')])\n"
    "print(json.dumps({'ms':dt,'heavy':heavy,'nsub':nsub}))\n"
)


def prewarm(tree: str) -> None:
    """Byte-compile the package so both sides start from the same state."""
    code = (
        "import compileall, sys;"
        "ok = compileall.compile_dir('rich', quiet=2, force=True);"
        "sys.exit(0 if ok else 1)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tree, capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit(f"compileall failed for {tree}:\n{result.stderr}")


def sample(tree: str, module: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", PROBE, module],
        cwd=tree,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"ms": float("nan"), "heavy": ["ERROR"], "nsub": -1}
    return json.loads(result.stdout)


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)

    pristine, patched = sys.argv[1], sys.argv[2]
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 15

    print("pre-warming bytecode for both trees ...")
    prewarm(pristine)
    prewarm(patched)

    print(f"interleaved A/B, {rounds} rounds, fresh interpreter per sample\n")
    header = (
        f"{'module':16s} {'base ms':>9s} {'patch ms':>9s} {'delta':>9s} "
        f"{'%':>6s}  {'pygments(base->patch)':>22s}"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for module in TARGETS:
        base_samples, patch_samples = [], []
        heavy_base = heavy_patch = None
        for _ in range(rounds):
            a = sample(pristine, module)
            b = sample(patched, module)
            base_samples.append(a["ms"])
            patch_samples.append(b["ms"])
            heavy_base, heavy_patch = a["heavy"], b["heavy"]

        base_ms = statistics.median(base_samples)
        patch_ms = statistics.median(patch_samples)
        delta = patch_ms - base_ms
        pct = (delta / base_ms * 100) if base_ms else 0.0

        tag = "" if module in CONTROLS else "  <- affected"
        print(
            f"{module:16s} {base_ms:9.1f} {patch_ms:9.1f} {delta:+9.1f} "
            f"{pct:+5.0f}%  {','.join(heavy_base) or '-'} -> "
            f"{','.join(heavy_patch) or '-'}{tag}"
        )
        rows.append(
            {
                "module": module,
                "control": module in CONTROLS,
                "base_ms": round(base_ms, 1),
                "patch_ms": round(patch_ms, 1),
                "delta_ms": round(delta, 1),
                "delta_pct": round(pct, 1),
                "base_heavy": heavy_base,
                "patch_heavy": heavy_patch,
            }
        )

    noise = [abs(r["delta_pct"]) for r in rows if r["control"]]
    print(
        f"\ncontrol-group |delta| max = {max(noise):.1f}% "
        f"(this is the noise floor; treat smaller deltas as no change)"
    )


if __name__ == "__main__":
    main()
