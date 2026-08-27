#!/usr/bin/env python3
"""Generate the Kaleidoscope Coffee logo animation and write kaleidoscope.star.

The mark is two mirrored flamingos flanking a pair of espresso cups. Rather
than hand-plotting 26px sprites, the birds are composed at the logo's native
resolution (head/neck split off as its own layer, rotated about the neck
base) and only then downscaled + thresholded -- so every pose keeps the real
logo proportions instead of drifting into hand-drawn approximations.

The bottom band (legs, perch line, cups, feet) IS hand-authored: at 26px the
downscale turns the thin legs and the two cups into an unreadable smear, so
those rows are cleared and redrawn as explicit 1px geometry.

Tune the constants below and re-run:  python3 logo/make_frames.py
"""
import base64
import datetime
import io

from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
LOGO = Path("/home/adam/Documents/Kaleidoscope/logo.png")
OUT_STAR = HERE / "kaleidoscope.star"

# ---------------------------------------------------------------- palette
CORAL = (242, 90, 60)      # brand #DF513B pushed up ~12% -- LEDs mute it
DARK = (169, 58, 40)       # the perch line only, so the gold cups stay the
                           # brightest thing down there instead of fusing
                           # with it into one horizontal smear
SHADOW = (168, 56, 40)     # the shape's lower edge, to give the mass a form
                           # instead of a flat fill. Roughly 2:1 against coral
                           # -- any closer and the panel washes the two together
EYE = (250, 240, 225)      # a bright pupil dropped into the logo's beak notch
WORDMARK_COLOR = (245, 245, 245)   # white: it separates the name from the birds
                                   # instead of competing with them in coral
GOLD = (236, 190, 94)      # the cups; same crema-gold as the shop dashboard
# Steam, brightest at the cup rim and fading out as it climbs. Never white:
# at panel brightness white steam out-shines the birds and the card stops
# being a logo.
# Measured against black: the old ramp's last two steps sat at 2.03:1 and
# 1.55:1, so on a lit shop floor the wisp truncated to its bottom 3-4 pixels
# and the sway read as flicker on a stub. Shorter wisp, every step >=3.4:1.
STEAM = [(190, 190, 190), (160, 160, 160), (128, 128, 128), (98, 98, 98)]

# ---------------------------------------------------------------- geometry
# 25 art rows + 1 blank + 6 wordmark = the full 32 rows. The blank row is not
# optional: LED bloom at across-the-room distance closes a 0px gap and the
# feet visually fuse with the text. TOP_MARGIN spends the row that was
# otherwise structurally dead (art ended at FOOT_ROW, leaving a permanently
# black row above the blank one) on giving the heads a pixel of air instead
# of letting them butt against the panel edge.
BIRD_H = 26                # proportion of the downscale (bottom rows redrawn)
CANVAS_W, CANVAS_H = 64, 25
TOP_MARGIN = 1             # art occupies canvas rows 1..24
PANEL_W, PANEL_H = 64, 32  # the device itself
GAP_ROWS = 1               # blank row between art and wordmark
TEXT_ROWS = 6              # tom-thumb inks 5 rows, the widget is 6 tall
EXPECTED_LOGO_SIZE = (1024, 1024)  # the export MARK_BOX was measured against
MARK_BOX = (304, 237, 719, 554)    # flamingo mark inside logo.png
MARK_INK_RANGE = (36000, 44000)    # opaque px the crop must catch (~40031)
# Splitting head+neck off the body needs a SLANTED cut, not a vertical one:
# the head sits left of the neck base, so any straight x cut either leaves a
# sliver of skull welded to the static body or swallows the wing. The cut
# line x > CUT_A + CUT_B*y clears the wing at every row while keeping the
# whole head. The two layers deliberately OVERLAP between BODY_CUT_Y and
# HEAD_CUT_Y so a rotated neck still meets the shoulder instead of tearing.
CUT_A, CUT_B = 60.0, 0.55
CUT_X_MAX = 210            # keeps the left bird's mask off the right bird
BODY_CUT_Y = 106           # body keeps everything below this (the stub)
HEAD_CUT_Y = 125           # head layer runs this far down (past the pivot)
PIVOT_Y = 118              # neck base -- heads rotate about this point
PIVOT_X = 150
LEG_TRIM = 258             # crop the long bare-leg run before downscaling
COMPACT_H = 275            # bird-scale knob, NOT a measured height: it is
                           # neither the 317px crop nor the 258px trim. Chosen
                           # so the torso fills rows 0..17 at BIRD_W == 39.
THRESHOLD = 110

# --- hand-authored bottom band, in bird-local columns (39 wide, mirror @19)
BAND_TOP = 18              # first row the downscale is discarded from, and
                           # the top of every hand-authored element below.
                           # It was previously written out in four separate
                           # places that had to agree by hand.
LEG_COL = 9
LEG_W = 2                  # NOT 1. A 1px leg is anatomically right and
                           # unreadable: the panel puts a black gutter between
                           # every diode, so a single-pixel line becomes a
                           # column of separate dots and the bird looks like it
                           # is standing next to its legs rather than on them.
                           # Confirmed on the device, not just in a render.
FOOT_W = 3
FOOT_ROW = 23
LEG_ROWS = range(BAND_TOP, FOOT_ROW)
BAR_ROW = BAND_TOP + 2     # the row the cup's handle sits on
# Perch line: only the stretch between the leg and the cup handle. The logo
# runs it outboard of the legs too, but at this size that turns leg-plus-line
# into a free-floating "+" that reads as a foreign object rather than a bird.
BAR_COLS = range(LEG_COL + LEG_W, 13)
CUP = {                            # left cup; the right one is mirrored
    BAND_TOP + 0: [14, 15, 16, 17],   # rim -- widest row, that is what reads
    BAND_TOP + 1: [14, 15, 16, 17],   # body
    BAND_TOP + 2: [13, 14, 15, 16, 17],  # body + handle, meets the perch line
    BAND_TOP + 3: [15, 16],           # tapered base
}
STEAM_COL = 16                     # wisp column for the left cup
STEAM_BASE_ROW = BAND_TOP - 1      # one row above the cup rim

# ---------------------------------------------------------------- motion
# Positive angle = heads lean INWARD, toward each other over the cups. The
# neck cannot actually reach the cups -- it is near-vertical, so rotating it
# about the shoulder slides the head sideways, not down, and no plausible
# angle puts the beak on a cup. Leaning in is the beat that IS available at
# this size, and past ~20 degrees the two heads collide into one blob.
# Retracting the neck to force a deeper dip was tried and rejected: it eats
# the neck, and the neck is the entire reason the silhouette reads flamingo.
NOD = [0, 7, 14, 20]
# Asleep: the head folds back over the body, which is what a roosting
# flamingo actually does. Past about -65 the head is swallowed by the wing
# and the silhouette stops reading as a bird at all; -48 keeps the tucked
# head distinct from the back. The birds already stand on one leg, so the
# head is the whole tell.
SLEEP_ANGLE = -48
SLEEP_POSE = len(NOD)          # the wardrobe's fifth entry
# frame -> NOD index. 48 frames @ 66ms = 3.17s; frame 47 flows into frame 0.
# Pose-to-pose with holds, never tweened 1px at a time -- smooth interpolation
# at 26px reads as the sprite melting, not as movement.
BEATS = ([0] * 13 + [1] * 3 + [2] * 3 + [3] * 8 +
         [2] * 3 + [1] * 3 + [0] * 15)
STEAM_LEN = len(STEAM)             # wisp height in rows

STEAM_WAVE = [0, 0, 1, 1, 0, 0, -1, -1]   # length 8 divides 48 -> seamless
RIGHT_STEAM_PHASE = 4              # desync the two cups; mirrored steam
                                   # looks mechanical rather than alive

# Sleep. One "z" drifting up the corridor between the birds -- a card with no
# motion at all reads as a crashed display rather than a closed shop, and this
# is the quietest motion that still says something.
Z_ROWS = 8                         # eight steps of climb
Z_FLOOR = 3                        # ...ending here rather than at the panel
                                   # edge, which keeps the climb clear of the
                                   # top rows and off the birds' heads.
Z_HOLD = 6                         # frames per step; 8 x 6 = the 48-frame loop
Z_OFFSETS = (0, 4)                 # two in flight. One reads as a lone mark;
                                   # three abut into a blue ladder, since each
                                   # is three rows tall
ZED = [(178, 194, 240), (162, 178, 226), (144, 160, 210), (126, 142, 194),
       (110, 124, 176), (96, 108, 158), (84, 94, 140), (72, 82, 124)]
DELAY_MS = 66
TIMEZONE = "America/New_York"   # the shop's clock decides the season

# Shop hours, and therefore when the birds turn in. Mon-Thu 8-5, Fri-Sun 8-6.
OPEN_HOUR = 8
CLOSE_HOUR = {"Mon": 17, "Tue": 17, "Wed": 17, "Thu": 17,
              "Fri": 18, "Sat": 18, "Sun": 18}
# These keys are matched against Go's weekday abbreviations, because that is
# what now.format("Mon") returns. A typo does not raise: is_open()'s lookup
# falls back to OPEN_HOUR, which reads as "shut all day", so one misspelled key
# would silently sleep through a whole weekday every week. A day the shop
# really is closed should be written as an explicit OPEN_HOUR value, so a
# genuine closure and a typo stay distinguishable.
assert set(CLOSE_HOUR) == {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}, (
    "CLOSE_HOUR keys must be Go weekday abbreviations: %s" % sorted(CLOSE_HOUR))
assert all(h >= OPEN_HOUR for h in CLOSE_HOUR.values()), "a day closes before it opens"


def _layers():
    # MARK_BOX is a crop of THIS logo file at its current 1024x1024 export.
    # A re-exported logo at another size would still crop, still downscale,
    # and still emit 48 valid frames -- of the wrong part of the image. Fail
    # loudly here instead of shipping quietly-wrong art to the shop floor.
    if not LOGO.exists():
        raise SystemExit("source logo not found: %s" % LOGO)
    src = Image.open(LOGO).convert("RGBA")
    if src.size != EXPECTED_LOGO_SIZE:
        raise SystemExit(
            "logo is %dx%d, expected %dx%d -- MARK_BOX and the layer-cut "
            "constants are calibrated to that export. Re-derive them against "
            "the new file before regenerating." % (src.size + EXPECTED_LOGO_SIZE))
    mark = src.crop(MARK_BOX)
    ink = int((np.array(mark.split()[3]) > 128).sum())
    if not MARK_INK_RANGE[0] <= ink <= MARK_INK_RANGE[1]:
        raise SystemExit(
            "MARK_BOX caught %d opaque pixels, expected %d-%d. The logo is the "
            "right size but the mark is not where the crop says it is -- a "
            "re-export that shifted the artwork passes the dimension check and "
            "would otherwise render a quietly-wrong bird." % ((ink,) + MARK_INK_RANGE))
    w, h = mark.size
    a = np.array(mark.split()[3]) > 128
    y, x = np.mgrid[0:h, 0:w]
    cut = CUT_A + CUT_B * y
    mx = w - 1 - x

    def side(col, ymax):
        return a & (y < ymax) & (col > cut) & (col < CUT_X_MAX)

    head_l = side(x, HEAD_CUT_Y)
    head_r = side(mx, HEAD_CUT_Y)
    body = a & ~(side(x, BODY_CUT_Y) | side(mx, BODY_CUT_Y))

    def gray(mask):
        im = Image.new("L", (w, h), 0)
        im.putdata((mask.astype(np.uint8) * 255).ravel().tolist())
        return im

    return gray(body), gray(head_l), gray(head_r), w


BODY, HEAD_L, HEAD_R, SRC_W = _layers()
BIRD_W = round(SRC_W * BIRD_H / COMPACT_H)          # 39
HAND_BAND_WIDTH = 39       # the width every hand-authored column assumes
OX = (CANVAS_W - BIRD_W) // 2                        # 12
MIRROR = BIRD_W - 1                                  # x -> MIRROR - x

# These couplings are what a well-meaning tune breaks silently rather than
# loudly, so state them where an edit trips over them.
assert BIRD_W % 2 == 1, (
    "BIRD_W must stay odd (%d) -- the hand band mirrors about a centre "
    "COLUMN, and an even width puts the axis between pixels" % BIRD_W)
assert BIRD_W == HAND_BAND_WIDTH, (
    "BIRD_W is %d but every hand-authored column (LEG_COL, BAR_COLS, CUP, "
    "STEAM_COL) and BAND_TOP are measured against a %d-wide sprite. Raising "
    "BIRD_H silently slides the legs and cups off the birds and moves the "
    "band wipe up into the torso -- re-tune those columns, then update this."
    % (BIRD_W, HAND_BAND_WIDTH))
assert CANVAS_H + GAP_ROWS + TEXT_ROWS == PANEL_H, (
    "art %d + gap %d + wordmark %d != the panel's %d rows"
    % (CANVAS_H, GAP_ROWS, TEXT_ROWS, PANEL_H))
assert CANVAS_W == PANEL_W, "the frames must be the full panel width"
assert len(BEATS) % len(STEAM_WAVE) == 0, (
    "the steam wave (%d) must divide the frame count (%d) or the wisp jumps "
    "sideways at the loop seam" % (len(STEAM_WAVE), len(BEATS)))
assert max(BEATS) < len(NOD), "BEATS indexes past the end of NOD"
assert FOOT_ROW + TOP_MARGIN < CANVAS_H, "the feet fall off the canvas"
assert max(CUP) + TOP_MARGIN < CANVAS_H, "the cups fall off the canvas"
assert min(CUP) == BAND_TOP, "the cup must start at the hand-authored band top"


def _holes(grid):
    """Unlit pixels the border cannot reach -- i.e. the logo's beak notch.

    Found by flood fill rather than by fixed coordinates, so the eye lands
    correctly at every head angle, including the tucked sleeping one, without
    anything to keep in sync.
    """
    h, w = grid.shape
    seen = np.zeros_like(grid)
    queue = deque()
    for r in range(h):
        for c in (0, w - 1):
            if not grid[r, c] and not seen[r, c]:
                seen[r, c] = True
                queue.append((r, c))
    for c in range(w):
        for r in (0, h - 1):
            if not grid[r, c] and not seen[r, c]:
                seen[r, c] = True
                queue.append((r, c))
    while queue:
        r, c = queue.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            y, x = r + dr, c + dc
            if 0 <= y < h and 0 <= x < w and not grid[y, x] and not seen[y, x]:
                seen[y, x] = True
                queue.append((y, x))
    return (~grid) & (~seen)


def _downscale(gray):
    """Source-resolution layer -> the sprite grid, thresholded."""
    im = gray.crop((0, 0, SRC_W, LEG_TRIM))
    small = im.resize((BIRD_W, round(LEG_TRIM * BIRD_H / COMPACT_H)), Image.LANCZOS)
    grid = np.zeros((BIRD_H, BIRD_W), dtype=bool)
    s = np.array(small) > THRESHOLD
    grid[:s.shape[0], :] = s
    return grid


def bird_bitmap(angle):
    """Full-res compose at this head angle, then downscale to the sprite grid."""
    hl = HEAD_L.rotate(-angle, resample=Image.BICUBIC, center=(PIVOT_X, PIVOT_Y))
    hr = HEAD_R.rotate(angle, resample=Image.BICUBIC,
                       center=(SRC_W - 1 - PIVOT_X, PIVOT_Y))
    merged = np.maximum(np.maximum(np.array(BODY), np.array(hl)), np.array(hr))
    grid = _downscale(Image.fromarray(merged))
    grid[BAND_TOP:, :] = False  # the downscale's leg/cup mush -- redrawn below

    # Mirror the left half onto the right rather than trusting the downscale
    # to come out symmetric. It does not: LANCZOS lands either side of
    # THRESHOLD by a hair and every frame carried a stray pixel on one bird
    # that its twin lacked. The mark is a mirrored pair, so make that true by
    # construction. The axis column is never lit (asserted at import).
    half = BIRD_W // 2
    grid[:, BIRD_W - half:] = np.fliplr(grid[:, :half])
    return grid


def draw_frame(angle, tick, steam=True, eye=True):
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 0, 0))
    px = img.load()

    def put(col, row, color):
        y = row + TOP_MARGIN
        if 0 <= y < CANVAS_H and 0 <= col < BIRD_W:
            px[OX + col, y] = color

    grid = bird_bitmap(angle)
    rows, cols = grid.shape
    legs = {LEG_COL + i for i in range(LEG_W)}
    legs |= {MIRROR - c for c in legs}
    for y in range(rows):
        for x in range(cols):
            if not grid[y, x]:
                continue
            # Shade the shape's lower edge -- but never in the leg columns.
            # Darkening the belly directly above a leg re-creates the detached
            # look the 2px legs were widened to fix.
            bottom = y + 1 >= rows or not grid[y + 1, x]
            put(x, y, SHADOW if (bottom and x not in legs) else CORAL)

    if eye:                                     # one eye per bird; a roosting
        holes = _holes(grid)                    # flamingo has its eyes shut
        for half in (range(MIRROR // 2), range(MIRROR // 2, cols)):
            lit = [(int(r), int(c)) for c in half for r in np.where(holes[:, c])[0]]
            if lit:
                put(min(lit)[1], min(lit)[0], EYE)

    # Perch line first, legs over it: drawn the other way round its dark
    # pixel lands on top of the leg at any crossing and severs it.
    for col in BAR_COLS:                                # perch line
        put(col, BAR_ROW, DARK)
        put(MIRROR - col, BAR_ROW, DARK)

    for i in range(LEG_W):                              # legs
        for row in LEG_ROWS:
            put(LEG_COL + i, row, CORAL)
            put(MIRROR - LEG_COL - i, row, CORAL)
    for i in range(FOOT_W):                             # feet
        put(LEG_COL + i, FOOT_ROW, CORAL)
        put(MIRROR - LEG_COL - i, FOOT_ROW, CORAL)

    for row, cols in CUP.items():                       # the two espresso cups
        for col in cols:
            put(col, row, GOLD)
            put(MIRROR - col, row, GOLD)

    if not steam:              # machines off -- no steam when the shop is shut
        return img

    n = len(STEAM_WAVE)
    for k in range(STEAM_LEN):                          # steam off the crema
        wave = STEAM_WAVE[(k + tick) % n]
        put(STEAM_COL + wave, STEAM_BASE_ROW - k, STEAM[k])
        wave_r = STEAM_WAVE[(k + tick + RIGHT_STEAM_PHASE) % n]
        put(MIRROR - (STEAM_COL + wave_r), STEAM_BASE_ROW - k, STEAM[k])
    return img


def zed_overlay(step):
    """The 'z's, at the heights they have drifted to, fading as they climb."""
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    px = img.load()
    m = MIRROR // 2
    for offset in Z_OFFSETS:
        i = (step + offset) % Z_ROWS
        row = (Z_ROWS - 1) - i + TOP_MARGIN + Z_FLOOR
        color = ZED[i] + (255,)
        for col in (m - 1, m, m + 1):                   # top and bottom bars
            for r in (row, row + 2):
                if 0 <= r < CANVAS_H:
                    px[OX + col, r] = color
        if 0 <= row + 1 < CANVAS_H:                     # the diagonal
            px[OX + m, row + 1] = color
    return img


def encode(img):
    buf = io.BytesIO()
    if img.mode == "RGBA":
        img.save(buf, "PNG", optimize=True)      # the z overlays keep alpha
    else:
        img.convert("P", palette=Image.ADAPTIVE, colors=16).save(
            buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


TEMPLATE = '''"""Kaleidoscope Coffee -- the shop's flamingo mark, animated.

Two mirrored flamingos lean in toward each other over a pair of espresso cups
while steam curls off the crema. A short seamless loop by design: a Tidbyt
only buffers a few seconds of a pushed animation and replays that chunk, so
the whole cycle fits inside the buffer and frame {last} flows back into 0.

Outside shop hours they sleep: heads folded back over their bodies, the
machines off so no steam, and a pair of "z"s drifting up between them. A
closed card with no motion at all would read as a crashed display rather than
a shut shop.

That choice is made HERE, at render time, so a plain re-push always puts up
the right thing without touching any code. It is also why this app is pushed
every fifteen minutes even though its artwork never changes: a pushed WebP is
frozen until it is replaced, so the cadence is what bounds how stale the card
can be at an 8am open or a 5pm close.

Frames are generated by make_frames.py -- edit the constants there and re-run,
don't hand-edit the blobs below.
"""

load("render.star", "render")
load("encoding/base64.star", "base64")
load("time.star", "time")

WORDMARK = "KALEIDOSCOPE"
WORDMARK_COLOR = "{wordmark_color}"
DELAY_MS = {delay}
TZ = "{tz}"

OPEN_HOUR = {open_hour}
CLOSE_HOUR = {close_hour}

FRAMES = [
{frames}
]

# Asleep: one still frame, plus a "z" that climbs one step every {z_hold}
# frames. Held as separate images indexed by ZEDS_SEQ rather than as 48
# near-identical frames.
SLEEP = "{sleep}"
ZEDS = [
{zeds}
]
ZEDS_SEQ = {zeds_seq}

def is_open(now):
    # There is no weekday attribute on a pixlet time; format("Mon") is how you
    # get one. An unrecognised key would fall back to OPEN_HOUR and read as
    # "shut all day", so the generator asserts the table's keys.
    close = CLOSE_HOUR.get(now.format("Mon"), OPEN_HOUR)
    return now.hour >= OPEN_HOUR and now.hour < close

def main(config):
    # `pixlet render ... state=asleep` forces the closed card, for previewing
    # without waiting for closing time.
    now = time.now().in_location(TZ)
    state = config.str("state", "")
    awake = is_open(now) if state not in ("awake", "asleep") else state == "awake"

    if awake:
        art = render.Animation(
            children = [render.Image(src = base64.decode(f)) for f in FRAMES],
        )
    else:
        art = render.Stack(
            children = [
                render.Image(src = base64.decode(SLEEP)),
                render.Animation(
                    children = [
                        render.Image(src = base64.decode(ZEDS[i]))
                        for i in ZEDS_SEQ
                    ],
                ),
            ],
        )

    return render.Root(
        delay = DELAY_MS,
        child = render.Column(
            children = [
                art,
                render.Box(width = {canvas_w}, height = {gap_rows}),
                # Box, not Row: a Row shrinks to fit its child, so main_align
                # has no slack to centre within and the wordmark sits flush
                # left. A fixed-width Box centres its child on both axes.
                # Height {text_rows}, not 5 -- tom-thumb inks 5 rows but the
                # widget is 6 tall, and a 5px box clips every glyph's bottom.
                render.Box(
                    width = {canvas_w},
                    height = {text_rows},
                    child = render.Text(
                        content = WORDMARK,
                        font = "tom-thumb",
                        color = WORDMARK_COLOR,
                    ),
                ),
            ],
        ),
    )
'''


def main():
    n = len(BEATS)
    frames = [draw_frame(NOD[BEATS[t]], t) for t in range(n)]

    # The device replays a buffered chunk on repeat, so the wrap has to be a
    # legal step. Render the hypothetical frame after the last one and require
    # it to be frame 0 exactly -- the guarantee every future tune to BEATS or
    # the steam wave has to keep.
    assert draw_frame(NOD[BEATS[0]], n).tobytes() == frames[0].tobytes(), (
        "loop is not seamless: frame %d does not wrap onto frame 0" % (n - 1))
    assert 13 in CUP[BAR_ROW], (
        "the perch line must meet the cup handle: BAR_ROW %d is not the cup "
        "row carrying column 13" % BAR_ROW)
    assert n % (Z_ROWS * Z_HOLD) == 0, (
        "the z drift (%d steps x %d frames) must divide the %d-frame loop"
        % (Z_ROWS, Z_HOLD, n))

    blobs = [encode(f) for f in frames]
    sleep = encode(draw_frame(SLEEP_ANGLE, 0, steam=False, eye=False))
    zeds = [encode(zed_overlay(i)) for i in range(Z_ROWS)]

    OUT_STAR.write_text(TEMPLATE.format(
        frames=",\n".join('    "%s"' % b for b in blobs),
        sleep=sleep,
        zeds=",\n".join('    "%s"' % b for b in zeds),
        zeds_seq=repr([(i // Z_HOLD) % Z_ROWS for i in range(n)]),
        z_hold=Z_HOLD,
        open_hour=OPEN_HOUR,
        close_hour=repr(CLOSE_HOUR),
        wordmark_color="#%02X%02X%02X" % WORDMARK_COLOR,
        delay=DELAY_MS,
        last=n - 1,
        tz=TIMEZONE,
        canvas_w=CANVAS_W,
        gap_rows=GAP_ROWS,
        text_rows=TEXT_ROWS,
    ))
    print("%d frames (%dKB) + sleep  ->  %s"
          % (n, sum(len(b) for b in blobs) // 1024, OUT_STAR))


if __name__ == "__main__":
    main()
