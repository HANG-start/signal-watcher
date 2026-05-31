#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


API_BASE = "https://api.x.com/2"
DEFAULT_RSS_URLS = [
    "https://nitter.net/{username}/rss",
    "https://xcancel.com/{username}/rss",
    "https://rss.xcancel.com/{username}/rss",
    "https://twiiit.com/{username}/rss",
    "https://rsshub.app/twitter/user/{username}",
]


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def request_json(url, headers=None, method="GET", body=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers = {**(headers or {}), "Content-Type": "application/json"}

    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc


def get_user_id(username, bearer_token):
    safe_username = urllib.parse.quote(username.lstrip("@"))
    url = f"{API_BASE}/users/by/username/{safe_username}?user.fields=username,name"
    payload = request_json(url, headers={"Authorization": f"Bearer {bearer_token}"})
    data = payload.get("data")
    if not data or not data.get("id"):
        raise RuntimeError(f"Could not find X user: {username}")
    return data["id"], data.get("username", username.lstrip("@"))


def get_latest_posts(user_id, bearer_token, since_id=None):
    query = {
        "max_results": "5",
        "tweet.fields": "created_at,text,referenced_tweets",
        "exclude": "retweets",
    }
    if since_id:
        query["since_id"] = since_id

    url = f"{API_BASE}/users/{user_id}/tweets?{urllib.parse.urlencode(query)}"
    payload = request_json(url, headers={"Authorization": f"Bearer {bearer_token}"})
    return payload.get("data", [])


def fetch_rss_posts(username, feed_url):
    url = feed_url.format(username=urllib.parse.quote(username))
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 x-watch/1.0",
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            xml_text = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"RSS feed failed with HTTP {exc.code}: {detail}") from exc

    xml_text = xml_text.lstrip()
    if not xml_text.startswith("<?xml") and not xml_text.startswith("<rss") and not xml_text.startswith("<feed"):
        raise RuntimeError("RSS source returned a non-RSS page")

    root = ET.fromstring(xml_text)
    posts = []

    channel_items = root.findall("./channel/item")
    for item in channel_items:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        guid = normalize_post_id(item.findtext("guid") or link or title)
        description = item.findtext("description") or ""
        created = item.findtext("pubDate") or ""
        posts.append(
            {
                "id": guid,
                "text": title or strip_html(description),
                "created_at": created,
                "url": link,
            }
        )

    if posts:
        validate_rss_posts(posts)
        return posts

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns):
        title = entry.findtext("atom:title", default="", namespaces=ns)
        link_node = entry.find("atom:link", ns)
        link = link_node.attrib.get("href", "") if link_node is not None else ""
        guid = normalize_post_id(entry.findtext("atom:id", default=link or title, namespaces=ns))
        created = entry.findtext("atom:updated", default="", namespaces=ns)
        posts.append(
            {
                "id": guid,
                "text": title,
                "created_at": created,
                "url": link,
            }
        )

    validate_rss_posts(posts)
    return posts


def validate_rss_posts(posts):
    if not posts:
        raise RuntimeError("RSS source returned no posts")

    invalid_markers = [
        "RSS reader not yet whitelisted",
        "Making sure you're not a bot",
        "Please enable cookies",
        "Cloudflare",
    ]
    joined = "\n".join((post.get("text", "") + "\n" + post.get("url", "")) for post in posts[:3])
    if any(marker in joined for marker in invalid_markers):
        raise RuntimeError("RSS source returned a block/placeholder feed")


def normalize_post_id(value):
    value = str(value or "")
    match = re.search(r"/status/(\d+)", value)
    if match:
        return match.group(1)
    match = re.search(r"\b(\d{15,25})\b", value)
    if match:
        return match.group(1)
    return value


def strip_html(value):
    text = []
    inside_tag = False
    for char in value:
        if char == "<":
            inside_tag = True
        elif char == ">":
            inside_tag = False
        elif not inside_tag:
            text.append(char)
    return "".join(text).strip()


def load_state(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def post_to_webhook(webhook_url, message, post):
    request_json(
        webhook_url,
        method="POST",
        body={
            "text": message,
            "post": post,
        },
    )


def post_to_serverchan(sendkey, title, desp):
    base_url = env("SERVERCHAN_BASE_URL", "https://sctapi.ftqq.com").rstrip("/")
    url = f"{base_url}/{urllib.parse.quote(sendkey)}.send"
    body = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ServerChan failed with HTTP {exc.code}: {detail}") from exc


def post_to_wecom(webhook_url, message):
    request_json(
        webhook_url,
        method="POST",
        body={
            "msgtype": "markdown",
            "markdown": {
                "content": message,
            },
        },
    )


def post_to_telegram(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    body = {
        "chat_id": chat_id,
        "text": message,
        "disable_web_page_preview": False,
    }
    request_json(url, method="POST", body=body)


def notify(message, post=None):
    serverchan_sendkey = env("SERVERCHAN_SENDKEY")
    wecom_webhook_url = env("WECOM_WEBHOOK_URL")
    telegram_token = env("TELEGRAM_BOT_TOKEN")
    telegram_chat_id = env("TELEGRAM_CHAT_ID")
    webhook_url = env("WEBHOOK_URL")

    if serverchan_sendkey:
        title = (post or {}).get("notification_title", "X 新推文提醒")
        post_to_serverchan(serverchan_sendkey, title, message)
        return

    if wecom_webhook_url:
        post_to_wecom(wecom_webhook_url, message)
        return

    if telegram_token and telegram_chat_id:
        post_to_telegram(telegram_token, telegram_chat_id, message)
        return

    if webhook_url:
        post_to_webhook(webhook_url, message, post)
        return

    print(message)


def format_message(username, post):
    url = post.get("url") or f"https://x.com/{username}/status/{post['id']}"
    text = post.get("text", "").strip()
    created = post.get("created_at", "")
    return f"@{username} 发了新推文\n\n{created}\n\n{text}\n\n{url}"


def format_batch_message(username, posts):
    parts = [f"@{username} 有 {len(posts)} 条新推文"]
    for index, post in enumerate(posts, start=1):
        url = post.get("url") or f"https://x.com/{username}/status/{post['id']}"
        text = post.get("text", "").strip()
        created = post.get("created_at", "")
        parts.append(f"{index}. {created}\n{text}\n{url}")
    return "\n\n".join(parts)


def check_api_once(username, state, state_file):
    bearer_token = env("X_BEARER_TOKEN", required=True)
    user_id, canonical_username = get_user_id(username, bearer_token)
    key = f"x-api:user:{user_id}"
    since_id = state.get(key, {}).get("last_seen_id")

    posts = get_latest_posts(user_id, bearer_token, since_id=since_id)
    handle_posts(username, canonical_username, key, posts, since_id, state, state_file)


def check_rss_once(username, state, state_file):
    feed_urls = parse_feed_urls(env("RSS_FEED_URLS") or env("RSS_FEED_URL"))
    posts = None
    last_error = None
    used_feed_url = None

    for feed_url in feed_urls:
        try:
            posts = fetch_rss_posts(username, feed_url)
            used_feed_url = feed_url
            break
        except Exception as exc:
            last_error = exc
            print(f"RSS source failed: {feed_url}: {exc}", file=sys.stderr)

    if posts is None:
        raise RuntimeError(f"All RSS sources failed. Last error: {last_error}")

    key = f"rss:{username}"
    last_seen_id = state.get(key, {}).get("last_seen_id")
    if used_feed_url:
        print(f"Using RSS source: {used_feed_url}")
    handle_posts(username, username, key, posts, last_seen_id, state, state_file)


def parse_feed_urls(value):
    if not value:
        return DEFAULT_RSS_URLS
    return [item.strip() for item in value.split(",") if item.strip()]


def handle_posts(username, canonical_username, key, posts, last_seen_id, state, state_file):
    if not posts:
        print(f"No posts found for @{canonical_username}")
        return

    newest_first = posts
    newest_id = newest_first[0]["id"]

    if not last_seen_id:
        state[key] = {
            "username": canonical_username,
            "last_seen_id": newest_id,
            "checked_at": int(time.time()),
        }
        save_state(state_file, state)
        print(f"Initialized @{canonical_username}; no notification sent")
        return

    new_posts = []
    found_last_seen = False
    for post in newest_first:
        if post["id"] == last_seen_id:
            found_last_seen = True
            break
        new_posts.append(post)

    if not new_posts:
        print(f"No new posts for @{canonical_username}")
        return

    if not found_last_seen:
        new_posts = newest_first[:1]
        print(f"Previous RSS marker not found for @{canonical_username}; notifying latest post only")

    posts_to_notify = list(reversed(new_posts))
    notify(
        format_batch_message(canonical_username, posts_to_notify),
        {"notification_title": f"@{canonical_username} 有 {len(posts_to_notify)} 条新推文"},
    )

    state[key] = {
        "username": canonical_username,
        "last_seen_id": newest_id,
        "checked_at": int(time.time()),
    }
    save_state(state_file, state)
    print(f"Sent {len(new_posts)} notification(s) for @{canonical_username}")


def check_once():
    mode = env("SOURCE_MODE", "rss").lower()
    username = env("X_USERNAME", required=True).lstrip("@")
    state_file = Path(env("STATE_FILE", ".state/x-watch.json"))

    state = load_state(state_file)

    if mode == "api":
        check_api_once(username, state, state_file)
        return

    if mode == "rss":
        check_rss_once(username, state, state_file)
        return

    raise RuntimeError("SOURCE_MODE must be rss or api")


def main():
    try:
        check_once()
    except Exception as exc:
        print(f"x-watch failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
