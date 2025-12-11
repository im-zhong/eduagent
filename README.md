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
