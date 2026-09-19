#!/usr/bin/env python3
"""每日领券省钱清单生成器。

输入：券数据 JSON（兼容 {"coupons": [...]} 与裸数组 [...]）
输出：按「低门槛券 / 近白嫖券 / 实物专区 / 其余品类」四组的 Markdown 清单

核心公式
    最低实付 = 使用门槛 - 券面额
即"买一件价格刚好等于门槛的商品，实际要付多少"，是该券能达到的理论下限。

无第三方依赖，Python 3.8+ 可直接运行。

用法
    python minpay.py --file coupons.json
    python minpay.py --file coupons.json --low 5 --near 1 --json
"""

import argparse
import json
import sys
from collections import defaultdict

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 只有这两类能买到实物 / 餐食，其余是到店、服务、医美等
PHYSICAL_TABS = ("美团闪购", "外卖")


def load_coupons(path):
    """读入券数据，兼容 {coupons:[...]} 与裸数组两种外层结构。"""
    if path == "-":
        data = json.load(sys.stdin)
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

    if isinstance(data, dict):
        for key in ("coupons", "data", "list", "items"):
            if isinstance(data.get(key), list):
                return data[key]
        raise ValueError("JSON 对象里找不到券数组（试过 coupons / data / list / items）")
    if isinstance(data, list):
        return data
    raise ValueError("无法识别的 JSON 结构，期望对象或数组")


def _to_yuan(raw, field_names):
    """取出金额并统一成"元"。

    优先按"分"解释（接口里的 priceLimit / couponValue 是分），
    只有显式给了 *_yuan 或被 --unit yuan 指定时才当元处理。
    """
    for name in field_names:
        if name in raw and raw[name] is not None:
            value = float(raw[name])
            if name.endswith("_yuan"):
                return value
            return value / 100.0
    return None


def normalize(raw, unit="cent"):
    """把一条原始券记录统一成内部结构。"""
    if unit == "yuan":
        limit = _pick(raw, ("priceLimit", "limit", "threshold", "minSpend"))
        value = _pick(raw, ("couponValue", "value", "discount", "amount"))
        limit = float(limit) if limit is not None else None
        value = float(value) if value is not None else None
    else:
        limit = _to_yuan(raw, ("priceLimit", "limit", "threshold", "minSpend"))
        value = _to_yuan(raw, ("couponValue", "value", "discount", "amount"))

    pay = None
    if limit is not None and value is not None:
        pay = max(0.0, limit - value)

    return {
        "name": raw.get("name") or raw.get("title") or "未命名券",
        "discount_info": raw.get("discount_info") or raw.get("discountInfo") or "",
        "tab": raw.get("tabName") or raw.get("tab") or raw.get("category") or "未分类",
        "period": raw.get("valid_period") or raw.get("validPeriod") or raw.get("expire") or "未返回",
        "limit": None if limit is None else round(limit, 2),
        "value": None if value is None else round(value, 2),
        "pay": None if pay is None else round(pay, 2),
        "incomplete": limit is None or value is None,
    }


def _pick(raw, names):
    for name in names:
        if name in raw and raw[name] is not None:
            return raw[name]
    return None


def group(coupons, low_limit=5.0, near_free=1.0):
    """按分组规则切分，返回 dict。"""
    low, near, physical, rest, incomplete = [], [], [], [], []
    for c in coupons:
        if c["incomplete"]:
            incomplete.append(c)
            continue
        if c["limit"] < low_limit:
            low.append(c)
        if c["limit"] >= low_limit and c["pay"] < near_free:
            near.append(c)
        if c["tab"] in PHYSICAL_TABS:
            physical.append(c)
        else:
            rest.append(c)
    key = lambda c: (c["pay"], -c["value"])
    low.sort(key=key)
    near.sort(key=key)
    physical.sort(key=key)
    return {"low": low, "near": near, "physical": physical, "rest": rest, "incomplete": incomplete}


def _money(x):
    if x is None:
        return "未返回"
    text = "{:.2f}".format(x).rstrip("0").rstrip(".")
    return text if text else "0"


def _face(c):
    """券面说明；接口没给时用门槛/面额拼一个，避免出现「未返回」。"""
    if c["discount_info"]:
        return c["discount_info"]
    if c["limit"] is None or c["value"] is None:
        return "未返回"
    if c["limit"] == 0:
        return "无门槛减{}元".format(_money(c["value"]))
    return "满{}元减{}元".format(_money(c["limit"]), _money(c["value"]))


def _row(c, index=None):
    name = c["name"] if index is None else "{}. {}".format(index, c["name"])
    return "| {} | {} | {} | {} | {} | {} | {} |".format(
        name,
        c["tab"],
        _face(c),
        "无门槛" if c["limit"] == 0 else _money(c["limit"]) + " 元",
        _money(c["value"]) + " 元",
        _money(c["pay"]) + " 元",
        c["period"],
    )


HEADER = "| 券名 | 品类 | 券面说明 | 使用门槛 | 券面额 | 最低实付 | 有效期 |"
DIVIDER = "| --- | --- | --- | --- | --- | --- | --- |"


def render(groups, total, low_limit=5.0, near_free=1.0):
    """输出 Markdown 清单。"""
    out = []
    out.append("## 每日领券省钱清单")
    out.append("")
    out.append("共解析 {} 张券。最低实付 = 使用门槛 − 券面额，是**理论下限**，具体商品价格请在平台 App 内看。".format(total))
    out.append("")

    out.append("### A 组 · 低门槛券（使用门槛 < {} 元）".format(_money(low_limit)))
    out.append("")
    if groups["low"]:
        out.append(HEADER)
        out.append(DIVIDER)
        for i, c in enumerate(groups["low"], 1):
            out.append(_row(c, i))
    else:
        out.append("今日没有使用门槛低于 {} 元的券。这是平台定价策略，不是获取失败。".format(_money(low_limit)))
    out.append("")

    out.append("### B 组 · 近白嫖券（门槛 ≥ {} 元，且最低实付 < {} 元）".format(_money(low_limit), _money(near_free)))
    out.append("")
    if groups["near"]:
        out.append(HEADER)
        out.append(DIVIDER)
        for i, c in enumerate(groups["near"], 1):
            out.append(_row(c, i))
    else:
        out.append("今日 0 张。下面列门槛达标、最低实付最接近的 2 张供参考：")
        out.append("")
        pool = sorted(
            [
                c
                for c in groups["physical"] + groups["rest"]
                if c["pay"] is not None and c["limit"] >= low_limit
            ],
            key=lambda c: c["pay"],
        )[:2]
        if pool:
            out.append(HEADER)
            out.append(DIVIDER)
            for c in pool:
                out.append(_row(c))
        else:
            out.append("（无可用数据）")
    out.append("")

    out.append("### 实物专区（美团闪购 / 外卖，能买到实物或餐食）")
    out.append("")
    if groups["physical"]:
        out.append(HEADER)
        out.append(DIVIDER)
        for i, c in enumerate(groups["physical"], 1):
            out.append(_row(c, i))
    else:
        out.append("今日没有闪购 / 外卖类券。")
    out.append("")

    out.append("### C 组 · 其余品类（按品类汇总）")
    out.append("")
    by_tab = defaultdict(list)
    for c in groups["rest"]:
        by_tab[c["tab"]].append(c)
    if by_tab:
        out.append("| 品类 | 张数 | 最低实付区间 | 门槛最低的一档 |")
        out.append("| --- | --- | --- | --- |")
        for tab in sorted(by_tab, key=lambda t: min(c["pay"] for c in by_tab[t])):
            items = by_tab[tab]
            pays = [c["pay"] for c in items]
            cheapest = min(items, key=lambda c: c["limit"])
            out.append(
                "| {} | {} | {} ~ {} 元 | {} |".format(
                    tab, len(items), _money(min(pays)), _money(max(pays)), _face(cheapest)
                )
            )
    else:
        out.append("（无）")
    out.append("")

    if groups["incomplete"]:
        out.append("### 字段缺失（无法计算，未推测）")
        out.append("")
        for c in groups["incomplete"]:
            out.append("- {}（{}）".format(c["name"], c["tab"]))
        out.append("")

    out.append("> 说明：最低实付是「买一件价格刚好等于门槛的商品」时的实付下限，不代表平台上一定存在该价格的商品；")
    out.append("> 券的可用范围、有效期与最终抵扣以平台 App 内结算页为准。")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="每日领券省钱清单生成器")
    parser.add_argument("--file", default="-", help="券数据 JSON 路径，- 表示从 stdin 读")
    parser.add_argument("--unit", choices=("cent", "yuan"), default="cent",
                        help="金额单位，默认 cent（分），与主流接口一致")
    parser.add_argument("--low", type=float, default=5.0, help="A 组门槛上限，默认 5 元")
    parser.add_argument("--near", type=float, default=1.0, help="B 组最低实付上限，默认 1 元")
    parser.add_argument("--json", action="store_true", help="改输出归一化后的 JSON")
    parser.add_argument("--out", help="写入文件而不打印到 stdout")
    args = parser.parse_args()

    raw = load_coupons(args.file)
    coupons = [normalize(item, args.unit) for item in raw]
    groups = group(coupons, args.low, args.near)

    if args.json:
        payload = {
            "total": len(coupons),
            "low": groups["low"],
            "near": groups["near"],
            "physical": groups["physical"],
            "rest": groups["rest"],
            "incomplete": groups["incomplete"],
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = render(groups, len(coupons), args.low, args.near)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("OK 已写入 {}".format(args.out))
    else:
        print(text)


if __name__ == "__main__":
    main()
