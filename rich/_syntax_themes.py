"""Built-in ANSI syntax themes that do not require Pygments.

Pygments token types are plain ``tuple`` subclasses whose hash and equality
behave exactly like the corresponding tuple of path components
(``Token.Comment.Preproc == ("Comment", "Preproc")``).  That means the theme
tables can be keyed by plain tuples, which lets Rich provide syntax colouring
for its own built-in themes without importing Pygments at all.

``ANSISyntaxTheme`` looks a token up by progressively truncating the tuple, so
a tuple key and a Pygments token key resolve to the same entry.
"""

from typing import Dict, Tuple

from .style import Style

# Token paths are spelled out as tuples on purpose.  Importing ``pygments.token``
# here would defeat the entire point of this module.
TokenType = Tuple[str, ...]

ANSI_LIGHT: Dict[TokenType, Style] = {
    (): Style(),
    ("Text", "Whitespace"): Style(color="white"),
    ("Comment",): Style(dim=True),
    ("Comment", "Preproc"): Style(color="cyan"),
    ("Keyword",): Style(color="blue"),
    ("Keyword", "Type"): Style(color="cyan"),
    ("Operator", "Word"): Style(color="magenta"),
    ("Name", "Builtin"): Style(color="cyan"),
    ("Name", "Function"): Style(color="green"),
    ("Name", "Namespace"): Style(color="cyan", underline=True),
    ("Name", "Class"): Style(color="green", underline=True),
    ("Name", "Exception"): Style(color="cyan"),
    ("Name", "Decorator"): Style(color="magenta", bold=True),
    ("Name", "Variable"): Style(color="red"),
    ("Name", "Constant"): Style(color="red"),
    ("Name", "Attribute"): Style(color="cyan"),
    ("Name", "Tag"): Style(color="bright_blue"),
    ("Literal", "String"): Style(color="yellow"),
    ("Literal", "Number"): Style(color="blue"),
    ("Generic", "Deleted"): Style(color="bright_red"),
    ("Generic", "Inserted"): Style(color="green"),
    ("Generic", "Heading"): Style(bold=True),
    ("Generic", "Subheading"): Style(color="magenta", bold=True),
    ("Generic", "Prompt"): Style(bold=True),
    ("Generic", "Error"): Style(color="bright_red"),
    ("Error",): Style(color="red", underline=True),
}

ANSI_DARK: Dict[TokenType, Style] = {
    (): Style(),
    ("Text", "Whitespace"): Style(color="bright_black"),
    ("Comment",): Style(dim=True),
    ("Comment", "Preproc"): Style(color="bright_cyan"),
    ("Keyword",): Style(color="bright_blue"),
    ("Keyword", "Type"): Style(color="bright_cyan"),
    ("Operator", "Word"): Style(color="bright_magenta"),
    ("Name", "Builtin"): Style(color="bright_cyan"),
    ("Name", "Function"): Style(color="bright_green"),
    ("Name", "Namespace"): Style(color="bright_cyan", underline=True),
    ("Name", "Class"): Style(color="bright_green", underline=True),
    ("Name", "Exception"): Style(color="bright_cyan"),
    ("Name", "Decorator"): Style(color="bright_magenta", bold=True),
    ("Name", "Variable"): Style(color="bright_red"),
    ("Name", "Constant"): Style(color="bright_red"),
    ("Name", "Attribute"): Style(color="bright_cyan"),
    ("Name", "Tag"): Style(color="bright_blue"),
    ("Literal", "String"): Style(color="yellow"),
    ("Literal", "Number"): Style(color="bright_blue"),
    ("Generic", "Deleted"): Style(color="bright_red"),
    ("Generic", "Inserted"): Style(color="bright_green"),
    ("Generic", "Heading"): Style(bold=True),
    ("Generic", "Subheading"): Style(color="bright_magenta", bold=True),
    ("Generic", "Prompt"): Style(bold=True),
    ("Generic", "Error"): Style(color="bright_red"),
    ("Error",): Style(color="red", underline=True),
}

RICH_SYNTAX_THEMES: Dict[str, Dict[TokenType, Style]] = {
    "ansi_light": ANSI_LIGHT,
    "ansi_dark": ANSI_DARK,
}
