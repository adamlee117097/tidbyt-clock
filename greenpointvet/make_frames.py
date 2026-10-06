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
import math
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


BALL = (255, 120, 40)
YARN = (255, 110, 170)
WING = (255, 220, 60)
BONE = (245, 235, 215)
FISH = (120, 190, 255)
DOG_X, DOG_Y = 9, 9      # dog sprite origin (sits on the ground at row 30)
CAT_X, CAT_Y = 37, 13


def edit(grid, changes):
    """Return grid with {(x, y): ch} applied."""
    rows = [list(r) for r in grid.strip("\n").split("\n")]
    for (x, y), ch in changes.items():
        rows[y][x] = ch
    return "\n".join("".join(r) for r in rows)


def dog_sprite(look=0, mouth="pant", eyes="open"):
    ch = {}
    if eyes == "closed":
        for x in (5, 6, 11, 12):
            ch[(x, 4)] = "T"
            ch[(x, 5)] = "K"
    elif look:
        # 2px eyes become 1px pupils on the side being looked at
        off = (5, 11) if look < 0 else (6, 12)
        for x in (5, 6, 11, 12):
            ch[(x, 4)] = "T"
        for x in off:
            ch[(x, 4)] = "K"
    if mouth == "shut":
        ch[(9, 9)] = "W"
    elif mouth == "open":     # yawn / catch
        for x in range(7, 11):
            ch[(x, 8)] = "K"
        for x in range(7, 11):
            ch[(x, 9)] = "P" if x in (8, 9) else "K"
    elif mouth == "chew":
        ch[(9, 9)] = "W"
        ch[(8, 8)] = "K"
    return edit(DOG_SIT, ch)


def cat_sprite(look=0, eyes="open", paw=None, mouth="shut"):
    ch = {}
    if eyes == "closed":
        for x in (2, 3, 6, 7):
            ch[(x, 5)] = "S"
    elif look:
        for x in ((2, 6) if look < 0 else (3, 7)):
            ch[(x, 5)] = "K"
    if mouth == "open":
        ch[(4, 6)] = "K"
        ch[(5, 6)] = "K"
        ch[(4, 7)] = "N"
        ch[(5, 7)] = "N"
    if paw == "left":       # swipe out to the left
        ch[(1, 17)] = "."
        ch[(2, 17)] = "."
        ch[(0, 11)] = "W"
        ch[(0, 12)] = "W"
    elif paw == "up":       # reach straight up past the face
        ch[(1, 17)] = "."
        ch[(2, 17)] = "."
        ch[(0, 9)] = "W"
        ch[(0, 10)] = "C"
        ch[(0, 11)] = "C"
    return edit(CAT_SIT, ch)


def stage():
    im = Image.new("RGB", (64, 32))
    for x in range(4, 60):
        dot(im, x, 31, DIM)
    return im


def put_dog(im, t, wag_speed=3, dy=0, **kw):
    bob = 1 if (t // 12) % 2 and dy == 0 else 0
    paste(im, dog_sprite(**kw), DOG_X, DOG_Y + bob + dy)
    for (x, y) in (TAIL_UP if (t // wag_speed) % 2 else TAIL_DN):
        dot(im, DOG_X + x, DOG_Y + y + 1 + dy, TAN)


def put_cat(im, t, swish=8, blink=True, **kw):
    if blink and t % 24 in (20, 21) and "eyes" not in kw:
        kw["eyes"] = "closed"
    paste(im, cat_sprite(**kw), CAT_X, CAT_Y)
    for (x, y) in CAT_TAILS[(t // swish) % 3]:
        dot(im, CAT_X + x, CAT_Y + y, GRAY)


def heart(im, x, y):
    paste(im, "X.X\nXXX\n.X.", x, y, {"X": PINK})


def scene_sit(t):
    """The original: sitting together, a heart rises between them."""
    im = stage()
    put_dog(im, t)
    put_cat(im, t)
    if 8 <= t < 40:
        heart(im, 30, 14 - (t - 8) // 4)
    return im


def scene_catch(t):
    """A ball lobbed back and forth; both watch it, the dog jumps for it."""
    im = stage()
    # 24 frames each way on a parabola, dog mouth (19,17) <-> cat paw (35,24)
    leg, u = divmod(t, 24)
    u = u / 23
    if leg:
        u = 1 - u
    bx = 19 + (35 - 19) * u
    by = 17 + (24 - 17) * u - 14 * 4 * u * (1 - u)
    look = -1 if bx < 28 else 1
    at_dog = u < 0.08
    at_cat = u > 0.92
    put_dog(im, t, wag_speed=2, dy=-2 if at_dog else 0, look=look,
            mouth="open" if at_dog else "pant")
    put_cat(im, t, look=look, paw="left" if at_cat else None, blink=False)
    paste(im, ".X.\nXXX\n.X.", int(round(bx)) - 1, int(round(by)) - 1, {"X": BALL})
    return im


def scene_yarn(t):
    """The cat bats a ball of yarn along the ground; the dog watches."""
    im = stage()
    # yarn rolls left from the cat's paw toward the dog and back, 48 frames
    u = t / 47
    yx = 32 - int(round(9 * (1 - abs(2 * u - 1))))   # 32 -> 23 -> 32
    near = yx >= 31
    put_cat(im, t, swish=4, paw="left" if near and t % 8 < 4 else None,
            look=-1, blink=False)
    put_dog(im, t, look=1, wag_speed=2)
    # yarn ball with a stray thread trailing back toward the cat
    paste(im, ".XX.\nXXXX\nXXXX\n.XX.", yx, 27, {"X": YARN})
    for k in range(1, 4):
        dot(im, yx + 3 + k, 30, YARN if (k + t // 2) % 2 else DIM)
    return im


def scene_butterfly(t):
    """A butterfly loops over them; eyes follow, the cat swipes at it."""
    im = stage()
    a = 2 * math.pi * t / 48
    fx = 31 + 22 * math.sin(a)
    fy = 6 + 3 * math.sin(2 * a)
    look = -1 if fx < 26 else (1 if fx > 36 else 0)
    put_dog(im, t, look=look, dy=-2 if abs(fx - 18) < 3 else 0)
    put_cat(im, t, look=look, paw="up" if abs(fx - 40) < 4 else None, blink=False)
    x, y = int(round(fx)), int(round(fy))
    if t % 4 < 2:      # wings open
        paste(im, "XX.XX\nXXXXX\nXX.XX", x - 2, y - 1, {"X": WING})
    else:              # wings up
        paste(im, ".X.X.\n.XXX.\n..X..", x - 2, y - 1, {"X": WING})
    return im


def scene_treat(t):
    """Treat time: a bone drops to the dog, then a fish to the cat."""
    im = stage()
    dog_kw, cat_kw = {}, {"blink": False}
    if t < 16:          # bone falls into the dog's mouth
        y = -2 + t * 19 // 15
        paste(im, "X...X\nXXXXX\nX...X", 16, y, {"X": BONE})
        dog_kw = {"look": 0, "mouth": "open" if t > 10 else "pant"}
        cat_kw["look"] = -1
    elif t < 24:
        dog_kw = {"mouth": "chew" if t % 4 < 2 else "shut", "eyes": "closed"}
        cat_kw["look"] = -1
    elif t < 40:        # fish falls to the cat
        y = -2 + (t - 24) * 18 // 15
        paste(im, "X.XX.\nXXXXX\nX.XX.", 39, min(y, 19), {"X": FISH})
        dog_kw = {"look": 1}
        cat_kw.update({"mouth": "open" if t > 34 else "shut"})
    else:
        cat_kw.update({"eyes": "closed"})
        heart(im, 30, 12 - (t - 40) // 3)
    put_dog(im, t, wag_speed=2, **dog_kw)
    put_cat(im, t, **cat_kw)
    return im


def scene_yawn(t):
    """Morning and closing time: the dog yawns, then the cat does."""
    im = stage()
    dog_yawn = 6 <= t < 22
    cat_yawn = 26 <= t < 40
    put_dog(im, t, wag_speed=6, mouth="open" if dog_yawn else "pant",
            eyes="closed" if dog_yawn else "open")
    put_cat(im, t, swish=12, eyes="closed" if cat_yawn else "open",
            mouth="open" if cat_yawn else "shut", blink=False)
    return im


SCENES = {
    "sit": scene_sit,
    "catch": scene_catch,
    "yarn": scene_yarn,
    "butterfly": scene_butterfly,
    "treat": scene_treat,
    "yawn": scene_yawn,
}


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
    day = {k: [b64(f(t)) for t in range(DAY_FRAMES)] for k, f in SCENES.items()}
    night = [b64(night_frame(t)) for t in range(NIGHT_FRAMES)]
    star = OUT_STAR.read_text()
    start = star.index("ICON = ")
    end = star.index("# --- end generated ---")
    lst = lambda xs: "[\n%s]" % "".join('    "%s",\n' % f for f in xs)
    dct = "{\n%s}" % "".join('    "%s": %s,\n' % (k, lst(v).replace("\n", "\n    ")) for k, v in day.items())
    gen = 'ICON = "%s"\n\nFRAMES = %s\n\nDAY = %s\n\nNIGHT = %s\n\n' % (
        b64(icon), lst(frames), dct, lst(night))
    OUT_STAR.write_text(star[:start] + gen + star[end:])
    print("wrote", OUT_STAR, len(frames), {k: len(v) for k, v in day.items()}, len(night))


if __name__ == "__main__":
    main()
