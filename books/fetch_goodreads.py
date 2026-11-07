#!/usr/bin/env python3
"""Pull HofReads from Goodreads' public shelf widget. No login, no export.

Goodreads retired the shelf RSS feeds in late Oct 2026 (they 404 for every user). The
embeddable shelf widget still works:

    https://www.goodreads.com/review/custom_widget/<user_id>?shelf=<shelf>&num_books=N&widget_id=<random>

It returns JS that writes HTML. Per book it has: review link (review id), title, author,
cover (book id is in the cover URL), and your star rating. It does NOT have read dates,
page counts, ISBN, publish year or your review text. So this script merges:

  - books already in books.json keep every field; only rating/title/author/cover refresh
  - a book that moves between shelves keeps its old record (to-read entries already have pages)
  - a book new to the read shelf gets dateRead = the day this script first sees it there
    (ET), and pages/isbn/year/avg rating from its public book page when available
  - a book no longer on a shelf is dropped from that list

Records are keyed by review id (stable per user + book).

Config: books/data/goodreads_config.json -> {"user_id": "12345678"}   (or env GOODREADS_USER_ID)

Usage:
    python3 books/fetch_goodreads.py
"""

import html
import json
import os
import random
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(SCRIPT_DIR, "data")
CONFIG = os.path.join(DATA_DIR, "goodreads_config.json")
OUT = os.path.join(DATA_DIR, "books.json")
LANDING = os.path.join(ROOT, "index.html")

WIDGET = ("https://www.goodreads.com/review/custom_widget/{uid}?shelf={shelf}&sort=date_read"
          "&order=d&num_books=500&widget_id={wid}")
BOOK_PAGE = "https://www.goodreads.com/book/show/{bid}"
SHELVES = {"read": "books", "currently-reading": "currentlyReading", "to-read": "toRead"}
RATINGS = {"did not like it": 1, "it was ok": 2, "liked it": 3, "really liked it": 4, "it was amazing": 5}
UA = {"User-Agent": "Mozilla/5.0 (HofReads personal dashboard)"}


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
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", "replace")


def text(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s or "")).strip() or None


def review_id(link):
    m = re.search(r"review/show/(\d+)", link or "")
    return m.group(1) if m else None


def fetch_shelf(uid, shelf):
    """Books on one shelf, in widget order: [{reviewId, title, author, rating, cover, id, link}]."""
    js = fetch(WIDGET.format(uid=uid, shelf=shelf, wid=random.randint(10**8, 10**9)))
    # The widget is a JS string literal; unescape it back to HTML.
    page = js.replace('\\"', '"').replace("\\/", "/").replace("\\n", "\n").replace("\\'", "'")
    if "gr_custom_container" not in page:
        raise RuntimeError(f"Widget for shelf '{shelf}' did not return a shelf. Is the profile public?")
    out = []
    for chunk in page.split('class="gr_custom_book_container')[1:]:
        link = re.search(r'href="(https://www\.goodreads\.com/review/show/\d+[^"]*)"', chunk)
        rid = review_id(link.group(1) if link else None)
        if not rid:
            continue
        cover = re.search(r'<img alt="[^"]*" border="0" src="([^"]+)"', chunk)
        cover = cover.group(1) if cover else None
        bid = re.search(r"/(\d+)(?:\.[^/]*)?\._S[XY]\d+_\.jpg", cover or "")
        if cover and "nophoto" in cover:
            cover = None
        elif cover:
            cover = re.sub(r"\._S[XY]\d+_\.", "._SY475_.", cover)   # match the old feed's size
        stars = re.search(r'staticStars[^"]*" title="([^"]*)"', chunk)
        title = re.search(r'class="gr_custom_title_\d+">\s*<a[^>]*>(.*?)</a>', chunk, re.S)
        author = re.search(r'class="gr_custom_author_\d+">\s*by\s*<a[^>]*>(.*?)</a>', chunk, re.S)
        out.append({
            "reviewId": rid,
            "id": int(bid.group(1)) if bid else None,
            "title": text(title.group(1)) if title else "Untitled",
            "author": text(author.group(1)) if author else "Unknown",
            "rating": RATINGS.get((stars.group(1) if stars else "").strip(), 0),
            "cover": cover,
            "link": f"https://www.goodreads.com/review/show/{rid}",
        })
    return out


def book_details(bid):
    """Pages / ISBN / year / avg rating from the public book page. Best effort."""
    if not bid:
        return {}
    page = ""
    for attempt in range(3):   # Goodreads sometimes answers 200 with an empty body
        try:
            page = fetch(BOOK_PAGE.format(bid=bid))
        except Exception as e:
            print(f"  (book {bid} attempt {attempt + 1}: {e})")
        if "numberOfPages" in page:
            break
        time.sleep(3)
    if not page:
        print(f"  (no details for book {bid}; pages will be blank)")
        return {}
    def num(pat, cast=int):
        m = re.search(pat, page)
        return cast(m.group(1)) if m else None
    isbn = re.search(r'"isbn":"(\d{9}[\dX])"', page) or re.search(r'"isbn":"([\dX]{13})"', page)
    year = None
    # The page lists the work's first publication and this edition's; the earliest is the original.
    times = [int(t) for t in re.findall(r'"publicationTime":(-?\d+)', page)]
    if times:
        year = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=min(times))).year
    return {"pages": num(r'"numberOfPages":(\d+)'), "isbn": isbn.group(1) if isbn else None,
            "yearPublished": year, "avgRating": num(r'"ratingValue":([\d.]+)', float)}


def merge(shelf, key, fresh, old_by_rid, old_order, today):
    out = []
    for w in fresh:
        old = old_by_rid.get(w["reviewId"])
        if old:
            rec = dict(old)
            # Keep stored title/author/cover: the widget drops series suffixes and uses a
            # different cover size, which would churn the file for no visible change.
            rec["rating"] = w["rating"]
            if not rec.get("cover"):
                rec["cover"] = w["cover"]
        else:
            rec = {"id": w["id"], "title": w["title"], "author": w["author"], "pages": None, "isbn": None,
                   "rating": w["rating"], "review": None, "dateRead": None, "dateAdded": today,
                   "yearPublished": None, "avgRating": None, "cover": w["cover"], "link": w["link"], "shelves": []}
            rec.update({k: v for k, v in book_details(w["id"]).items() if v is not None})
            time.sleep(1)
        if key == "books":
            rec["shelves"] = []
            was_read = old is not None and old.get("_shelf") == "books"
            if not was_read:
                rec["dateRead"] = today   # first day we see it on the read shelf
        elif not (old and old.get("_shelf") == key):
            rec["shelves"] = [shelf]
        rec.pop("_shelf", None)
        out.append(rec)
    # Keep the stored order (so the file diff stays small); books new to this shelf go on top.
    pos = {review_id(b.get("link")): i for i, b in enumerate(old_order.get(key, []))}
    out.sort(key=lambda b: pos.get(review_id(b.get("link")), -1))
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
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

    old = {}
    if os.path.exists(OUT):
        with open(OUT) as f:
            old = json.load(f)
    old_by_rid = {}
    for key in SHELVES.values():
        for b in old.get(key, []):
            rid = review_id(b.get("link"))
            if rid:
                old_by_rid[rid] = {**b, "_shelf": key}

    fresh = {}
    for shelf, key in SHELVES.items():
        fresh[key] = fetch_shelf(uid, shelf)
        print(f"  {shelf}: {len(fresh[key])} books")
        time.sleep(1)

    if not fresh["books"]:
        sys.exit("The read shelf came back empty. Is the profile public and the user id right? Leaving books.json untouched.")
    if old.get("books") and len(fresh["books"]) < len(old["books"]) * 0.8:
        sys.exit(f"Read shelf dropped from {len(old['books'])} to {len(fresh['books'])}. That looks like a "
                 "Goodreads hiccup, not real removals. Leaving books.json untouched.")

    data = {key: merge(shelf, key, fresh[key], old_by_rid, old, today) for shelf, key in SHELVES.items()}

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
    if {k: old.get(k) for k in payload} == payload:
        print("No changes.")
        return
    payload = {"generated": datetime.now(timezone.utc).isoformat(), "source": f"goodreads widget user {uid}", **payload}
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=1, ensure_ascii=False)
    update_landing(summary)
    print(f"Wrote {len(read)} read, {summary['currentlyReading']} reading, {summary['toRead']} to-read "
          f"({summary['totalPages']:,} pages, avg {summary['avgRating']})")


if __name__ == "__main__":
    main()
