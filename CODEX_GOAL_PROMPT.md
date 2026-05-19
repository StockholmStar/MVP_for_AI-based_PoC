# Codex /goal 提示词 - AI 产品工作台 PoC

> 用法：把下方「给 Codex /goal 模式的提示词」整段复制到 Codex 的 `/goal` 模式中执行。  
> 目标：让 Codex 基于 LangGraph 搭建一个可演示的 AI 辅助、多 Agent 产品工作台 PoC。

---

# 给 Codex /goal 模式的提示词

你是一名可以自主执行任务的资深全栈工程师，也熟悉 AI Agent 系统架构。

请搭建一个可以在云端或 Linux 服务器上运行的 PoC Web 平台，名称为 **AI Product Workspace**。平台需要支持通过局域网或公网地址从另一台电脑访问。

这个平台需要演示一个基于 **LangGraph** 的多 Agent 产品开发工作流，帮助产品经理把一个粗略产品想法转化为一组互相对齐的产品产出物，包括：PRD、UX flow、交互式原型、一致性检查报告、QA 验收标准和 Jira story 草稿。

这是 PoC，不是生产级系统。请优先保证：演示能跑通、架构清楚、端到端流程可用，并且可以在 Linux 服务器上启动服务后从另一台电脑访问。不要为了企业级完整性过度设计。

## 1. 产品背景

目标用户是软件产品经理，尤其是手机系统软件产品经理。

平台需要支持以下产品工作流：

`产品想法 → 需求澄清 → PRD 草稿 → UX flow → 交互式 HTML 原型 → PRD 与原型一致性检查 → QA 验收标准 → Jira story 草稿`

核心价值是 **产品产出物之间的一致性对齐**：

- PRD 和原型不能各写各的、各改各的。
- UX flow 需要同时体现在 PRD 和原型里。
- QA 验收标准需要覆盖关键状态、边界场景和验收条件。
- Jira story 需要能追溯到对应的 PRD 章节和原型页面。

这个平台不只是一个 AI PRD 生成器。它是一个平台级的多 Agent 产品工作台，用来对齐产品、设计、研发和 QA 的关键产出物。

## 2. 参考工作流

请参考 `arcsin1/pm-agile-workflow` 的 7 步工作流，但不要简单复制它。

参考流程如下：

1. 对话式需求澄清
2. 初始化项目和产出物目录结构
3. 生成初版 PRD
4. 生成交互式 HTML 原型
5. 生成 Mermaid 流程图
6. 生成嵌入原型切片的最终版 PRD
7. 版本化迭代管理

请把这个思路升级成一个由 LangGraph 编排的 Web 平台。

## 3. MVP 范围

请先搭建第一版 PoC，包含以下能力。

### 本次需要实现

- Web 产品工作台
- 左侧项目 / 文档导航
- 主区域左侧展示 PRD 内容
- 主区域右侧展示原型预览
- 底部 Agent 对话框 / 指令输入框
- 后端使用 LangGraph 编排多个逻辑 Agent
- 根据产品想法生成 PRD 草稿
- 生成 UX flow 和 Mermaid 流程图
- 生成单文件交互式 HTML 原型
- 原型尽量支持 `?focus=<feature_id>` 和 hash 路由，用于聚焦展示某个功能点
- 生成 PRD 与原型一致性检查报告
- 生成 QA 验收标准
- 生成 Jira story 草稿，格式可以是 JSON / Markdown，不需要调用真实 Jira API
- 支持基础项目版本管理，例如 v1.0、v1.1
- 将生成的产出物保存到本地
- 内置一个手机系统软件功能的 demo case，方便直接演示

### 本次不需要实现

- 生产级登录认证
- 多人协作
- 真实 Figma API 集成
- 真实 Jira API 集成
- 企业 SSO
- 完整 RAG / 向量数据库
- 真实 Android 代码生成
- 真实手机端构建流水线
- 复杂权限模型

可以先使用 mock 集成，但代码结构要方便后续接入真实 Figma、Jira 和知识库。

### 云端运行要求

MVP 不是只给开发者本机 localhost 使用。它需要能部署或运行在一台 Linux 服务器上，并允许用户用另一台电脑通过浏览器访问。

最低要求：

- 前端服务支持绑定 `0.0.0.0`。
- 后端服务支持绑定 `0.0.0.0`。
- 前端可以通过环境变量配置后端 API 地址，例如 `NEXT_PUBLIC_API_BASE_URL`。
- README 需要说明如何在 Linux 服务器上启动前端和后端。
- README 需要说明如何通过 `http://<server-ip>:<port>` 从另一台电脑访问。
- 如实现成本不高，提供 Docker Compose；如果时间不够，至少提供清晰的非 Docker 启动方式。

## 4. 推荐技术栈

除非有明确理由，否则请使用以下技术栈。

### 前端

- Next.js
- React
- TypeScript
- Tailwind CSS

### 后端

- FastAPI
- Python
- LangGraph
- LangChain 仅在模型封装或工具封装有帮助时使用，不要为了使用而使用

### 存储

第一版采用本地优先的简单方案：

- 使用 SQLite 存储项目、运行记录和产出物元数据
- 使用本地文件保存生成的产出物
- 建议目录结构：
  - `data/projects/<project_id>/requirements/`
  - `data/projects/<project_id>/prototypes/`
  - `data/projects/<project_id>/flows/`
  - `data/projects/<project_id>/qa/`
  - `data/projects/<project_id>/jira/`
  - `data/projects/<project_id>/reviews/`

### 大模型调用

请创建一个模型调用抽象层。

- 如果环境变量中配置了 API key，则支持 OpenAI-compatible API。
- 如果没有 API key，则提供确定性的 mock 输出，保证 demo 仍然可以端到端跑通。

不要在代码里硬编码任何密钥。

## 5. 产品工作台 UI

请搭建一个清爽、可演示的 Web UI，布局如下。

### 左侧栏：项目和产出物导航

展示以下内容：

- 项目列表
- 当前项目
- 产出物列表：
  - PRD
  - Prototype
  - UX Flow
  - Consistency Review
  - QA Criteria
  - Jira Stories
- 如已有版本，展示版本列表

### 主内容区

主内容区分为左右两个大面板。

#### 左侧面板：PRD 工作区

展示生成的 PRD 内容。可以使用 Markdown 渲染，也可以使用 HTML 渲染。

PRD 至少需要包含：

- 产品概述
- 背景和问题定义
- 目标和非目标
- 目标用户和使用场景
- 用户旅程
- 功能需求
- 关键状态和边界场景
- 验收标准
- 待确认问题

#### 右侧面板：原型工作区

用 iframe 展示生成的交互式 HTML 原型。

原型至少需要包含：

- 2-3 个页面或状态
- 主用户流程
- loading 状态
- empty 状态或 error 状态
- success 状态
- 基础点击交互
- 如果提供了 `feature_id`，尽量支持 focus mode

### 底部区域：Agent 对话框 / 指令栏

用户可以输入产品想法或指令，例如：

- `为智能通知摘要功能生成 PRD 和原型。`
- `增加网络错误状态。`
- `检查 PRD 和原型是否一致。`
- `生成 Jira stories。`

对话框需要展示工作流进度和最终响应。

## 6. LangGraph 工作流

请实现一个 LangGraph 工作流，并使用共享的 `ProductState`。

### ProductState 至少包含

- `project_id`
- `user_input`
- `product_idea`
- `clarification_questions`
- `assumptions`
- `prd_markdown`
- `ux_flow_markdown`
- `mermaid_flowchart`
- `prototype_html`
- `feature_map`
- `consistency_report`
- `qa_criteria`
- `jira_stories`
- `open_questions`
- `version`
- `status`
- `errors`

### 逻辑 Agent 节点

请把以下节点实现为独立函数或类。

#### 1. 需求澄清 Agent

职责：

- 理解用户输入的粗略产品想法
- 识别缺失信息
- 生成假设和澄清问题

输出：

- 当前理解
- 假设
- 3-7 个澄清问题

PoC 阶段不要因为等待用户回答而阻塞整个流程。可以基于合理假设继续往下生成，但必须清楚标注待确认问题。

#### 2. PRD Agent

职责：

- 生成结构化 PRD 草稿
- 让 PRD 对 PM、UX、研发和 QA 都有 review 价值

输出：

- PRD Markdown
- 功能需求章节
- 验收标准
- 待确认问题

如果 demo case 是手机系统软件功能，需要包含以下手机系统产品考虑项：

- 功能出现在哪个系统界面或入口，例如 Launcher、Lock screen、Notification shade、Settings、Home screen、-1 screen
- 权限和隐私处理
- 离线、无数据、错误等状态
- 性能、功耗和内存影响
- 如相关，说明区域、机型、Android 版本或 OTA 约束
- owner 边界假设，例如 Launcher、System UI、app team、data/logging、QA

#### 3. UX Flow Agent

职责：

- 生成用户旅程和 UX flow
- 生成 Mermaid 流程图

输出：

- UX flow Markdown
- Mermaid 流程图
- 用于原型 focus mode 的 feature ID

#### 4. Prototype Agent

职责：

- 生成单文件交互式 HTML 原型

输出：

- `prototype_vX.X.html`

要求：

- 使用 Tailwind CSS CDN 或内嵌 CSS
- 使用简单 JavaScript 实现页面切换和状态变化
- 包含可点击交互
- 包含关键状态：default、loading、empty/error、success
- 尽量支持 `?focus=<feature_id>`
- feature ID 需要和 PRD 章节对应

#### 5. 一致性检查 Agent

职责：

- 检查 PRD、UX flow 和原型是否一致

输出：

- 一致性检查报告，覆盖：
  - PRD 中有但原型缺失的需求
  - 原型中有但 PRD 未描述的元素
  - 缺失的边界场景
  - 缺失的验收标准
  - 待确认问题
  - 建议修正项

#### 6. QA 验收标准 Agent

职责：

- 生成测试场景和验收标准

输出：

- QA 验收标准 Markdown
- 需要包含正常路径、边界场景、失败状态、权限状态和回归风险

#### 7. Jira Story Agent

职责：

- 生成 Jira 风格的交付条目，但不调用真实 Jira API

输出：

- JSON 和 Markdown 格式的 story 草稿
- 每条 story 至少包含：
  - Epic / Story 标题
  - User story
  - 描述
  - 验收标准
  - 依赖项
  - 关联 PRD 章节
  - 关联原型 feature ID

#### 8. Orchestrator / Router

职责：

- 路由工作流
- 维护状态
- 处理错误
- 决定什么时候运行检查节点或生成节点

第一版 PoC 可以采用线性工作流：

`START → 需求澄清 → PRD → UX flow → 原型 → 一致性检查 → QA 验收标准 → Jira stories → 保存产出物 → END`

如果实现成本不高，可以再增加简单条件路由。

## 7. Human-in-the-loop 设计

即使第一版 PoC 不实现完整审批 gates，也要把代码设计成后续可以加入人工确认。

建议后续支持的 gates：

- 生成原型前确认 PRD
- 生成 Jira story 前确认原型
- 推送到真实 Jira 或 Figma 前需要人工批准

PoC 阶段可以先在 UI 上展示审批状态或占位标签。

## 8. 版本管理要求

实现简单版本管理。

- 新项目从 `v1.0` 开始
- 每次主要重新生成可以创建新版本，例如 `v1.1`
- PRD、原型、流程图、QA 验收标准和 Jira stories 应使用相同版本号
- 未经用户明确操作，不要覆盖历史产出物

建议产出物命名：

- `prd_v1.0.md`
- `prototype_v1.0.html`
- `flowchart_v1.0.md`
- `consistency_review_v1.0.md`
- `qa_criteria_v1.0.md`
- `jira_stories_v1.0.json`

## 9. 知识库 / Context Pack MVP

V1 不需要建设完整 RAG 系统。

请在 `context/` 目录下创建轻量 context pack，例如：

- `context/smartphone_system_pm_checklist.md`
- `context/design_system_guidelines.md`
- `context/qa_review_checklist.md`
- `context/jira_story_template.md`
- `context/sample_prd.md`

Agent 需要读取这些文件，并把它们作为额外上下文使用。

手机系统 PM checklist 需要提醒 Agent 考虑：

- 用户界面和功能入口
- owner 边界
- 权限和隐私
- loading / empty / error / no permission / offline 状态
- 性能、功耗、内存和稳定性
- 区域、机型、Android 版本和 OTA 约束
- 如相关，考虑埋点和数据分析

## 10. 内置 demo case

请内置一个 demo case，保证平台可以立即演示。

建议 demo case：

**Smart Notification Summary**

这是一个手机系统软件功能，用来汇总低优先级通知，并以更清爽的通知体验展示给用户。

生成 PRD 和原型时需要考虑：

- Notification shade 入口
- Settings 入口
- 摘要卡片
- 用户控制，例如 opt-in 或 settings toggle
- 权限和隐私问题
- empty 状态
- error 状态
- 用户与摘要卡片的交互
- QA 验收标准
- Jira story 草稿

如果这个 case 过于复杂，可以换成更简单的手机系统软件功能，但平台本身仍要保持通用。

## 11. API 要求

请创建类似以下后端 API：

- `POST /api/projects` - 创建项目
- `GET /api/projects` - 获取项目列表
- `GET /api/projects/{project_id}` - 获取项目详情
- `POST /api/projects/{project_id}/runs` - 基于用户输入运行 LangGraph 工作流
- `GET /api/projects/{project_id}/artefacts` - 获取产出物列表
- `GET /api/projects/{project_id}/artefacts/{artefact_id}` - 获取产出物内容
- `GET /api/projects/{project_id}/prototype/{version}` - 返回指定版本的原型 HTML

具体 API 结构可以根据实现情况调整，但必须在 README 里说明。

## 12. 工程质量要求

- 代码结构要清楚，方便阅读。
- 添加清晰的 README，说明安装、运行和演示方式。
- 提供 `.env.example`。
- 如可行，为后端工作流函数添加基础测试。
- 避免过度设计。
- 使用 mock LLM 输出兜底，保证 demo 稳定可跑。
- 前端和后端服务需要支持绑定 `0.0.0.0`，方便在 Linux 服务器上通过 IP + 端口从另一台电脑访问。
- README 需要说明本地访问和服务器访问两种启动方式。
- 提供 seed data 或一键 demo 脚本。
- 确保应用可以在 Linux 服务器上运行，并可通过浏览器远程访问。

## 13. 交付物

完成后需要提供：

1. 可运行的代码仓库
2. 前端应用
3. FastAPI 后端
4. LangGraph 工作流实现
5. 本地存储结构
6. 内置 demo case
7. 包含安装、运行和演示说明的 README
8. 简短架构说明
9. 已知限制和下一步建议

## 14. 验收标准

如果满足以下条件，则 PoC 成功：

- 用户可以在本地打开 Web 应用。
- 用户可以创建或打开 demo 项目。
- 用户可以在 Agent 对话框中输入粗略产品想法。
- 后端可以运行 LangGraph 工作流。
- 平台可以生成 PRD 草稿。
- 平台可以生成 UX flow 和 Mermaid 流程图。
- 平台可以生成交互式 HTML 原型。
- 原型可以在右侧 iframe 中展示。
- 平台可以生成 PRD 与原型一致性检查报告。
- 平台可以生成 QA 验收标准。
- 平台可以生成 Jira story 草稿。
- 产出物可以按版本号保存在本地。
- README 能说明如何运行和演示系统。

## 15. 重要产品原则

不要只优化成一个看起来很酷的 AI demo。

请优化成一个对 PM 真有用的工作流，能在正式评审前暴露需求缺口、UX 状态不清、工程风险和 QA 覆盖不足等问题。

核心产品信息是：

> 更高质量的前期产品产出物，可以减少后续跨角色对齐成本和返工成本。

## 16. 第一版实现计划

请按小步推进：

1. 创建代码仓库结构。
2. 搭建 FastAPI 后端骨架。
3. 加入带 mock 模型输出的 LangGraph 工作流。
4. 加入本地存储和产出物保存能力。
5. 搭建前端页面布局。
6. 将对话框输入连接到后端工作流运行接口。
7. 在工作台中渲染 PRD 和原型。
8. 增加一致性检查、QA 验收标准和 Jira story 视图。
9. 增加内置 demo case。
10. 增加 README 和基础测试。
11. 运行应用并修复错误，直到 demo 可以端到端跑通。

不要只停留在架构设计。请搭建一个可以在 Linux 服务器上运行、并能从另一台电脑通过浏览器访问的 PoC。

---

# 给 Felix 的使用说明

这份提示词的目标不是让 Codex 一次性搭出完整企业平台，而是让它先搭一个能在 Linux 服务器上跑通、并能从另一台电脑访问的云端 PoC。

第一轮验收建议只看三件事：

1. Web 工作台能否在 Linux 服务器上启动，并能从另一台电脑打开和跑 demo。
2. LangGraph workflow 是否真的串起 PRD、prototype、review、QA、Jira draft。
3. 输出物是否能体现手机系统软件 PM 的场景，而不是泛泛的 Web 产品 PRD。

第一版先 mock Figma / Jira 是合理的。等 PoC 证明 workflow 有价值，再考虑真实集成。
