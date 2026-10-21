"""Kaleidoscope closing card: the shop's name, the last day, a thank you.

Three pages per cycle: the logo's "KALEIDOSCOPE / COFFEE" wordmark (redrawn
for the panel by make_frames.py), which a cream glint crosses once, the last
day with a countdown, and a thank you. The countdown is worked out here from the date, so the daily push is
what keeps it right. On the last day it says so; from the day after, the
date page drops out and the card is just the wordmark and the thank you --
no redeploy needed.

The whole cycle is held under the device's 15s app cut-off (see the news
card's docstring): 80 + 2 x 90 frames at 50ms = 13s. The 50ms frame is for
the glint's sake; the text pages just hold twice as many frames.

Preview a date with `pixlet render closing/closing.star today=2026-11-14`.
"""

load("encoding/base64.star", "base64")
load("render.star", "render")
load("time.star", "time")

DELAY_MS = 50
WORD_FRAMES = 80
SHINE_AT = 16      # the name sits still 0.8s before the glint crosses it
PAGE_FRAMES = 90
TZ = "America/New_York"
LAST_DAY = "2026-11-15"

CORAL = "#F25A3C"
GOLD = "#ECBE5E"
CREAM = "#FFEED6"
GP_GREEN = "#57AB5A"

WORDMARK = "iVBORw0KGgoAAAANSUhEUgAAAD8AAAATCAIAAACoU0LFAAAA6ElEQVR4nO1WwRHEIAgkTN6pyEosMJWkIivIwxmGEYLAnTf3yL7cFXQTA2ZrtQDAcV4A0GqhAQBwncZ8tos0O+hD8JPipKqCNCJ1eB5IoSfydKnYVG4tFZSOnTjOS42XoqpwUVLnCmhE2EgfSyL36RyULye3gRNq8URzCcgn1LLzr5U24UkZsjrdObffh9p5pBW72tQtjJ5mm8FpXA7dilGLMsCOf/Hii9gSOaG7PUSjTsJVG7rbV2Ofh2iQvWKwbjSTKfVjVcf0/41J6scq97/B2tsqR/1Ium+1fFKvMj338YTd/9XdfgOnBcGLK9zNPwAAAABJRU5ErkJggg=="

SHINE = [
    "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",
]

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

def name_page(src):
    return render.Box(width = 64, height = 32, child = render.Image(src = base64.decode(src)))

def main(config):
    days = days_left(config)
    wordmark = name_page(WORDMARK)
    frames = [wordmark] * SHINE_AT + [name_page(src) for src in SHINE]
    frames.extend([wordmark] * (WORD_FRAMES - len(frames)))
    if days >= 0:
        frames.extend([date_page(days)] * PAGE_FRAMES)
    # the heart beats twice a second: big for 6 frames, small for 4
    big = thanks_page(HEARTS[0])
    small = thanks_page(HEARTS[1])
    frames.extend([big if i % 10 < 6 else small for i in range(PAGE_FRAMES)])
    return render.Root(
        delay = DELAY_MS,
        show_full_animation = True,
        child = render.Animation(children = frames),
    )
