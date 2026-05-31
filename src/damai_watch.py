#!/usr/bin/env python3
import hashlib
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


APP_KEY = "12574478"
ITEM_DETAIL_API = "mtop.alibaba.damai.detail.getdetail"
ITEM_DETAIL_VERSION = "1.2"
ITEM_LEGACY_API = "mtop.damai.item.detail.getdetail"
ITEM_LEGACY_VERSION = "1.0"


def env(name, default=None, required=False):
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def compact_json(data):
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def token_from_cookiejar(cookiejar):
    for cookie in cookiejar:
        if cookie.name == "_m_h5_tk":
            return cookie.value.split("_")[0]
    return ""


def mtop_sign(token, timestamp_ms, data):
    raw = f"{token}&{timestamp_ms}&{APP_KEY}&{data}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def mtop_call(api, version, data):
    cookiejar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookiejar))

    for _ in range(2):
        timestamp_ms = str(int(time.time() * 1000))
        data_text = compact_json(data)
        params = {
            "jsv": "2.7.2",
            "appKey": APP_KEY,
            "t": timestamp_ms,
            "sign": mtop_sign(token_from_cookiejar(cookiejar), timestamp_ms, data_text),
            "api": api,
            "v": version,
            "type": "json",
            "dataType": "json",
            "data": data_text,
        }
        url = f"https://mtop.damai.cn/h5/{api}/{version}/?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
                "Referer": "https://m.damai.cn/",
                "Accept": "application/json,text/plain,*/*",
            },
        )
        payload = json.loads(opener.open(request, timeout=20).read().decode("utf-8"))
        ret = " ".join(payload.get("ret", []))
        if "TOKEN" in ret or "令牌" in ret:
            continue
        return payload

    raise RuntimeError("Damai token handshake failed")


def fetch_project(item_id):
    payload = mtop_call(
        ITEM_DETAIL_API,
        ITEM_DETAIL_VERSION,
        {
            "itemId": item_id,
            "dmChannel": "damai@damaih5_h5",
        },
    )
    ret = " ".join(payload.get("ret", []))
    if "SUCCESS" not in ret:
        raise RuntimeError(f"Damai API failed: {ret}")

    result = json.loads(payload["data"]["result"])
    item_component = result["detailViewComponentMap"]["item"]
    static = item_component.get("staticData", {})
    item_base = static.get("itemBase", {})
    item = item_component.get("item", {})

    legacy = fetch_legacy_project(item_id)

    return {
        "title": item_base.get("itemName") or item.get("title") or "",
        "city": item_base.get("cityName", ""),
        "show_time": item_base.get("showTime", ""),
        "project_status": item_base.get("projectStatus", "") or legacy.get("project_status", ""),
        "price_range": item.get("priceRange") or (item_component.get("price") or {}).get("range") or "",
        "tour_status": extract_tour_status(legacy),
        "perform_dates": extract_perform_dates(item_base),
        "raw_buy_text": legacy.get("buy_text", ""),
    }


def fetch_legacy_project(item_id):
    payload = mtop_call(
        ITEM_LEGACY_API,
        ITEM_LEGACY_VERSION,
        {
            "itemId": item_id,
            "dmChannel": "damai@damaih5_h5",
        },
    )
    data = payload.get("data") or {}
    return {
        "tour": (data.get("guide") or {}).get("tour") or {},
        "project_status": (data.get("item") or {}).get("projectStatus", ""),
        "buy_text": (data.get("buyButton") or {}).get("text", ""),
    }


def extract_tour_status(legacy):
    tour = legacy.get("tour") or {}
    for project in tour.get("projectList", []):
        if str(project.get("itemId")) == env("DAMAI_ITEM_ID", ""):
            return project.get("saleStatus", "")
    return ""


def extract_perform_dates(item_base):
    dates = []
    for note in item_base.get("serviceNotes", []):
        text = note.get("tagDescJson", "")
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        for rule in data.get("performRules", []):
            perform_date = re.sub(r"\s+", " ", rule.get("performDate", "")).strip()
            if perform_date:
                dates.append(perform_date)
    return dates


def likely_available(project):
    positive = " ".join(
        [
            project.get("tour_status", ""),
            project.get("raw_buy_text", ""),
            project.get("project_status", ""),
        ]
    )
    bad_words = ["预约", "无票", "缺货", "暂时", "售罄", "登记"]
    good_words = ["热卖", "立即购买", "购买", "开抢", "可购", "有票"]
    return any(word in positive for word in good_words) and not any(word in positive for word in bad_words)


def load_state(path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def post_to_serverchan(sendkey, title, desp):
    base_url = env("SERVERCHAN_BASE_URL", "https://sctapi.ftqq.com").rstrip("/")
    url = f"{base_url}/{urllib.parse.quote(sendkey)}.send"
    body = urllib.parse.urlencode({"title": title, "desp": desp}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    return json.loads(urllib.request.urlopen(request, timeout=20).read().decode("utf-8"))


def notify(title, body):
    sendkey = env("SERVERCHAN_SENDKEY", required=True)
    response = post_to_serverchan(sendkey, title, body)
    if response.get("code") != 0:
        raise RuntimeError(f"ServerChan failed: {response}")


def summary(project):
    fallback_dates = env("DAMAI_TARGET_DATES", "请以大麦页面为准")
    target_text = env("DAMAI_TARGET_TEXT", "请以你的 .env 配置为准")
    dates = "\n".join(f"- {date}" for date in project.get("perform_dates", [])) or f"- {fallback_dates}"
    return "\n".join(
        [
            project.get("title", "大麦项目"),
            f"目标：{target_text}",
            f"当前巡演状态：{project.get('tour_status') or '未知'}",
            f"价格范围：{project.get('price_range') or '未知'}",
            "",
            "场次：",
            dates,
            "",
            f"链接：https://m.damai.cn/shows/item.html?itemId={env('DAMAI_ITEM_ID')}",
        ]
    )


def check_once():
    item_id = env("DAMAI_ITEM_ID", required=True)
    state_file = Path(env("DAMAI_STATE_FILE", ".state/damai-watch.json"))
    state = load_state(state_file)
    project = fetch_project(item_id)
    fingerprint = compact_json(
        {
            "tour_status": project.get("tour_status"),
            "project_status": project.get("project_status"),
            "raw_buy_text": project.get("raw_buy_text"),
            "price_range": project.get("price_range"),
        }
    )

    old = state.get(item_id, {})
    if not old:
        state[item_id] = {"fingerprint": fingerprint, "checked_at": int(time.time())}
        save_state(state_file, state)
        print("Initialized Damai monitor; no notification sent")
        print(summary(project))
        return

    if fingerprint != old.get("fingerprint") or likely_available(project):
        title = "大麦票务状态变化提醒"
        body = summary(project)
        notify(title, body)
        state[item_id] = {"fingerprint": fingerprint, "checked_at": int(time.time())}
        save_state(state_file, state)
        print("Notification sent")
        print(body)
        return

    print("No Damai status change")
    print(summary(project))


def main():
    try:
        check_once()
    except Exception as exc:
        print(f"damai-watch failed: {exc}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
