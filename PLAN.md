## Me

我要做一个AI出题智能体系统。

目前的技术选型：
前端我使用streamlit，后端使用fastapi和langgraph。
文档解析和转换使用pandoc。

1. 我已经基于Flag Embedding和fastapi搭建了一个embedding service微服务，用来提供embedding api服务，因为我使用的是BGE-M3，所以我的api可以同时支持dense和sparse embedding。
2.我使用neo4j llm graph builder 搭建了另外一个微服务，可以用来提供从文档到知识图谱构建的过程，并且他提供了一系列的知识图谱和图数据库相关的API
2. 我打算使用pgsql来保存从教材中提取出来的例题和我们的系统自己生成的例题。

目前打算使用 1 2 3 三个外部存储库作为智能体的外部数据来源， 搭建两种类型的智能体

1. 第一种是出题智能体：比如单选题出题智能体， 解答题出题智能体。
2. 第二种是试卷出题智能体：这应该是一种multi agent系统，因为试卷往往由多种类型的题目构成，所以可以复用第一种出题智能体。

智能体和外部数据来源交互最简单的方式是使用RAG，那么在向量数据库上我选择使用milvus，并且结合混合检索，因为我使用了BGE-M3作为embedding model，同时结合graph rag，因为我使用了neo4j。

功能需求：
 利用出版社已有教材（如章节内容、例题解析、练习题设计原理）构建AI出题智能体，解决在无大规模样例题微调情况下，生成高质量、学段契合、知识点匹配、干扰项合理的客观题（如选择题）和主观题。关键难点攻克方向：

       （1）教材或学科的知识抽取（知识点、能力目标、常错点提取）。

       （2）优化出题语言风格、可控出题难易度。

       （3）干扰项设计逻辑建模（模拟错误思路）。

       （4）在学段合理范围内控制模型输出题目的“解题负担”。

我希望你帮我把目前的这份需求进行拆解， 看看我的技术选型能否覆盖这些需求？

## ChatGPT 5.2

这是一个非常成熟、工程与研究边界都很清晰的 AI 出题智能体系统设想。我会不改变你现有技术路线，而是从**“需求 → 能力 → 组件映射 → 缺口与增强点”**四个层面，系统性拆解，回答你最核心的问题：

你现在的技术选型，是否能够覆盖这些需求？如果能，覆盖到哪一层？如果不能，差的是什么？

⸻

一、总体判断（先给结论）

结论一句话版：

👉 你的技术选型在“数据层 + 检索层 + 编排层 + Agent 形态”上是完全正确且先进的，
👉 真正的难点不在“技术栈缺失”，而在“智能体能力拆解 + 中间表征设计 + 控制信号注入”。

换句话说：
 • ❌ 不需要推翻你的选型
 • ✅ 需要在 LangGraph Agent 设计层和中间数据结构上补 4 个关键模块

下面我详细拆解。

⸻

二、需求 → 能力拆解（抽象成 6 个“核心能力块”）

你给的 4 点“关键难点”，实际上可以抽象为 6 个能力模块：

编号 能力模块 本质
C1 教材知识结构化 把“教材”变成“可推理对象”
C2 出题约束建模 把“出题要求”变成“显式控制信号”
C3 题目生成 生成题干 / 选项 / 问题
C4 干扰项建模 模拟错误认知路径
C5 难度与解题负担控制 认知负载与学段对齐
C6 试卷级协同编排 Multi-Agent 协作

你目前的 1/2/3 组件，主要覆盖的是 C1 的“数据基础层” + C6 的“可扩展性基础”。

⸻

三、你的技术选型逐项对照能力覆盖情况

1️⃣ 文档 → 知识 → 向量 / 图（C1：教材知识结构化）

你已有的能力

组件 覆盖点
Pandoc 教材结构化解析（章节 / 段落 / 例题）
BGE-M3 + Embedding Service 语义向量化（dense + sparse）
Milvus（混合检索） 概念 /表述/例题相似度检索
Neo4j LLM Graph Builder 知识点、关系、例题—知识映射

✅ 这一层你做得非常好，而且是“出题系统”的地基

但这里有一个非常关键的隐性缺口
❗ 你现在“抽的是知识”，但还没“抽出教学认知属性”

教材里其实有 4 类信息你需要显式建模：

（1）知识点
（2）能力目标（理解 / 应用 / 迁移）
（3）常错点（错误概念 / 错误推理）
（4）典型题型意图（训练什么）

📌 建议你在 Neo4j 中显式引入如下节点类型：

(:KnowledgePoint)
(:SkillTarget)        // 如：计算能力、概念辨析
(:Misconception)     // 常错点
(:QuestionIntent)    // 出题意图

并建立关系：

(KnowledgePoint)-[:LEADS_TO_ERROR]->(Misconception)
(QuestionExample)-[:TARGETS]->(SkillTarget)
(QuestionExample)-[:ILLUSTRATES]->(KnowledgePoint)

👉 这一步是你后面“干扰项设计”和“难度控制”的基础。

⸻

2️⃣ 出题智能体（C2 + C3）

你提出的：

单选题出题智能体、解答题出题智能体

这是正确的 Agent 粒度。

你现有选型的覆盖能力

能力 是否覆盖 说明
Agent 编排 ✅ LangGraph 非常适合
数据访问 ✅ RAG + GraphRAG
出题生成 ✅ LLM 本身

但你现在还缺一个“中间态”
❌ 目前你是：RAG → LLM → 题目文本

你真正需要的是：

RAG
 ↓
【出题规划状态（结构化）】
 ↓
题目生成

📌 建议定义一个 QuestionPlan（中间表征）：

{
  "knowledge_points": [...],
  "skill_level": "应用",
  "difficulty": 0.6,
  "student_stage": "初中二年级",
  "common_mistakes": [...],
  "question_type": "single_choice",
  "solution_steps_limit": 3
}

👉 LangGraph 中的每个 node 只负责填充一部分 Plan。

⸻

3️⃣ 干扰项设计（C4）

这是你需求中最难、也是最有研究价值的一点。

你的技术是否支持？
✅ 支持，但必须“显式建模错误”

组件 能否支持
Neo4j ✅（建模错误路径）
BGE-M3 ✅（错误语义相似度）
LangGraph ✅（多步推理）

推荐的干扰项生成逻辑（非常重要）
不是“让 LLM 编 3 个错误选项”

而是：

正确解题路径
 ↓
每一步 → 可发生的错误
 ↓
错误结果
 ↓
干扰项文本

📌 你可以在 Neo4j 中维护：

(Misconception)-[:PRODUCES]->(WrongAnswerPattern)

然后：
 • GraphRAG：检索与当前知识点相关的错误模式
 • LLM：将错误模式“语言化”为干扰项

⸻

4️⃣ 难度与“解题负担”控制（C5）

这是大多数系统做不到，但你是有条件做到的。

技术是否覆盖？

控制点 是否可实现
难度分级 ✅
学段对齐 ✅
解题步骤控制 ⚠️ 需要显式设计

## 里程碑计划（功能优先 + 最小数据定义）

### 阶段 1：系统骨架可运行（最小闭环）

**目标**

- API + UI 可运行并互通
- 用户能在 UI 看到 API 健康状态

**依赖**

- FastAPI、Streamlit、uv
- 不依赖 Postgres / Milvus / Neo4j

**产出**

- API: `GET /health`, `GET /version`
- UI: 首页健康检查模块
- 配置: API base url

**需要做什么**

- API: 若已有 `/health`，新增 `/version`
- UI: 首页显示健康状态与版本

**如何测试**

- 手动: 访问 `/health`、`/version`，UI 显示结果
- 可选: 添加最小 API 测试用例

**验收标准**

- API 返回健康和版本
- UI 展示健康检查结果

### 阶段 2：文档上传与列表

**目标**

- 支持上传教材并在 UI 列表展示

**依赖**

- FastAPI 文件上传
- 最小存储（本地或对象存储占位）

**产出**

- 表: `source_document`（id, filename, storage_path, created_at）
- API: `POST /documents`, `GET /documents`
- UI: 文档上传 + 列表页

**需要做什么**

- 接收 multipart 上传，保存文件
- 写入 `source_document`

**如何测试**

- 上传 docx/pdf，列表可见

**验收标准**

- 上传成功，列表可查询

### 阶段 3：文档解析与分段

**目标**

- 将文档转换为 markdown 并生成 chunk 列表

**依赖**

- Pandoc
- Postgres

**产出**

- 表: `document_chunk`（id, doc_id, text, chunk_index）
- API: `POST /documents/{id}/parse`, `GET /documents/{id}/chunks`
- UI: 文档详情页显示 chunks

**需要做什么**

- 调用 Pandoc 转换
- 分段规则（标题/空行）
- 写入 `document_chunk`

**如何测试**

- 对上传文档执行解析并查看 chunks

**验收标准**

- 每个文档有可浏览的 chunk 列表

### 阶段 4：Embedding + Milvus 检索

**目标**

- chunk 向量入库并可检索 topk

**依赖**

- Embedding Service（BGE-M3 dense+sparse）
- Milvus

**产出**

- Milvus collection: chunk_id, doc_id, text, dense_vector, sparse_vector, metadata
- API: `POST /index/chunks/{doc_id}`, `POST /search/chunks`
- UI: 检索输入框 + 结果展示

**需要做什么**

- Embedding client（批量/超时/重试）
- Milvus schema 与入库

**如何测试**

- 用 query 检索返回 topk 文段

**验收标准**

- 检索结果与输入语义相关

### 阶段 5：最小出题闭环（单选题）

**目标**

- RAG 检索 + LLM 生成单选题并保存

**依赖**

- LLM 服务
- 阶段 4 的检索能力

**产出**

- 表: `generated_question`（id, doc_id, question_json, created_at）
- API: `POST /generate/single_choice`
- UI: 生成按钮 + 保存结果

**需要做什么**

- Prompt 模板输出结构化 JSON
- 保存题目结果

**如何测试**

- 输入 query 生成题目并保存

**验收标准**

- 题目 JSON 合法且可展示

### 阶段 6：LangGraph 可控流程

**目标**

- 引入 QuestionPlan 并实现可控生成流程

**依赖**

- LangGraph

**产出**

- Pydantic: `QuestionPlan`
- 表: `agent_run`（id, input, plan_json, output_json, status, created_at）
- API: `POST /agents/question`
- UI: 运行记录列表 + 详情页

**需要做什么**

- graph: retrieve -> plan -> draft -> validate -> finalize
- 保存运行记录

**如何测试**

- 给出 plan 运行并查看 run 记录

**验收标准**

- 生成流程可追踪、可复现

### 阶段 7：例题库与错因输入

**目标**

- 支持例题录入及常错点维护

**依赖**

- Postgres

**产出**

- 表: `example_question`（id, doc_id, content_json, common_mistakes）
- API: 例题 CRUD
- UI: 例题录入/编辑

**需要做什么**

- 例题模型与接口

**如何测试**

- 手动录入并查询例题

**验收标准**

- 例题可维护，可用于后续生成

### 阶段 8：干扰项逻辑（GraphRAG）

**目标**

- 基于错因生成干扰项

**依赖**

- Neo4j Graph Builder
- GraphRAG 检索

**产出**

- 题目输出包含干扰项来源或错因解释
- 相关图谱查询接口（knowledge/misconception）

**需要做什么**

- Graph 查询（知识点、错因）
- 干扰项生成节点

**如何测试**

- 生成题目含错因解释

**验收标准**

- 干扰项可解释且相关

### 阶段 9：难度与解题负担控制

**目标**

- 控制难度与解题负担

**依赖**

- GraphRAG（知识点范围）
- LangGraph 校验节点

**产出**

- `agent_run.load_metrics`（知识点数量、步数、长度）
- 校验失败自动重试

**需要做什么**

- 负担代理指标
- 校验与重写策略

**如何测试**

- 指定限制条件，观察重试与达标输出

**验收标准**

- 可稳定满足难度/负担约束

### 阶段 10：试卷 Multi-Agent

**目标**

- 多题型组卷并导出

**依赖**

- LangGraph Multi-Agent
- 已有题型生成能力

**产出**

- 表: `generated_paper`（id, plan_json, paper_json）
- API: `POST /generate/paper`
- UI: 组卷 + 导出

**需要做什么**

- PaperPlan schema
- 题型编排与去重

**如何测试**

- 生成试卷并导出 markdown/docx

**验收标准**

- 试卷结构完整、题型与难度满足要求

关键思想：解题负担 ≠ 难度
你需要一个 Cognitive Load Proxy，例如：

指标 来源
知识点数量 Graph
推理步数 QuestionPlan
表达复杂度 文本长度 + 句法
干扰项迷惑性 错误路径深度

📌 LangGraph 中可以有一个：

“负担评估节点” → 不合格则回滚重生成

⸻

5️⃣ 试卷出题智能体（C6：Multi-Agent）

你这里的判断是 完全正确的：

试卷 = 多种题型 + 统一难度曲线 + 知识覆盖

你的选型是否合适？
✅ LangGraph 非常适合试卷级 Agent

推荐结构：

PaperAgent
 ├─ ChoiceAgent
 ├─ FillBlankAgent
 ├─ SubjectiveAgent
 └─ DifficultyBalancer

每个子 Agent 输出结构化题目描述，不是最终文本。

⸻

四、总结：你的技术选型是否“够用”？

✅ 覆盖情况总结表

需求 技术是否覆盖 评价
教材知识抽取 ✅ 很强
知识结构化 ✅ 需加教学语义
高质量出题 ✅ 需中间规划层
干扰项逻辑 ⚠️ 需错误建模
难度控制 ⚠️ 需认知负担代理
Multi-Agent 试卷 ✅ 非常合适

⸻

五、我给你的一个关键判断（很重要）

你现在做的不是“应用级 AI 出题系统”，而是一个“教学认知建模 + Agent 推理系统”

这意味着：
 • 你现在这套技术栈
👉 足够支撑博士论文 / 重点项目 / 工程落地
 • 难点不在 infra
👉 在 中间表征 + Agent 行为设计

⸻

如果你愿意，下一步我可以直接帮你：

1️⃣ 设计 完整 LangGraph 出题 Agent 拓扑图
2️⃣ 给你一个 QuestionPlan / PaperPlan 的标准 schema
3️⃣ 帮你区分 工程 MVP 路线 vs 科研增强路线

你可以直接说：
👉「下一步先从 单选题出题智能体的 LangGraph 设计 开始」
