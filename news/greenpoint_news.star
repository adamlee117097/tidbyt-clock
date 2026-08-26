"""Hyper-local Greenpoint news for Tidbyt (64x32).

Merges the two feeds that actually cover the neighborhood — Greenpointers
(greenpointers.com) and Brooklyn Paper's Greenpoint tag — sorts by
recency, and vertically scrolls three stories per cycle (rotating by
wall-clock so every story gets airtime): white headline, gray one-line
summary, source tag colored per feed. A story fresher than an hour goes
breaking-news yellow with +++ brackets. Free RSS, no API keys.

Pushed by GitHub Actions; the scrolling animation loops on-device
between pushes.
"""

load("http.star", "http")
load("render.star", "render")
load("time.star", "time")
load("xpath.star", "xpath")

FEEDS = [
    {"tag": "GPTRS", "url": "https://greenpointers.com/feed/", "accent": "#57AB5A"},
    {"tag": "BK PAPER", "url": "https://www.brooklynpaper.com/tag/greenpoint/feed/", "accent": "#6BB1FF"},
]
PER_FEED = 3
SHOW_PER_CYCLE = 3
CACHE_TTL_SECONDS = 600
ANIMATION_SPEED = 100  # ms per frame
TZ = "America/New_York"
BREAKING_SECS = 3600
MAX_AGE_DAYS = 3

GP_GREEN = "#1E7A33"
GOLD = "#FFB000"
WHITE = "#FFFFFF"
STORY = "#B8BEC6"
BREAKING = "#FFE100"
HAIRLINE = "#3A3A3A"
HEADER_H = 6

def strip_html(s):
    # Tag mode only opens on "<" followed by a letter or "/": a bare "<"
    # in prose ("Rents < $2K") must not swallow the rest of the line.
    out = ""
    intag = False
    n = len(s)
    for i in range(n):
        ch = s[i]
        if intag:
            if ch == ">":
                intag = False
        elif ch == "<" and i + 1 < n and (s[i + 1].isalpha() or s[i + 1] == "/"):
            intag = True
        else:
            out += ch

    # Specific entities first; bare &amp; LAST so double-encoded
    # sequences don't decode into tag-eating angle brackets.
    for a, b in [
        ("&#039;", "'"),
        ("&#038;", "&"),
        ("&#8217;", "'"),
        ("&#8216;", "'"),
        ("&#8220;", "\""),
        ("&#8221;", "\""),
        ("&#8211;", "-"),
        ("&#8212;", "-"),
        ("&#8230;", "..."),
        ("&#8243;", "\""),
        ("&#124;", "|"),
        ("&nbsp;", " "),
        ("&quot;", "\""),
        ("&lt;", "<"),
        ("&gt;", ">"),
        ("&amp;", "&"),
        ("’", "'"),
        ("‘", "'"),
        ("“", "\""),
        ("”", "\""),
        ("—", "-"),
        ("–", "-"),
        ("…", "..."),
    ]:
        out = out.replace(a, b)
    for marker in ["[ more", "The post "]:
        i = out.find(marker)
        if i >= 0:
            out = out[:i]
    return " ".join(out.split())

STOPWORDS = ["with", "this", "that", "from", "will", "after", "have",
             "been", "they", "their", "them", "were", "when", "what",
             "your", "more", "some", "just", "into", "over", "about"]

def stems_of(s):
    """4-char stems of significant words, so open/opening and
    prepares/preparing count as the same word."""
    out = []
    cur = ""
    for ch in s.lower().elems():
        if ch.isalnum():
            cur += ch
        else:
            if len(cur) > 3 and cur not in STOPWORDS:
                out.append(cur[:4])
            cur = ""
    if len(cur) > 3 and cur not in STOPWORDS:
        out.append(cur[:4])
    return out

def sentences_of(s):
    sents = []
    start = 0
    n = len(s)
    for i in range(n - 1):
        end = False
        if s[i] in (".", "!", "?") and s[i + 1] == " ":
            end = True
        elif s[i] == "\"" and i > 0 and s[i - 1] in (".", "!", "?") and s[i + 1] == " ":
            end = True
        if end:
            sents.append(s[start:i + 1])
            start = i + 2
    if start < n:
        sents.append(s[start:])
    return sents

def shorten(s):
    if len(s) <= 70:
        return s
    # always cut at a word boundary — byte slicing mid-word can split a
    # multibyte character into a garbage glyph
    cut = s[:70]
    last_space = cut.rfind(" ")
    if last_space > 20:
        cut = cut[:last_space]
    return cut + "..."

def pick_summary(title, desc):
    """First sentence that ADDS information. A sentence is an echo if a
    third of its words repeat the headline, or if it covers a third of the
    headline's content (stem-matched, so inflections count)."""
    tstems = stems_of(title)
    if not tstems:
        return ""
    for sent in sentences_of(desc)[:4]:
        sent = sent.strip()
        if len(sent) < 20:
            continue
        sstems = stems_of(sent)
        if not sstems:
            continue
        dup = 0
        for w in sstems:
            if w in tstems:
                dup += 1
        cov = 0
        for w in tstems:
            if w in sstems:
                cov += 1
        if dup * 3 >= len(sstems):
            continue
        if cov * 3 >= len(tstems):
            continue
        return shorten(sent)
    return ""

def parse_pub(pub):
    """RFC-2822 date, defensively: time.parse_time ERRORS on mismatch
    (no None return), so only attempt the one exact shape WordPress
    emits — 'Mon, 02 Jan 2006 15:04:05 +0000' (31 bytes, numeric zone)."""
    if not pub or len(pub) != 31:
        return None
    tail = pub[-5:]
    if tail[0] not in ("+", "-") or not tail[1:].isdigit():
        return None
    return time.parse_time(pub, "Mon, 02 Jan 2006 15:04:05 -0700")

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

def looks_like_feed(body):
    head = body[:300]
    return "<rss" in head or "<?xml" in head

def get_articles():
    items = []
    for feed in FEEDS:
        res = http.get(feed["url"], ttl_seconds = CACHE_TTL_SECONDS)
        if res.status_code != 200:
            continue
        body = res.body()
        if not looks_like_feed(body):
            # HTML error page served with a 200 — xpath.loads would
            # hard-fail the whole render
            continue
        doc = xpath.loads(body)
        for i in range(1, PER_FEED + 1):
            title = doc.query("//item[%d]/title" % i)
            description = doc.query("//item[%d]/description" % i)
            pub = doc.query("//item[%d]/pubDate" % i)
            if title == None:
                continue
            parsed = parse_pub(pub or "")
            clean_title = strip_html(title)
            items.append({
                "title": clean_title,
                "description": pick_summary(clean_title, strip_html(description or "")),
                "meta": feed["tag"] + " - " + ago(parsed) if parsed else feed["tag"],
                "accent": feed["accent"],
                "ts": parsed.unix if parsed else 0,
            })
    cutoff = time.now().unix - MAX_AGE_DAYS * 86400
    items = [it for it in items if it["ts"] == 0 or it["ts"] >= cutoff]
    if not items:
        return [{"title": "No Greenpoint news in the last %d days" % MAX_AGE_DAYS, "description": "", "meta": "", "accent": STORY, "ts": 0}]
    return sorted(items, key = lambda a: a["ts"], reverse = True)

def render_header():
    return render.Column(
        children = [
            render.Box(
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
            ),
            render.Box(width = 64, height = 1, color = GOLD),
        ],
    )

def render_articles(articles, breaking_lead):
    elements = []
    for idx in range(len(articles)):
        article = articles[idx]
        title = article["title"]
        color = WHITE
        if idx == 0 and breaking_lead:
            title = "+++ " + title + " +++"
            color = BREAKING
        elements.append(render.WrappedText(
            content = title,
            width = 64,
            color = color,
            font = "tom-thumb",
        ))
        if article["description"]:
            elements.append(render.Box(height = 2))
            elements.append(render.WrappedText(
                content = article["description"],
                width = 64,
                color = STORY,
                font = "tom-thumb",
                linespacing = 1,
            ))
        if article["meta"]:
            elements.append(render.Box(height = 1))
            elements.append(render.Text(
                content = article["meta"],
                color = article["accent"],
                font = "CG-pixel-3x5-mono",
            ))
        elements.append(render.Box(height = 2))
        elements.append(render.Box(width = 64, height = 1, color = HAIRLINE))
        elements.append(render.Box(height = 2))
    return elements

def main(config):
    articles = get_articles()

    # rotate the visible trio by wall clock so every story gets airtime
    if len(articles) > SHOW_PER_CYCLE:
        start = time.now().in_location(TZ).minute // 10 % len(articles)
        articles = [articles[(start + i) % len(articles)] for i in range(SHOW_PER_CYCLE)]

    breaking_lead = articles[0]["ts"] > 0 and (time.now().unix - articles[0]["ts"]) < BREAKING_SECS

    body_h = 32 - HEADER_H - 1
    return render.Root(
        delay = ANIMATION_SPEED,
        show_full_animation = True,
        child = render.Column(
            children = [
                render_header(),
                render.Marquee(
                    height = body_h,
                    scroll_direction = "vertical",
                    offset_start = body_h,
                    child = render.Column(
                        children = render_articles(articles, breaking_lead),
                    ),
                ),
            ],
        ),
    )
