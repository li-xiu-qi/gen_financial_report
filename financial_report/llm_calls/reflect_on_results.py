from typing import List, Dict, Any
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array
from financial_report.utils.rag_utils import parse_json_with_retry, build_context
from financial_report.utils.calculate_tokens import TransformerTokenCalculator

reflect_system_prompt = """
你是一名顶尖的信息分析师。请根据检索结果，严格按照以下要求完成任务：
1.  **提取关键信息**: 归纳出与用户问题直接相关的核心信息点，并清晰标注每条信息来源于哪个文档块chunk_id。
2.  **评估信息完整性**:
    -   判断当前所有信息是否足以全面、准确地回答用户问题。
    -   在 reason 字段中，必须提供清晰、可执行的判断依据。如果信息不完整，请明确指出**缺失了哪些具体方面的信息**，这将直接用于指导下一步的检索。
3.  **生成补充查询**: 如果信息不完整，基于 reason 中指出的缺失方向，生成一组具有探索性的、互补的补充检索词。
4.  **滚动更新摘要**: 在上一轮 summary 的基础上，整合本轮提取到的新关键信息，形成一个更新、更全面的版本。

请严格使用以下 JSON 格式输出，不要添加任何额外解释：
```
{
  "key_points": [
    {"content": "关键信息1", "chunk_id": "1-1"},
    {"content": "关键信息2", "chunk_id": "2-1"}
  ],
  "is_complete": false,
  "reason": "当前信息已覆盖A和B方面，但缺失了关于C方面的具体数据和实例。",
  "supplementary_queries": ["C方面的具体数据", "C方面的应用实例"],
  "summary": "已收集到的关于A、B、C三方面的全部信息摘要..."
}
```
"""

reflect_prompt = """
用户问题：{user_query}
检索结果：
{docs_content}
"""

def reflect_on_results(
    user_query: str,
    documents: List[dict],
    summary: str,
    api_key: str,
    base_url: str,
    chat_model: str,
    token_calculator: TransformerTokenCalculator,
    max_context_length: int,
) -> Dict[str, Any]:
    """对检索到的文档进行反思，判断信息完整性并提出建议。"""
    docs_for_context = []
    for doc in documents:
        if hasattr(doc, 'payload'):
            d = dict(doc.payload)
            d['id'] = getattr(doc, 'id', d.get('id', ''))
            docs_for_context.append(d)
        else:
            docs_for_context.append(doc)
    docs_context_str = build_context(
        user_query, docs_for_context, token_calculator, max_context_length
    )
    summary_prompt = (
        f"当前已收集信息摘要：{summary}" if summary else "当前无已收集信息摘要。"
    )
    reflect_prompt_str = (
        reflect_prompt.format(
            user_query=user_query, docs_content=docs_context_str
        )
        + "\n"
        + summary_prompt
    )

    def llm_call():
        response = chat_no_tool(
            api_key=api_key,
            base_url=base_url,
            model=chat_model,
            system_content=reflect_system_prompt,
            user_content=reflect_prompt_str,
        )
        return extract_json_array(response.strip(), mode="auto")

    return parse_json_with_retry(llm_call, default={})
