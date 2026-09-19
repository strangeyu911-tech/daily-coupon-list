#!/usr/bin/env python3
"""领券记账：记录领取 / 查看 / 核销事件，并按渠道与日期汇总。

数据落在 ~/.workbuddy/data/daily-coupon-list/coupon_events.jsonl，每行一条 JSON。
只写本机，不上传任何服务器。无第三方依赖，Python 3.8+ 可直接运行。

用法
    python record.py --event claim --platform meituan --channel 私聊
    python record.py --event redeem --platform meituan --channel 私聊
    python record.py --summary --days 30
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DATA_FILE = Path.home() / ".workbuddy" / "data" / "daily-coupon-list" / "coupon_events.jsonl"
VALID_EVENTS = ("claim", "view", "redeem")
EVENT_LABEL = {"claim": "领取", "view": "查看", "redeem": "核销"}


def load_events(days=None):
    if not DATA_FILE.exists():
        return []
    cutoff = None
    if days:
        cutoff = (datetime.now() - timedelta(days=int(days))).strftime("%Y-%m-%d")
    events = []
    with DATA_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if cutoff and item.get("date", "") < cutoff:
                continue
            events.append(item)
    return events


def record_event(event, platform, channel, note=""):
    now = datetime.now()
    item = {
        "ts": now.isoformat(timespec="seconds"),
        "date": now.strftime("%Y-%m-%d"),
        "event": event,
        "platform": platform or "unknown",
        "channel": channel or "default",
        "note": note,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DATA_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(
        "OK 已记录 1 次{}，平台：{}，渠道：{}".format(
            EVENT_LABEL.get(event, event), item["platform"], item["channel"]
        )
    )


def show_summary(days=None):
    events = load_events(days)
    if not events:
        print("EMPTY 暂无记录")
        return

    total = Counter(e["event"] for e in events)
    range_text = "近 {} 天".format(days) if days else "全部历史"
    print("=== 领券记录（{}）===".format(range_text))
    print("总计：" + "  ".join("{} {}".format(EVENT_LABEL.get(k, k), v) for k, v in total.items()))

    claims = total.get("claim", 0)
    views = total.get("view", 0)
    redeems = total.get("redeem", 0)
    if claims:
        print("核销率：{:.1f}%  （核销 {} / 领取 {}）".format(redeems * 100.0 / claims, redeems, claims))
    if views:
        print("领取意愿：{:.1f}%  （领取 {} / 查看 {}）".format(claims * 100.0 / views, claims, views))

    by_platform = defaultdict(Counter)
    for e in events:
        by_platform[e.get("platform", "unknown")][e["event"]] += 1
    print("\n--- 按平台 ---")
    for p, c in sorted(by_platform.items(), key=lambda kv: -kv[1].get("claim", 0)):
        parts = "  ".join("{}{}".format(EVENT_LABEL.get(k, k), v) for k, v in c.items())
        extra = ""
        if c.get("claim"):
            extra = "  核销率 {:.1f}%".format(c.get("redeem", 0) * 100.0 / c["claim"])
        print("{}: {}{}".format(p, parts, extra))

    by_channel = defaultdict(Counter)
    for e in events:
        by_channel[e.get("channel", "default")][e["event"]] += 1
    print("\n--- 按渠道 ---")
    for ch, c in sorted(by_channel.items(), key=lambda kv: -kv[1].get("claim", 0)):
        parts = "  ".join("{}{}".format(EVENT_LABEL.get(k, k), v) for k, v in c.items())
        print("{}: {}".format(ch, parts))

    by_date = defaultdict(Counter)
    for e in events:
        by_date[e.get("date", "")][e["event"]] += 1
    print("\n--- 按日期 ---")
    for d in sorted(by_date):
        c = by_date[d]
        print(
            "{}: 查看 {}  领取 {}  核销 {}".format(
                d, c.get("view", 0), c.get("claim", 0), c.get("redeem", 0)
            )
        )


def main():
    parser = argparse.ArgumentParser(description="领券记账与汇总")
    parser.add_argument("--event", choices=VALID_EVENTS, help="记录事件：claim/view/redeem")
    parser.add_argument("--summary", action="store_true", help="输出统计汇总")
    parser.add_argument("--platform", default="unknown", help="平台 key，如 meituan")
    parser.add_argument("--channel", default="default", help="渠道名，如 私聊")
    parser.add_argument("--note", default="", help="备注")
    parser.add_argument("--days", type=int, help="只统计最近 N 天")
    args = parser.parse_args()

    if args.summary:
        show_summary(args.days)
    elif args.event:
        record_event(args.event, args.platform, args.channel, args.note)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
