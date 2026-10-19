"""Generate the social preview card (1280x640, GitHub's og:image size).

Design notes
------------
One idea has to land in the two seconds someone spends scrolling: *the thing
you were forced to install was never used by default*.  So the card shows the
import chain, the conditional that guards it, and what the default install
sheds -- three panels, same warm-ink-on-paper palette as the other repos.

No stock imagery, no gradient mush.  Warm editorial, not corporate blue.

Run: python assets/make_cover.py
"""

from __future__ import annotations

import pathlib

from PIL import Image, ImageDraw, ImageFont

OUT = pathlib.Path(__file__).resolve().parent / "cover.png"

W, H = 1280, 640

INK = (26, 24, 22)
PAPER = (250, 248, 244)
MUTED = (138, 130, 120)
RULE = (223, 217, 208)
AMBER = (196, 132, 42)
WRONG = (176, 68, 52)
RIGHT = (86, 118, 92)

MONO = "C:/Windows/Fonts/consola.ttf"
MONO_B = "C:/Windows/Fonts/consolab.ttf"
SANS_B = "C:/Windows/Fonts/segoeuib.ttf"
SANS = "C:/Windows/Fonts/segoeui.ttf"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)

    # Paper grain: a few thousand near-invisible dots beat a flat fill.
    for y in range(0, H, 3):
        for x in range(0, W, 3):
            if (x * 7 + y * 13) % 97 == 0:
                d.point((x, y), fill=(244, 241, 236))

    # --- header ------------------------------------------------------------
    d.text((64, 50), "rich-optional-deps", font=font(SANS_B, 50), fill=INK)
    d.text(
        (66, 114),
        "Pygments and markdown-it-py, demoted to optional extras",
        font=font(SANS, 23),
        fill=MUTED,
    )
    d.rectangle([64, 154, 132, 159], fill=AMBER)

    # --- three panels ------------------------------------------------------
    top = 196
    gap = 24
    panel_w = (W - 64 * 2 - gap * 2) // 3
    panel_h = 310

    panels = [
        ("THE CHAIN", MUTED),
        ("THE GUARD", AMBER),
        ("DEFAULT INSTALL", RIGHT),
    ]

    for index, (title, colour) in enumerate(panels):
        x = 64 + index * (panel_w + gap)
        d.rounded_rectangle(
            [x, top, x + panel_w, top + panel_h],
            radius=10,
            fill=(255, 255, 255),
            outline=RULE,
            width=2,
        )
        d.text((x + 22, top + 20), title, font=font(SANS_B, 18), fill=colour)
        d.line([x + 22, top + 50, x + panel_w - 22, top + 50], fill=RULE, width=1)

    mono = font(MONO, 19)
    mono_sm = font(MONO, 17)

    # panel 1: the import chain
    x1 = 64 + 22
    y = top + 70
    chain = [
        ("rich.logging", INK),
        ("  └─ traceback", MUTED),
        ("      └─ syntax", MUTED),
        ("          └─ pygments", WRONG),
    ]
    for line, colour in chain:
        d.text((x1, y), line, font=mono_sm, fill=colour)
        y += 30
    y += 8
    d.text((x1, y), "all top-level imports", font=font(SANS, 17), fill=MUTED)
    d.text((x1, y + 24), "8.3 MB, pulled in on import", font=font(SANS, 17), fill=WRONG)

    # panel 2: the conditional that guards it
    x2 = 64 + panel_w + gap + 22
    y = top + 70
    guard = [
        ("if self.rich_tracebacks", INK),
        ("   and record.exc_info:", INK),
        ("    ...Traceback(...)", MUTED),
    ]
    for line, colour in guard:
        d.text((x2, y), line, font=mono_sm, fill=colour)
        y += 30
    y += 8
    d.text((x2, y), "defaults to False", font=font(SANS_B, 18), fill=AMBER)
    d.text((x2, y + 26), "so most users never", font=font(SANS, 17), fill=MUTED)
    d.text((x2, y + 50), "reached that code", font=font(SANS, 17), fill=MUTED)

    # panel 3: what the default install sheds
    x3 = 64 + (panel_w + gap) * 2 + 22
    y = top + 70
    d.text((x3, y), "before", font=font(SANS, 16), fill=MUTED)
    y += 26
    d.text((x3, y), "2 required deps", font=font(MONO_B, 20), fill=WRONG)
    y += 46
    d.text((x3, y), "after", font=font(SANS, 16), fill=MUTED)
    y += 26
    d.text((x3, y), "0 required deps", font=font(MONO_B, 20), fill=RIGHT)
    y += 50
    d.line([x3, y, x3 + panel_w - 44, y], fill=RULE, width=1)
    y += 16
    d.text((x3, y), "−8.8 MB", font=font(MONO_B, 24), fill=INK)
    d.text((x3, y + 32), "−823 files", font=font(MONO_B, 24), fill=INK)

    # --- footer ------------------------------------------------------------
    d.line([64, 546, W - 64, 546], fill=RULE, width=1)
    d.text(
        (64, 568),
        "892 tests pass  ·  78 render cases byte-identical",
        font=font(SANS_B, 22),
        fill=INK,
    )
    d.text(
        (W - 64 - 356, 572),
        "github.com/linmoxi33/rich-optional-deps",
        font=font(MONO, 17),
        fill=MUTED,
    )

    img.save(OUT, "PNG", optimize=True)
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {W}x{H})")


if __name__ == "__main__":
    main()
