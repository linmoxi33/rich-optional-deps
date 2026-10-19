"""Tests for the optional-dependency behaviour of syntax / traceback / logging.

These tests pin down the contract introduced when Pygments and markdown-it-py
became optional extras:

* the built-in ANSI themes must work with Pygments absent;
* a missing Pygments theme degrades to an ANSI theme with a warning;
* ``rich.logging`` / ``rich.traceback`` must not import Pygments on the happy path;
* ``Markdown`` must raise an actionable ImportError when markdown-it-py is missing.
"""
from __future__ import annotations

import builtins
import io
import sys
import warnings
from typing import Any, Iterator

import pytest

from rich.console import Console
from rich.syntax import ANSISyntaxTheme, RICH_SYNTAX_THEMES, Syntax


@pytest.fixture
def no_pygments(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Simulate an environment where Pygments is not installed."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "pygments" or name.startswith("pygments."):
            raise ImportError("No module named 'pygments'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    # ``_pygments_available`` is lru_cached, so clear it for the duration.
    from rich import syntax as syntax_module

    syntax_module._pygments_available.cache_clear()
    yield
    syntax_module._pygments_available.cache_clear()


def render(renderable: Any, width: int = 60) -> str:
    console = Console(
        file=io.StringIO(),
        width=width,
        force_terminal=False,
        _environ={},
    )
    console.print(renderable)
    return console.file.getvalue()


def test_ansi_themes_are_tuple_keyed() -> None:
    """Built-in themes must not depend on Pygments token objects."""
    for name, theme in RICH_SYNTAX_THEMES.items():
        for key in theme:
            assert isinstance(key, tuple), f"{name} has a non-tuple key: {key!r}"


def test_ansi_theme_lookup_matches_pygments_tokens() -> None:
    """A tuple key and the equivalent Pygments token must resolve identically."""
    pygments_token = pytest.importorskip("pygments.token")
    theme = ANSISyntaxTheme(RICH_SYNTAX_THEMES["ansi_dark"])

    probes = [
        pygments_token.Token,
        pygments_token.Comment,
        pygments_token.Comment.Preproc,
        pygments_token.Keyword,
        pygments_token.Keyword.Type,
        pygments_token.Operator.Word,
        pygments_token.Name.Function,
        pygments_token.Name.Class,
        pygments_token.String,
        pygments_token.Number,
        pygments_token.Generic.Error,
        pygments_token.Error,
        pygments_token.Whitespace,
    ]
    for token in probes:
        assert theme.get_style_for_token(token) == theme.get_style_for_token(tuple(token))


def test_syntax_works_without_pygments(no_pygments: None) -> None:
    """Code still renders as text using a built-in theme."""
    syntax = Syntax("x = 1\n", "python", theme="ansi_dark")
    assert "x = 1" in render(syntax)


def test_pygments_theme_falls_back_with_warning(no_pygments: None) -> None:
    """A Pygments theme degrades to ANSI instead of raising."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        syntax = Syntax("x = 1\n", "python", theme="monokai")
        output = render(syntax)

    assert "x = 1" in output
    assert any("pygments" in str(w.message) for w in caught)


def test_ansi_theme_does_not_warn_without_pygments(no_pygments: None) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        render(Syntax("x = 1\n", "python", theme="ansi_light"))
    assert not caught


def test_guess_lexer_without_pygments_returns_default(no_pygments: None) -> None:
    assert Syntax.guess_lexer("example.py") == "default"


def test_rich_logging_does_not_import_pygments() -> None:
    """Importing the logging handler must not drag Pygments in."""
    code = (
        "import sys; import rich.logging; "
        "print('pygments' in sys.modules)"
    )
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_rich_traceback_does_not_import_pygments() -> None:
    code = (
        "import sys; import rich.traceback; "
        "print('pygments' in sys.modules)"
    )
    import subprocess

    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


def test_markdown_raises_actionable_error_without_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "markdown_it" or name.startswith("markdown_it."):
            raise ImportError("No module named 'markdown_it'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    from rich.markdown import Markdown

    with pytest.raises(ImportError) as excinfo:
        Markdown("# hi")

    message = str(excinfo.value)
    assert "markdown-it-py" in message
    assert "rich[markdown]" in message
