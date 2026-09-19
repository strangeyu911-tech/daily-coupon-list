---
name: daily-coupon-list
display_name: 每日领券省钱清单
display_name_en: Daily Coupon Savings List
description: 每日自动领券 + 券后省钱清单助手。当用户提到领券、优惠券、外卖红包、券后价、最低实付、这单能省多少钱、今天有哪些券、值不值得买、怎么凑单更便宜时使用。自动领券通道目前只支持美团，其他平台需要手动提供券数据；领到券后按「使用门槛 − 券面额」算出每张券的理论最低实付，分为低门槛券、近白嫖券、实物专区、其余品类四组输出清单，支持记录领取与核销，并可挂在定时任务上每天自动重跑。相比美团官方专家的固定话术问答，它用脚本直接产出结构化清单：分组、排序、阈值全部可调，可批量与定时编排，且纯本地计算、不联网、不依赖任何第三方专家包。
description_zh: 每天自动领券（自动领券通道目前仅支持美团，其他平台需手动提供券数据），再把券列表按使用门槛减券面额算出理论最低实付，分组输出省钱清单，并记录领取与核销，可挂定时任务每日重跑。比官方专家的固定话术更灵活：清单可分组排序、阈值可调、可定时批量，纯本地计算不联网、不依赖专家包。
description_en: Claim today's coupons and turn the coupon list into a grouped savings report by computing the theoretical minimum out-of-pocket cost as threshold minus face value, then log claims and redemptions; it can also be wired to a daily scheduled run. Automatic claiming currently supports Meituan only — for every other platform the coupon data has to be supplied manually, while the calculation itself is platform-agnostic. Unlike the fixed-script replies of the Meituan official expert, it emits a structured list through a local script, with grouping, sorting and thresholds all tunable, batch or scheduled runs, and fully offline execution with no third-party expert bundle.
category: 生活服务
version: 1.0.0
author: Strange
---

# 每日领券省钱清单

先领券，再把一堆券变成一张能直接照着花钱的清单。

```
每日 09:00  →  自动领券（美团）  →  按「券后最低实付」分组  →  省钱清单
```

自动领券只对美团成立，别家没有接口 —— 见下面的「平台支持范围」。

## 核心公式

```
最低实付 = 使用门槛 − 券面额
```

含义是「买一件价格刚好等于门槛的商品，实际要付多少」，也就是这张券能达到的**理论下限**。

它只需要两个数字（门槛、面额），**不需要商品价格、不需要搜索商品**。
这是本技能的关键判断：想回答「用券后能不能花很少钱买到东西」，
券本身的数据就够了，去抓商品价格是白费功夫，而且抓不到。

## 什么时候用

用户提到这些就触发：领券、优惠券、外卖红包、券后价、最低实付、省多少钱、
今天有哪些券、哪个券划算、券能不能叠加、怎么凑单。

## 平台支持范围

| 平台 | 自动领券 | 出清单 |
| --- | --- | --- |
| 美团 | ✅ 走路径 A 一键领取当日全部券 | ✅ |
| 淘宝闪购、京东外卖、饿了么、打车/团购等 | ❌ 无接口，只有人工点击的 H5 领券入口 | ✅ 走路径 B，用户手动提供券数据即可 |

**说「自动领券」时只算美团。** 用户问到别家时照实说「这个平台目前只能手动」，
然后把券数据要过来继续算 —— 第 ② ③ ④ 步与来源平台无关。

**禁止为了「支持更多平台」去爬活动页。** 这类页面改版频繁、登录态一失效还会
静默少券，产出缺券的清单比没有更糟。详见 @references/data-sources.md。

## 与美团官方专家的关系

美团官方专家 `MeituanLivingAssistant` 是一条**取数通道**，它能拿到官方券数据
（`issue` 返回的 `coupons[]`）。但它有三条硬约束：

1. **话术被锁死** —— 专家定义里写明「话术必须严格按模板原样输出，禁止附加任何分析/步骤标签」，
   你拿到的是固定文案，不是可以自己加工的中间结果。
2. **问答形态** —— 一次问一件事，没法把它编排进批量或定时流程里。
3. **只有原始数字** —— 门槛、面额是原始字段，没有分档、没有排序、没有「这张值不值得点」的结论。

本技能是**下游加工层**，正好补上这三条：

| | 美团官方专家 | 本技能 |
| --- | --- | --- |
| 输出形态 | 固定话术文本 | 结构化四组清单，可 `--json` 二次处理 |
| 加工自由度 | 不可改 | 分组、排序、阈值（`--low` / `--near`）全部可调 |
| 编排能力 | 只能对话 | 纯脚本，可批量、可定时（如每天出清单） |
| 运行依赖 | 需登录美团账号 + 官方专家包 | 纯标准库本地计算，**不联网**、不依赖任何专家包 |
| 字段缺失 | — | 明确写「未返回」，不推测、不补数 |

**两者是上下游而不是替代**：用官方专家（或任何合法路径）取数，用本技能出清单。

## 执行步骤

1. **先领券** —— 走 @references/data-sources.md 里的取数路径，一键领取当日券并拿到完整的
   `coupons[]` 数组。**自动领取只支持美团**；其他平台没有接口，直接问用户要券数据，
   不要改成去爬页面。当天已领过会返回「您今天已经领取过优惠券」这类提示码，
   但**数组照旧是齐的**，照常解析，不要报成「领券失败」。
2. **把返回落到一份 JSON 文件**（不要直接读管道，Windows 下中文会乱码）。
3. **跑分组脚本**：

   ```bash
   python scripts/minpay.py --file coupons.json
   ```

   数据里金额是「元」而不是「分」时，加 `--unit yuan`。
4. **按模板输出** → 见 @references/output-template.md。脚本已经吐成品 Markdown，通常原样转发即可，
   但**必须**在最前面补一句一句话结论。
5. **（可选）记账**：用户提到「记一下」「我领了哪张」时：

   ```bash
   python scripts/record.py --event claim --platform meituan --channel 私聊
   ```

## 每日自动重跑

把上面 1~4 步挂到定时任务上，就是「每天自动领券 + 出清单」。
**前提是本机有美团的取数通道** —— 定时任务没法跟用户要数据，所以它只对美团成立。

- 触发时间建议**早上 9 点**（当日券池刚刷新，且离到期还有一整天）。
- 任务里要写死这几条约束，否则很容易跑偏：
  1. 当天已领过（提示码非 0）**不算失败**，继续解析返回的券数组；
  2. 取数失败（未登录 / 无 token）时**只输出「需要重新登录」和具体步骤**，
     禁止改用网页抓取或编造领券结果；
  3. 所有券名、门槛、面额必须来自真实返回，缺失写「未返回」，不推测不补数；
  4. 不要顺带做商品搜索（见「常见坑」第 3 条）。
- 单次输出就是一份可直接转发的 Markdown 清单，人不用介入。

## 分组规则

| 分组 | 判据 | 为什么这样分 |
| --- | --- | --- |
| A 组 · 低门槛券 | 使用门槛 < 5 元 | 最容易真用上，是用户最关心的 |
| B 组 · 近白嫖券 | 门槛 ≥ 5 元 **且** 最低实付 < 1 元 | 高门槛但抵扣几乎全额，值得单列 |
| 实物专区 | 品类属于「可买到实物/餐食」的两类 | 只有这类能兑现"低价买实物" |
| C 组 · 其余品类 | 剩下的，按品类汇总 | 到店、服务类通常门槛远高于单价，一行带过 |
| 字段缺失 | 门槛或面额缺失 | 列出但**不计算、不推测** |

A 组和实物专区**会重叠**（一张门槛 3 元的闪购券同时属于两组），这是有意为之：
前者回答「有没有低门槛的」，后者回答「能不能买到实物」。

`--low` / `--near` 可调阈值，默认 5 元 / 1 元。

## 输出纪律

- 给出最低实付的地方，**都要挨着一句**「这是理论下限，具体商品价格要在平台 App 内看」。
- A 组、B 组为 0 张是常态（低门槛券每天通常只有一到两张，主流券门槛在 20~45 元），
  如实说明这是平台定价策略，**不是抓取失败，也不要为了凑数放宽判据**。
- 未返回的字段写「未返回」，不猜不补。
- 到店餐饮类券的门槛常常高于所有候选商品价格，此时结论就是「券后价 = 原价」，
  直说，不要硬套外卖券/闪购券去制造一个好看的券后价。
- 结论里的每个数字都能在下表里对上。

## 脚本

### scripts/minpay.py

券数据 → 四组清单。纯标准库，不联网。

```bash
python scripts/minpay.py --file coupons.json                    # Markdown 清单
python scripts/minpay.py --file coupons.json --json             # 归一化 JSON，便于二次处理
python scripts/minpay.py --file coupons.json --low 3 --near 0.5 # 收紧阈值
python scripts/minpay.py --file coupons.json --out report.md    # 落盘
```

`{"coupons": [...]}`、`{"data": [...]}`、裸数组 `[...]` 三种外层结构都认。
`priceLimit`/`couponValue`/`limit`/`threshold` 等常见字段名都做了映射。

### scripts/record.py

领券记账，数据写在 `~/.workbuddy/data/daily-coupon-list/coupon_events.jsonl`，只落本机。

```bash
python scripts/record.py --event claim  --platform meituan --channel 私聊
python scripts/record.py --event redeem --platform meituan --channel 私聊
python scripts/record.py --summary --days 30
```

## 常见坑

**1. 单位是分。** 接口里的门槛和面额绝大多数是**分**（`couponValue: 100` = 1 元）。
默认按分处理；数据本身是元时必须加 `--unit yuan`，否则整张表放大 100 倍。

**2. `code` 非 0 不等于失败。** 当天重复取券会返回
「您今天已经领取过优惠券」之类的提示码，但券数组照旧是齐的，直接解析。

**3. 券清单任务不要去做商品搜索。** 很多平台的搜索能力只覆盖到店餐饮团购，
与「券后低价买实物」目标不匹配；而且券的门槛/面额本来就在券数据里，绕远路。

**4. 别把不同品类的券混用。** 外卖券、闪购券不能用在到店餐饮订单上。

**5. 有效期当天到期的很常见**，输出时要保留有效期列，别省掉。

## 资源

- @references/data-sources.md —— 券数据的两条获取路径、标准结构、别打进包的东西
- @references/output-template.md —— 输出骨架与措辞纪律

本技能的脚本只做本地计算与本地记录，不发起网络请求、不上传任何数据。
券信息以平台 App 内为准，本技能不保证一定能领到或一定能省到。
