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

# ---------------------------------------------------------------- costumes
# Seasonal dress. Everything is anchored to the HEAD's own downscaled bitmap
# rather than to fixed coordinates, so a costume rides the nod instead of
# floating where the head used to be. Colours are deliberately not coral: at
# this size a costume only reads if it contrasts with the bird wearing it.
SANTA_RED = (198, 40, 34)
SNOW = (238, 236, 232)
PINK = (255, 95, 162)
YELLOW = (255, 211, 77)
BLUE = (59, 110, 245)
GREEN = (47, 190, 76)
PURPLE = (154, 77, 224)      # never black -- the background is black
CRIMSON = (212, 33, 61)      # Polish flag red, kept distinct from Santa's
CARAMEL = (176, 123, 54)     # a true pilgrim brown would vanish
UNLIT = (0, 0, 0)            # only ever inside a lit shape, never on black
LEI_PETALS = [PINK, YELLOW]  # hibiscus, frangipani
PLAIN, SANTA, LEI = "plain", "santa", "lei"
NEWYEAR, VALENTINE, STPAT, EASTER = "newyear", "valentine", "stpat", "easter"
POLISH, JULY4, HALLOWEEN = "polish", "july4", "halloween"
MARATHON, THANKSGIVING = "marathon", "thanksgiving"

# Occasions that move around the calendar, resolved to real dates here rather
# than recomputed in Starlark, where the arithmetic would be easy to get subtly
# wrong and impossible to test. Regenerate by re-running this script; extend
# MOVABLE_YEARS before the table runs out.
MOVABLE_YEARS = range(2026, 2041)


def _easter(year):
    """Gregorian Easter -- Meeus/Jones/Butcher."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    return datetime.date(year, month, ((h + l - 7 * m + 114) % 31) + 1)


def _nth_weekday(year, month, weekday, n):
    """The nth <weekday> of a month; weekday 0=Monday per date.weekday()."""
    first = datetime.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + datetime.timedelta(days=offset + 7 * (n - 1))


def _movable():
    out = {}
    for y in MOVABLE_YEARS:
        out[_easter(y).isoformat()] = EASTER
        # Thanksgiving: fourth Thursday of November.
        out[_nth_weekday(y, 11, 3, 4).isoformat()] = THANKSGIVING
        # The NYC Marathon runs the first Sunday in November, and it is one of
        # the shop's biggest days of the year.
        out[_nth_weekday(y, 11, 6, 1).isoformat()] = MARATHON
    return out


MOVABLE = _movable()

# (start_MMDD, end_MMDD, costume). First match wins, so a narrow occasion must
# be listed before any broad season it sits inside.
WINDOWS = [
    (1231, 101, NEWYEAR),      # wraps the year boundary
    (1201, 1230, SANTA),       # ...so Santa yields to it on the 31st
    (1027, 1031, HALLOWEEN),
    (704, 704, JULY4),         # inside the lei window, so it must precede it
    (503, 503, POLISH),        # Polish Constitution Day -- Greenpoint's own
    (317, 317, STPAT),
    (214, 214, VALENTINE),
    (601, 831, LEI),
]
STEAM_WAVE = [0, 0, 1, 1, 0, 0, -1, -1]   # length 8 divides 48 -> seamless
RIGHT_STEAM_PHASE = 4              # desync the two cups; mirrored steam
                                   # looks mechanical rather than alive

# Sleep. One "z" drifting up the corridor between the birds -- a card with no
# motion at all reads as a crashed display rather than a closed shop, and this
# is the quietest motion that still says something.
Z_ROWS = 8                         # eight steps of climb
Z_FLOOR = 3                        # ...ending here, not at the panel edge. The
                                   # valentine heart and the easter egg are
                                   # single centred elements in the same three-
                                   # column corridor, and the z is drawn last,
                                   # so a z climbing to row 0 painted straight
                                   # through them. Reordering the stack only
                                   # swaps which mark gets holes punched in it.
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


def _downscale(gray):
    """Source-resolution layer -> the sprite grid, thresholded."""
    im = gray.crop((0, 0, SRC_W, LEG_TRIM))
    small = im.resize((BIRD_W, round(LEG_TRIM * BIRD_H / COMPACT_H)), Image.LANCZOS)
    grid = np.zeros((BIRD_H, BIRD_W), dtype=bool)
    s = np.array(small) > THRESHOLD
    grid[:s.shape[0], :] = s
    return grid


_HEAD_CACHE = {}


def head_bitmap(angle):
    """The left bird's head+neck alone, so costumes can anchor to it."""
    if angle not in _HEAD_CACHE:
        hl = HEAD_L.rotate(-angle, resample=Image.BICUBIC, center=(PIVOT_X, PIVOT_Y))
        _HEAD_CACHE[angle] = _downscale(hl)
    return _HEAD_CACHE[angle]


def _anchor(head):
    """Where the skull is right now: top row, its column span, its centre."""
    rows = np.where(head.any(axis=1))[0]
    top = int(rows.min())
    cols = np.where(head[top])[0]
    c0, c1 = int(cols.min()), int(cols.max())
    return top, c0, c1, (c0 + c1) // 2


def _span(a, b, row, color):
    return [(c, row, color) for c in range(a, b + 1)]


def santa_hat(head):
    """Red cone, white brim, pom lolling back off the skull.

    Every hat here replaces the top of the skull rather than sitting above
    it -- which is where a hat goes anyway, and is the only option: the head
    already reaches the first row of the canvas, leaving exactly one row
    (top-1) to poke into. Rows top+3..top+5 are the beak and eye and are
    never painted over, or the bird stops reading as a flamingo.
    """
    top, c0, c1, _ = _anchor(head)
    return ([(c0 - 1, top - 1, SNOW)]
            + [(c, top - 1, SANTA_RED) for c in (c0, c0 + 1)]
            + _span(c0, c1, top, SANTA_RED)
            + _span(c0 - 1, c1 + 1, top + 1, SNOW)), []


def party_hat(head):
    """New Year: a tapering cone with a gold knob, and actual confetti.

    Confetti is meant to be single-pixel noise -- that is what confetti is --
    and it rides the nod, which reads as stuck to the bird rather than wrong.
    """
    top, c0, c1, cm = _anchor(head)
    return ([(cm, top - 1, GOLD)]
            + _span(c0 + 1, c0 + 3, top, BLUE)
            + _span(c0, c1, top + 1, BLUE)
            + [(c0 - 3, top, YELLOW), (c0 - 4, top + 3, PINK),
               (c0 - 2, top + 5, SNOW), (c1 + 2, top + 2, YELLOW)]), []


def heart(head):
    """Valentine's: ONE heart between the two heads, not one per bird.

    Three wide and confined to rows -1..1, because the gap between the heads
    narrows from nine columns at rest to three at full lean. At full lean the
    crowns just touch its lobes, which reads as nuzzling.
    """
    m = MIRROR // 2
    return [], ([(m - 1, -1, PINK), (m + 1, -1, PINK)]
                + _span(m - 1, m + 1, 0, PINK)
                + _span(m - 1, m + 1, 1, PINK)
                + [(m, 2, PINK)])


def leprechaun_hat(head):
    """St Patrick's: Santa's proven geometry, one saturated hue, gold buckle."""
    top, c0, c1, cm = _anchor(head)
    crown = [(c, top, GREEN) for c in range(c0, c1 + 1) if c != cm]
    return (_span(c0, c1, top - 1, GREEN) + crown + [(cm, top, GOLD)]
            + _span(c0 - 1, c1 + 1, top + 1, GREEN)), []


def easter_egg(head):
    """Easter: a decorated egg between the birds, not a hat.

    Bunny ears were tried first and abandoned: three rows is not enough
    height for two prongs to separate, so they read as a notched white crown
    rather than as ears. The centred slot the heart uses is free, an egg is
    as iconic as ears, and white-with-a-band has far more contrast than
    anything wearable at this size.
    """
    m = MIRROR // 2
    return [], ([(m, -1, SNOW)]
                + _span(m - 1, m + 1, 0, SNOW)
                + _span(m - 1, m + 1, 1, PINK)
                + _span(m - 1, m + 1, 2, SNOW))


def uncle_sam_hat(head):
    """Independence Day: striped crown, blue band, wide white brim.

    The stripes are two rows tall so they read as stripes rather than as a
    row of noise -- the same lesson the lei taught.
    """
    top, c0, c1, _ = _anchor(head)
    # Derived from the span, never a fixed five columns: the skull is 5 wide at
    # the four awake angles but 4 wide asleep, and hardcoded offsets there had
    # later writes clobber both white stripes and leave a hole in the crown.
    stripes = []
    for row in (top - 1, top):
        stripes += [(c, row, SANTA_RED if (c - c0) % 2 == 0 else SNOW)
                    for c in range(c0, c1 + 1)]
    return (stripes + _span(c0 - 1, c1 + 1, top + 1, BLUE)
            + _span(c0 - 2, c1 + 2, top + 2, SNOW)), []


def witch_hat(head):
    """Halloween: purple, never black, tip bent back over the bird's rear.

    The 1-3-5-9 taper with an off-centre apex is the witch-hat gestalt; the
    gold band gives the dim purple a bright internal edge so the hat parts
    from both the black sky and the coral face.
    """
    top, c0, c1, _ = _anchor(head)
    return ([(c0 + 1, top - 1, PURPLE)]
            + _span(c0, c0 + 2, top, PURPLE)
            + [(c0, top + 1, PURPLE), (c1, top + 1, PURPLE)]
            + _span(c0 + 1, min(c0 + 3, c1 - 1), top + 1, GOLD)
            + _span(c0 - 2, c1 + 2, top + 2, PURPLE)), []


def pilgrim_hat(head):
    """Thanksgiving: caramel capotain with a gold band and a buckle glint.

    A true pilgrim brown vanishes against black, and caramel is only about
    1.6:1 in value against coral, so the crown alone reads as a warm smudge.
    A gold band did not rescue it -- gold on caramel is warm on warm. The
    white band does, by putting the set's highest-contrast colour across the
    middle of the hat, with the gold kept for the buckle alone.
    """
    top, c0, c1, cm = _anchor(head)
    band = [(c, top + 1, SNOW) for c in range(c0 - 1, c1 + 2) if c != cm]
    return (_span(c0, c1, top - 1, CARAMEL) + _span(c0, c1, top, CARAMEL)
            + band + [(cm, top + 1, GOLD)]        # buckle
            + _span(c0 - 2, c1 + 2, top + 2, CARAMEL)), []


def polish_cap(head):
    """3 May: white over red, in that order, because that IS the flag."""
    top, c0, c1, cm = _anchor(head)
    return ([(cm, top - 1, SNOW)] + _span(c0, c1, top, SNOW)
            + _span(c0 - 1, c1 + 1, top + 1, CRIMSON)), []


def race_bib(head):
    """Marathon: a bib pinned to the chest -- anchored to the body, not the
    head, so it does not ride the nod.

    The largest single costume element in the set. The unlit number strokes
    work here precisely because they sit inside a white field: black fails on
    black, but it is maximum contrast inside a lit shape.
    """
    out = _span(8, 12, 12, BLUE)
    for row in (13, 14, 15):
        out += _span(8, 12, row, SNOW)
    out += [(c, r, UNLIT) for c in (9, 11) for r in (13, 14)]
    return out, []


def lei(head):
    """A flower garland round the neck, with a bloom at the ear.

    Two rows, not one: three pixels of alternating colour on a 3px neck read
    as noise rather than as an object. And one hue, not two -- alternating
    colours inside a shape this small dissolve it again. The colour play
    belongs in the bloom, which is big enough to hold it.
    """
    rows = np.where(head.any(axis=1))[0]
    top, base = int(rows.min()), int(rows.max())
    out = []
    for row in (base - 1, base):
        cols = np.where(head[row])[0]
        out += _span(int(cols.min()), int(cols.max()), row, PINK)
    ear = int(np.where(head[top + 2])[0].min())
    out += [(ear, top + 2, PINK), (ear + 1, top + 2, PINK),
            (ear, top + 3, PINK), (ear + 1, top + 3, YELLOW)]
    return out, []


COSTUMES = {
    PLAIN: lambda head: ([], []),
    SANTA: santa_hat,
    LEI: lei,
    NEWYEAR: party_hat,
    VALENTINE: heart,
    STPAT: leprechaun_hat,
    EASTER: easter_egg,
    JULY4: uncle_sam_hat,
    HALLOWEEN: witch_hat,
    THANKSGIVING: pilgrim_hat,
    POLISH: polish_cap,
    MARATHON: race_bib,
}


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


def draw_frame(angle, tick, steam=True):
    img = Image.new("RGB", (CANVAS_W, CANVAS_H), (0, 0, 0))
    px = img.load()

    def put(col, row, color):
        y = row + TOP_MARGIN
        if 0 <= y < CANVAS_H and 0 <= col < BIRD_W:
            px[OX + col, y] = color

    for y, row in enumerate(bird_bitmap(angle)):
        for x, on in enumerate(row):
            if on:
                put(x, y, CORAL)

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


def costume_overlay(angle, season):
    """One costume, one pose, on transparent film.

    Costumes are stacked over the art rather than drawn into it because they
    depend only on the POSE -- of which there are four -- while the art
    depends on the frame, of which there are 48. Baking each costume into a
    full 48-frame set costs ~19KB of base64 apiece and does not scale to a
    wardrobe; four transparent overlays cost a few hundred bytes.
    """
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 0))
    px = img.load()

    def put(col, row, color):
        y = row + TOP_MARGIN
        if 0 <= y < CANVAS_H and 0 <= col < BIRD_W:
            px[OX + col, y] = color + (255,)

    mirrored, absolute = COSTUMES[season](head_bitmap(angle))
    for col, row, color in mirrored:
        put(col, row, color)                    # left bird
        put(MIRROR - col, row, color)           # and its mirror
    for col, row, color in absolute:            # single centred elements
        if 0 <= row + TOP_MARGIN < CANVAS_H and 0 <= OX + col < CANVAS_W:
            px[OX + col, row + TOP_MARGIN] = color + (255,)
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
        img.save(buf, "PNG", optimize=True)      # costume overlays keep alpha
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
machines off so no steam, and a "z" drifting up between them. A closed card
with no motion at all would read as a crashed display rather than a shut
shop.

They also dress for the occasion. Both the costume and the sleeping are
decided HERE, at render time, so a plain re-push always puts up the right
thing without touching any code. That is also why this app is pushed every
fifteen minutes even though its artwork never changes: a pushed WebP is
frozen until it is replaced, so the cadence is what bounds how stale the card
can be at an 8am open or a 5pm close.

Costumes are transparent overlays stacked on the art, keyed by POSE rather
than by frame: a costume only cares which way the head is turned, and there
are four head positions awake plus one asleep, against 48 frames.

Frames are generated by make_frames.py -- edit the constants there and re-run,
don't hand-edit the blobs below.
"""

load("render.star", "render")
load("encoding/base64.star", "base64")
load("time.star", "time")

WORDMARK = "KALEIDOSCOPE"
CORAL = "{coral}"
DELAY_MS = {delay}
TZ = "{tz}"

OPEN_HOUR = {open_hour}
CLOSE_HOUR = {close_hour}

FRAMES = [
{frames}
]

# Which head position each frame wears, so an overlay can follow the nod.
POSES = {poses}

# Asleep: one still frame, plus a "z" that climbs one step every {z_hold}
# frames. Held as separate images indexed by ZEDS_SEQ rather than as 48
# near-identical frames.
SLEEP = "{sleep}"
ZEDS = [
{zeds}
]
ZEDS_SEQ = {zeds_seq}
SLEEP_POSE = {sleep_pose}

WARDROBE = {{
{wardrobe}
}}

# Occasions that move around the calendar -- Easter, Thanksgiving, the NYC
# Marathon -- resolved to real dates ahead of time. Computing them in Starlark
# would be a lot of arithmetic to get subtly wrong; a table is checkable.
MOVABLE = {{
{movable}
}}

# Fixed-date windows, first match wins, so narrow occasions are listed before
# the broad seasons they sit inside.
WINDOWS = [
{windows}
]

def pick(now):
    # Integer date keys, not formatted strings: Starlark's %% has no width
    # specifiers, so "%02d" is a runtime error rather than a zero-padded day.
    key = now.year * 10000 + now.month * 100 + now.day
    if key in MOVABLE:
        return MOVABLE[key]
    md = now.month * 100 + now.day
    for w in WINDOWS:
        start, end, name = w[0], w[1], w[2]
        if start <= end:
            if md >= start and md <= end:
                return name
        elif md >= start or md <= end:      # a window that wraps new year
            return name
    return "plain"

def is_open(now):
    # There is no weekday attribute on a pixlet time; format("Mon") is how you
    # get one.
    close = CLOSE_HOUR.get(now.format("Mon"), OPEN_HOUR)
    return now.hour >= OPEN_HOUR and now.hour < close

def main(config):
    # `pixlet render ... costume=santa state=asleep` forces either, for
    # previewing without waiting for the calendar or for closing time.
    now = time.now().in_location(TZ)

    forced = config.str("costume", "")
    name = forced if forced in WARDROBE else pick(now)
    # Undressed rather than broken, if a window ever names a costume that was
    # cut from the wardrobe. The generator asserts against this too.
    coat = WARDROBE.get(name, WARDROBE["plain"])

    state = config.str("state", "")
    awake = is_open(now) if state not in ("awake", "asleep") else state == "awake"

    if awake:
        art = [
            render.Animation(
                children = [
                    render.Image(src = base64.decode(f)) for f in FRAMES
                ],
            ),
            render.Animation(
                children = [
                    render.Image(src = base64.decode(coat[p])) for p in POSES
                ],
            ),
        ]
    else:
        art = [
            render.Image(src = base64.decode(SLEEP)),
            render.Image(src = base64.decode(coat[SLEEP_POSE])),
            render.Animation(
                children = [
                    render.Image(src = base64.decode(ZEDS[i])) for i in ZEDS_SEQ
                ],
            ),
        ]

    return render.Root(
        delay = DELAY_MS,
        child = render.Column(
            children = [
                render.Stack(children = art),
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
                        color = CORAL,
                    ),
                ),
            ],
        ),
    )
'''


def contact_sheet(path, scale=5):
    """A labelled sheet of every costume, so the README cannot drift."""
    tiles = []
    for name in COSTUMES:
        art = draw_frame(NOD[0], 0)
        card = Image.new("RGBA", (CANVAS_W, CANVAS_H), (0, 0, 0, 255))
        card.paste(art, (0, 0))
        card.alpha_composite(costume_overlay(NOD[0], name), (0, 0))
        crop = card.convert("RGB").crop((OX - 4, 0, OX + BIRD_W + 4, CANVAS_H))
        tiles.append((name, crop.resize(
            (crop.width * scale, crop.height * scale), Image.NEAREST)))

    cols = 4
    w, h = tiles[0][1].size
    rows = -(-len(tiles) // cols)
    sheet = Image.new("RGB", (cols * (w + 6), rows * (h + 14)), (12, 11, 10))
    draw = ImageDraw.Draw(sheet)
    for i, (name, tile) in enumerate(tiles):
        x, y = (i % cols) * (w + 6), (i // cols) * (h + 14)
        sheet.paste(tile, (x, y))
        draw.text((x + 3, y + h + 2), name, fill=(190, 186, 180))
    sheet.save(path)


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

    # A costume that paints the same pixel twice in different colours is not
    # expressing intent, it is a hardcoded offset that stopped fitting the
    # head -- which is exactly how the striped Uncle Sam crown came to render
    # as a solid block with a hole in it once the sleep pose made the skull a
    # column narrower. UNLIT is exempt: the marathon bib deliberately knocks
    # its numbers out of a field it has already laid down.
    for name, costume in COSTUMES.items():
        for angle in list(NOD) + [SLEEP_ANGLE]:
            painted = {}
            mirrored, absolute = costume(head_bitmap(angle))
            strokes = [(c, r, k) for c, r, k in mirrored]
            strokes += [(MIRROR - c, r, k) for c, r, k in mirrored]
            strokes += list(absolute)
            for col, row, color in strokes:
                prev = painted.get((col, row))
                assert prev in (None, color) or color == UNLIT, (
                    "%s at angle %d repaints (%d,%d) from %s to %s"
                    % (name, angle, col, row, prev, color))
                painted[(col, row)] = color

    # The sleeping z's climb the same narrow corridor the centred costumes
    # occupy, and they are drawn last, so any overlap silently erases the
    # costume rather than compositing with it.
    zed_lit = set()
    for step in range(Z_ROWS):
        a = np.array(zed_overlay(step).split()[3])
        zed_lit |= {(int(x), int(y)) for y, x in np.argwhere(a > 0)}
    for name in COSTUMES:
        a = np.array(costume_overlay(SLEEP_ANGLE, name).split()[3])
        lit = {(int(x), int(y)) for y, x in np.argwhere(a > 0)}
        clash = sorted(lit & zed_lit)
        assert not clash, (
            "the sleeping z's would paint over the %s costume at %s"
            % (name, clash[:6]))

    named = set(MOVABLE.values()) | {w[2] for w in WINDOWS}
    missing = named - set(COSTUMES)
    assert not missing, (
        "the calendar names costumes that do not exist: %s" % sorted(missing))

    blobs = [encode(f) for f in frames]
    wardrobe = {name: [encode(costume_overlay(a, name))
                       for a in list(NOD) + [SLEEP_ANGLE]]
                for name in COSTUMES}
    sleep = encode(draw_frame(SLEEP_ANGLE, 0, steam=False))
    zeds = [encode(zed_overlay(i)) for i in range(Z_ROWS)]
    assert n % (Z_ROWS * Z_HOLD) == 0, (
        "the z drift (%d steps x %d frames) must divide the %d-frame loop"
        % (Z_ROWS, Z_HOLD, n))

    OUT_STAR.write_text(TEMPLATE.format(
        frames=",\n".join('    "%s"' % b for b in blobs),
        poses=repr(list(BEATS)),
        sleep=sleep,
        zeds=",\n".join('    "%s"' % b for b in zeds),
        zeds_seq=repr([(i // Z_HOLD) % Z_ROWS for i in range(n)]),
        sleep_pose=SLEEP_POSE,
        z_hold=Z_HOLD,
        open_hour=OPEN_HOUR,
        close_hour=repr(CLOSE_HOUR),
        wardrobe=",\n".join(
            '    "%s": [\n%s\n    ]' % (
                name, ",\n".join('        "%s"' % b for b in coats))
            for name, coats in sorted(wardrobe.items())),
        movable="\n".join('    %d: "%s",  # %s' % (
                               int(d.replace("-", "")), c, d)
                           for d, c in sorted(MOVABLE.items())),
        windows=",\n".join('    (%d, %d, "%s")' % w for w in WINDOWS),
        coral="#%02X%02X%02X" % CORAL,
        delay=DELAY_MS,
        last=n - 1,
        tz=TIMEZONE,
        canvas_w=CANVAS_W,
        gap_rows=GAP_ROWS,
        text_rows=TEXT_ROWS,
    ))
    contact_sheet(HERE / "costumes.png")

    art = sum(len(b) for b in blobs) // 1024
    coats = sum(len(b) for v in wardrobe.values() for b in v) // 1024
    print("%d frames (%dKB) + %d costumes (%dKB)  ->  %s"
          % (n, art, len(wardrobe), coats, OUT_STAR))


if __name__ == "__main__":
    main()
