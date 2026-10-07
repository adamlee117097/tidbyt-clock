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


# wave -- a cheery hello to customers walking past. One bird raises and
# flaps its wing (bill open, head up, eyes OPEN -- stretch's yawn is the
# closed-eyes version of this pose) while the other watches; then they swap.


def wave_waver(p):
    """One bird mid-wave: wing toggling up/down every 3 frames, bill open,
    head lifted 1px. Eyes hard open -- never blinking -- so no frame ever
    duplicates scene_stretch's closed-eye yawn."""
    up = (p // 3) % 2 == 0
    return bird(head=(14, 4), wing="up" if up else "down",
                bill_open=True, eyes="open")


def wave_watcher(t, offset=0):
    """The attentive neighbour: head tilted 1px toward the waver, blinking."""
    return bird(head=(15, 5), eyes=blinking(t, offset))


def scene_wave(t):
    """Hello! Right bird flaps a raised wing, then the left bird does."""
    im = blank()
    if t < 6:                      # both standing, blinking
        l = bird(head=STAND, eyes=blinking(t))
        r = bird(head=STAND, eyes=blinking(t, 7))
    elif t < 26:                   # right bird waves, left watches
        l = wave_watcher(t)
        r = wave_waver(t - 6)
    elif t < 46:                   # they swap
        l = wave_waver(t - 26)
        r = wave_watcher(t, 7)
    else:                          # settle to STAND: the drop from the last
        l = bird(head=STAND, eyes=blinking(t))      # wing-up frame reads as
        r = bird(head=STAND, eyes=blinking(t, 7))   # the final down-beat,
    place(im, l, r)                                 # and t=47 flows into t=0
    cups(im, t)
    return im

# FLAPHOP -- excited happy hops, both birds together (mirrored).
# One hop per 24 frames (two per loop): crouch to load the spring, pop into
# the air with wings up and a chirp at the peak, drop back, squash the
# landing, then stand and catch a breath. bird() always draws the legs down
# to the floor, so airborne frames erase the feet after place(): the left
# bird's legs live at x6..11 (upper leg, knee back-step, toes) and the right
# bird is the mirror (x -> 63-x).


def flaphop_pose(p):
    """(dy, head_y, wing, chirp) for phase p = t % 24 of one hop."""
    if p < 4:
        return 1, 6, "down", False                         # crouch
    if p == 4:
        return -1, 4, "up", False                          # launch
    if p < 9:
        return -2, 3, ("up" if p < 8 else "down"), True    # peak: flap, chirp
    if p == 9:
        return -1, 4, "down", False                        # falling
    if p == 10:
        return 1, 6, "down", False                         # landing squash
    return 0, 5, "down", False                             # stand


def scene_flaphop(t):
    """Excited hops: both birds spring up together, chirping at the peak."""
    im = blank()
    dy, hy, wing, chirp = flaphop_pose(t % 24)
    b = bird(head=(14, hy), wing=wing, dy=dy, bill_open=chirp,
             eyes=blinking(t))
    place(im, b, b)
    if dy < 0:
        # feet off the ground: black out the leg bottoms on both sides
        for x in range(6, 12):
            for y in range(31 + dy, 32):
                dot(im, x, y, (0, 0, 0))
                dot(im, 63 - x, y, (0, 0, 0))
    cups(im, t)
    return im

# Drowsy — the coffee joke. The left bird nods off, faceplants into its
# espresso, drinks, and comes back up ludicrously awake (sparkles). The right
# bird is the straight man: stands, blinks, leans back 1px during the sip.
# Pure function of t, 48 frames, seam: t47 == t0 pose.

drowsy_SPARKLE = (255, 240, 180)          # pale gold; drawn only as 2x2 blocks
drowsy_SPOTS = [(6, 2), (20, 2), (12, 0)]  # around the perky head; clear of
                                           # bill (x<=19,y4-7), neck, steam


def drowsy_r(v):
    """Round half UP (round() banker's-rounds 18.5 -> 18, double-stepping
    an eased path)."""
    return int(v + 0.5)


def drowsy_left(t):
    """bird() kwargs for the left bird at frame t."""
    if t < 6:                 # sag 1: chin starts to drop, lids fall at t4
        u = (t / 5.0) ** 2
        return dict(head=(drowsy_r(14 - u), drowsy_r(5 + 2 * u)),
                    eyes="closed" if t >= 4 else blinking(t))
    if t < 8:                 # the catch: jerks 1px back up, eyes snap open
        return dict(head=(13, 6), eyes="open")
    if t < 12:                # sag 2: loses the fight
        u = (t - 7) / 4.0
        return dict(head=(drowsy_r(13 - u), drowsy_r(6 + 3 * u)), eyes="closed")
    if t < 19:                # the fall: plop into the cup, soft landing
        u = (1 - math.cos(math.pi * (t - 11) / 7.0)) / 2
        return dict(head=(drowsy_r(12 + 13 * u), drowsy_r(9 + 12 * u)),
                    eyes="closed", bill="down" if u > 0.45 else "fwd")
    if t < 26:                # sipping, out cold, tiny 1px bob
        return dict(head=(25, 21 + ((t - 19) // 3) % 2),
                    eyes="closed", bill="down")
    if t < 30:                # the pop: straight back up, wide awake
        u = (t - 25) / 5.0
        hy = drowsy_r(21 - 17 * u)
        return dict(head=(drowsy_r(25 - 11 * u), hy), eyes="open",
                    bill="down" if hy >= 14 else "fwd")
    if t == 30:               # 1px overshoot above STAND
        return dict(head=(14, 4), eyes="open")
    if t < 44:                # perky: caffeinated bounce, 3-frame beat
        b = ((t - 31) // 3) % 2
        return dict(head=(14, 5 + b), dy=b, eyes="open")
    return dict(head=STAND, eyes="open")   # settled; flows into t=0


def drowsy_sparkles(im, t):
    """2-3 twinkles near the perky head, each a 2x2 block on its own phase."""
    for i, (sx, sy) in enumerate(drowsy_SPOTS):
        if ((t + 3 * i) // 2) % 2 == 0:
            for ox in (0, 1):
                for oy in (0, 1):
                    dot(im, sx + ox, sy + oy, drowsy_SPARKLE)


def scene_drowsy(t):
    """Left bird nods off into its espresso, sips, perks RIGHT up."""
    im = blank()
    l = bird(**drowsy_left(t))
    r = bird(head=(13, 5) if 16 <= t < 28 else STAND, eyes=blinking(t, 7))
    place(im, l, r)
    cups(im, t)
    if 31 <= t <= 43:
        drowsy_sparkles(im, t)
    return im

# CURIOUS — a lavender butterfly laps the open sky between the birds and
# both flamingos follow it with their heads (crane when it's far, rear back
# a touch when it's close), eyes open, offset blinks. Cups + steam stay.
curious_LAV = (200, 160, 255)


def curious_path(t):
    """Butterfly centre: one closed ellipse lap of the sky per 48 frames,
    plus a 4-cycle sine bob (both period-48, so the loop is seamless)."""
    ph = 2 * math.pi * t / 48
    x = 32 + 10 * math.cos(ph)
    y = 10 + 4 * math.sin(ph) + 1.2 * math.sin(4 * ph)
    return x, y


def curious_butterfly(im, t):
    bx = round(curious_path(t)[0])
    by = round(curious_path(t)[1])
    if (t // 2) % 2 == 0:
        spans = range(-2, 2)        # WINGS OPEN: two 2x2 blocks side by side
    else:
        spans = range(-1, 1)        # WINGS CLOSED: one 2x2 block, same centre
    for ox in spans:
        for oy in (-1, 0):
            dot(im, bx + ox, by + oy, curious_LAV)


def curious_head(t, mirrored):
    """Head tracking the butterfly, in THIS bird's own canvas coords
    (the right bird is placed mirrored, so feed it the mirrored x).
    Driven by the ellipse only — the bob would twitch the head."""
    ph = 2 * math.pi * t / 48
    bx = 32 + 10 * math.cos(ph)
    ye = 10 + 4 * math.sin(ph)
    mx = (63 - bx) if mirrored else bx          # butterfly x as this bird sees it
    hx = 13 + max(0, min(3, round(3 * (mx - 21) / 20)))   # far -> crane to 16
    hy = 3 + max(0, min(2, round(2 * (ye - 6) / 8)))      # high -> look up (3)
    return hx, hy


def curious_base(im, t):
    l = bird(head=curious_head(t, False), eyes=blinking(t))
    r = bird(head=curious_head(t, True), eyes=blinking(t, 11))
    place(im, l, r)
    cups(im, t, steam=True)


def scene_curious(t):
    """A butterfly flits between them; both birds track it."""
    im = blank()
    curious_base(im, t)
    curious_butterfly(im, t)
    return im

# STRUT -- proud march in place: heads held high, chest out, legs
# alternating on a 12-frame beat with the two birds counter-phased.
# 24-frame leg cycle per bird (front up 12, back up 12); the right bird
# marches at phase t+12, so it always lifts the opposite leg while both
# bob to the same drum (dip for the first half-beat, tall for the second).


def strut_lift(im, lx, dy, mirror):
    """Fold up one leg AFTER place(): erase exactly the lower-leg pixels
    bird() drew from the knee (y=26+dy) down -- (lx, knee), (lx-1, knee+1..31)
    and the toes (lx, 31) -- leaving a 3px thigh stub, then draw a 2px
    folded shin trailing back-and-down from the thigh. Coords are left-bird
    canvas coords; the right bird's mirror maps x -> 63-x."""
    def px(x, y, col):
        dot(im, 63 - x if mirror else x, y, col)
    knee = 26 + dy
    for y in range(knee, 32):
        px(lx if y <= knee else lx - 1, y, (0, 0, 0))
    px(lx, 31, (0, 0, 0))                     # the forward toe pixel
    px(lx - 1, knee, LEG)                     # folded shin: back...
    px(lx - 2, knee + 1, LEG)                 # ...and tucked under


def strut_pose(p):
    """One bird's march sub-beat: dip-and-nod for the first half of each
    12-frame step, tall and proud (head high, hy=4) for the second."""
    dip = 1 if p % 12 < 6 else 0
    return dip, (14 + dip, 4 + dip)


def scene_strut(t):
    """Proud march in place: heads high, legs alternating on a 12-frame
    beat, birds counter-phased, body bobbing with each step."""
    im = blank()
    marchers = []
    for k, phase in enumerate((t, t + 12)):
        dip, head = strut_pose(phase)
        marchers.append((bird(head=head, dy=dip, eyes=blinking(t, 7 * k)),
                         dip, phase))
    place(im, marchers[0][0], marchers[1][0])
    for k, (_, dip, phase) in enumerate(marchers):
        lifted = LEG_X[1] if (phase // 12) % 2 == 0 else LEG_X[0]
        strut_lift(im, lifted, dip, mirror=(k == 1))
    cups(im, t)
    return im


SCENES = {
    "heart": scene_heart,
    "sip": scene_sip,
    "oneleg": scene_oneleg,
    "dance": scene_dance,
    "preen": scene_preen,
    "wave": scene_wave,
    "flaphop": scene_flaphop,
    "drowsy": scene_drowsy,
    "curious": scene_curious,
    "strut": scene_strut,
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
