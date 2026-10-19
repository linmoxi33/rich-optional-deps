"""Render a broad matrix of Rich output and dump it to a JSON file.

Used to prove that making Pygments/markdown-it-py optional does not change a
single byte of rendered output.  Run it once against a pristine rich 14.1.0
checkout and once against a patched one, then compare the two JSON files.

    python tools/render_matrix.py /path/to/rich-14.1.0 base.json
    python tools/render_matrix.py /path/to/rich-14.1.0-patched new.json
    python tools/compare_render.py base.json new.json

Requires Pygments and markdown-it-py to be installed, since the point is to
compare the *full* feature set, not the degraded one.
"""

from __future__ import annotations

import io
import json
import logging
import os
import sys
import tempfile
import traceback

if len(sys.argv) < 3:
    raise SystemExit(__doc__)

sys.path.insert(0, sys.argv[1])
out_path = sys.argv[2]

results: dict[str, str] = {}


def capture(name: str, fn) -> None:
    """Record rendered output, or the exception, under ``name``."""
    try:
        results[name] = fn()
    except Exception:
        results[name] = "EXCEPTION:\n" + traceback.format_exc()


from rich.console import Console  # noqa: E402


def make_console(**kwargs) -> Console:
    return Console(
        file=io.StringIO(),
        width=kwargs.pop("width", 80),
        force_terminal=kwargs.pop("force_terminal", True),
        color_system=kwargs.pop("color_system", "truecolor"),
        _environ={},
        **kwargs,
    )


def flush(console: Console) -> str:
    return console.file.getvalue()


# ---- Syntax: every built-in + a spread of Pygments themes ------------
from rich.syntax import Syntax  # noqa: E402

CODE = "def f(x):\n    return x + 1  # comment\n\nclass A:\n    pass\n"

for theme in [
    "ansi_dark",
    "ansi_light",
    "monokai",
    "default",
    "emacs",
    "friendly",
    "colorful",
    "murphy",
    "native",
    "vim",
    "bw",
    "one-dark",
    "dracula",
]:
    for line_numbers in (False, True):
        for word_wrap in (False, True):
            key = f"syntax:{theme}:ln={line_numbers}:wrap={word_wrap}"
            capture(
                key,
                lambda t=theme, ln=line_numbers, w=word_wrap: (
                    lambda c: (
                        c.print(
                            Syntax(CODE, "python", theme=t, line_numbers=ln, word_wrap=w)
                        ),
                        flush(c),
                    )[1]
                )(make_console(width=60)),
            )

capture(
    "syntax:line_range",
    lambda: (
        lambda c: (
            c.print(
                Syntax(
                    CODE,
                    "python",
                    theme="monokai",
                    line_numbers=True,
                    line_range=(2, 4),
                    highlight_lines={2},
                    indent_guides=True,
                )
            ),
            flush(c),
        )[1]
    )(make_console(width=60)),
)

# from_path with an explicit lexer
fd, path = tempfile.mkstemp(suffix=".py")
os.write(fd, CODE.encode())
os.close(fd)
capture(
    "syntax:from_path",
    lambda: (
        lambda c: (c.print(Syntax.from_path(path, lexer="python")), flush(c))[1]
    )(make_console(width=60)),
)
os.remove(path)

capture(
    "syntax:guess",
    lambda: json.dumps(
        [
            Syntax.guess_lexer("a.py"),
            Syntax.guess_lexer("a.py", "import this"),
            Syntax.guess_lexer("a.html", "<a href='#'>hi</a>"),
            Syntax.guess_lexer("a.unknown"),
        ]
    ),
)

# ---- Traceback: several themes, with and without locals --------------
from rich.traceback import Traceback  # noqa: E402


def make_exc():
    try:
        _payload = {"k": [1, 2, {"n": None}], "s": "text", "b": True}
        1 / 0
    except ZeroDivisionError:
        return sys.exc_info()


for theme in ["ansi_dark", "ansi_light", "monokai", "default", "emacs"]:
    for show_locals in (False, True):
        key = f"traceback:{theme}:locals={show_locals}"
        capture(
            key,
            lambda t=theme, sl=show_locals: (
                lambda c: (
                    c.print(
                        Traceback.from_exception(
                            *make_exc(), width=80, theme=t, show_locals=sl
                        )
                    ),
                    flush(c),
                )[1]
            )(make_console(width=100)),
        )

# ---- RichHandler: plain and with rich tracebacks ---------------------
from rich.logging import RichHandler  # noqa: E402


def run_logging(rich_tracebacks: bool, theme: str | None = None) -> str:
    console = make_console(width=100)
    handler = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        rich_tracebacks=rich_tracebacks,
        tracebacks_theme=theme,
    )
    logger = logging.getLogger(f"cmp-{rich_tracebacks}-{theme}")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    try:
        raise ValueError("kaboom")
    except ValueError:
        logger.exception("exception happened")
    return flush(console)


capture("logging:plain", lambda: run_logging(False))
capture("logging:rich_tb", lambda: run_logging(True))
capture("logging:rich_tb_monokai", lambda: run_logging(True, "monokai"))
capture("logging:rich_tb_ansi_light", lambda: run_logging(True, "ansi_light"))

# ---- Markdown ---------------------------------------------------------
from rich.markdown import Markdown  # noqa: E402

MD = """# Title

Some **bold** and *italic* text with `inline code`.

```python
def f():
    return 1
```

| a | b |
|---|---|
| 1 | 2 |

- item one
- item two

> quote

[link](https://example.com)
"""

capture(
    "markdown:default",
    lambda: (lambda c: (c.print(Markdown(MD)), flush(c))[1])(make_console(width=70)),
)
capture(
    "markdown:theme",
    lambda: (
        lambda c: (c.print(Markdown(MD, code_theme="monokai")), flush(c))[1]
    )(make_console(width=70)),
)

# ---- Core renderables -------------------------------------------------
from rich.json import JSON  # noqa: E402
from rich.panel import Panel  # noqa: E402
from rich.pretty import Pretty  # noqa: E402
from rich.table import Table  # noqa: E402
from rich.tree import Tree  # noqa: E402

capture(
    "core:table",
    lambda: (
        lambda c: (
            (
                lambda t: (
                    t.add_column("k"),
                    t.add_column("v"),
                    t.add_row("a", "1"),
                    c.print(t),
                )
            )(Table(title="t")),
            flush(c),
        )[1]
    )(make_console(width=50)),
)

capture(
    "core:pretty",
    lambda: (
        lambda c: (
            c.print(Pretty({"a": [1, 2, 3], "b": None, "c": True})),
            flush(c),
        )[1]
    )(make_console(width=60)),
)
capture(
    "core:json",
    lambda: (lambda c: (c.print(JSON('{"k": [1,2],"n":null}')), flush(c))[1])(
        make_console(width=60)
    ),
)
capture(
    "core:panel",
    lambda: (lambda c: (c.print(Panel("body", title="t")), flush(c))[1])(
        make_console(width=50)
    ),
)
capture(
    "core:tree",
    lambda: (
        lambda c: ((lambda tr: (tr.add("kid"), c.print(tr)))(Tree("root")), flush(c))[1]
    )(make_console(width=40)),
)

# ---- ANSI theme token resolution (the tuple-key change) --------------
from rich.syntax import ANSISyntaxTheme, RICH_SYNTAX_THEMES  # noqa: E402

TOKENS = [
    ("Text",),
    ("Text", "Whitespace"),
    ("Comment",),
    ("Comment", "Preproc"),
    ("Keyword",),
    ("Keyword", "Type"),
    ("Operator", "Word"),
    ("Name", "Builtin"),
    ("Name", "Function"),
    ("Name", "Namespace"),
    ("Name", "Class"),
    ("Name", "Exception"),
    ("Name", "Decorator"),
    ("Name", "Variable"),
    ("Name", "Constant"),
    ("Name", "Attribute"),
    ("Name", "Tag"),
    ("Literal", "String"),
    ("Literal", "Number"),
    ("Literal", "String", "Delimiter"),
    ("Generic", "Deleted"),
    ("Generic", "Inserted"),
    ("Generic", "Heading"),
    ("Generic", "Subheading"),
    ("Generic", "Prompt"),
    ("Generic", "Error"),
    ("Error",),
    ("Name",),
    ("Operator",),
    ("Unknown", "Thing"),
]


def dump_theme(name: str) -> str:
    theme = ANSISyntaxTheme(RICH_SYNTAX_THEMES[name])
    rows = [[list(tok), repr(theme.get_style_for_token(tok))] for tok in TOKENS]
    rows.append([["bg"], repr(theme.get_background_style())])
    return json.dumps(rows)


capture("theme:ansi_dark", lambda: dump_theme("ansi_dark"))
capture("theme:ansi_light", lambda: dump_theme("ansi_light"))

with open(out_path, "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=1, ensure_ascii=False, sort_keys=True)

print(f"wrote {len(results)} captures to {out_path}")
