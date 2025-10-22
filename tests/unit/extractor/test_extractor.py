from eduagent.extractor.text_extractor import *  # noqa: F403, INP001


def test_call_zhipu_api() -> None:
    text_result = """```json
{
    "knowledge_points": [
        {
            "title": "机器学习",
            "content": "人工智能的一个重要分支，研究计算机如何模拟或实现人类的学习行为，以获取新知识或技能，重新组织已有知识结构以改善性能。",
            "category": "概念",
            "importance": "high",
            "prerequisites": ["人工智能"],
            "related_points": ["监督学习", "无监督学习"],
            "examples": [],
            "tags": ["人工智能", "基础概念"]
        },
        {
            "title": "监督学习",
            "content": "机器学习的一种方法，使用带有标签的数据进行训练。",
            "category": "方法",
            "importance": "high",
            "prerequisites": ["机器学习"],
            "related_points": ["线性回归", "逻辑回归", "支持向量机", "决策树"],
            "examples": [],
            "tags": ["机器学习方法", "有标签数据"]
        },
        {
            "title": "线性回归",
            "content": "监督学习的常见算法，用于预测连续值。",
            "category": "方法",
            "importance": "medium",
            "prerequisites": ["监督学习"],
            "related_points": ["逻辑回归"],
            "examples": ["房价预测"],
            "tags": ["监督学习", "回归算法"]
        },
        {
            "title": "逻辑回归",
            "content": "监督学习的常见算法，用于分类问题。",
            "category": "方法",
            "importance": "medium",
            "prerequisites": ["监督学习"],
            "related_points": ["线性回归"],
            "examples": ["垃圾邮件分类"],
            "tags": ["监督学习", "分类算法"]
        },
        {
            "title": "支持向量机",
            "content": "监督学习的常见算法。",
            "category": "方法",
            "importance": "medium",
            "prerequisites": ["监督学习"],
            "related_points": ["决策树"],
            "examples": [],
            "tags": ["监督学习", "分类算法"]
        },
        {
            "title": "决策树",
            "content": "监督学习的常见算法。",
            "category": "方法",
            "importance": "medium",
            "prerequisites": ["监督学习"],
            "related_points": ["支持向量机"],
            "examples": [],
            "tags": ["监督学习", "分类算法"]
        },
        {
            "title": "无监督学习",
            "content": "使用没有标签的数据进行训练的机器学习方法。",
            "category": "方法",
            "importance": "high",
            "prerequisites": ["机器学习"],
            "related_points": ["K-means聚类", "主成分分析(PCA)"],
            "examples": [],
            "tags": ["机器学习方法", "无标签数据"]
        },
        {
            "title": "K-means聚类",
            "content": "无监督学习的常见算法，可以将数据分成不同的组。",
            "category": "方法",
            "importance": "medium",
            "prerequisites": ["无监督学习"],
            "related_points": ["主成分分析(PCA)"],
            "examples": ["将客户分成不同群体"],
            "tags": ["无监督学习", "聚类算法"]
        },
        {
            "title": "主成分分析(PCA)",
            "content": "无监督学习的常见算法，可以用于数据降维。",
            "category": "方法",
            "importance": "medium",
            "prerequisites": ["无监督学习"],
            "related_points": ["K-means聚类"],
            "examples": ["将高维特征降到低维"],
            "tags": ["无监督学习", "降维算法"]
        }
    ],
    "summary": "本文提取了机器学习及其主要方法（监督学习和无监督学习）的相关知识点，包括基本概念、常见算法及其应用场景。",
    "total_points": "9"
}
```"""
    assert isinstance(tex2data(text_result), ExtractedData)  # noqa: F405
