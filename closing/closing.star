"""Kaleidoscope closing card: the shop's name, the last day, a thank you.

Three pages per cycle: the logo's "KALEIDOSCOPE / COFFEE" wordmark (redrawn
for the panel by make_frames.py), the last day with a countdown, and a thank
you. The countdown is worked out here from the date, so the daily push is
what keeps it right. On the last day it says so; from the day after, the
date page drops out and the card is just the wordmark and the thank you --
no redeploy needed.

The whole cycle is held under the device's 15s app cut-off (see the news
card's docstring): 30 + 2 x 45 frames at 100ms = 12s.

Preview a date with `pixlet render closing/closing.star today=2026-11-14`.
"""

load("encoding/base64.star", "base64")
load("render.star", "render")
load("time.star", "time")

DELAY_MS = 100
WORD_FRAMES = 30
PAGE_FRAMES = 45
TZ = "America/New_York"
LAST_DAY = "2026-11-15"

CORAL = "#F25A3C"
GOLD = "#ECBE5E"
CREAM = "#FFEED6"
GP_GREEN = "#57AB5A"

WORDMARK = "iVBORw0KGgoAAAANSUhEUgAAAD8AAAATCAIAAACoU0LFAAAA6ElEQVR4nO1WwRHEIAgkTN6pyEosMJWkIivIwxmGEYLAnTf3yL7cFXQTA2ZrtQDAcV4A0GqhAQBwncZ8tos0O+hD8JPipKqCNCJ1eB5IoSfydKnYVG4tFZSOnTjOS42XoqpwUVLnCmhE2EgfSyL36RyULye3gRNq8URzCcgn1LLzr5U24UkZsjrdObffh9p5pBW72tQtjJ5mm8FpXA7dilGLMsCOf/Hii9gSOaG7PUSjTsJVG7rbV2Ofh2iQvWKwbjSTKfVjVcf0/41J6scq97/B2tsqR/1Ium+1fFKvMj338YTd/9XdfgOnBcGLK9zNPwAAAABJRU5ErkJggg=="

HEARTS = [
    "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAGCAIAAACAbBMhAAAAMElEQVR4nGNgYGD4X7Hgf8UCZAYjhEIDTJhCDAwMTIwdCWhCjB0JTBAKWQhFCbIFAI/kEDaIAhclAAAAAElFTkSuQmCC",
    "iVBORw0KGgoAAAANSUhEUgAAAAcAAAAGCAIAAACAbBMhAAAAJ0lEQVR4nGNgwAX+Vyz4X7EAmcGELAdnMzEwMDB2JMD5yGx0tdgBAIkEDmHLnNziAAAAAElFTkSuQmCC",
]

# --- end generated ---

def days_left(config):
    """Whole days from today (local) to LAST_DAY: 0 on the day, <0 after."""
    today = config.str("today", "")
    if today:
        now = time.parse_time(today, "2006-01-02", TZ)
    else:
        now = time.now().in_location(TZ)
    start = time.time(year = now.year, month = now.month, day = now.day, location = TZ)
    last = time.parse_time(LAST_DAY, "2006-01-02", TZ)

    # +12h absorbs the 23h/25h days around a DST change
    return (last.unix - start.unix + 43200) // 86400

def text(content, font, color, bold):
    if not bold:
        return render.Text(content = content, font = font, color = color)

    # the big font is a 1px stroke the panel's gutters thin out. Each glyph
    # is drawn twice, a pixel apart, so every upright is 2px; the shifted
    # copy makes each glyph 7px wide, so a space shrinks to 3px to keep
    # "SUN NOV 15" inside 64.
    glyphs = []
    for ch in content.elems():
        if ch == " ":
            glyphs.append(render.Box(width = 3, height = 1))
            continue
        t = render.Text(content = ch, font = font, color = color)
        glyphs.append(render.Stack(children = [t, render.Padding(pad = (1, 0, 0, 0), child = t)]))
    return render.Row(children = glyphs)

def line(content, font, color, bold = False):
    return render.Row(
        expanded = True,
        main_align = "center",
        children = [text(content, font, color, bold)],
    )

def page(lines):
    return render.Box(
        width = 64,
        height = 32,
        child = render.Column(
            expanded = True,
            main_align = "space_evenly",
            cross_align = "center",
            children = lines,
        ),
    )

def date_page(days):
    if days == 0:
        return page([
            line("TODAY IS OUR", "tom-thumb", CORAL),
            line("LAST DAY", "6x13", GOLD, bold = True),
            line("COME SAY BYE!", "tom-thumb", CREAM),
        ])
    left = "1 DAY LEFT" if days == 1 else "%d DAYS LEFT" % days
    return page([
        line("OUR LAST DAY", "tom-thumb", CORAL),
        line("SUN NOV 15", "6x13", GOLD, bold = True),
        line(left, "tom-thumb", CREAM),
    ])

def thanks_page(heart):
    return page([
        line("THANK YOU", "6x13", CREAM, bold = True),
        line("GREENPOINT", "tom-thumb", GP_GREEN),
        render.Image(src = base64.decode(heart)),
    ])

def main(config):
    days = days_left(config)
    wordmark = render.Box(width = 64, height = 32, child = render.Image(src = base64.decode(WORDMARK)))
    frames = [wordmark] * WORD_FRAMES
    if days >= 0:
        frames.extend([date_page(days)] * PAGE_FRAMES)
    # the heart beats twice a second: big for 3 frames, small for 2
    big = thanks_page(HEARTS[0])
    small = thanks_page(HEARTS[1])
    frames.extend([big if i % 5 < 3 else small for i in range(PAGE_FRAMES)])
    return render.Root(
        delay = DELAY_MS,
        show_full_animation = True,
        child = render.Animation(children = frames),
    )
