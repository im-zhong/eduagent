# EduAgent

[![codecov](https://codecov.io/gh/im-zhong/eduagent/branch/main/graph/badge.svg)](https://codecov.io/gh/im-zhong/eduagent)

Education Agent: An Intelligent Question Generation System

Assist educators and learners by automatically generating educational questions from text materials or knowledge bases. It leverages natural language processing (NLP) and modern AI models to create meaningful and context-aware questions.

## Quiz Workflow (ReAct)

The quiz pipeline now uses a Chinese-first ReAct agent implemented with LangGraph:

1. **Plan** – the agent analyses the user prompt and existing context, deciding the next action (检索 / 总结 / 出题 / 质检 / 结束).
2. **Act** – it calls the appropriate tool (Milvus retrieval, summarisation, question generation, critique) and records observations plus tool-usage metrics.
3. **Evaluate** – progress is checked after every action; the agent either loops with a new plan or finalises the quiz artifact.

Every step is logged with the ingestion job ID, including the latest thought, action, observation and tool counters, so failures can be traced quickly.

### Configuration

Tune the workflow via `eduagent.toml` (or `example.eduagent.toml`):

```toml
[quiz_workflow]
default_language = "zh"   # Prompt language used when the document metadata lacks one
retrieval_limit = 5       # Milvus hits per retrieval action
max_iterations = 3        # Safety cap for ReAct loops
```

These values are available under `settings.quiz_workflow` and applied automatically when `QuizWorkflowRunner` executes the agent.

### Streaming API

Use the SSE endpoint to monitor agent progress in real time:

```
POST /api/v1/quiz/workflow/stream
{"ingestion_job_id": "<id>", "prompt": "生成练习题"}
```

Each event arrives as `data: {...}` with a `phase` (plan/act/evaluate/final) and detailed payload for rendering in the UI.

## Maintainers

- YunX <xyiu.run@gmail.com>
- Eon-Flight <eon3209036707@gmail.com>
- G_shang_hui <271278430@qq.com>
- Marisolebxf <835245656@qq.com>
- Zhou <lz4530_j@163.com>
- qinxingkun <1915732401@qq.com>

## Test Service JWT

eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJuZXh0anMtc2VydmljZSIsImF1ZCI6ImVkdWFnZW50LWFwaSIsInN1YiI6InVuaXQtdGVzdC1zZXJ2aWNlIiwiaWF0IjoxNzY1MzYyNzMwLCJleHAiOjE3Njc5NTQ3MzB9.NKmetvh2yUBgXBgfJBqDCk_MYAaRgbQHECbOrH2jYLM

87eef7f1-8145-405f-bb2c-478c237eda8f

## 2025/12/22 汇报总结

汇报文档补充一个层次方框图
文档方面：需求分析，系统设计，详细设计等等文档。需求及设计文档，维护文档，系统使用说明书。
难度控制参数：去掉小学这个级别的
流程图：给开发人员看
新功能：出卷子智能体：输出成PDF文件。出卷子的要求，题型，分数。
题型：填空题。
新功能：出题质量评估。试卷评估指标。可以形成闭环。
软著，专利。基于智能体的出题及评估专利。先调研。
以后再开发系统，先给出需求分析，系统界面，demo等。
高优先级：先写文档。就是上面提到的文档，直接AI一把梭！

1）《自动出题智能体系统需求分析及设计》：需求分析、总体设计（实现方案选择、功能层次方框图）、详细设计（数据库设计、用户界面+算法流程、系统菜单）：给开发人员
2）《用户使用手册》：给系统使用者
3）《系统维护文档》：给其他人用来维护和升级系统

# 两个事情

1. 现在看一下聊天记录， 等项目下来或者现在和qiu老师确认一下，清华那边在项目上需要我们做什么事情。
2. 新的智能体的同学，基于藏倩师姐的智能体，重新设计。
