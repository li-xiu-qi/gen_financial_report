from typing import List
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array
from financial_report.utils.rag_utils import parse_json_with_retry


rewrite_query_system_prompt = """
【角色】
你是一名专业的检索策略专家。你的任务是根据用户问题、不完整的具体原因、以及查询历史，生成一组全新的、高质量的检索词，用于补充当前的信息空白。

【要求】

1.  **多样性**: 生成的查询应该在措辞、角度或侧重点上有所不同，以提高召回新信息的机会。例如，可以尝试同义词替换、改变问法、或从更宏观/微观的视角提问。
2.  **目标导向**: 所有新查询都必须紧密围绕“反思原因（reason）”和“补充建议”中指出的信息缺口。
3.  **历史感知**: 参考查询历史，避免生成与历史查询高度重复的语句。

请以 JSON 数组格式输出建议的查询，例如：
```
["扩展查询1", "扩展查询2", "换个角度的查询3"]
```
"""

rewrite_query_prompt_with_query_history = """
【背景说明】每次检索最多返回{top_k}条内容。
用户问题：{user_query}
反思原因：{reason}
进一步信息收集建议：{suggestions}
查询历史：
{query_history}
"""

def rewrite_query(
    user_query: str,
    reason: str,
    suggestions: list,
    query_history: str,
    api_key: str,
    base_url: str,
    chat_model: str,
    top_k: int = 5,
) -> List[str]:
    """根据反思和历史记录，生成新的、优化的查询。"""
    user_content = rewrite_query_prompt_with_query_history.format(
        user_query=user_query,
        reason=reason,
        suggestions="\n".join(suggestions),
        top_k=top_k,
        query_history=query_history,
    )
    system_content = rewrite_query_system_prompt

    def llm_call():
        response = chat_no_tool(
            api_key=api_key,
            base_url=base_url,
            model=chat_model,
            system_content=system_content,
            user_content=user_content,
        )
        return extract_json_array(response.strip(), mode="auto")

    queries = parse_json_with_retry(llm_call, default=[])
    return queries if isinstance(queries, list) else []
