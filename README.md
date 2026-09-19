# 每日领券省钱清单 · Daily Coupon Savings List

每天自动领券，再把一堆券变成一张**能直接照着花钱**的清单。

> **券后最低实付 = 使用门槛 − 券面额**
>
> 含义是「买一件价格刚好等于门槛的商品，实际要付多少」——这张券能达到的理论下限。

只靠门槛和面额两个数字，就能回答「今天有没有券能让某样东西几乎白拿」。
不需要去搜商品、也不需要抓价格。

![status](https://img.shields.io/badge/WorkBuddy-%E6%8A%80%E8%83%BD-blue)
![python](https://img.shields.io/badge/python-3.8%2B%20%E7%BA%AF%E6%A0%87%E5%87%86%E5%BA%93-brightgreen)

---

## 它长什么样

跑一次的输出（真实数据，56 张券）见 **[docs/example-output.md](docs/example-output.md)**。摘一段：

| 券名 | 品类 | 使用门槛 | 券面额 | 最低实付 | 有效期 |
| --- | --- | --- | --- | --- | --- |
| 神价频道新客红包 | 美团闪购 | 3 元 | 3 元 | **0 元** | 当日到期 |
| 玩乐变美1元券 | 丽人医疗 | 无门槛 | 1 元 | **0 元** | 一周内 |
| 闪购惊喜神券 | 美团闪购 | 20 元 | 14 元 | 6 元 | 当日到期 |

开头一句话给结论，后面四块分组，每张券都能在表里对上数字。

## 工作原理

```
      每天 09:00（定时触发）
              │
              ▼
   ① 领券 —— 一键领取当日全部券 ──► coupons[]
              │
              ▼
   ② 计算 —— 门槛 − 面额，逐张算最低实付
              │
              ▼
   ③ 分组 —— A 低门槛 / B 近白嫖 / 实物专区 / C 其余品类
              │
              ▼
   ④ 出清单 —— Markdown，可直接转发；可选记账落盘
```

第 ① 步是一条**取数通道**，任何能返回「每张券的门槛 + 面额」的来源都行（见
[skill/references/data-sources.md](daily-coupon-list/references/data-sources.md)）。
第 ② ③ ④ 步是本项目的主体：纯本地计算，不联网、不上传。

## 快速开始

### 作为 WorkBuddy 技能

把 `daily-coupon-list/` 整个目录拷进技能目录：

```bash
cp -r daily-coupon-list ~/.workbuddy/skills/
```

之后说到「领券」「今天有哪些券」「这单能省多少」就会自动触发。

### 直接当命令行工具用

`scripts/minpay.py` 不依赖任何第三方库，喂它一份 JSON 就行：

```bash
cd daily-coupon-list

# Markdown 清单
python scripts/minpay.py --file coupons.json

# 归一化 JSON，便于二次处理
python scripts/minpay.py --file coupons.json --json

# 收紧阈值 + 落盘
python scripts/minpay.py --file coupons.json --low 3 --near 0.5 --out report.md
```

输入结构（`{"coupons": [...]}`、`{"data": [...]}`、裸数组 `[...]` 三种都认）：

```json
{
  "coupons": [
    {
      "name": "神价频道新客红包",
      "discount_info": "满3元减3元",
      "priceLimit": 300,
      "couponValue": 300,
      "tabName": "美团闪购",
      "valid_period": "2026-09-19 至 2026-09-19"
    }
  ]
}
```

> ⚠️ **`priceLimit` / `couponValue` 默认按「分」解释**（上面 `300` = 3 元）。
> 数据本来就是「元」时必须加 `--unit yuan`，否则整张表放大 100 倍。

### 记账（可选）

```bash
python scripts/record.py --event claim  --platform meituan --channel 私聊
python scripts/record.py --event redeem --platform meituan --channel 私聊
python scripts/record.py --summary --days 30
```

数据写在 `~/.workbuddy/data/daily-coupon-list/coupon_events.jsonl`，只落本机。

## 分组规则

| 分组 | 判据 | 为什么这样分 |
| --- | --- | --- |
| **A 组 · 低门槛券** | 使用门槛 < 5 元 | 最容易真用上，用户最关心 |
| **B 组 · 近白嫖券** | 门槛 ≥ 5 元 **且** 最低实付 < 1 元 | 高门槛但几乎全额抵扣，值得单列 |
| **实物专区** | 品类可买到实物/餐食（如闪购、外卖） | 只有这类能兑现「低价买到东西」 |
| **C 组 · 其余品类** | 剩下的，按品类汇总 | 到店/服务类门槛远高于单价，一行带过 |
| **字段缺失** | 门槛或面额缺失 | 列出但**不计算、不推测** |

A 组和实物专区**会重叠**（门槛 3 元的闪购券同时属于两组），这是有意为之：
前者回答「有没有低门槛的」，后者回答「能不能买到实物」。

阈值可调：`--low`（默认 5）/ `--near`（默认 1）。

## 两个关键设计判断

**1. 不做商品搜索。**
一开始的思路是「搜出低价商品再算券后价」，实测发现走不通：平台的商品搜索能力往往只覆盖
到店餐饮团购，跟「券后低价买实物」的目标不匹配；而券的门槛/面额本来就躺在券数据里。
**绕远路反而拿不到数据。**

**2. 0 张也要如实报。**
低门槛券每天通常只有一到两张，主流券门槛在 20~45 元。A 组、B 组为 0 是**常态**，
不是抓取失败。输出纪律写死：不为凑数放宽判据、不推测缺失字段、结论里每个数字都要在表里对得上。

## 与「官方专家」的关系

平台上的官方助手能拿到券数据，但有三条硬约束：

1. **话术被锁死** —— 定义里写明「话术必须严格按模板原样输出」，拿到的是成品文案，不是可加工的中间结果；
2. **问答形态** —— 一次问一件事，没法编排进批量或定时流程；
3. **只有原始数字** —— 门槛、面额是原始字段，没有分档、没有排序、没有「这张值不值得点」的结论。

本项目正好补上这三条，**两者是上下游而不是替代**：用官方助手取数，用本项目出清单。

| | 官方助手 | 每日领券省钱清单 |
| --- | --- | --- |
| 输出形态 | 固定话术文本 | 结构化四组清单，可 `--json` 二次处理 |
| 加工自由度 | 不可改 | 分组、排序、阈值全部可调 |
| 编排能力 | 只能对话 | 纯脚本，可批量、可定时（每天出清单） |
| 运行依赖 | 需登录 + 官方专家包 | 纯标准库本地计算，**不联网**、不依赖专家包 |
| 字段缺失 | — | 明确写「未返回」，不推测不补数 |

## 目录结构

```
.
├── daily-coupon-list/          # 技能本体，整目录可直接拷进技能目录
│   ├── SKILL.md                # 主文件：公式、步骤、分组规则、输出纪律
│   ├── scripts/
│   │   ├── minpay.py           # 核心：券 JSON → 四组清单
│   │   └── record.py           # 领取/核销记账
│   └── references/
│       ├── data-sources.md     # 券数据从哪来 + 标准结构
│       └── output-template.md  # 输出骨架与措辞纪律
├── docs/
│   └── example-output.md       # 真实运行输出示例
└── tools/
    └── pack.py                 # 校验 frontmatter + 打发布包
```

## 打包发布

```bash
python tools/pack.py daily-coupon-list 1.0.0
```

一次做完：frontmatter 字段齐全性 → 危险字符检查 → **`yaml.safe_load` 真解析** →
目录层级 → 打 zip（根目录 = `daily-coupon-list/`）。

> 为什么不用手写正则自检：第一版就是这么干的，本地「通过」了，上传却被打回
> `yaml: mapping values are not allowed in this context` —— 英文描述里一个
> `script: grouping` 的半角冒号加空格，被 YAML 当成了嵌套 mapping 的起始。
> **启发式规则替代不了真解析器。**

## 边界与免责

- 脚本**只做本地计算与本地记录**，不发起网络请求、不上传任何数据。
- 「最低实付」是**理论下限**，不代表平台上一定存在该价格的商品。
- 券的可用范围、有效期与最终抵扣**以平台 App 内结算页为准**。
- 不保证一定能领到券、也不保证一定能省到钱。
- 本项目与任何平台官方无隶属关系，使用时请遵守相应平台的服务条款。

## License

[MIT](LICENSE)
