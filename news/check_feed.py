#!/usr/bin/env python3
"""Exit 0 if a downloaded source is usable, so push-news.yml only replaces
the mirror's last good copy with something the card can read.

    python3 -I news/check_feed.py rss|json FILE

rss: XML whose root is <rss> (an HTML error page is neither), and that the
card would not skip (it wants '<rss' or '<?xml' up front). Whitespace or a
BOM before the declaration and anything after </rss> (a plugin's PHP
warning) are trimmed off, and the file is rewritten to exactly what was
checked: pixlet reads past </rss> and fails on a stray '&' or '<' there.
json: a JSON list (the city's API answers errors and throttling with an
object). The card's own parsers fail the whole render on anything else.
"""
import json
import sys
import xml.etree.ElementTree as ET

kind, path = sys.argv[1], sys.argv[2]
try:
    with open(path, "rb") as f:
        raw = f.read()
    if kind == "rss":
        body = raw.lstrip(b"\xef\xbb\xbf \t\r\n")
        body = body[:body.rfind(b"</rss>") + 6] if b"</rss>" in body else b""
        ok = (b"<rss" in body[:300] or b"<?xml" in body[:300]) and ET.fromstring(body).tag == "rss"
        if ok:
            with open(path, "wb") as f:
                f.write(body)
    else:
        ok = isinstance(json.loads(raw), list)
except (ET.ParseError, ValueError, OSError):
    ok = False
sys.exit(0 if ok else 1)
