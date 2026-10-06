#!/usr/bin/env python3
"""Greenpoint Veterinary Hospital card for a friend's Tidbyt (145 Nassau Ave).

The mark is the hospital's own: a white paw in a green (#96BC3A) disc, here
redrawn pixel by pixel at 22px rather than downscaled, since a resampled paw
smears into a blob on the panel. Under the name a trail of small paw prints
walks left to right, and the trail wraps so the loop is seamless.

Open hours (10am-7pm, every day) follow the logo with a pixel dog and cat
doing one of several things, changing every 15 minutes: sitting with a
heart, playing catch, the cat batting yarn, chasing a butterfly, treat time,
and yawning for the first and last half hour. After hours they are curled up
asleep on a green bed under the moon.

On top of that the card dresses for the date (Halloween, Thanksgiving,
Christmas, New Year's, Valentine's, July 4th: hats, a jack-o'-lantern,
leaves, confetti, fireworks) and for the real Greenpoint weather from the
NWS hourly forecast (rain with a raincoat, snow, storm, clouds, sun).

This runs at every push: it decides all of that for the current moment,
writes only those frames into greenpointvet.star, and pixlet renders that.
    python3 greenpointvet/make_frames.py            # now, live weather
    python3 greenpointvet/make_frames.py --at "2026-10-31 14:00" --weather rain
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
Z_SMALL = ["XXXX", "..X.", ".X..", "XXXX"]

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


# What this render is dressed for. Set once by main() from the clock and the
# forecast; the scene functions read it and record where the heads ended up
# so the holiday hats can follow a jumping dog.
CTX = {"holiday": None, "weather": None, "night": False, "dog_y": 0, "cat_y": 0}

RAINCOAT = (255, 205, 40)
PUMPKIN = (255, 130, 20)
PUMPKIN_RIB = (190, 80, 10)


def coat_colors():
    """Body recolour for the sitting dog, or None. A holiday costume wins
    over the raincoat."""
    if CTX["holiday"] == "halloween":
        return PUMPKIN, PUMPKIN_RIB
    if CTX["weather"] in ("rain", "storm") and not CTX["night"]:
        return RAINCOAT, (200, 150, 20)
    return None


def stage():
    im = Image.new("RGB", (64, 32))
    ground = (220, 230, 255) if CTX["weather"] == "snow" else DIM
    for x in range(4, 60):
        dot(im, x, 31, ground)
    return im


def put_dog(im, t, wag_speed=3, dy=0, **kw):
    bob = 1 if (t // 12) % 2 and dy == 0 else 0
    y0 = DOG_Y + bob + dy
    sprite = dog_sprite(**kw)
    pal = PAL
    coat = coat_colors()
    if coat:
        # the coat covers the body (rows 11-18) but leaves the cream chest
        rows = sprite.split("\n")
        for j in range(11, 19):
            rows[j] = "".join(
                ("R" if i in (5, 12) else "Y") if c == "T" else c
                for i, c in enumerate(rows[j]))
        sprite = "\n".join(rows)
        pal = dict(PAL, Y=coat[0], R=coat[1])
    paste(im, sprite, DOG_X, y0, pal)
    for (x, y) in (TAIL_UP if (t // wag_speed) % 2 else TAIL_DN):
        dot(im, DOG_X + x, DOG_Y + y + 1 + dy, TAN)
    CTX["dog_y"] = y0


def put_cat(im, t, swish=8, blink=True, **kw):
    if blink and t % 24 in (20, 21) and "eyes" not in kw:
        kw["eyes"] = "closed"
    paste(im, cat_sprite(**kw), CAT_X, CAT_Y)
    CTX["cat_y"] = CAT_Y
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
    clear = CTX["weather"] not in ("rain", "storm", "snow", "cloudy")
    if not clear:
        if CTX["weather"] == "cloudy":
            cloud(im, 49 + round(math.sin(2 * math.pi * t / NIGHT_FRAMES)), 3, (70, 75, 95))
    # moon (crescent) top right
    for y in (range(2, 10) if clear else ()):
        for x in range(50, 60):
            if (x - 54.5) ** 2 + (y - 5.5) ** 2 <= 14 and not (x - 56.5) ** 2 + (y - 4.5) ** 2 <= 11:
                dot(im, x, y, MOON)
    for i, (sx, sy) in enumerate([(4, 3), (22, 2), (40, 6), (31, 9), (12, 9)]):
        if clear and (t // 8 + i) % 3:
            dot(im, sx, sy, STAR)
    # bed
    for y in range(27, 32):
        inset = {27: 3, 31: 1}.get(y, 0)
        for x in range(5 + inset, 59 - inset):
            dot(im, x, y, GREEN if y > 27 else DIM)
    breathe = 1 if (t // 12) % 2 else 0
    paste(im, DOG_SLEEP, 8, 17 + breathe)
    paste(im, CAT_SLEEP, 32, 19 + (1 - breathe))
    CTX["dog_y"], CTX["cat_y"] = 17 + breathe, 19 + (1 - breathe)
    # z's rising from the dog's head
    for k in range(2):
        ph = (t + k * 24) % NIGHT_FRAMES
        zy = 14 - ph // 4
        zx = 7 + ph // 8
        if zy >= 0:
            paste(im, "\n".join(Z if k == 0 else Z_SMALL), zx, zy, {"X": (200, 210, 255)})
    return im

# ---------------------------------------------------------------- dressing

HATS = {
    # bottom row is the brim; (dx, dy) place it relative to the sprite origin
    "santa": ("...RRW\n..RRR.\n.RRRR.\nWWWWWW",
              {"R": (230, 30, 40), "W": (255, 255, 255)}),
    "party": ("..Y..\n..B..\n.BYB.\n.YBY.\nBYBYB",
              {"Y": (255, 220, 40), "B": (60, 140, 255)}),
    "witch": ("...P...\n...PP..\n..PPP..\n..PPPP.\nPPPPPPP",
              {"P": (150, 70, 200)}),
    "pilgrim": (".HHHH.\n.HHHH.\n.HGGH.\nHHHHHH",
                {"H": (110, 80, 60), "G": (240, 200, 60)}),
    "stem": (".G.\nGG.", {"G": (60, 170, 40)}),
    "bow": ("XX.XX\n.XNX.\nXX.XX", {"X": (255, 90, 150), "N": (200, 40, 100)}),
}
# which hat each animal wears per holiday
OUTFITS = {
    "halloween": ("stem", "witch"),
    "thanksgiving": ("pilgrim", None),
    "christmas": ("santa", "santa"),
    "newyear": ("party", "party"),
    "valentine": (None, "bow"),
    "july4": (None, None),
}


def put_hat(im, name, x, y_bottom):
    grid, pal = HATS[name]
    h = len(grid.split("\n"))
    paste(im, grid, x, y_bottom - h + 1, pal)


def dress(im):
    hol = CTX["holiday"]
    if hol not in OUTFITS:
        return
    dog_hat, cat_hat = OUTFITS[hol]
    if CTX["night"]:
        dog_at = (8 + 0, CTX["dog_y"] + 2)      # on the curled-up head
        cat_at = (32 + 0, CTX["cat_y"] + 0)
    else:
        dog_at = (DOG_X + 6, CTX["dog_y"] + 1)
        cat_at = (CAT_X + 2, CTX["cat_y"] + 3)
    if dog_hat:
        w = len(HATS[dog_hat][0].split("\n")[0])
        x = DOG_X + 9 - w // 2 if not CTX["night"] else dog_at[0] + 3 - w // 2
        put_hat(im, dog_hat, x, dog_at[1])
    if cat_hat:
        w = len(HATS[cat_hat][0].split("\n")[0])
        if cat_hat == "bow":
            put_hat(im, "bow", (CAT_X + 7) if not CTX["night"] else 37, cat_at[1] + 1)
        else:
            x = CAT_X + 5 - w // 2 if not CTX["night"] else 32 + 3 - w // 2
            put_hat(im, cat_hat, x, cat_at[1])


def jack_o_lantern(im, t, x, y):
    flick = (255, 230, 90) if t % 6 < 4 else (255, 170, 40)
    paste(im, ".G...\nOOOOO\nOFOFO\nOOOOO\nOFFFO\n.OOO.", x, y,
          {"O": PUMPKIN, "G": (60, 170, 40), "F": flick})


def cloud(im, x, y, col):
    paste(im, ".XX...\nXXXXX.\nXXXXXX", x, y, {"X": col})


def sun(im, t):
    core = (255, 210, 60)
    paste(im, ".XXX.\nXXXXX\nXXXXX\nXXXXX\n.XXX.", 2, 2, {"X": core})
    # rays alternate straight / diagonal every 8 frames
    rays = ([(4, 0), (8, 4), (4, 8), (0, 4)] if t % 16 < 8
            else [(1, 1), (7, 1), (7, 7), (1, 7)])
    for (x, y) in rays:
        dot(im, x, y, (255, 240, 150))


def on_black(im, x, y, col):
    if 0 <= x < 64 and 0 <= y < 32 and im.getpixel((x, y)) == (0, 0, 0):
        im.putpixel((x, y), col)


def particles(im, t, kind):
    """Rain, snow, leaves, confetti -- drawn only on empty sky so they never
    paint over the animals. Every motion divides the 48-frame loop evenly."""
    n = 48
    if kind in ("rain", "storm"):
        for i in range(12):
            x0 = (i * 23 + 5) % 64
            y = ((i * 11) + t * 2) % 32       # 2 px/frame: 16-frame fall
            x = (x0 - (y // 4)) % 64
            for k in range(2):
                on_black(im, x, y + k, (110, 160, 255))
        if kind == "storm" and t % 48 in (30, 31, 33):
            for (x, y) in [(52, 0), (51, 1), (50, 2), (51, 3), (52, 4), (51, 5), (50, 6), (49, 7)]:
                on_black(im, x, y, (255, 255, 200))
    elif kind == "snow":
        for i in range(16):
            x0 = (i * 37 + 3) % 64
            y = ((i * 7) + t // 3 * 2) % 32   # 2 px every 3 frames
            x = x0 + (1 if (t // 6 + i) % 2 else 0)
            on_black(im, x, y, (235, 240, 255))
    elif kind in ("leaves", "confetti"):
        cols = ([(255, 130, 20), (220, 60, 30), (240, 190, 40)] if kind == "leaves"
                else [(255, 80, 80), (80, 200, 255), (255, 220, 40), (150, 255, 120), (255, 120, 220)])
        for i in range(9 if kind == "leaves" else 14):
            x0 = (i * 29 + 7) % 64
            y = ((i * 13) + t * 32 // n) % 32
            x = x0 + round(2 * math.sin(2 * math.pi * (t / n + i / 5)))
            c = cols[i % len(cols)]
            on_black(im, x, y, c)
            if kind == "leaves":
                on_black(im, x + 1, y, c)


def fireworks(im, t):
    for k, (cx, cy, c) in enumerate([(14, 7, (255, 70, 70)), (50, 6, (90, 160, 255)), (31, 4, (255, 255, 255))]):
        ph = (t + k * 16) % 48
        if ph < 12:
            r = ph // 3 + 1
            for a in range(8):
                ang = a * math.pi / 4
                on_black(im, cx + round(r * math.cos(ang)), cy + round(r * math.sin(ang)), c)


def decorate(im, t):
    hol, wx = CTX["holiday"], CTX["weather"]
    precip = wx in ("rain", "storm", "snow")
    if not CTX["night"]:
        if wx == "sun":
            sun(im, t)
        elif wx == "cloudy":
            cloud(im, 2 + round(math.sin(2 * math.pi * t / 48)), 1, (150, 155, 170))
    if hol == "halloween":
        if CTX["night"]:
            jack_o_lantern(im, t, 53, 21)
        else:
            jack_o_lantern(im, t, 53, 25)
    if hol == "valentine" and not CTX["night"]:
        for k in range(2):
            ph = (t + 24 * k) % 48
            heart(im, (6, 56)[k], 14 - ph // 4)
    if hol == "july4":
        fireworks(im, t)
    dress(im)
    if precip:
        particles(im, t, wx)
    elif hol == "thanksgiving":
        particles(im, t, "leaves")
    elif hol == "newyear":
        particles(im, t, "confetti")
    return im


# ---------------------------------------------------------------- choosing

TZ = "America/New_York"
OPEN_HOUR, CLOSE_HOUR = 10, 19
ROTATION = ["sit", "catch", "yarn", "butterfly", "treat"]
NWS_HOURLY = "https://api.weather.gov/gridpoints/OKX/35,43/forecast/hourly"  # 145 Nassau


def holiday_for(d):
    import datetime
    if d.month == 10 and d.day >= 24:
        return "halloween"
    if d.month == 11:
        first_thu = 1 + (3 - datetime.date(d.year, 11, 1).weekday()) % 7
        tg = first_thu + 21
        if tg - 3 <= d.day <= tg:
            return "thanksgiving"
    if d.month == 12 and 18 <= d.day <= 26:
        return "christmas"
    if (d.month, d.day) in ((12, 31), (1, 1)):
        return "newyear"
    if d.month == 2 and 12 <= d.day <= 14:
        return "valentine"
    if d.month == 7 and d.day in (3, 4):
        return "july4"
    return None


def weather_now():
    """Classify the current NWS hourly period. Any failure -> None, and the
    card simply renders without weather."""
    import datetime
    import json
    import urllib.request
    try:
        req = urllib.request.Request(NWS_HOURLY, headers={
            "User-Agent": "tidbyt-greenpointvet (github.com/adamlee117097/tidbyt-clock)",
            "Accept": "application/geo+json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            periods = json.load(r)["properties"]["periods"]
        # the feed can still lead with the hour that just ended
        now = datetime.datetime.now(datetime.timezone.utc)
        p = next((q for q in periods
                  if datetime.datetime.fromisoformat(q["endTime"]) > now), periods[0])
        f = p["shortForecast"].lower()
        print("NWS:", p["startTime"], p["shortForecast"], p["temperature"],
              "pop", (p.get("probabilityOfPrecipitation") or {}).get("value"))
    except Exception as e:
        print("NWS failed, no weather:", e)
        return None
    # NWS says "Slight Chance Rain Showers" at 15% -- only draw rain or snow
    # when it is actually likely, else fall through to the sky condition.
    pop = (p.get("probabilityOfPrecipitation") or {}).get("value") or 0
    if pop < 50:
        f = f.replace("thunderstorms", "").replace("rain", "").replace("showers", "") \
             .replace("snow", "").replace("drizzle", "")
    if "thunder" in f:
        return "storm"
    if any(w in f for w in ("snow", "flurr", "sleet", "wintry")):
        return "snow"
    if any(w in f for w in ("rain", "shower", "drizzle")):
        return "rain"
    if any(w in f for w in ("cloudy", "overcast", "fog")) and "partly" not in f:
        return "cloudy"
    if any(w in f for w in ("sunny", "clear")):
        return "sun"
    return None


def main():
    import argparse
    import datetime
    from zoneinfo import ZoneInfo
    ap = argparse.ArgumentParser(description="Render the card for right now (or a forced moment).")
    ap.add_argument("--at", help='local time "YYYY-MM-DD HH:MM" instead of now')
    ap.add_argument("--state", choices=["awake", "asleep"])
    ap.add_argument("--scene", choices=list(SCENES))
    ap.add_argument("--holiday", choices=list(OUTFITS) + ["none"])
    ap.add_argument("--weather", choices=["rain", "storm", "snow", "cloudy", "sun", "none"])
    a = ap.parse_args()

    now = (datetime.datetime.strptime(a.at, "%Y-%m-%d %H:%M") if a.at
           else datetime.datetime.now(ZoneInfo(TZ)).replace(tzinfo=None))
    mins = now.hour * 60 + now.minute
    awake = OPEN_HOUR * 60 <= mins < CLOSE_HOUR * 60
    if a.state:
        awake = a.state == "awake"
    if a.scene:
        scene = a.scene
    elif mins < OPEN_HOUR * 60 + 30 or mins >= CLOSE_HOUR * 60 - 30:
        scene = "yawn"
    else:
        scene = ROTATION[(mins // 15) % len(ROTATION)]
    hol = a.holiday if a.holiday else holiday_for(now.date())
    wx = a.weather if a.weather else weather_now()
    CTX.update(holiday=None if hol == "none" else hol,
               weather=None if wx == "none" else wx,
               night=not awake)

    if awake:
        strip = []
        for head in range(N_STEPS):
            strip += [b64(strip_frame(head))] * FRAMES_PER_STEP
        frames = [b64(decorate(SCENES[scene](t), t)) for t in range(DAY_FRAMES)]
    else:
        strip = []
        frames = [b64(decorate(night_frame(t), t)) for t in range(NIGHT_FRAMES)]

    icon = grid_image(ICON, {"G": GREEN, "W": WHITE})
    star = OUT_STAR.read_text()
    start = star.index("ICON = ")
    end = star.index("# --- end generated ---")
    lst = lambda xs: "[\n%s]" % "".join('    "%s",\n' % f for f in xs)
    gen = 'ICON = "%s"\n\nSTRIP = %s\n\nSCENE = %s\n\n' % (b64(icon), lst(strip), lst(frames))
    OUT_STAR.write_text(star[:start] + gen + star[end:])
    print("rendered %s %s, scene=%s holiday=%s weather=%s" % (
        now.strftime("%Y-%m-%d %H:%M"), "awake" if awake else "asleep",
        scene if awake else "-", CTX["holiday"], CTX["weather"]))


if __name__ == "__main__":
    main()
