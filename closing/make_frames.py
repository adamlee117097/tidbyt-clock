#!/usr/bin/env python3
"""Kaleidoscope closing card: bake the shop's wordmark and the heart.

The wordmark is the logo's "KALEIDOSCOPE / COFFEE" lockup redrawn letter by
letter. Shrinking the real lettering to fit 64px leaves letters 6px tall that
read as mush, so each glyph copies the logo's shape -- bold, round O/C/S --
on an 8px grid with 2px strokes (1px strokes break into dots on the panel).
"KALEIDOSCOPE" comes out 63px wide.

The text pages are drawn live by closing.star (the countdown depends on the
date); only the wordmark and the beating heart are baked here.

Re-run to rewrite closing.star:  python3 closing/make_frames.py
"""
import base64
import io
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT_STAR = HERE / "closing.star"

CORAL = (0xF2, 0x5A, 0x3C)   # the logo's #E0513B, pushed so the LEDs don't mute it
PINK = (255, 120, 160)

GLYPHS = {
    "K": ["##..#", "##.##", "####.", "###..", "####.", "##.##", "##..#", "##..#"],
    "A": [".###.", "##.##", "##.##", "##.##", "#####", "##.##", "##.##", "##.##"],
    "L": ["##..", "##..", "##..", "##..", "##..", "##..", "####", "####"],
    "E": ["####", "####", "##..", "###.", "###.", "##..", "####", "####"],
    "I": ["##"] * 8,
    "D": ["####.", "#####", "##.##", "##.##", "##.##", "##.##", "#####", "####."],
    "O": [".###.", "#####", "##.##", "##.##", "##.##", "##.##", "#####", ".###."],
    "S": [".###", "####", "##..", "###.", ".###", "..##", "####", "###."],
    "C": [".###", "####", "##..", "##..", "##..", "##..", "####", ".###"],
    "P": ["####.", "#####", "##.##", "#####", "####.", "##...", "##...", "##..."],
    "F": ["####", "####", "##..", "###.", "###.", "##..", "##..", "##.."],
}
GLYPH_H = 8
LINE_GAP = 3


def word_width(text):
    return sum(len(GLYPHS[ch][0]) for ch in text) + len(text) - 1


def draw_word(im, text, x, y, col):
    for ch in text:
        rows = GLYPHS[ch]
        for j, row in enumerate(rows):
            for i, c in enumerate(row):
                if c == "#":
                    im.putpixel((x + i, y + j), col)
        x += len(rows[0]) + 1


def wordmark():
    """The two-line lockup, each line centred on the wider one."""
    lines = ["KALEIDOSCOPE", "COFFEE"]
    w = max(word_width(t) for t in lines)
    im = Image.new("RGB", (w, len(lines) * GLYPH_H + (len(lines) - 1) * LINE_GAP))
    for k, t in enumerate(lines):
        draw_word(im, t, (w - word_width(t)) // 2, k * (GLYPH_H + LINE_GAP), CORAL)
    return im


def paste(im, grid, col):
    for j, row in enumerate(grid.split("\n")):
        for i, c in enumerate(row):
            if c == "X":
                im.putpixel((i, j), col)


def heart(big):
    """A 7x6 heart, full size or one pixel in on every side (the beat)."""
    im = Image.new("RGB", (7, 6))
    if big:
        paste(im, ".XX.XX.\nXXXXXXX\nXXXXXXX\n.XXXXX.\n..XXX..\n...X...", PINK)
    else:
        paste(im, ".......\n.XX.XX.\n.XXXXX.\n..XXX..\n...X...", PINK)
    return im


def b64(im):
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def main():
    star = OUT_STAR.read_text()
    start = star.index("WORDMARK = ")
    end = star.index("# --- end generated ---")
    hearts = "".join('    "%s",\n' % b64(heart(big)) for big in (True, False))
    OUT_STAR.write_text(star[:start] + 'WORDMARK = "%s"\n\nHEARTS = [\n%s]\n\n' % (b64(wordmark()), hearts) + star[end:])
    print("wrote", OUT_STAR)


if __name__ == "__main__":
    main()
