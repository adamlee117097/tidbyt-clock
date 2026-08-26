"""WNYC / Gothamist news for Tidbyt (64x32).

A close clone of the proven catalog NPR-news app layout — branded header
bar + vertically scrolling story list — pointed at Gothamist, the local
newsroom of WNYC (New York Public Radio). Free RSS, no API key.

Pushed by GitHub Actions; the scrolling animation loops on-device
between pushes.
"""

load("http.star", "http")
load("render.star", "render")
load("time.star", "time")
load("xpath.star", "xpath")

FEED_URL = "https://gothamist.com/feed"
CACHE_TTL_SECONDS = 600
ARTICLE_COUNT = 3
ANIMATION_SPEED = 100  # ms per frame
TZ = "America/New_York"

WNYC_RED = "#C8102E"
WHITE = "#FFFFFF"
HEADLINE = "#FFFFFF"
STORY = "#9AA0A6"
TIME_C = "#6E6E6E"
HEADER_H = 6
ACCENT_GOLD = "#D9A21B"

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
        ("&#8230;", "..."),
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

def format_time(timestamp):
    if not timestamp:
        return ""
    parsed = time.parse_time(timestamp, "Mon, 02 Jan 2006 15:04:05 -0700")
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
    res = http.get(FEED_URL, ttl_seconds = CACHE_TTL_SECONDS)
    if res.status_code != 200:
        return [{"title": "WNYC feed unavailable", "description": "", "pubDate": ""}]

    doc = xpath.loads(res.body())
    articles = []
    for i in range(1, ARTICLE_COUNT + 1):
        title = doc.query("//item[%d]/title" % i)
        description = doc.query("//item[%d]/description" % i)
        pub = doc.query("//item[%d]/pubDate" % i)
        if title == None:
            continue
        desc = strip_html(description or "")
        if len(desc) > 160:
            desc = desc[:160] + "..."
        articles.append({
            "title": strip_html(title),
            "description": desc,
            "pubDate": format_time(pub or ""),
        })
    if not articles:
        return [{"title": "No stories right now", "description": "", "pubDate": ""}]
    return articles

def render_header():
    return render.Box(
        width = 64,
        height = HEADER_H,
        color = WNYC_RED,
        child = render.Row(
            expanded = True,
            main_align = "space_between",
            cross_align = "center",
            children = [
                render.Padding(
                    pad = (1, 0, 0, 0),
                    child = render.Text(content = "WNYC", font = "tom-thumb", color = WHITE),
                ),
                render.Padding(
                    pad = (0, 0, 1, 0),
                    child = render.Text(content = "NYC NEWS", font = "tom-thumb", color = "#FFB3BE"),
                ),
            ],
        ),
    )

def render_articles(articles):
    elements = []
    for article in articles:
        elements.append(render.WrappedText(
            content = article["title"],
            width = 64,
            color = HEADLINE,
            font = "tb-8",
        ))
        if article["description"]:
            elements.append(render.Box(height = 1))
            elements.append(render.WrappedText(
                content = article["description"],
                width = 64,
                color = STORY,
                font = "tom-thumb",
            ))
        if article["pubDate"]:
            elements.append(render.Box(height = 1))
            elements.append(render.Text(
                content = article["pubDate"],
                color = ACCENT_GOLD,
                font = "tom-thumb",
            ))
        elements.append(render.Box(height = 2))
        elements.append(render.Box(width = 64, height = 1, color = "#3A0810"))
        elements.append(render.Box(height = 2))
    return elements

def main(config):
    articles = get_articles()
    return render.Root(
        delay = ANIMATION_SPEED,
        show_full_animation = True,
        child = render.Column(
            children = [
                render_header(),
                render.Marquee(
                    height = 32 - HEADER_H,
                    scroll_direction = "vertical",
                    offset_start = 32 - HEADER_H,
                    child = render.Column(
                        children = render_articles(articles),
                    ),
                ),
            ],
        ),
    )
