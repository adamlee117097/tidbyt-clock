#!/usr/bin/env python3
"""Rocket Fuel promo card for the Tidbyt -- a pixel-art take on Sweetleaf's
Rocket Fuel can: the rider with the swept-up hair and pink shades, tattooed
arm raised, standing on a chunky gold rocket climbing up and to the right
with an orange flame, on a night field of pink and blue splatter, over
ROCKET FUEL in cream.

The rocket is built as geometry (a cylinder with a rounded nose and fins,
rotated) rather than typed in, because a tilted cylinder is miserable to
hand-plot and trivial to describe; the rider is a hand-drawn grid placed on
its back. Stars stream left one column per frame (64 frames, so the field
wraps seamlessly), the flame flickers on a 4-frame cycle and the whole ship
bobs a row every 16 frames. Re-run to rewrite rocketfuel.star:
    python3 rocketfuel/make_frames.py
"""
import base64
import io
import math
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
OUT_STAR = HERE / "rocketfuel.star"

GOLD = (246, 178, 60)
GOLD_HI = (252, 200, 96)    # top highlight of the hull (kept close to gold:
                            # the flame core must own the pale yellow)
ORANGE = (232, 98, 42)      # lower hull
UNDER = (170, 60, 30)       # underside
FIN = (215, 75, 40)
PORTHOLE = (150, 210, 255)
FLAME_CORE = (255, 246, 160)
FLAME = (255, 100, 30)
NOZZLE = (130, 36, 28)      # dark band at the tail so the flame reads as
                            # exhaust rather than more hull
PINK = (255, 61, 138)
BLUE = (70, 130, 255)
SKIN = (255, 205, 170)
HAIR = (120, 90, 230)       # navy on the can; navy vanishes on black
TOP = (60, 80, 180)         # the black tank top, lifted to a readable navy
JEANS = (110, 150, 235)
TATTOO = (80, 140, 255)

W, H = 64, 24               # scene; ROCKET FUEL (8 rows) sits under it
DELAY_MS = 50
N_FRAMES = 64
BOB_PERIOD = 16
FLAME_PERIOD = 4
FLAME_SEQ = [0, 1, 2, 1]    # flame length variants; 4 x 4 = 16 divides 64

# ---- rocket geometry, in rocket-local units (x along the axis, y radial)
BODY_LEN = 24.0
RADIUS = 4.5
NOSE_LEN = 10.0
FIN_LEN = 6.0
FIN_REACH = 2.4             # how far past the hull a fin reaches
PORT_X, PORT_R = 8.0, 1.6
ANGLE_DEG = 12              # climb angle, up and to the right; flatter
                            # than the can so the rider fits above the hull
TAIL_AT = (16.0, 17.0)      # canvas position of the tail's centre (x, y)
FLAME_LENS = [8.0, 6.0, 10.0]

# ---- the rider, hand-drawn, facing right, standing on the hull
# h hair  p pink streak  k shades  s skin  t top  j jeans  a tattooed arm
RIDER = [
    ".ss......hhhh.",
    ".aa.....hhhhph",
    ".aa.....hkkkk.",
    "..aa.....sss..",
    "..aa....tttt..",
    "...aa..tttttt.",
    "....s..tttttt.",
    ".......jjjjjj.",
    "......jjj.jjj.",
    ".....jjj...jjj",
    ".....jj.....jj",
]
RIDER_AT = (19, 0)          # canvas col,row of the grid's top-left; feet
                            # land on the hull's top at row 10
SHADES = (245, 245, 255)    # the white-framed shades, the rider's one bright cue
RIDER_PAL = {"h": HAIR, "p": PINK, "k": SHADES, "s": SKIN, "t": TOP, "j": JEANS, "a": TATTOO}

STARS = [(2, 1, PINK), (9, 5, BLUE), (20, 2, PINK), (26, 22, BLUE), (44, 3, BLUE),
         (51, 1, PINK), (57, 6, BLUE), (61, 13, PINK), (40, 23, BLUE), (6, 23, PINK),
         (33, 22, BLUE), (48, 19, PINK), (12, 10, BLUE), (58, 17, PINK), (36, 4, BLUE),
         (54, 23, PINK), (3, 12, BLUE), (62, 9, BLUE)]

assert all(len(r) == len(RIDER[0]) for r in RIDER)
assert N_FRAMES % BOB_PERIOD == 0 and N_FRAMES % (FLAME_PERIOD * len(FLAME_SEQ)) == 0 and N_FRAMES % W == 0
assert (N_FRAMES // BOB_PERIOD) % 2 == 0, "the bob must end where it started"

_c, _s = math.cos(math.radians(ANGLE_DEG)), math.sin(math.radians(ANGLE_DEG))


def to_local(px, py):
    """Canvas pixel centre -> rocket-local (x along axis, y radial, +y = down)."""
    dx, dy = px + 0.5 - TAIL_AT[0], py + 0.5 - TAIL_AT[1]
    # canvas y grows downward; a climb means the axis points up-right
    x = dx * _c - dy * _s
    y = dx * _s + dy * _c
    return x, y


def rocket_color(x, y, flame_len):
    """Colour of the ship at local (x, y), or None."""
    # nose: rounded, radius shrinking to 0 over NOSE_LEN
    if BODY_LEN <= x <= BODY_LEN + NOSE_LEN:
        t = (x - BODY_LEN) / NOSE_LEN
        r = RADIUS * math.sqrt(max(0.0, 1 - t * t))
        if abs(y) <= r:
            return GOLD_HI if y < -r * 0.45 else (GOLD if y < r * 0.35 else ORANGE)
        return None
    if 0 <= x < BODY_LEN:
        if (x - PORT_X) ** 2 + (y + 0.6) ** 2 <= PORT_R ** 2:
            return PORTHOLE
        if x < 1.2 and abs(y) <= RADIUS:
            return NOZZLE
        if abs(y) <= RADIUS:
            if y < -RADIUS * 0.55:
                return GOLD_HI
            if y < RADIUS * 0.15:
                return GOLD
            if y < RADIUS * 0.7:
                return ORANGE
            return UNDER
        # fins: triangles off the hull at the tail
        if x <= FIN_LEN:
            reach = FIN_REACH * (1 - x / FIN_LEN)
            if abs(y) <= RADIUS + reach:
                return FIN
        return None
    if -flame_len <= x < 0:
        t = -x / flame_len                       # 0 at the tail, 1 at the tip
        r = RADIUS * 0.9 * (1 - t) + 0.8
        if abs(y) <= r:
            if abs(y) <= r * 0.45 and t < 0.75:
                return FLAME_CORE
            if t > 0.8:
                return PINK
            return FLAME
    return None


def frame(t):
    img = Image.new("RGB", (W, H), (0, 0, 0))
    px = img.load()
    bob = -1 if (t // BOB_PERIOD) % 2 else 0
    flame_len = FLAME_LENS[FLAME_SEQ[(t // FLAME_PERIOD) % len(FLAME_SEQ)]]
    for (c, r, col) in STARS:
        px[(c - t) % W, r] = col
    for y in range(H):
        for x in range(W):
            lx, ly = to_local(x, y - bob)
            col = rocket_color(lx, ly, flame_len)
            if col:
                px[x, y] = col
    rx, ry = RIDER_AT
    for r, line in enumerate(RIDER):
        for c, ch in enumerate(line):
            if ch != ".":
                y = ry + r + bob
                if 0 <= y < H and 0 <= rx + c < W:
                    px[rx + c, y] = RIDER_PAL[ch]
    return img


def encode(img):
    buf = io.BytesIO()
    img.convert("P", palette=Image.ADAPTIVE, colors=32).save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


TEMPLATE = '''"""Rocket Fuel -- Sweetleaf's maple oat-milk cold brew, on the Tidbyt.

Frames are generated by make_frames.py; edit the geometry and grids there
and re-run. Static promo card: nothing here depends on the time of day.
"""

load("render.star", "render")
load("encoding/base64.star", "base64")

DELAY_MS = {delay}
CREAM = "#F5ECD2"

FRAMES = [
{frames}
]

def main(config):
    return render.Root(
        delay = DELAY_MS,
        child = render.Column(
            children = [
                render.Animation(children = [render.Image(src = base64.decode(f)) for f in FRAMES]),
                # No spacer Box here: a Box of height 0 means "expand" in
                # pixlet and pushes the wordmark clean off the panel.
                render.Box(width = 64, height = 8, child = render.Text(content = "ROCKET FUEL", font = "5x8", color = CREAM)),
            ],
        ),
    )
'''


def main():
    frames = [frame(t) for t in range(N_FRAMES)]
    assert frame(N_FRAMES).tobytes() == frames[0].tobytes(), "loop is not seamless"
    blobs = [encode(f) for f in frames]
    assert H + 8 == 32
    OUT_STAR.write_text(TEMPLATE.format(delay=DELAY_MS,
                                        frames=",\n".join('    "%s"' % b for b in blobs)))
    print("%d frames (%dKB) -> %s" % (len(frames), sum(map(len, blobs)) // 1024, OUT_STAR))


if __name__ == "__main__":
    main()
