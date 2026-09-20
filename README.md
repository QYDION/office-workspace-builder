<a href="https://www.qydion.com" target="_blank" rel="noopener"><img src="https://qydion.com/brand/16-horizontal-full-deepspace.png" alt="QYDION" width="240"></a>

# office-workspace-builder

> 中文 | [English](README.en.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![type: Agent Skill](https://img.shields.io/badge/type-Agent%20Skill-blue.svg)](skills/office-workspace-builder/SKILL.md)
[![verify: 3 gates · 0 FAIL](https://img.shields.io/badge/verify-3%20gates%20%C2%B7%200%20FAIL-brightgreen.svg)](#交付前验证)

## 包含的技能

| 技能 | 说明 |
|---|---|
| `office-workspace-builder`（办公工作台生成器） | 把一句办公需求变成打开即用的网页工作台。生成单文件 HTML，全部 CSS / JS / 图标 / 图表内联，零外部依赖；默认走宿主在线存储能力部署并交付在线链接，能力不可用时降级为本地 HTML + 本地存储。内置 20+ 办公模块、13 条踩坑铁律，以及交付前的三道自动验证闸门。 |

## 它解决什么问题

让模型直接生成工作台类页面，通常会掉进同一批坑。本技能把这批坑逐条固化成铁律，并配了可执行的检查脚本：

| 常见问题 | 本项目的处理 |
|---|---|
| 引用外部 JS 库，用户只存了 HTML，库 404，功能全废 | 全内联，图表用内联 SVG 手写 |
| 首屏空白，等用户自己填数据，用户判定「不好用」 | 预置 3–5 条示例数据，其中 1 条处于逾期状态 |
| 模块越加越多，单次输出被截断，页面白屏 | 规模闸门：单期最多 4 个模块，超限先出分期方案 |
| 渲染函数互相调用，无限递归，栈溢出 | 单向调用架构，`refreshAll()` 统一调度 |
| 存储写失败被 `catch` 静默吞掉，用户以为存上了，刷新后数据全丢 | 失败必须渲染成用户可见的告警条 |
| 所有元素共用一个圆角值、每张卡片都带阴影，一眼就是模板味 | 圆角分档递级，阴影只给浮起层 |
| 生成完直接交付，运行时错误没人发现 | 交付前跑三道自动验证闸门 |

## 安装

**方式一：skills CLI**

```bash
npx skills add QYDION/office-workspace-builder --skill office-workspace-builder
```

**方式二：手动**

下载本仓库，把 `skills/office-workspace-builder` 整个文件夹复制到所用客户端的技能目录（各客户端的技能目录位置不同，以该客户端文档为准），重开一次生效。

装好后在对话里直接提需求即可，例如「帮我做个周报台」「我想每天记一下做了什么，周五一键拼成周报」，不需要任何特殊指令。

> 技能文档里带了 7 份参考资料和 1 个骨架模板。**修改技能后请重新加载全量 skill**，避免客户端只注入开头一部分、实际执行的仍是旧规则。

## 目录结构

```
.
├── LICENSE
├── README.md
├── README.en.md
└── skills/
    └── office-workspace-builder/
        ├── SKILL.md                        技能主文件（输入输出契约、S0–S6 标准流程）
        ├── references/                     7 份参考资料
        │   ├── iron-rules.md               13 条铁律全文 + 正误对照速查表
        │   ├── generation-contract.md      需求解析 → 模块映射 → 规模闸门 → 生成顺序
        │   ├── office-modules.md           20+ 办公模块规格 + 6 个现成组合套餐
        │   ├── design-taste.md             配色 / 圆角 / 阴影纪律 + 3 档版式预设
        │   ├── library-integration.md      宿主能力适配、降级、冲突处理
        │   ├── iteration-and-data.md       迭代红线 + 加模块五步法 + CSV 导入
        │   └── worked-example.md           从需求到交付的完整走查 + 反面教材
        ├── assets/
        │   └── workspace-skeleton.html     骨架模板（1367 行，已通过全部校验）
        └── scripts/                        验证脚本
            ├── verify.py                   三道闸门一键入口
            ├── selftest.py                 检查器回归测试
            ├── smoke_check.py              静态检查
            └── runtime_smoke.js            运行时检查
```

## 依赖

| 项 | 是否必需 | 说明 |
|---|---|---|
| Python 3.8+ | 验证时需要 | 只用标准库，无需 pip 安装任何包 |
| Node.js | 可选 | 装了才能跑 JS 语法校验与运行时冒烟；没装会自动跳过并提示 |
| 宿主在线存储 / 网页发布能力 | 可选 | 可用则部署上线并多端同步；不可用则降级为纯本地存储 |

生成出来的工作台本身**零依赖**，浏览器打开即用。

## 交付前验证

一条命令跑完三道闸门：

```bash
python skills/office-workspace-builder/scripts/verify.py <生成的工作台.html>
```

| 闸门 | 脚本 | 作用 |
|---|---|---|
| 1 · 尺子自检 | `selftest.py` | 先验证检查器本身可信：对每个已知坏样本必须逐个报错，对基准骨架必须零误报 |
| 2 · 静态检查 | `smoke_check.py` | 外链、emoji 图标、调用环、渲染互调、DOM 缺失、模块数、移动端要点、设计同质化、版式预设、失败可见性、CSV 入口、文件完整性、JS 语法 |
| 3 · 运行时检查 | `runtime_smoke.js` | 用 DOM 桩真跑一遍内联 JS：初始化、示例数据、日期边界、交互链路、CSV 导入、存储写满告警、空数据不崩 |

也可分开跑：

```bash
python skills/office-workspace-builder/scripts/selftest.py                  # 尺子自检
python skills/office-workspace-builder/scripts/smoke_check.py  <file.html>  # 静态
node   skills/office-workspace-builder/scripts/runtime_smoke.js <file.html> # 运行时
```

仓库自带骨架的当前状态：**尺子自检 12/12 · 静态 25 PASS / 0 FAIL / 0 WARN · 运行时 72 PASS / 0 FAIL**。

> **为什么先跑「尺子自检」**：如果检查器自己坏了，它会对着一份烂代码报 PASS。所以每把尺子都必须被反测——先确认它认得坏样本，它的 PASS 才有意义。

## 13 条铁律

技能的核心是一份踩坑清单，完整版见 [`references/iron-rules.md`](skills/office-workspace-builder/references/iron-rules.md)，每条都附正误对照与代码模板。

| # | 铁律 | 要点 |
|---|---|---|
| 1 | 存储与部署 | 宿主在线存储优先，本地兜底；key 统一前缀 |
| 2 | 数据备份 | 导出 / 导入放首屏，导入走合并，清空要二次确认 |
| 3 | 全内联零外链 | 不引用任何 CDN / 字体 / 图表库；图标用内联 SVG |
| 4 | 移动适配 | 点击区 ≥44px，输入框 ≥16px，适配 iPhone 安全区 |
| 5 | 今天要处理 | 置顶区列逾期 / 今天 / 3 天内，逾期标红并支持一键顺延 |
| 6 | 预置示例数据 | 3–5 条，含 1 条逾期；首屏不能空白 |
| 7 | 规模闸门 | 单期 ≤4 个模块；超限先出分期方案；体量超限先写骨架再增量写入 |
| 8 | 国内习惯 | 支出红、收入绿，货币 ¥，优先级 P0/P1/P2 |
| 9 | 防调用环 | 单向 DAG，`refreshAll()` 统一刷新，渲染函数之间不互调 |
| 10 | 冒烟自检 | 三道闸门全过才交付；改动后必须重跑 |
| 11 | 设计不同质化 | 圆角分 3–4 档递级；阴影只给浮起层 |
| 12 | 失败必须可见 | 捕获后渲染成用户可见告警；可忽略的须显式声明 |
| 13 | 文件操作纪律 | 不删除任何文件；该删的列清单交用户处理；覆盖前先取得授权 |

## 兼容性

技能按「**抽象能力 ← 映射表 → 具体宿主**」的方式设计，不与任何单一平台绑定：

| 抽象能力 | 参考宿主对应物 | 其他宿主 |
|---|---|---|
| 在线网页发布 | 「资料库」技能 | 任意静态托管 |
| 在线数据表 | 「资料库」数据表 | Airtable / Notion DB / 云数据库 |
| 展示交付物 | `present_files` | 任意文件预览机制 |

换宿主时只需改映射表（`references/library-integration.md` 第 0 节），技能逻辑不变。

## 更新日志

见 [CHANGELOG.md](CHANGELOG.md)。

## 许可

[MIT](LICENSE) © 2026 盘锦奇点科技有限公司 (Panjin QYDION Technology Co., Ltd.)
