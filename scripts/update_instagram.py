#!/usr/bin/env python3
"""Optional Instagram Business Discovery collector. No credentials = no requests."""
import datetime as dt
import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DATA = Path(__file__).resolve().parents[1] / "data"
API_VERSION = "v25.0"

def load(path, default):
    try:
        return json.loads((DATA / path).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return default

def username(url):
    try:
        parsed = urlparse(url)
        if parsed.hostname not in ("instagram.com", "www.instagram.com"):
            return None
        name = parsed.path.strip("/").split("/")[0]
        if name and name not in ("p", "reel", "stories") and all(c.isalnum() or c in "._" for c in name):
            return name
    except (ValueError, AttributeError):
        pass
    return None

def fetch(account, username_, token):
    fields = ("business_discovery.username(" + username_ + ")"
              "{username,media.limit(8){id,caption,media_type,permalink,timestamp}}")
    query = urlencode({"fields": fields, "access_token": token})
    url = f"https://graph.facebook.com/{API_VERSION}/{account}?{query}"
    with urlopen(Request(url, headers={"User-Agent":"FukuokaSNSPortal/1.0"}), timeout=20) as res:
        return json.loads(res.read().decode("utf-8")).get("business_discovery", {})

def main():
    token = os.getenv("META_ACCESS_TOKEN", "")
    account = os.getenv("META_IG_USER_ID", "")
    people = load("people.json", [])
    excluded = set(load("excluded_names.json", []))
    old = load("posts.json", [])
    status = load("status.json", {})
    if not token or not account:
        print("Instagram credentials not configured; preserving existing posts.")
        status.update({"instagram": {"configured": False, "checkedAt": None, "succeeded": 0,
                                     "expected": len(people), "errors": []}})
        (DATA / "status.json").write_text(json.dumps(status, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")
        return
    gathered = []
    errors = []
    ok = 0
    expected = 0
    for person in people:
        if person["name"] in excluded:
            continue
        handle = username(person.get("links", {}).get("Instagram", ""))
        if not handle:
            continue
        expected += 1
        try:
            info = fetch(account, handle, token)
            for media in info.get("media", {}).get("data", []):
                url = media.get("permalink", "")
                if not url.startswith("https://www.instagram.com/") and not url.startswith("https://instagram.com/"):
                    continue
                gathered.append({
                    "id": "instagram:" + str(media.get("id","")),
                    "name": person["name"], "district": person.get("district",""),
                    "media":"Instagram","url":url,"date":media.get("timestamp",""),
                    "title":"","text":(media.get("caption") or "")[:350],
                    "image": media.get("thumbnail_url") or media.get("media_url") or "",
                    "publish":"公開","source":"instagram-business-discovery",
                })
            ok += 1
        except (HTTPError, URLError, ValueError, KeyError) as e:
            # Never log request URL or token; errors may include sensitive request params.
            reason = type(e).__name__
            if isinstance(e, HTTPError):
                reason += " HTTP " + str(e.code)
                try:
                    detail = json.loads(e.read().decode("utf-8")).get("error", {})
                    # Log only structured error codes, never credentials or URL.
                    reason += " code=" + str(detail.get("code", "unknown"))
                    reason += " subcode=" + str(detail.get("error_subcode", "none"))
                    reason += " type=" + str(detail.get("type", "unknown"))
                except (ValueError, KeyError, AttributeError):
                    pass
            errors.append(person["name"] + ": " + reason)
    combined = {p["url"]:p for p in old if p.get("url") and
                p.get("source") != "instagram-business-discovery" and p.get("name") not in excluded}
    for p in old:
        if p.get("source") == "instagram-business-discovery" and p.get("url") and p.get("name") not in excluded:
            combined[p["url"]] = p
    for p in gathered:
        combined[p["url"]] = p
    posts = sorted(combined.values(),key=lambda p:p.get("date",""),reverse=True)[:300]
    (DATA/"posts.json").write_text(json.dumps(posts,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    status["posts"] = len(posts)
    status["instagram"] = {"configured":True,"checkedAt":dt.datetime.now(dt.timezone.utc).isoformat(),
                            "succeeded":ok,"expected":expected,"errors":errors}
    (DATA/"status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Instagram discovery: ",ok,"/",expected,"accounts; posts:",len(gathered))

if __name__ == "__main__":
    main()
