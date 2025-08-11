from typing import List
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array
from financial_report.utils.rag_utils import parse_json_with_retry, chunk_id_sort_key

outline_plan_system_prompt = """
你是一名专业的报告规划师。请根据用户问题和所有已提取的关键信息，设计一个结构化、层级化的回答大纲。

要求：

1.  **结构清晰**: 先梳理出回答的主要章节（一级要点），每个章节下再细分出具体的二级要点。
2.  **全面覆盖**: 设计的大纲必须能全面覆盖所有给出的关键信息，无遗漏。
3.  **高度聚焦**: 每个二级要点都应高度聚焦于一个独立的主题，避免内容宽泛或重叠。
4.  **关联引用**: 为每个二级要点，关联上所有支持该要点的 [chunk_id] 列表。
5.  **严格格式**: 必须严格按照下面的JSON格式输出，不要添加任何额外说明。

JSON输出格式：
```
[
  {
    "section_index": 1,
    "section": "章节标题1",
    "points": [
      {
        "point_index": 1,
        "point": "二级要点内容1",
        "reference_chunk_ids": ["1-1", "2-2"]
      }
    ]
  }
]
```

"""

outline_plan_prompt = """
用户问题：{user_query}
已提取的关键信息及引用文献id：
{key_points}
"""

def plan_answer_outline(
    user_query: str,
    key_points: List[dict],
    all_chunks: List[dict],
    api_key: str,
    base_url: str,
    chat_model: str,
) -> List[dict]:
    """根据关键信息点，规划答案的整体大纲。"""
    key_points_str = "\n".join(
        [
            f"{kp['content']} [chunk_id:{kp['chunk_id']}]"
            for kp in key_points
            if kp.get("content") and kp.get("chunk_id")
        ]
    )
    plan_prompt_str = outline_plan_prompt.format(
        user_query=user_query, key_points=key_points_str
    )

    def llm_call():
        response = chat_no_tool(
            api_key=api_key,
            base_url=base_url,
            model=chat_model,
            system_content=outline_plan_system_prompt,
            user_content=plan_prompt_str,
        )
        return extract_json_array(response, mode="auto")

    plan = parse_json_with_retry(llm_call, default=[])
    if not isinstance(plan, list):
        return []

    valid_chunk_ids = {chunk["chunk_id"] for chunk in all_chunks}
    for section in plan:
        for point in section.get("points", []):
            if "reference_chunk_ids" in point:
                filtered_ids = [
                    cid
                    for cid in point["reference_chunk_ids"]
                    if cid in valid_chunk_ids
                ]
                point["reference_chunk_ids"] = sorted(
                    filtered_ids, key=chunk_id_sort_key
                )
    return plan
