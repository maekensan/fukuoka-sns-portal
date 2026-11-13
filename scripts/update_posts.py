#!/usr/bin/env python3
"""Collect public YouTube uploads from registered channel feeds without an API key."""
import datetime as dt
import html
import json
import os
import pathlib
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urlencode

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


def youtube_api(path, params, key):
    query = urlencode({**params, "key": key})
    body = download("https://www.googleapis.com/youtube/v3/" + path + "?" + query)
    return json.loads(body.decode("utf-8"))

def channel_api_id(url, key):
    match = CHANNEL_RE.search(url)
    if match and "/channel/" in url:
        return match.group()
    parsed = urlparse(url)
    handle = parsed.path.strip("/").split("/")[0]
    if handle.startswith("@"):
        result = youtube_api("channels", {"part": "id", "forHandle": handle}, key)
        items = result.get("items", [])
        return items[0]["id"] if items else None
    return channel_id(url)

def collect_api(channel, person, key):
    response = youtube_api("channels", {"part": "contentDetails", "id": channel}, key)
    items = response.get("items", [])
    if not items:
        raise ValueError("YouTube channels.list returned no matching channel (check channel URL/ID)")
    uploads = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
    try:
        playlist = youtube_api("playlistItems", {"part": "snippet,contentDetails",
                            "playlistId": uploads, "maxResults": 20}, key)
    except urllib.error.HTTPError as error:
        reason = "unknown"
        try:
            details = json.loads(error.read().decode("utf-8"))
            reason = details.get("error", {}).get("errors", [{}])[0].get("reason", "unknown")
        except (ValueError, IndexError, AttributeError):
            pass
        if error.code == 404 and reason == "playlistNotFound":
            # Use the official search endpoint only for channels whose uploads playlist fails.
            # This should consume at most 2 search calls per 2-hour update at current scale.
            results = youtube_api("search", {"part":"snippet", "channelId":channel,
                          "type":"video", "order":"date", "maxResults":20}, key)
            found = []
            for video in results.get("items", []):
                vid = (video.get("id") or {}).get("videoId", "")
                snippet = video.get("snippet") or {}
                if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
                    continue
                found.append({"id":"youtube:" + vid, "name":person["name"],
                              "district":person["district"], "media":"YouTube",
                              "url":"https://www.youtube.com/watch?v=" + vid,
                              "date":snippet.get("publishedAt",""),
                              "title":snippet.get("title",""), "text":snippet.get("description","")[:350],
                              "image":"https://i.ytimg.com/vi/" + vid + "/hqdefault.jpg",
                              "publish":"公開","source":"youtube-rss"})
            return found
        raise ValueError("playlistItems.list HTTP " + str(error.code) + " (" + reason + ")") from None
    posts = []
    for item in playlist.get("items", []):
        snippet = item.get("snippet") or {}
        video_id = (item.get("contentDetails") or {}).get("videoId")
        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            continue
        posts.append({
            "id": "youtube:" + video_id, "name": person["name"],
            "district": person["district"], "media": "YouTube",
            "url": "https://www.youtube.com/watch?v=" + video_id,
            "date": (item.get("contentDetails") or {}).get("videoPublishedAt")
                    or snippet.get("publishedAt", ""),
            "title": snippet.get("title", ""),
            "text": (snippet.get("description") or "")[:350],
            "image": "https://i.ytimg.com/vi/" + video_id + "/hqdefault.jpg",
            "publish": "公開", "source": "youtube-rss",
        })
    return posts

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
    root = None
    for prefix in ("https://www.youtube.com/feeds/videos.xml?channel_id=",
                   "https://www.youtube.com/xml/feeds/videos.xml?channel_id="):
        try:
            candidate = ET.fromstring(download(prefix + channel))
            if candidate.findall(ATOM + "entry"):
                root = candidate
                break
            failures.append("feed returned zero entries")
        except (urllib.error.HTTPError, urllib.error.URLError, ET.ParseError, TimeoutError) as error:
            failures.append(str(error))
    if root is None:
        raise ValueError("No usable feed entries: " + "; ".join(failures))
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
    retained = [p for p in previous if p.get("source") in ("youtube-rss", "instagram-business-discovery")
                and p.get("name") not in excluded]
    submitted = [p for p in manual if p.get("publish") == "公開"
                 and p.get("name") not in excluded and valid_url(p.get("url"))]
    fresh = []
    success = 0
    errors = []
    expected = 0
    api_key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    for person in people:
        if person["name"] in excluded:
            continue
        url = person.get("links", {}).get("YouTube")
        if not url:
            continue
        expected += 1
        try:
            identity = channel_api_id(url, api_key) if api_key else channel_id(url)
            if not identity:
                errors.append(person["name"] + ": channel ID not found")
                continue
            fresh += collect_api(identity, person, api_key) if api_key else collect(identity, person)
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
    status = load("status.json", {})
    status.update({"checkedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
              "youtubeFeedsSucceeded": success, "youtubeFeedsExpected": expected,
              "errors": errors, "posts": len(posts)})
    (DATA / "status.json").write_text(
        json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(status, ensure_ascii=False))

if __name__ == "__main__":
    main()
