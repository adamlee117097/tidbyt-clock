#!/usr/bin/env python3
"""Greenpoint Veterinary Hospital card for a friend's Tidbyt (145 Nassau Ave).

The mark is the hospital's own: a white paw in a green (#96BC3A) disc, here
redrawn pixel by pixel at 22px rather than downscaled, since a resampled paw
smears into a blob on the panel. Under the name a trail of small paw prints
walks left to right across the bottom strip, one step every 6 frames, and
the trail wraps so the loop is seamless. Re-run to rewrite greenpointvet.star:
    python3 greenpointvet/make_frames.py
"""
import base64
import io
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
OUT_STAR = HERE / "greenpointvet.star"

GREEN = (150, 188, 58)
WHITE = (255, 255, 255)
DIM = (60, 80, 25)

# 22x22 disc with the paw, hand-plotted. G = green, W = white, . = black.
ICON = """\
.......GGGGGGGG.......
.....GGGGGGGGGGGG.....
....GGGGGGGGGGGGGG....
...GGGGGGGGGGGGGGGG...
..GGGGGWWGGGGWWGGGGG..
.GGGGGWWWWGGWWWWGGGGG.
.GGGGGWWWWGGWWWWGGGGG.
GGGWWGWWWWGGWWWWGWWGGG
GGWWWWGWWGGGGWWGWWWWGG
GGWWWWGGGGGGGGGGWWWWGG
GGWWWWGGGGGGGGGGWWWWGG
GGGWWGGGGWWWWGGGGWWGGG
GGGGGGGGWWWWWWGGGGGGGG
GGGGGGGWWWWWWWWGGGGGGG
.GGGGGWWWWWWWWWWGGGGG.
.GGGGWWWWWWWWWWWWGGGG.
..GGGWWWWWWWWWWWWGGG..
...GGWWWWWWWWWWWWGG...
....GGGWWWWGWWWWGGG...
.....GGGGGGGGGGGGG....
.......GGGGGGGG.......
......................
"""

# One small print, 5 wide x 5 tall.
PRINT = """\
.X.X.
X...X
..X..
.XXX.
.XXX.
"""

STRIP_W, STRIP_H = 64, 8
STEP = 9            # px between prints
N_STEPS = 64 // STEP + 1
FRAMES_PER_STEP = 6
TRAIL = 5           # prints visible at once, oldest dimmest
DELAY_MS = 100


def grid_image(rows, palette):
    rows = rows.strip("\n").split("\n")
    im = Image.new("RGB", (len(rows[0]), len(rows)))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            im.putpixel((x, y), palette.get(ch, (0, 0, 0)))
    return im


def b64(im):
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def strip_frame(head):
    """Trail whose newest print is step `head`; prints alternate high/low
    like left and right feet."""
    im = Image.new("RGB", (STRIP_W, STRIP_H))
    for age in range(TRAIL):
        s = head - age
        if s < 0:
            s += N_STEPS
        x = s * STEP - 4
        y = 0 if s % 2 else 3
        f = 1 - age / TRAIL
        col = tuple(int(DIM[i] + (GREEN[i] - DIM[i]) * f) for i in range(3)) if age else WHITE
        pr = grid_image(PRINT, {"X": col})
        mask = grid_image(PRINT, {"X": (255, 255, 255)}).convert("L")
        im.paste(pr, (x, y), mask)
    return im



TAN = (214, 150, 84)
EAR = (130, 78, 40)
CREAM = (250, 230, 200)
NOSE = (45, 28, 20)
TONGUE = (255, 110, 140)
GRAY = (150, 158, 175)
STRIPE = (95, 102, 120)
EYE = (170, 230, 60)
PINK = (255, 140, 170)
MOON = (255, 236, 160)
STAR = (120, 130, 170)
PAL = {"T": TAN, "D": EAR, "W": CREAM, "K": NOSE, "P": TONGUE,
       "C": GRAY, "S": STRIPE, "E": EYE, "N": PINK, "G": GREEN}

DOG_SIT = """\
...DD........DD...
..DDDTTTTTTTTDDD..
.DDDTTTTTTTTTTDDD.
.DDDTTTTTTTTTTDDD.
.DDTTKKTTTTKKTTDD.
.DDTTTTTTTTTTTTDD.
.DD.TTTWWWWTTT.DD.
..D.TTWWKKWWTT.D..
....TTWWWWWWTT....
.....TTWWPWWT.....
......TTTTTT......
.....TTWWWWTT.....
....TTTWWWWTTT....
....TTTWWWWTTT....
...TTTTTWWTTTTT...
...TTTTTTTTTTTT...
...TTTTTTTTTTTT...
...TTTTTTTTTTTT...
...TTTTTTTTTTTT...
...TTT.TTTT.TTT...
..WWWW.TTTT.WWWW..
..WWWW......WWWW..
"""
# Tail on the dog's right flank, two positions for the wag.
TAIL_UP = [(15, 15), (16, 14), (17, 13), (17, 12)]
TAIL_DN = [(15, 17), (16, 17), (17, 18), (17, 19)]

CAT_SIT = """\
.C......C.....
.CC....CC.....
.CNC..CNC.....
.CCCCCCCC.....
CCSCCCCSCC....
CCEECCEECC....
CCCCNNCCCC....
.CCCCCCCC.....
..CCCCCC......
...CWWC.......
..CCWWCC......
.CCCWWCCC.....
.CSCCCCSCC....
CCSCCCCSCC....
CCCCCCCCCC....
CCCCCCCCCC....
.CCCCCCCC.....
.WW.CC.WW.....
"""
# Cat tail curls up on its right; three positions for the swish.
CAT_TAILS = [
    [(10, 16), (11, 16), (12, 15), (13, 14), (13, 13), (13, 12)],
    [(10, 16), (11, 16), (12, 16), (13, 15), (13, 14), (12, 13)],
    [(10, 16), (11, 16), (12, 15), (12, 14), (12, 13), (11, 12)],
]

DOG_SLEEP = """\
.........TTTTTTT.......
......TTTTTTTTTTTTT....
....TTTTTTTTTTTTTTTTT..
..DDDTTTTTTTTTTTTTTTTT.
.DDDDDTTTTTTTTTTTTTTTTT
TTDDDDTTTTTTTTTTTTTTTTT
TKKTDDTTTTTTTTTTTTTTTTT
TTTTTDTTTTTTTTTTTTTTTTT
WWWTTTTTTTTTTTTTTTTTTT.
KWWWWTTTTTTTTTTTTTTTTT.
.WWWWWWTTTTTTTTTTTTTT..
"""

CAT_SLEEP = """\
.C...C.........
.CC.CCCCCCCC...
CCCCCCCCCCCCCC.
CSSCCSSCCCCCCCC
CCCNCCCCCCCCCCC
.CCCCCCCCCCCCCC
CCCCCCCCCCCCCC.
SSSSSSSSSSCCC..
.SSSSSSSS......
"""

Z = ["XXX", "..X", ".X.", "X..", "XXX"]
Z_SMALL = ["XXX", ".X.", "XXX"]

DAY_FRAMES = 48
NIGHT_FRAMES = 48


def paste(im, grid, x, y, pal=PAL):
    rows = grid.strip("\n").split("\n")
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in pal:
                px, py = x + i, y + j
                if 0 <= px < 64 and 0 <= py < 32:
                    im.putpixel((px, py), pal[ch])


def dot(im, x, y, col):
    if 0 <= x < 64 and 0 <= y < 32:
        im.putpixel((x, y), col)


def day_frame(t):
    im = Image.new("RGB", (64, 32))
    # ground
    for x in range(4, 60):
        dot(im, x, 31, DIM)
    dx, dy = 9, 9
    paste(im, DOG_SIT, dx, dy + 1 if (t // 12) % 2 else dy)  # small pant bob
    for (x, y) in (TAIL_UP if (t // 3) % 2 else TAIL_DN):
        dot(im, dx + x, dy + y + 1, TAN)
    cx, cy = 37, 13
    cat = CAT_SIT
    if t % 24 in (20, 21):   # blink
        cat = cat.replace("E", "C")
    paste(im, cat, cx, cy)
    for (x, y) in CAT_TAILS[(t // 8) % 3]:
        dot(im, cx + x, cy + y, GRAY)
    # a heart rises between them once per loop
    if 8 <= t < 40:
        hy = 14 - (t - 8) // 4
        heart = ["X.X", "XXX", ".X."]
        paste(im, "\n".join(heart), 30, hy, {"X": PINK})
    return im


def night_frame(t):
    im = Image.new("RGB", (64, 32))
    # moon (crescent) top right
    for y in range(2, 10):
        for x in range(50, 60):
            if (x - 54.5) ** 2 + (y - 5.5) ** 2 <= 14 and not (x - 56.5) ** 2 + (y - 4.5) ** 2 <= 11:
                dot(im, x, y, MOON)
    for i, (sx, sy) in enumerate([(4, 3), (22, 2), (40, 6), (31, 9), (12, 9)]):
        if (t // 8 + i) % 3:
            dot(im, sx, sy, STAR)
    # bed
    for y in range(27, 32):
        inset = {27: 3, 31: 1}.get(y, 0)
        for x in range(5 + inset, 59 - inset):
            dot(im, x, y, GREEN if y > 27 else DIM)
    breathe = 1 if (t // 12) % 2 else 0
    paste(im, DOG_SLEEP, 8, 17 + breathe)
    paste(im, CAT_SLEEP, 32, 19 + (1 - breathe))
    # z's rising from the dog's head
    for k in range(2):
        ph = (t + k * 24) % NIGHT_FRAMES
        zy = 14 - ph // 4
        zx = 7 + ph // 8
        if zy >= 0:
            paste(im, "\n".join(Z if k == 0 else Z_SMALL), zx, zy, {"X": (200, 210, 255)})
    return im

def main():
    icon = grid_image(ICON, {"G": GREEN, "W": WHITE})
    frames = []
    for head in range(N_STEPS):
        fr = strip_frame(head)
        frames += [b64(fr)] * FRAMES_PER_STEP
    day = [b64(day_frame(t)) for t in range(DAY_FRAMES)]
    night = [b64(night_frame(t)) for t in range(NIGHT_FRAMES)]
    star = OUT_STAR.read_text()
    start = star.index("ICON = ")
    end = star.index("# --- end generated ---")
    lst = lambda xs: "[\n%s]" % "".join('    "%s",\n' % f for f in xs)
    gen = 'ICON = "%s"\n\nFRAMES = %s\n\nDAY = %s\n\nNIGHT = %s\n\n' % (
        b64(icon), lst(frames), lst(day), lst(night))
    OUT_STAR.write_text(star[:start] + gen + star[end:])
    print("wrote", OUT_STAR, len(frames), len(day), len(night))


if __name__ == "__main__":
    main()
