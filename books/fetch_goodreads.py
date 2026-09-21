#!/usr/bin/env python3
"""Pull HofReads straight from Goodreads' public shelf RSS feeds. No login, no export.

    https://www.goodreads.com/review/list_rss/<user_id>?shelf=<shelf>&per_page=200&page=N

Shelves pulled: read, currently-reading, to-read. Writes books/data/books.json and
refreshes the HofReads card on the landing page. The profile must be public.

Config: books/data/goodreads_config.json -> {"user_id": "12345678"}   (or env GOODREADS_USER_ID)

Usage:
    python3 books/fetch_goodreads.py
"""

import html
import json
import os
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
CONFIG = os.path.join(DATA_DIR, "goodreads_config.json")
OUT = os.path.join(DATA_DIR, "books.json")
LANDING = os.path.join(ROOT, "index.html")

FEED = "https://www.goodreads.com/review/list_rss/{uid}?shelf={shelf}&per_page=200&page={page}"
SHELVES = {"read": "books", "currently-reading": "currentlyReading", "to-read": "toRead"}


def user_id():
    uid = os.environ.get("GOODREADS_USER_ID", "").strip()
    if not uid and os.path.exists(CONFIG):
        with open(CONFIG) as f:
            uid = str(json.load(f).get("user_id", "")).strip()
    uid = re.match(r"\d+", uid or "")
    if not uid:
        msg = "No Goodreads user id. Put {\"user_id\": \"<digits>\"} in books/data/goodreads_config.json"
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning::{msg}")   # keep the scheduled job green until the id is configured
            sys.exit(0)
        sys.exit(msg)
    return uid.group(0)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (HofReads personal dashboard)"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def iso_date(rfc822):
    if not rfc822:
        return None
    try:
        return parsedate_to_datetime(rfc822).date().isoformat()
    except (TypeError, ValueError):
        return None


def clean(text):
    if not text:
        return None
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = html.unescape(re.sub(r"<[^>]+>", "", text)).strip()
    return text or None


def to_int(v):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def parse_item(it):
    book = it.find("book")
    pages = to_int(book.findtext("num_pages")) if book is not None else None
    title = clean(it.findtext("title")) or "Untitled"
    cover = (it.findtext("book_large_image_url") or it.findtext("book_medium_image_url") or "").strip() or None
    if cover and "nophoto" in cover:
        cover = None
    return {
        "id": to_int(it.findtext("book_id")),
        "title": title,
        "author": clean(it.findtext("author_name")) or "Unknown",
        "pages": pages,
        "isbn": (it.findtext("isbn") or "").strip() or None,
        "rating": to_int(it.findtext("user_rating")) or 0,
        "review": clean(it.findtext("user_review")),
        "dateRead": iso_date(it.findtext("user_read_at")),
        "dateAdded": iso_date(it.findtext("user_date_added")),
        "yearPublished": to_int(it.findtext("book_published")),
        "avgRating": float(it.findtext("average_rating") or 0) or None,
        "cover": cover,
        "link": (it.findtext("link") or "").strip() or None,
        "shelves": [s.strip() for s in (it.findtext("user_shelves") or "").split(",") if s.strip()],
    }


def fetch_shelf(uid, shelf):
    items, page = [], 1
    max_pages = int(os.environ.get("GOODREADS_MAX_PAGES", "20"))
    while page <= max_pages:
        root = ET.fromstring(fetch(FEED.format(uid=uid, shelf=shelf, page=page)))
        batch = root.findall("./channel/item")
        if not batch:
            break
        items.extend(parse_item(it) for it in batch)
        if len(batch) < 200:
            break
        page += 1
        time.sleep(1)
    # the feed can repeat a book across pages; keep the first
    seen, out = set(), []
    for b in items:
        if b["id"] in seen:
            continue
        seen.add(b["id"])
        out.append(b)
    return out


def update_landing(summary):
    if not os.path.exists(LANDING):
        return
    with open(LANDING) as f:
        s = f.read()
    m = re.search(r"<h2>HofReads</h2>.*?<div class=\"card-links\">", s, re.S)
    if not m:
        return
    block = m.group(0)
    pages = summary["totalPages"]
    pages_str = f"{pages / 1000:.1f}K" if pages >= 1000 else str(pages)
    new = re.sub(r'(<div class="val">)[^<]*(</div><div class="lbl">Books</div>)', rf"\g<1>{summary['totalBooks']}\g<2>", block)
    new = re.sub(r'(<div class="val">)[^<]*(</div><div class="lbl">Pages</div>)', rf"\g<1>{pages_str}\g<2>", new)
    new = re.sub(r'(<div class="val">)[^<]*(</div><div class="lbl">Avg Rating</div>)', rf"\g<1>{summary['avgRating']}\g<2>", new)
    if new != block:
        with open(LANDING, "w") as f:
            f.write(s.replace(block, new))


def main():
    uid = user_id()
    data = {}
    for shelf, key in SHELVES.items():
        data[key] = fetch_shelf(uid, shelf)
        print(f"  {shelf}: {len(data[key])} books")
        time.sleep(1)

    if not data["books"]:
        sys.exit("The read shelf came back empty. Is the profile public and the user id right? Leaving books.json untouched.")

    read = data["books"]
    rated = [b["rating"] for b in read if b["rating"]]
    summary = {
        "totalBooks": len(read),
        "totalPages": sum(b["pages"] or 0 for b in read),
        "avgRating": round(sum(rated) / len(rated), 1) if rated else 0,
        "fiveStars": sum(1 for r in rated if r == 5),
        "toRead": len(data["toRead"]),
        "currentlyReading": len(data["currentlyReading"]),
    }

    # Only rewrite when the books changed, so the daily job does not commit a new timestamp every run.
    payload = {"summary": summary, **data}
    if os.path.exists(OUT):
        with open(OUT) as f:
            old = json.load(f)
        if {k: old.get(k) for k in payload} == payload:
            print("No changes.")
            return
    payload = {"generated": datetime.now(timezone.utc).isoformat(), "source": f"goodreads rss user {uid}", **payload}
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    update_landing(summary)
    print(f"Wrote {len(read)} read, {summary['currentlyReading']} reading, {summary['toRead']} to-read "
          f"({summary['totalPages']:,} pages, avg {summary['avgRating']})")


if __name__ == "__main__":
    main()
