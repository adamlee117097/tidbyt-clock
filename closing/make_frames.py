#!/usr/bin/env python3
"""Kaleidoscope closing card: the flamingos' wave, borrowed from the logo card.

The text pages are drawn live by closing.star (the countdown depends on the
date); only the bird animation and the beating heart are baked here, so the
birds stay pixel-identical to the logo card's "wave" scene.

Re-run to rewrite closing.star:  python3 closing/make_frames.py
"""
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "logo"))
import make_frames as logo  # noqa: E402

OUT_STAR = HERE / "closing.star"


def heart(big):
    """A 7x6 heart, full size or one pixel in on every side (the beat)."""
    im = Image.new("RGBA", (7, 6))
    if big:
        logo.big_heart(im, 0, 0)
    else:
        logo.paste(im, "XX.XX\nXXXXX\n.XXX.\n..X..", 1, 1, {"X": logo.PINK})
    return im


def main():
    star = OUT_STAR.read_text()
    start = star.index("BIRDS = ")
    end = star.index("# --- end generated ---")
    birds = "".join('    "%s",\n' % logo.b64(logo.scene_wave(t)) for t in range(logo.N))
    hearts = "".join('    "%s",\n' % logo.b64(heart(big)) for big in (True, False))
    OUT_STAR.write_text(star[:start] + "BIRDS = [\n%s]\n\nHEARTS = [\n%s]\n\n" % (birds, hearts) + star[end:])
    print("wrote", OUT_STAR, logo.N, "frames")


if __name__ == "__main__":
    main()
