# 分析指引

给 Agent 用的短清单。不要把本文暴露给最终用户。

## 先定仓库形态

形态决定叙事，不要强行套成 Web App：

- 终端产品 / 应用
- 库或 SDK
- CLI / 开发者工具
- 服务或分布式系统
- 数据 / ML 流水线
- 基础设施 / 配置
- Monorepo（先讲包边界）

## 调查顺序

1. 项目自我描述（README、docs）→ 当假说
2. 清单文件（package.json、go.mod、pyproject、Cargo.toml、workspace）→ 边界
3. 可执行入口与公开 API
4. 组合根（main、bootstrap、DI、router 注册）
5. 抽 1～3 条真实路径，顺着调用读下去
6. 状态、持久化、外部系统、队列、构建/发布边界
7. 测试里能证明意图的例子

每条架构关系、每个流程步骤，尽量落到 `path:行号`。编不出来就写进「未知」。

## 页面叙事（自顶向下）

1. **一句话**：它解决谁的什么问题
2. **心智模型**：系统如何转起来（3～6 句）
3. **结构**：模块与关系（Mermaid flowchart）
4. **动态**：一次真实流程（flowchart 或 sequenceDiagram）
5. **语言**：项目特有概念
6. **入口**：先打开哪些文件
7. **路径**：按什么顺序学
8. **边界**：还不知道什么

少而准。宁可缺章节，不要空章节。

## 图表

默认 **Mermaid**（Agent 好写、版式稳定）。填进模板的 `{{ARCHITECTURE_MERMAID}}` / `{{FLOW_*_MERMAID}}`。

| 图种 | 何时用 |
|------|--------|
| `flowchart LR` / `TB` | 架构、模块关系、生命周期 |
| `sequenceDiagram` | client / api / worker 等多角色协作 |
| `flowchart` 子图 `subgraph` | 清晰分层时再用，别堆砌 |

示例（架构）：

```mermaid
flowchart LR
  ingest[Ingest 采集] -->|快照| graph[Graph 实体]
  graph -->|索引| retrieve[Retrieve 问答]
```

原则：

- 节点用项目自己的名字，不用空泛的 Frontend / Backend（除非仓库就这么叫）
- 边写短标签（调用、发布、读写…）
- 图与正文说同一件事；图不是装饰
- 节点大约 ≤12；太大就拆图或只画核心
- 不要手搓 SVG 坐标，除非 Mermaid 表达不了且用户明确要求

## 文案语气

冷静、精确、可亲近。像一位靠谱同事在白板上讲，而不是营销稿或审计报告。

## 页面气质（对齐模板）

浅色编辑部研报：纸色底 `#FBFAF7` + 青绿强调 `#0E6E6E`，Source Serif / Inter，sticky 顶栏用短章节名锚点（心智模型 / 架构 / …），masthead + KPI 栅格，章节 `sec-head`，Mermaid 嵌在浅底 panel。不要退回暗色霓虹图鉴，也不要发灰的「说明书默认皮」。

KPI（形态 / 入口 / 置信度 / 范围）填不上就删掉整块 `.stats`，不要留空壳。