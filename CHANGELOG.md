# CHANGELOG

## 0.1.0 — 2026-10-19

Patch against `Textualize/rich` **v14.1.0** (MIT).

### Changed

- `pygments` and `markdown-it-py` are now **optional** dependencies.
  New extras: `syntax`, `markdown`, `all`.
  A default `pip install rich` no longer pulls in ≈8.8 MB / 823 files.
- `rich.syntax` no longer imports Pygments at module level. Pygments is imported
  only when a Pygments theme or a lexer is actually requested.
- `rich.traceback` no longer imports Pygments at module level. Its theme table is
  keyed by plain tuples; `_guess_lexer` imports Pygments lazily.
- `rich.markdown` imports `markdown-it-py` at `Markdown` construction rather than
  at module import, and raises an actionable `ImportError` when it is missing.
- `rich.logging` therefore no longer transitively requires Pygments. This matters
  because `RichHandler` only uses `Traceback` when `rich_tracebacks=True`
  (default `False`).

### Added

- `rich/_syntax_themes.py` — ANSI theme tables keyed by plain tuples, so the
  built-in themes work with no Pygments installed. Pygments token types are
  `tuple` subclasses with tuple-equivalent hashing, so lookups are unchanged.
- `syntax.MissingPygmentsError` and `syntax._pygments_available()`.
- `tests/test_optional_deps.py` — 9 tests pinning the new contract.

### Behaviour when Pygments is absent

| Situation | Before | After |
|---|---|---|
| `Syntax(theme="ansi_dark")` | `ModuleNotFoundError` at import | renders, no warning |
| `Syntax(theme="monokai")` | `ModuleNotFoundError` at import | renders with `ansi_dark`, one `UserWarning` |
| `RichHandler()` | `ModuleNotFoundError` at import | works |
| `RichHandler(rich_tracebacks=True)` | `ModuleNotFoundError` at import | works, code frames unstyled |
| `Markdown(...)` | `ModuleNotFoundError` at import | `ImportError` naming `markdown-it-py` and `rich[markdown]` |

### Verification

- 892 passed / 23 skipped (upstream baseline: 883 / 23).
- 78 render cases byte-identical between pristine and patched trees, with
  Pygments installed. See `tools/render_matrix.py`.
- 19/19 checks pass in a venv with neither optional dependency installed.
- `mypy` strict: unchanged at 1 pre-existing error. `black`: clean.

### Known limitations

- Test suite requires **Pygments 2.19.2**. Upstream's snapshot tests fail on
  2.21 (7 failures) and on 2.18/2.17 (3 each). Pre-existing, not caused by this
  patch, but it will confuse you if you don't pin it.
- Degraded rendering (no Pygments) is *correct but plain*: code is rendered as
  unstyled text, not colourised. This is intentional — no attempt is made to
  fake Pygments' tokenisation.
- Only `pygments` and `markdown-it-py` were made optional. `ipywidgets` was
  already optional upstream.
