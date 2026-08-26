"""Hyper-local Greenpoint news for Tidbyt (64x32).

Merges the two feeds that actually cover the neighborhood — Greenpointers
(greenpointers.com) and Brooklyn Paper's Greenpoint tag — sorts by
recency, and scrolls a rotating pair of stories in the proven
catalog-news layout (branded header + vertical marquee). Free RSS,
no API keys.

Pushed by GitHub Actions; the scrolling animation loops on-device
between pushes.
"""

load("http.star", "http")
load("render.star", "render")
load("time.star", "time")
load("xpath.star", "xpath")

FEEDS = [
    {"tag": "GPTRS", "url": "https://greenpointers.com/feed/"},
    {"tag": "BK PAPER", "url": "https://www.brooklynpaper.com/tag/greenpoint/feed/"},
]
PER_FEED = 3
CACHE_TTL_SECONDS = 600
ANIMATION_SPEED = 100  # ms per frame
TZ = "America/New_York"

GP_GREEN = "#1E7A33"
WHITE = "#FFFFFF"
HEADLINE = "#FFFFFF"
STORY = "#9AA0A6"
ACCENT_GOLD = "#D9A21B"
HEADER_H = 6

def strip_html(s):
    out = ""
    intag = False
    for ch in s.elems():
        if ch == "<":
            intag = True
        elif ch == ">":
            intag = False
        elif not intag:
            out += ch
    for a, b in [
        ("&amp;", "&"),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&quot;", "\""),
        ("&#039;", "'"),
        ("&#8217;", "'"),
        ("&#8216;", "'"),
        ("&#8220;", "\""),
        ("&#8221;", "\""),
        ("&#8211;", "-"),
        ("&#8212;", "-"),
        ("&#8230;", "..."),
        ("&#124;", "|"),
        ("&nbsp;", " "),
        ("’", "'"),
        ("‘", "'"),
        ("“", "\""),
        ("”", "\""),
        ("—", "-"),
        ("–", "-"),
        ("…", "..."),
    ]:
        out = out.replace(a, b)
    i = out.find("[ more")
    if i >= 0:
        out = out[:i]
    return " ".join(out.split())

def summarize(s):
    """First sentence (past a minimum length), else a word-boundary cut."""
    if len(s) <= 55:
        return s
    for i in range(20, min(len(s) - 1, 70)):
        if s[i] in (".", "!", "?") and s[i + 1] == " ":
            return s[:i + 1]
    cut = s[:70]
    last_space = cut.rfind(" ")
    if last_space > 35:
        cut = cut[:last_space]
    return cut + "..."

def ago(parsed):
    if parsed == None:
        return ""
    mins = int((time.now() - parsed).minutes)
    if mins < 1:
        return "JUST NOW"
    if mins < 60:
        return str(mins) + "M AGO"
    if mins < 60 * 24:
        return str(mins // 60) + "H AGO"
    return str(mins // (60 * 24)) + "D AGO"

def get_articles():
    items = []
    for feed in FEEDS:
        res = http.get(feed["url"], ttl_seconds = CACHE_TTL_SECONDS)
        if res.status_code != 200:
            continue
        doc = xpath.loads(res.body())
        for i in range(1, PER_FEED + 1):
            title = doc.query("//item[%d]/title" % i)
            description = doc.query("//item[%d]/description" % i)
            pub = doc.query("//item[%d]/pubDate" % i)
            if title == None:
                continue
            parsed = None
            if pub:
                parsed = time.parse_time(pub, "Mon, 02 Jan 2006 15:04:05 -0700")
            items.append({
                "title": strip_html(title),
                "description": summarize(strip_html(description or "")),
                "meta": feed["tag"] + " - " + ago(parsed) if parsed else feed["tag"],
                "ts": parsed.unix if parsed else 0,
            })
    if not items:
        return [{"title": "Greenpoint feeds unavailable", "description": "", "meta": "", "ts": 0}]
    return sorted(items, key = lambda a: a["ts"], reverse = True)

def render_header():
    return render.Box(
        width = 64,
        height = HEADER_H,
        color = GP_GREEN,
        child = render.Row(
            expanded = True,
            main_align = "center",
            cross_align = "center",
            children = [
                render.Text(content = "GREENPOINT NEWS", font = "tom-thumb", color = WHITE),
            ],
        ),
    )

def clip(s, n):
    if len(s) <= n:
        return s
    cut = s[:n]
    last_space = cut.rfind(" ")
    if last_space > n // 2:
        cut = cut[:last_space]
    return cut + "..."

def ticker_lane(article, font, color, lead_spaces, max_chars):
    return render.Marquee(
        width = 64,
        scroll_direction = "horizontal",
        child = render.Text(
            content = " " * lead_spaces + clip(article["title"], max_chars),
            font = font,
            color = color,
        ),
    )

def main(config):
    articles = get_articles()

    # three stories fit a full scroll under pixlet frame cap (smaller fonts); rotate the
    # visible trio each 10-minute push so all stories get airtime
    if len(articles) > 3:
        start = time.now().in_location(TZ).minute // 10 % len(articles)
        articles = [articles[(start + i) % len(articles)] for i in range(3)]

    a = [articles[i % len(articles)] for i in range(3)]

    # headlines only: top story big and white, the next two smaller in
    # gold and blue, each lane a staggered right-to-left crawl
    return render.Root(
        delay = 80,
        child = render.Column(
            children = [
                render_header(),
                ticker_lane(a[0], "tb-8", "#FFFFFF", 0, 36),
                render.Box(height = 1),
                ticker_lane(a[1], "tom-thumb", ACCENT_GOLD, 3, 44),
                render.Box(height = 1),
                ticker_lane(a[2], "tom-thumb", "#6FB7FF", 6, 44),
            ],
        ),
    )
