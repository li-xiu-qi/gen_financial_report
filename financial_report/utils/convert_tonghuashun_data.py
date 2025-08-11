# convert_tonghuashun_data.py
"""
将 competitors_tonghuashun_data.json 数据转换为 PreDoc 列表，便于 ReflectRAG 导入。
"""
import json
from typing import List
from .document_types import PreDoc
import os

def convert_tonghuashun_json_to_predocs(json_path: str) -> List[PreDoc]:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    predocs = []
    for company in data:
        tonghuashun_data = company.get("tonghuashun_data", {})
        # navs
        for nav in tonghuashun_data.get("navs", []):
            title = nav.get("title", "")
            url = nav.get("url", "")
            content = nav.get("md", "")
            data_source_type = nav.get("data_source_type", "html")
            if content:
                predocs.append(
                    PreDoc(
                        content=content,
                        source=url,
                        others={"title": title, "company": company.get("company", {})},
                        data_source_type=data_source_type,
                        raw_content=content,
                    )
                )
        # news
        for news in tonghuashun_data.get("news", []):
            title = news.get("title", "")
            url = news.get("url", "")
            content = news.get("md", "")
            data_source_type = news.get("data_source_type", "html")
            if content:
                predocs.append(
                    PreDoc(
                        content=content,
                        source=url,
                        others={"title": title, "company": company.get("company", {})},
                        data_source_type=data_source_type,
                        raw_content=content,
                    )
                )
    return predocs

if __name__ == "__main__":
    # 示例用法
    json_path = os.path.join(os.path.dirname(__file__), "..", "..", "test_datas", "competitors_tonghuashun_data.json")
    predocs = convert_tonghuashun_json_to_predocs(json_path)
    print(f"转换得到 {len(predocs)} 条 PreDoc 数据样例：")
    for doc in predocs[:2]:
        print(doc)
