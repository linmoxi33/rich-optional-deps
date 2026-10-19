"""Verify Rich still works with the optional dependencies absent.

Run this with an interpreter that does NOT have Pygments or markdown-it-py
installed:

    python -m venv /tmp/minimal
    /tmp/minimal/bin/pip install --no-deps .
    /tmp/minimal/bin/python tools/check_minimal_env.py

Exits non-zero if any expectation fails, so it can gate CI.
"""

from __future__ import annotations

import io
import logging
import sys
import warnings

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    suffix = f"  ({detail})" if detail else ""
    print(f"[{status}] {name}{suffix}")
    if not condition:
        FAILURES.append(name)


def console(**kwargs) -> "object":
    from rich.console import Console

    return Console(
        file=io.StringIO(),
        width=kwargs.pop("width", 60),
        force_terminal=kwargs.pop("force_terminal", False),
        _environ={},
        **kwargs,
    )


# --- 0. the environment must actually be minimal ----------------------
try:
    import pygments  # noqa: F401

    check("pygments absent", False, "pygments IS installed; run in a clean venv")
except ImportError:
    check("pygments absent", True)

try:
    import markdown_it  # noqa: F401

    check("markdown_it absent", False, "markdown_it IS installed")
except ImportError:
    check("markdown_it absent", True)

# --- 1. core import must not pull Pygments ----------------------------
import rich  # noqa: E402
from rich.console import Console  # noqa: E402

check("import rich", True)
check("pygments not imported by core", "pygments" not in sys.modules)

# --- 2. core renderables ----------------------------------------------
from rich.panel import Panel  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.tree import Tree  # noqa: E402

c = console(width=50)
table = Table(title="demo")
table.add_column("k")
table.add_column("v")
table.add_row("a", "1")
c.print(table)
c.print(Panel("inside a panel", title="box"))
tree = Tree("root")
tree.add("child")
c.print(tree)
text = c.file.getvalue()

check("table renders", "demo" in text and "a" in text)
check("panel renders", "inside a panel" in text and "┌" in text)
check("tree renders", "root" in text and "child" in text)

# --- 3. rich.logging must work without Pygments ----------------------
from rich.logging import RichHandler  # noqa: E402

check("rich.logging imports without pygments", "pygments" not in sys.modules)

buf = io.StringIO()
log_console = Console(
    file=buf, width=80, force_terminal=True, color_system="truecolor", _environ={}
)
handler = RichHandler(
    console=log_console, show_time=False, show_path=False, rich_tracebacks=True
)
logger = logging.getLogger("minimal")
logger.handlers = [handler]
logger.setLevel(logging.DEBUG)
logger.propagate = False
logger.info("plain message")
try:
    1 / 0
except ZeroDivisionError:
    logger.exception("boom")

logged = buf.getvalue()
check("RichHandler logs a plain message", "plain message" in logged)
check(
    "RichHandler renders a rich traceback",
    "Traceback" in logged and "ZeroDivisionError" in logged,
)
check("logging did not import pygments", "pygments" not in sys.modules)

# --- 4. Syntax falls back to the built-in ANSI theme -----------------
from rich.syntax import Syntax  # noqa: E402

check("rich.syntax imports without pygments", "pygments" not in sys.modules)

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    syntax = Syntax("def f(x):\n    return x + 1\n", "python", theme="monokai",
                    line_numbers=True)
    out = console(width=50)
    out.print(syntax)
rendered = out.file.getvalue()

check("Syntax renders code without pygments", "def f(x):" in rendered)
check(
    "Syntax warns about the Pygments fallback",
    any("pygments" in str(w.message) for w in caught),
)

# --- 5. an explicit built-in theme must stay silent ------------------
with warnings.catch_warnings(record=True) as quiet:
    warnings.simplefilter("always")
    out2 = console(width=40)
    out2.print(Syntax("x = 1\n", "python", theme="ansi_dark"))
check("ansi_dark renders", "x = 1" in out2.file.getvalue())
check("ansi_dark does not warn", not quiet)

# --- 6. Markdown must fail with an actionable message ----------------
try:
    from rich.markdown import Markdown

    Markdown("# hi")
    check("markdown raises without markdown-it-py", False, "no exception raised")
except ImportError as error:
    message = str(error)
    check(
        "markdown raises actionable ImportError",
        "markdown-it-py" in message and "rich[markdown]" in message,
        message.splitlines()[0],
    )

# --- 7. Pretty / JSON -------------------------------------------------
from rich.json import JSON  # noqa: E402
from rich.pretty import Pretty  # noqa: E402

out3 = console(width=60)
out3.print(Pretty({"a": [1, 2, 3]}))
out3.print(JSON('{"k": 1}'))
check("Pretty renders", "a" in out3.file.getvalue())
check("JSON renders", "k" in out3.file.getvalue())

print()
if FAILURES:
    print(f"FAILURES ({len(FAILURES)}): {FAILURES}")
    sys.exit(1)
print("ALL CHECKS PASSED")
