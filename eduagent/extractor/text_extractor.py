import requests
from pydantic import BaseModel, Field

secret_key = "XXXXXXXXXX"

## 这个就非常不错，就用这个prompt


def call_zhipu_api(messages: list[dict[str, str]], model: str = "glm-4.5"):  # noqa: ANN201
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    headers = {"Authorization": secret_key, "Content-Type": "application/json"}

    data = {"model": model, "messages": messages, "temperature": 0.4}

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:  # noqa: PLR2004
        return response.json()
    msg = f"API调用失败: {response.status_code}, {response.text}"
    raise Exception(msg)  # noqa: TRY002


# 定义知识点数据结构
class KnowledgePoint(BaseModel):
    """知识点结构定义"""

    title: str = Field(description="知识点的标题或名称")
    content: str = Field(description="知识点的详细内容描述")
    category: str = Field(description="知识点分类，如：概念、方法、原理、事实等")
    importance: str = Field(description="重要性等级：low/medium/high")
    prerequisites: list[str] = Field(default=[], description="前置知识点列表")
    related_points: list[str] = Field(default=[], description="相关知识点列表")
    examples: list[str] | None = Field(default=[], description="示例列表")
    tags: list[str] = Field(default=[], description="标签列表")


class ExtractedData(BaseModel):
    """多人物信息提取容器
    用于封装多个Person实体,形成结构化列表输出
    DeepSeek模型请严格按照此结构返回JSON数组"""

    knowledge_points: list[KnowledgePoint] = Field(default=[], description="知识点列表")

    summary: str = Field(description="知识点总结")
    total_points: int = Field(description="知识点个数")


def tex2data(text_str: str) -> ExtractedData | None:
    text_result = text_str.lstrip("\n").lstrip("```json").rstrip("```")  # noqa: B005
    return ExtractedData.model_validate_json(text_result)


def text_extractor(template: str) -> ExtractedData | None:
    text1 = """
请从以下文本中提取关键知识点，并按照指定的JSON格式输出。

文本内容：
"""
    text2 = """

请按照以下要求提取知识点：
1. 识别文本中的核心概念、原理、方法、事实等
2. 为每个知识点分配适当的重要性等级
3. 建立知识点之间的关联关系
4. 提供相关的示例（如果有）

输出格式要求：
{{
    "knowledge_points": [
        {{
            "title": "知识点标题",
            "content": "详细描述",
            "category": "概念/方法/原理/事实",
            "importance": "low/medium/high",
            "prerequisites": ["前置知识点1", "前置知识点2"],
            "related_points": ["相关知识点1", "相关知识点2"],
            "examples": ["示例1", "示例2"],
            "tags": ["标签1", "标签2"]
        }}
    ],
    "summary": "对提取结果的简要总结",
    "total_points": "知识点总数"
}}

请确保输出是有效的JSON格式，不要包含其他内容。
    """
    input_text = text1 + template + text2

    messages = [{"role": "user", "content": input_text}]

    result = call_zhipu_api(messages=messages)
    text_result = result["choices"][0]["message"]["content"]
    return tex2data(text_result)


def Test() -> None:  # noqa: N802
    template = """
机器学习是人工智能的一个重要分支。它主要研究计算机如何模拟或实现人类的学习行为，
以获取新的知识或技能，重新组织已有的知识结构使之不断改善自身的性能。

监督学习是机器学习的一种方法，它使用带有标签的数据进行训练。常见的监督学习算法包括：
线性回归、逻辑回归、支持向量机和决策树。线性回归用于预测连续值，逻辑回归用于分类问题。

无监督学习则使用没有标签的数据，常见的算法有K-means聚类和主成分分析(PCA)。
K-means聚类可以将数据分成不同的组，而PCA可以用于数据降维。
"""
    result = text_extractor(template)
    print(type(result))
    print(result)
