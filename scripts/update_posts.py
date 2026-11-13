#!/usr/bin/env python3
"""Collect public YouTube uploads from registered channel feeds without an API key."""
import datetime as dt
import html
import json
import pathlib
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ATOM = "{http://www.w3.org/2005/Atom}"
YT = "{http://www.youtube.com/xml/schemas/2015}"
MEDIA = "{http://search.yahoo.com/mrss/}"
CHANNEL_RE = re.compile(r"UC[A-Za-z0-9_-]{22}")

def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default

def download(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; FukuokaSNSFeed/1.0)",
        "Accept": "application/atom+xml,text/xml,text/html;q=0.9,*/*;q=0.5",
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read()

def channel_id(url):
    if "/channel/" in url:
        match = CHANNEL_RE.search(url)
        if match:
            return match.group()
    if "/@" in url:
        try:
            source = download(url).decode("utf-8", errors="replace")
            for pattern in (r'"externalId":"(UC[A-Za-z0-9_-]{22})"',
                            r'"channelId":"(UC[A-Za-z0-9_-]{22})"'):
                match = re.search(pattern, source)
                if match:
                    return match.group(1)
        except Exception as error:
            print("Could not resolve YouTube handle:", type(error).__name__)
    return None

def valid_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.hostname)
    except ValueError:
        return False

def collect(channel, person):
    # YouTube currently uses /xml/feeds/ for its working notification topic.
    # Keep the older /feeds/ route as a fallback for intermittent changes.
    failures = []
    for prefix in ("https://www.youtube.com/xml/feeds/videos.xml?channel_id=",
                   "https://www.youtube.com/feeds/videos.xml?channel_id="):
        try:
            feed = download(prefix + channel)
            root = ET.fromstring(feed)
            break
        except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError, TimeoutError) as error:
            failures.append("%s: %s" % (prefix.split(".com/")[1].split("/")[0], str(error)))
    else:
        raise ValueError("All feed URLs failed: " + "; ".join(failures))
    items = []
    for entry in root.findall(ATOM + "entry"):
        video_id = (entry.findtext(YT + "videoId") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            continue
        group = entry.find(MEDIA + "group")
        description = group.findtext(MEDIA + "description") if group is not None else ""
        items.append({
            "id": "youtube:" + video_id,
            "name": person["name"],
            "district": person["district"],
            "media": "YouTube",
            "url": "https://www.youtube.com/watch?v=" + video_id,
            "date": entry.findtext(ATOM + "published") or "",
            "title": html.unescape(entry.findtext(ATOM + "title") or ""),
            "text": html.unescape(description or "")[:350],
            "image": "https://i.ytimg.com/vi/" + video_id + "/hqdefault.jpg",
            "publish": "公開",
            "source": "youtube-rss",
        })
    return items

def main():
    people = load("people.json", [])
    excluded = set(load("excluded_names.json", []))
    previous = load("posts.json", [])
    manual = load("manual_posts.json", [])
    retained = [p for p in previous if p.get("source") == "youtube-rss"
                and p.get("name") not in excluded]
    submitted = [p for p in manual if p.get("publish") == "公開"
                 and p.get("name") not in excluded and valid_url(p.get("url"))]
    fresh = []
    success = 0
    errors = []
    expected = 0
    for person in people:
        if person["name"] in excluded:
            continue
        url = person.get("links", {}).get("YouTube")
        if not url:
            continue
        expected += 1
        try:
            identity = channel_id(url)
            if not identity:
                errors.append(person["name"] + ": channel ID not found")
                continue
            fresh += collect(identity, person)
            success += 1
        except (urllib.error.URLError, ET.ParseError, TimeoutError, ValueError) as error:
            errors.append(person["name"] + ": " + str(error)[:220])
    by_url = {}
    for item in retained + fresh + submitted:
        url = item.get("url", "")
        if not valid_url(url) or item.get("publish") != "公開":
            continue
        by_url[url] = item
    posts = sorted(by_url.values(), key=lambda x: x.get("date", ""), reverse=True)[:300]
    (DATA / "posts.json").write_text(
        json.dumps(posts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    status = {"checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
              "youtubeFeedsSucceeded": success, "youtubeFeedsExpected": expected,
              "errors": errors, "posts": len(posts)}
    (DATA / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, ensure_ascii=False))

if __name__ == "__main__":
    main()
