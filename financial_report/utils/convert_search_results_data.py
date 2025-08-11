# convert_search_results_data.py
"""
将 heuristic_search_results_v1.json 网络检索结果转换为 PreDoc 列表，便于 ReflectRAG 导入。
"""
import json
from typing import List
from .document_types import PreDoc
import os

def convert_search_results_json_to_predocs(json_path: str) -> List[PreDoc]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    predocs = []
    for section in data:
        for query_result in section:
            for result in query_result.get("results", []):
                content = result.get("md", "")
                source = result.get("url", "")
                title = result.get("title", "")
                data_source_type = result.get("data_source_type", "html")
                if content:
                    predocs.append(
                        PreDoc(
                            content=content,
                            source=source,
                            others={"title": title},
                            data_source_type=data_source_type,
                            raw_content=content,
                        )
                    )
    return predocs

if __name__ == "__main__":
    # 示例用法
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "test_datas", "heuristic_search_results_v1.json")
    predocs = convert_search_results_json_to_predocs(json_path)
    print(f"转换得到 {len(predocs)} 条 PreDoc 数据样例：")
    for doc in predocs[:2]:
        print(doc)
