import requests
from typing import List, Dict, Any, Optional

def rerank(query: str, documents: List[str], top_n: int = 5, model: Optional[str] = None, base_url: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    标准重排函数，所有参数均需外部传入。
    :param query: 查询文本
    :param documents: 待重排的文档列表
    :param top_n: 返回Top N结果
    :param model: 模型名称（必填）
    :param base_url: API完整地址（必填）
    :param api_key: API密钥（必填）
    :return: 重排结果（dict）
    """
    if not (model and base_url and api_key):
        raise ValueError("model、base_url、api_key均为必填参数")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "query": query, "documents": documents, "top_n": top_n}
    response = requests.post(f"{base_url}", headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()
    query = "人工智能的最新进展"
    documents = [
        "人工智能在医疗领域的应用正在快速发展。",
        "深度学习推动了计算机视觉的进步。",
        "AI技术在自动驾驶中扮演重要角色。",
        "区块链与AI结合带来新机遇。",
        "自然语言处理是AI的核心方向之一。",
    ] * 10
    model = os.getenv("LOCAL_RERANK_MODEL", "Qwen3-Reranker-0.6B")
    base_url = os.getenv("LOCAL_BASE_URL", "http://localhost:10002/v1") + "/rerank"
    api_key = os.getenv("LOCAL_API_KEY", "your_api_key")
    result = rerank(query, documents, top_n=3, model=model, base_url=base_url, api_key=api_key)
    print("Rerank结果原始：", result)
    results = result.get('results', [])
    if results:
        print("重排序后的文档：")
        for i, item in enumerate(results, 1):
            idx = item.get('index')
            score = item.get('relevance_score')
            doc_text = documents[idx] if idx is not None and idx < len(documents) else "索引超出范围"
            print(f"{i}. [score={score:.4f}] {doc_text}")
    else:
        print("未找到重排序结果字段，请检查API返回格式。")
