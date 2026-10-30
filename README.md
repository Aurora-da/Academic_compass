# 学业罗盘 · 学业情况分析智能体

> 面向本科生的「学分账本 + 选课参谋 + 毕业审核预演」智能体。
>
> **所有学分数字由 Python 约束引擎计算，LLM 只负责理解与表达。**
> 技术栈：**FastAPI + LangChain + LangGraph + Vue 3 + ECharts**。

本项目严格按《学业情况分析智能体设计方案 v1.2》落地，数据基准为
《2024 版 计算机科学与技术（拔尖班）培养方案》：

- 总学分 **169**，七个模块：38 / 10 / 44.5 / 22.5 / 6 / 17 / 31
- 弹性学制 3–6 年
- 毕业三条件：**修满 169 学分 ∧ 第二课堂合格 ∧ 毕业论文答辩合格**
- 示例学生验收值：**已获 124 / 缺口 45 / 在修 4 / 超修 1**，且专业任选课能正确报出
  **“总量差 2 分、模块 1 必选差 3 分”** 的结构缺口

![登录页](docs/screenshots/01-login.png)

---

## 1. 已实现的功能

### 学生端

| 页面 | 能力 |
|---|---|
| **学业总览** | 学分环形进度、四张统计卡、七模块进度、毕业三条件、风险雷达、本学期待办、学期缺口趋势、六维雷达 |
| **培养方案** | 模块树逐层下钻（all_of / any_of / free 三种模式）、要求/已获/未获得三数、结构缺口高亮、方向三选一、课程明细与状态 |
| **选课助手** | 方向比较与锁定、稳妥/均衡/冲刺三档课表、学分计量、时间冲突、先修检查、开课计划硬约束、课表预览、挂科 What-if、3/4/5 年毕业可行性预检 |
| **学业报告** | 学期汇总、快照 diff、模块明细、毕业三条件、第二课堂周期明细、风险与下一步，支持浏览器打印为 PDF |
| **第二课堂** | 四类周期进度（学年/学期/累计）、三态判定（达标/未达标/数据缺失）、登记活动、审核状态 |
| **数据导入** | 拖拽 PDF / Excel / Word / CSV / JSON、逐字段校对、置信度、课程匹配候选、插件 Canonical JSON 同步、导入历史 |
| **学业助手** | 全局悬浮，SSE 流式；节点级进度（理解 → 检查 → 计算 → 校验 → 组织），数字一致性校验，离线可用 |

### 管理员端

| 模块 | 能力 |
|---|---|
| **学业大盘** | 学生总数、平均完成度、风险学生、待处理队列、学生明细、模块缺口分布、风险摘要、方案哈希/引擎版本 |
| **映射审核** | 低置信度映射队列、目标课程确认、别名沉淀 |
| **第二课堂审核** | 学生登记记录通过/驳回，通过后计入周期 |
| **方案试算** | 用真实学生跑审核，对比快照“要求/获得/未获得”三列；一致性校验；冻结发布 |
| **开课计划** | 按学期查看课程、班级、教师、时间、容量 |

![学业总览](docs/screenshots/02-dashboard.png)

---

## 2. 设计文档 → 代码对照

| 设计方案 | 实现位置 |
|---|---|
| 第 4 章 总体架构、分层红线 | `backend/app/api`（契约）/ `services`（纯计算）/ `agent`（编排） |
| 第 5 章 数据基准、八条硬约束 | `backend/data/plans/CS-BT-2024-v1.yaml`、`backend/app/services/plan` |
| 第 6 章 领域模型 | `backend/app/models/entities.py`（17 张表） |
| 第 7 章 方案 DSL、规则原语 | YAML DSL + `loader.py` / `compiler.py` / `validator.py` |
| 第 8 章 文档导入 | `services/ingestion/{pdf,excel,docx,normalizer,documents}.py` |
| 第 9 章 学分审核引擎 | `services/audit/{evaluator,matcher,assigner,engine,second_classroom}.py` |
| 9.6 快照与 diff | `audit_snapshots` 表 + `engine.diff_snapshots` |
| 10 章 推荐引擎 | `services/planner/{filter,scorer,solver,feasibility,direction,recommendation_service}.py` |
| 10.4 毕业可行性 | `planner/feasibility.py`（3/4/5 年三情景） |
| 11 章 四级接入 | `integrations/adapters/{base,plugin,zf}.py` + 文件导入 |
| 12 章 LangGraph 编排 | `agent/graph.py`、`agent/nodes/*`、`agent/subgraphs/audit_graph.py` |
| 12.2 State / Checkpointer | `agent/state.py`、`AsyncSqliteSaver`（生产可换 PostgresSaver） |
| 12.9 防幻觉后置校验 | `agent/nodes/verify.py` + `compose` 模板注入 |
| 12.10 SSE 流式 | `POST /api/v1/chat/stream` |
| 13 章 学期报告 / 推送 | `ReportView.vue`、`jobs/semester_tick.py` |
| 14 章 产品界面 | `frontend/src/views/*`、`layouts/AppShell.vue` |
| 15 章 目录结构与接口 | `backend/app/{api,core,models,schemas,services,agent,integrations,jobs}` |
| 16 章 评测 | `backend/tests`：108 个用例，引擎红线 100% |

### 核心架构

```
┌──────────────────────────────────────────────────────────────┐
│ Vue 3 + ECharts   学生端 / 管理员端 / 全局学业助手            │
├──────────────────────────────────────────────────────────────┤
│ FastAPI   Routers · JWT · SSE · 静态资源 · 后台任务           │
├──────────────────────────────────────────────────────────────┤
│ LangGraph StateGraph                                         │
│ intake → guard → {plan | audit | recommend | chat}            │
│        → verify → (recompose → verify) → compose              │
│        audit 子图：match → assign → evaluate → check          │
├──────────────────────────────────────────────────────────────┤
│ Service 纯 Python（不 import LLM）                            │
│ PlanService · AuditEngine · Matcher · CP-SAT · Planner · RAG  │
├──────────────────────────────────────────────────────────────┤
│ SQLAlchemy 2.0 · SQLite（开发）/ PostgreSQL（生产）· 快照表   │
└──────────────────────────────────────────────────────────────┘
```

**红线执行**：

- `api/` 只做鉴权、参数校验和编排，不写学分算法；
- `services/` 不 import `langchain` / `langgraph`，可独立单测；
- `agent/` 只调用 service，不自己算学分；
- 所有数字来自引擎，`compose` 用模板注入；`verify` 校验封顶、缺口求和、预算、时间冲突、重复课程；
- 未配置 API Key 时，整张图仍可运行（离线模板），不会退回“把成绩单丢给大模型”。

---

## 3. 数据与验收

### 3.1 培养方案

`backend/data/plans/CS-BT-2024-v1.yaml` 从 PDF 逐表结构化：

- 7 个顶层模块、102 门课程、先修/同修关系、第二课堂周期要求、毕业三条件；
- 每门课含：课程编码、名称、学分、指导性学期（1-1…4-2）、考核方式、修读要求、课程类别、标签；
- 支持 `all_of` / `any_of` / `free` 三种模式，**父节点 `require` 独立于子项下限**；
- 校验器检查：顶层学分和 = 169、必修叶子课程学分和 = 模块要求、毕业条件学分一致、课程编码唯一、学期合法、any_of 子项可达父项下限。

### 3.2 示例学生

`backend/data/seeds/students.json` 中 `2023001 张三`：

| 指标 | 值 |
|---|---|
| 已获（封顶后） | 124.0 |
| 缺口 | 45.0 |
| 在修（不计入已获） | 4.0 |
| 超修（不计入总学分） | 1.0 |
| 模块 | 35 / 11 / 44.5 / 10.5 / 2 / 15 / 7 |
| M6 结构 | 总量 15/17（差 2），模块 1 必选 9/12（差 3） |
| 第二课堂 | 社会实践 ✅、创新实践 ✅、竞赛 0/1 ⚠️、学术研讨 1/2 ⚠️ |

验收测试：`cd backend && pytest` → **108 passed**，包含 all_of / any_of / free / 超修 / 在修 / 重考 / 退课 / 转方向 / 总量达标但结构不达标 / 第二课堂三态 / 周期边界 / 成绩单状态归一化 等。

![培养方案](docs/screenshots/03-plan.png)

---

## 4. 快速启动

### 4.1 环境要求

- Python **3.11+**（本机验证 3.12.14）
- Node.js **20+** / pnpm（或 npm）
- Windows / macOS / Linux 均可

### 4.2 后端

```bash
# 项目根目录
python -m venv .venv

# Windows
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# macOS / Linux
.venv/bin/pip install -r requirements.txt

# 可选：配置 LLM（不配也能跑，自动离线模板）
copy .env.example backend\.env
```

### 4.3 前端

```bash
cd frontend
pnpm install --node-linker=hoisted   # Windows 建议；或 npm install
pnpm build                           # 产物 frontend/dist
```

> 若 pnpm 提示 `Ignored build scripts: esbuild`，执行 `pnpm approve-builds` 勾选 esbuild，
> 或直接 `pnpm rebuild esbuild` 即可。Windows 使用 `node-linker=hoisted` 是为了避免 junction
> 软链导致的依赖解析问题。
>
> 已提供构建好的 `frontend/dist` 时，可跳过构建直接启动。
> 开发模式：`pnpm dev`（Vite 5173，代理 `/api` 到 8000）。

### 4.4 启动

```powershell
# Windows
.\start.ps1
```

```bash
# macOS / Linux
./start.sh
```

或手动：

```bash
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

打开 **http://127.0.0.1:8000**。API 文档：**http://127.0.0.1:8000/docs**。

### 4.5 演示账号

| 角色 | 账号 | 密码 | 说明 |
|---|---|---|---|
| 学生 | `2023001` | `123456` | 张三，完整示例（124/45/4，结构缺口） |
| 学生 | `2023002` | `123456` | 王五，嵌入式方向，合成数据 |
| 学生 | `2024002` | `123456` | 李四，大二，风险较高，方向未锁定 |
| 管理员 | `admin` | `123456` | 教务大盘、映射/第二课堂审核、方案试算 |

---

## 5. 页面预览

| | |
|---|---|
| ![选课助手](docs/screenshots/04-recommend.png) | ![学业报告](docs/screenshots/05-report.png) |
| ![第二课堂](docs/screenshots/06-second-classroom.png) | ![数据导入](docs/screenshots/07-import.png) |
| ![学业助手](docs/screenshots/08-assistant.png) | ![教务管理](docs/screenshots/09-admin.png) |

更多截图见 `docs/screenshots/`。

---

## 6. 关键实现说明

### 6.1 三层约束求值

```python
own_ok   = earned >= node.require
child_ok = all(c.ok for c in required_children)   # mode 决定
ok       = own_ok and child_ok
gap      = max(0, require - earned)               # 只反映节点自身下限
```

- `all_of`：子项全部通过，父项只查自身下限；
- `any_of`：只认 `picked` 方向，支持“换方向会怎样”；
- `free`：只对 `require > 0` 的子项判定，无下限子项只做归属统计；
- 方向锁定写入 `plan_overlay`，审核与推荐都按锁定方向计算；
- 总学分按模块封顶：`Σ min(earned_i, require_i)`；在修单独口径。

### 6.2 推荐引擎

1. **硬约束**：当学期 offering、先修、已通过、时间冲突、学分上限、年级限制、容量；
2. **优先级打分**：必修缺口、关键路径、模块紧迫度、方向课、结构优先、负载、难度；
3. **组合求解**：稳妥 20 / 均衡 24 / 冲刺 28（含在修），输出理由与后果；
4. **毕业可行性**：3/4/5 年三个情景，按剩余学期均摊并检查目标毕业前开课；
5. **学分归属**：`assigner.py` 优先 OR-Tools CP-SAT，缺失时退化为确定性贪心。

### 6.3 LangGraph

- `intake`：规则 + LLM 结构化输出（Pydantic `IntentResult`）；
- `guard`：数据就绪检查，缺成绩转 chat 引导导入；
- `audit`：子图 `match → assign → evaluate → check`，纯计算，0 token；
- `recommend`：规则引擎 + LLM 写理由；
- `verify`：封顶、缺口和、预算、时间冲突、重复课程、先修；
- `recompose`：只修正数字事实，最多 1 次；
- `compose`：关键数字模板注入，可附 LLM 共情开场（出现数字则丢弃）；
- `confirm_mapping`：`interrupt()` 人在环，确认后回边重算；
- Checkpointer：`AsyncSqliteSaver`，`thread_id = student_id:session_id`，支持多轮复用；
- SSE：节点级进度 + 最终答案分片。

### 6.4 防幻觉

- 审核/推荐/报告全部走 Python；
- 聊天“规章问答”只检索知识库，不回答“你差多少”（路由到审核）；
- `verify` 校验数字一致性；失败走 `recompose`，再失败降级模板；
- 所有结论标注“预演，以教务处终审为准”。

---

## 7. API 概览

```
POST /api/v1/auth/login
GET  /api/v1/auth/me
GET  /api/v1/auth/demo-accounts

GET  /api/v1/plans
GET  /api/v1/plans/{plan_id}
GET  /api/v1/plans/{major}/{grade}
GET  /api/v1/plans/{plan_id}/validation

GET  /api/v1/students/me
GET  /api/v1/students/me/audit?semester=&save=
GET  /api/v1/students/me/recommend?semester=&max_credits=
POST /api/v1/students/me/simulate
GET  /api/v1/students/me/report
GET  /api/v1/students/me/snapshots
GET  /api/v1/students/me/diff
GET  /api/v1/students/me/second-classroom
POST /api/v1/students/me/second-classroom
POST /api/v1/students/me/direction

GET  /api/v1/recommend/me
GET  /api/v1/audit/me
POST /api/v1/audit/simulate

POST /api/v1/documents
GET  /api/v1/documents
POST /api/v1/documents/{id}/review
POST /api/v1/documents/plugin

POST /api/v1/chat
POST /api/v1/chat/stream      # SSE
GET  /api/v1/chat/history

GET  /api/v1/admin/dashboard
GET  /api/v1/admin/mappings
POST /api/v1/admin/mappings/{id}/confirm
GET  /api/v1/admin/second-classroom
POST /api/v1/admin/second-classroom/{id}/review
GET  /api/v1/admin/plans
POST /api/v1/admin/plans/{id}/trial
POST /api/v1/admin/plans/{id}/publish
GET  /api/v1/admin/offerings
```

---

## 8. 目录结构

```
backend/
  app/
    main.py                 FastAPI 入口、静态资源、lifespan
    seed.py                 方案/学生/开课/快照种子
    api/v1/                 auth students plans audit recommend documents chat admin
    core/                   config security db logging
    models/                 17 张 SQLAlchemy 表
    schemas/                Pydantic 请求/响应
    services/
      plan/                 loader compiler validator plan_service terms
      audit/                evaluator matcher assigner engine second_classroom
      planner/              filter scorer solver feasibility direction recommendation_service
      ingestion/            pdf excel docx normalizer documents
      rag/                  BM25 规章知识库
    agent/
      state.py graph.py
      nodes/                intake guard route plan_node audit_node recommend_node
                            verify recompose compose confirm chat
      subgraphs/            audit_graph
      prompts/              system extract
    integrations/adapters/  base plugin zf
    jobs/                   sync semester_tick
  data/
    plans/CS-BT-2024-v1.yaml
    seeds/students.json offerings.json
    knowledge/regulations.md
  tests/                    108 个用例
frontend/
  src/
    layouts/AppShell.vue
    components/             AuroraBackground CreditRing EChart PlanTreeNode AssistantPanel ...
    views/                  Login Dashboard Plan Recommend Report SecondClassroom Import Admin
    stores/                 auth meta toast
    styles/                 tokens base effects
    api/index.js
docs/screenshots/           验收截图
```

---

## 9. 测试

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest
# 108 passed
```

覆盖：

- 学分数值红线（169/124/45/4/1）；
- all_of / any_of / free、锁定方向、换方向、超修、在修、重考、退课；
- 总量达标但结构不达标、父项 gap 与子项 gap 分离；
- 第二课堂三态、学年/学期边界、待审核不计入；
- 学期换算、毕业时点、剩余学期、3/4/5 年可行性；
- 课程匹配 L1/L2/L3/pending、别名、语义相似度；
- 方案 DSL 一致性校验；
- 推荐预算、时间冲突、锁定课程、先修过滤。

---

## 10. LLM 配置（可选）

在 `backend/.env` 中配置任意 OpenAI 兼容端点：

```env
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

- 未配置：`/api/v1/meta` 返回 `llm_enabled=false`，前端显示“离线模板”；所有页面与对话仍可用；
- 配置后：intake / chat / recommend 理由 / compose 开场白走模型；数字仍由引擎提供，`verify` 失败会降级模板；
- LangSmith 可自行加 `LANGCHAIN_TRACING_V2`，当前默认关闭。

---

## 11. 与设计方案的边界与差异

为便于单机运行与验收，以下为有意选择的工程化折中，均已在代码中隔离：

| 设计 | 当前实现 | 说明 |
|---|---|---|
| PostgreSQL 16 + pgvector | 开发默认 SQLite；`DATABASE_URL` 可切 PG | 生产建议 PG；SQL 层已用 SQLAlchemy 2.0 |
| `PostgresSaver` | `AsyncSqliteSaver` | 接口一致，切换只改 `main.py` lifespan |
| bge-m3 + pgvector 检索 | 中文 BM25 + 标题分块 | `services/rag` 可替换 retriever，不影响 Agent 图 |
| CP-SAT 推荐组合 | 启发式三档 + CP-SAT 学分归属 | `assigner.py` 已是 CP-SAT；组合求解可替换 |
| PDF 双栏校对 UI | 后端解析 + 逐字段校对表 | 双栏原文高亮未做完整 UI；导入/校对/入库闭环可用 |
| 浏览器插件 | Canonical JSON 接口 + Adapter 抽象 | 插件本体未实现，接口已就绪 |
| 教师端 | 未做，`role=teacher` 预留 | 与设计一致 |
| Redis / Celery | 同步任务 CLI，可接 APScheduler/Celery | `jobs/sync.py` / `semester_tick.py` 已提供 |

**刻意保留的实现细节**（设计强调的红线）：

- 不把“在修”算进“已获”；
- 不把父节点 `require` 实现成子项求和；
- 不让 LLM 算任何学分；
- 不承诺“一定毕业/一定选上”；
- 所有结论带“预演，以教务处终审为准”。

---

## 12. 后续路线

1. 接入真实教务 Adapter（强智/正方）与浏览器插件；
2. 方案 PDF 双栏校对 + 多专业版本管理；
3. PGVector + bge-m3 替换 BM25，支持规章引用定位；
4. 推荐组合 CP-SAT 化，支持学生偏好（时段/教师/难度）；
5. 学期主动巡检与消息推送（企业微信/服务号）；
6. 教师/辅导员视图（班级预警、课程通过率）。

---

*本项目以“算得准”为第一优先级，“说得清”为第二，“接得进”为第三。*


