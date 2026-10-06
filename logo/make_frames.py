#!/usr/bin/env python3
"""Kaleidoscope Coffee flamingo card: two cartoon flamingos facing each other
over a pair of espresso cups.

Redesign 2026-10-06 in the style of the Greenpoint Vet card: chunky, cute
birds with a big eye and a blush, doing something different every 15
minutes while the shop is open, asleep on one leg after closing. The neck is
a cubic Bezier from the front of the body to the head, so a pose is just a
head position -- leaning in for a heart, dipping to sip, turning to preen --
instead of a hand-drawn grid per pose. (The hand-drawn generator before this
is in git history, commit d3e59e7 and earlier.)

Re-run to rewrite kaleidoscope.star:  python3 logo/make_frames.py
"""
import base64
import io
import math
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
OUT_STAR = HERE / "kaleidoscope.star"

# ---------------------------------------------------------------- palette
CORAL = (242, 90, 60)      # brand #DF513B pushed up -- LEDs mute it
LIGHT = (255, 140, 110)    # top of the body, so it reads round, not flat
WING = (175, 52, 38)       # folded wing; ~2:1 against coral or they merge
BLUSH = (255, 160, 170)
BILL = (255, 238, 214)
TIP = (70, 45, 45)         # the black tip, lifted so it stays visible
EYE = (0, 0, 0)            # unlit inside a lit head = the strongest mark
LEG = (255, 150, 130)
GOLD = (236, 190, 94)      # cups
CUP_DARK = (150, 110, 50)
PUFF = [(150, 150, 150), (130, 130, 130), (110, 110, 110), (95, 95, 95)]
PINK = (255, 120, 160)
NOTE = (236, 190, 94)
MOON = (255, 236, 160)
STAR = (120, 130, 170)
ZED = (200, 210, 255)
COUNTER = (110, 40, 30)

N = 48            # frames per scene
DELAY_MS = 100

# ---------------------------------------------------------------- the bird
# Drawn facing right in a 32x32 half-panel; the right bird is the mirror.
BODY = """\
.....LLLLLL....
...LLLLLLLLLL..
PPPPPWWWWWPPPPP
.PPPWWWWWWWPPPP
..PPPWWWWWWPPPP
...PPPPWWWPPPP.
.....PPPPPPPP..
.......PPPP....
"""
BODY_X, BODY_Y = 1, 15
NECK_BASE = (13.0, 16.0)          # top front of the body
HEAD = """\
.PPP.
PPPPP
PPPPP
PPPPP
.PPP.
"""
WING_UP = """\
.......LL.
.....LLLL.
...LLLLWW.
.LLLLWWWW.
LLWWWWWW..
.WWWWWW...
"""
LEG_X = (7, 10)


def dot(im, x, y, col):
    if 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((int(x), int(y)), col)


def paste(im, grid, x, y, pal):
    for j, row in enumerate(grid.strip("\n").split("\n")):
        for i, ch in enumerate(row):
            if ch in pal:
                dot(im, x + i, y + j, pal[ch])


def bezier(p0, p1, p2, p3, steps=60):
    for k in range(steps + 1):
        t = k / steps
        u = 1 - t
        yield (u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
               u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1])


def bird(head=(14, 5), face=1, bill="fwd", eyes="open", legs="two",
         wing="down", dy=0, bill_open=False):
    """One flamingo facing right. head = head centre; face = +1 looking
    right / -1 looking back; bill = fwd | down | tucked."""
    im = Image.new("RGBA", (32, 32))
    pal = {"P": CORAL, "L": LIGHT, "W": WING}
    by = BODY_Y + dy
    # legs first so the body overlaps their tops. 1px, at Adam's call after
    # seeing 2px on the panel (2026-10-06: "a bit too thick") -- despite the
    # README's gutter lesson. A knee and a 2px foot anchor each leg.
    for i, lx in enumerate(LEG_X):
        if legs == "one" and i == 1:
            # tucked up under the belly: down, then folded back
            for (x, y) in [(lx, by + 8), (lx, by + 9), (lx - 1, by + 10), (lx - 2, by + 10), (lx - 3, by + 9)]:
                dot(im, x, y, LEG)
            continue
        knee = 26 + dy
        for y in range(by + 8, 32):
            # the lower leg steps back one column: a flamingo's "knee"
            # (really the ankle) bends backward
            dot(im, lx if y <= knee else lx - 1, y, LEG)
        dot(im, lx, 31, LEG)                                      # toes forward
    paste(im, BODY, BODY_X, by, pal)
    if wing == "up":
        paste(im, WING_UP, BODY_X, by - 5, pal)
    # neck: S-curve from the body's front up to under the head
    hx, hy = head
    base = (NECK_BASE[0], NECK_BASE[1] + dy)
    end = (hx - face * 1, hy + 2)
    if hx > 18:
        # reaching forward (heart, sip): arch the neck up and over, like a
        # swan's, instead of letting the curve flatten into a stick
        top = min(base[1], end[1]) - 7
        c1 = (base[0] + 1, top)
        c2 = (end[0] - 3, top + 1)
    else:
        c1 = (base[0] + 4, base[1] - (base[1] - end[1]) * 0.35)
        c2 = (end[0] - 5 * face, end[1] + (base[1] - end[1]) * 0.45)
    for (x, y) in bezier(base, c1, c2, end):
        # 2x2 brush: 2 wide AND 2 tall, or the flat top of an arch is a
        # 1px row the gutters turn into dots
        for ox in (0, 1):
            for oy in (0, 1):
                dot(im, round(x) + ox, round(y) + oy, CORAL)
    # head
    paste(im, HEAD, hx - 2, hy - 2, {"P": CORAL})
    ex = hx + face
    if eyes == "open":
        dot(im, ex, hy - 1, EYE)
    else:
        dot(im, ex - 1, hy, WING)
        dot(im, ex, hy, WING)
    dot(im, hx, hy + 1, BLUSH)
    # bill
    if bill == "fwd":
        pts = [(3, -1, BILL), (4, -1, BILL), (4, 0, BILL), (5, 0, BILL), (5, 1, TIP)]
        if bill_open:
            pts = [(3, -1, BILL), (4, -2, BILL), (5, -2, TIP), (3, 1, BILL), (4, 1, BILL), (5, 2, TIP)]
    elif bill == "down":
        pts = [(1, 3, BILL), (2, 3, BILL), (2, 4, BILL), (2, 5, TIP)]
    else:  # tucked into the back feathers: just the tip shows
        pts = [(3, 0, BILL), (3, 1, TIP)]
    for (bx, by_, col) in pts:
        dot(im, hx + face * bx, hy + by_, col)
    return im


def place(frame, left, right):
    frame.paste(left, (0, 0), left)
    m = right.transpose(Image.FLIP_LEFT_RIGHT)
    frame.paste(m, (32, 0), m)


# ---------------------------------------------------------------- props
CUPS = [(25, 26), (34, 26)]


def cups(im, t, steam=True):
    for x in range(22, 42):
        dot(im, x, 31, COUNTER)
    for k, (cx, cy) in enumerate(CUPS):
        paste(im, "GGGGG\nGGGGGH\nGGGGG.\n.GGG.", cx, cy, {"G": GOLD, "H": GOLD})
        dot(im, cx + 5, cy + 1, GOLD)
        dot(im, cx + 1, cy, CUP_DARK)
        if steam:
            for p in range(2):
                ph = (t + k * 7 + p * 12) % 24
                step = ph // 6
                px = cx + 1 + (1 if (ph // 3 + p) % 2 else 0)
                py = cy - 3 - step * 2
                for ox in (0, 1):          # 2x2 puffs: a 1px wisp vanishes
                    for oy in (0, 1):      # into the panel's gutters
                        dot(im, px + ox, py + oy, PUFF[step])


def heart(im, x, y, col=PINK):
    paste(im, "X.X\nXXX\n.X.", x, y, {"X": col})


def big_heart(im, x, y, col=PINK):
    paste(im, ".XX.XX.\nXXXXXXX\nXXXXXXX\n.XXXXX.\n..XXX..\n...X...", x, y, {"X": col})


def note(im, x, y):
    paste(im, ".XX\n.X.\n.X.\nXX.", x, y, {"X": NOTE})


def blank():
    return Image.new("RGBA", (64, 32), (0, 0, 0, 255))


def blinking(t, offset=0):
    return "closed" if (t + offset) % 24 in (20, 21) else "open"


# ---------------------------------------------------------------- scenes
STAND = (14, 5)


def scene_heart(t):
    """They lean in until their bills meet over the cups; a heart pops."""
    im = blank()
    u = min(1, max(0, (t - 4) / 14)) if t < 34 else max(0, 1 - (t - 34) / 10)
    hx = 14 + (27 - 14) * u
    hy = 5 + (12 - 5) * u
    b = bird(head=(round(hx), round(hy)), bill="down" if u > 0.6 else "fwd",
             eyes="closed" if u > 0.95 else blinking(t))
    place(im, b, b)
    cups(im, t)
    if 18 <= t < 34:
        big_heart(im, 29, max(0, 4 - (t - 18) // 2))
    return im


def scene_sip(t):
    """Left bird dips to its cup, then the right bird does."""
    im = blank()
    def pose(phase):
        u = math.sin(math.pi * min(1, max(0, phase / 20)))
        head = (round(14 + (25 - 14) * u), round(5 + (21 - 5) * u))
        return bird(head=head, bill="down" if u > 0.6 else "fwd",
                    eyes="closed" if u > 0.8 else "open")
    left = pose(t) if t < 22 else bird(head=STAND, eyes=blinking(t))
    right = pose(t - 24) if t >= 24 else bird(head=STAND, eyes=blinking(t, 7))
    place(im, left, right)
    cups(im, t, steam=True)
    return im


def scene_oneleg(t):
    """The classic: both on one leg, swaying, with a slow blink."""
    im = blank()
    sway = round(math.sin(2 * math.pi * t / N))
    l = bird(head=(14 + sway, 5), legs="one", eyes=blinking(t))
    r = bird(head=(14 - sway, 5), legs="one", eyes=blinking(t, 11))
    place(im, l, r)
    cups(im, t)
    return im


def scene_dance(t):
    """Heads bob to the beat; notes drift up from between them."""
    im = blank()
    beat = (t // 6) % 4
    off = [0, 2, 0, -2][beat]
    l = bird(head=(14 + off, 5 + (beat % 2)), dy=beat % 2, eyes="open")
    r = bird(head=(14 - off, 5 + (beat % 2)), dy=beat % 2, eyes="open")
    place(im, l, r)
    cups(im, t, steam=False)
    for k in range(2):
        ph = (t + 24 * k) % N
        note(im, 28 + 5 * k, 20 - ph // 3)
    return im


def scene_preen(t):
    """One turns to tidy its wing while the other watches; then they swap."""
    im = blank()
    def preening(p):
        wig = 1 if (p // 3) % 2 else 0
        return bird(head=(9 + wig, 12), face=-1, bill="tucked", eyes="closed")
    def watching(p):
        return bird(head=(15, 6), eyes=blinking(p))
    if t < 24:
        place(im, preening(t), watching(t))
    else:
        place(im, watching(t), preening(t))
    cups(im, t)
    return im


def scene_stretch(t):
    """Opening and closing: wings up for a stretch and a big yawn."""
    im = blank()
    l_up = 6 <= t < 22
    r_up = 26 <= t < 42
    l = bird(head=(14, 4) if l_up else STAND, wing="up" if l_up else "down",
             bill_open=l_up, eyes="closed" if l_up else "open")
    r = bird(head=(14, 4) if r_up else STAND, wing="up" if r_up else "down",
             bill_open=r_up, eyes="closed" if r_up else "open")
    place(im, l, r)
    cups(im, t)
    return im


Z_BIG = "XXX\n..X\n.X.\nX..\nXXX"


def scene_sleep(t):
    """After hours: one leg, head tucked on the back, cups cold, moon up."""
    im = blank()
    breathe = 1 if (t // 12) % 2 else 0
    b = bird(head=(8, 13 + breathe), face=-1, bill="tucked", eyes="closed",
             legs="one", dy=breathe)
    place(im, b, b)
    cups(im, t, steam=False)
    # moon and stars in the empty top middle
    for y in range(0, 8):
        for x in range(28, 37):
            if (x - 32) ** 2 + (y - 3.5) ** 2 <= 12 and not (x - 34) ** 2 + (y - 2.5) ** 2 <= 9:
                dot(im, x, y, MOON)
    for i, (sx, sy) in enumerate([(22, 2), (41, 4), (25, 8), (39, 9)]):
        if (t // 8 + i) % 3:
            dot(im, sx, sy, STAR)
    for k in range(2):
        ph = (t + 24 * k) % N
        zy = 20 - ph // 4
        if zy >= 9:
            paste(im, Z_BIG, (20 if k == 0 else 39) + ph // 16, zy, {"X": ZED})
    return im


SCENES = {
    "heart": scene_heart,
    "sip": scene_sip,
    "oneleg": scene_oneleg,
    "dance": scene_dance,
    "preen": scene_preen,
    "stretch": scene_stretch,
    "sleep": scene_sleep,
}


def b64(im):
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def main():
    star = OUT_STAR.read_text()
    start = star.index("SCENES = ")
    end = star.index("# --- end generated ---")
    body = "".join(
        '    "%s": [\n%s    ],\n' % (k, "".join('        "%s",\n' % b64(f(t)) for t in range(N)))
        for k, f in SCENES.items())
    OUT_STAR.write_text(star[:start] + "SCENES = {\n%s}\n\n" % body + star[end:])
    print("wrote", OUT_STAR, {k: N for k in SCENES})


if __name__ == "__main__":
    main()
