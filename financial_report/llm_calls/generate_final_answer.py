from typing import List
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.rag_utils import get_best_docs_content
from financial_report.llm_calls.plan_answer_outline import plan_answer_outline
from financial_report.utils.calculate_tokens import TransformerTokenCalculator

# 迁移自 reflect_rag_prompt.py
answer_system_prompt = """
你是一名专业的问答写作专家。请根据下方提供的所有参考内容及其引用来源（chunk_id），完成以下任务：

1.  **综合理解**: 首先对所有信息进行全面、深入的理解。
2.  **生成回答**: 围绕用户问题，生成一个逻辑连贯、条理清晰、内容详实的回答。
3.  **标注引用**: 必须在每条结论或数据的末尾，使用 [chunk_id] 格式准确标注其来源。例如：“……这是结论内容 [1-1]”。只允许引用下方内容中实际存在的 chunk_id，不要添加其他前缀或说明。
4.  **格式要求**: 请直接输出回答正文，不要包含“好的”、“根据您提供的信息”等多余的开场白或解释。
"""

answer_prompt = """
用户问题：{user_query}
参考内容：
{docs_content}
注意：不要虚构任何信息，所有回答必须基于提供的参考内容。
"""

detail_answer_system_prompt = """
你是一名专注于根据既定大纲和参考材料，撰写精确、详细答案的写作助手。

任务要求：

1.  **严格遵从**: 严格按照下方指定的“当前要点”进行回答，不要涉及大纲中的其他章节或要点。
2.  **忠于原文**: 回答内容必须完全基于下方“参考内容”中的信息，并在每条结论后准确标注引用 `[chunk_id]`。
3.  **处理空内容**: 如果“参考内容”无法支撑当前要点，请直接回答“无可用文献支撑本要点。”，不要虚构。
4.  **格式精准**:
      - 回答的首行必须是 `"{section_index}.{point_index} {point}"` 格式的小标题。
      - 正文内容另起一行开始。
      - 不要添加任何超出要求内容的备注或解释。
引用格式要求：请确保只用 [chunk_id] 形式。
引用示例：这是结论内容 [1-1]。
"""

detail_answer_prompt = """
用户问题：{user_query}
完整大纲结构：
{outline_str}

当前章节：{section_index}. {section}
当前要点：{point_index}. {point}

参考内容：
{blocks_content}
注意：不要虚构任何信息，所有回答必须基于提供的参考内容。

"""

def generate_final_answer(
    user_query: str,
    all_chunks: List[dict],
    all_documents: List[dict],
    all_reports: List[dict],
    api_key: str,
    base_url: str,
    chat_model: str,
    token_calculator: TransformerTokenCalculator,
    max_context_length: int,
) -> str:
    """整合所有信息，生成最终的、带引用的完整答案。"""
    key_points = []
    if all_reports:
        for report in all_reports:
            key_points.extend(
                kp
                for kp in report.get("key_points", [])
                if kp.get("content") and kp.get("chunk_id")
            )
    else:
        key_points = [
            {"content": c.get("content", ""), "chunk_id": c.get("chunk_id", "")}
            for c in all_chunks
            if c.get("content") and c.get("chunk_id")
        ]

    seen = set()
    unique_key_points = []
    for kp in key_points:
        key = (kp["content"], kp["chunk_id"])
        if key not in seen:
            unique_key_points.append(kp)
            seen.add(key)

    if not unique_key_points:
        return "未检索到相关内容，无法回答。"

    # total_content = "".join(chunk.get("content", "") for chunk in all_chunks)
    # if token_calculator.count_tokens(user_query + total_content) <= max_context_length:
    #     docs_content = get_best_docs_content(
    #         [c["chunk_id"] for c in all_chunks],
    #         user_query,
    #         all_chunks,
    #         all_documents,
    #         token_calculator,
    #         max_context_length,
    #     )
    #     answer_prompt_str = answer_prompt.format(
    #         user_query=user_query, docs_content=docs_content
    #     )
    #     return chat_no_tool(
    #         api_key=api_key,
    #         base_url=base_url,
    #         model=chat_model,
    #         system_content=answer_system_prompt,
    #         user_content=answer_prompt_str,
    #     ).strip()

    outline = plan_answer_outline(
        user_query, unique_key_points, all_chunks, api_key, base_url, chat_model
    )
    if not outline:
        return "无法根据现有信息生成回答大纲，请检查检索结果。"

    answer_parts = []
    outline_str = "\n".join(
        [
            f"{s['section_index']}. {s['section']}\n"
            + "\n".join(
                [
                    f"  {s['section_index']}.{p['point_index']} {p['point']}"
                    for p in s.get("points", [])
                ]
            )
            for s in outline
        ]
    )

    for section in outline:
        answer_parts.append(
            f"{section.get('section_index', '')}. {section.get('section', '')}"
        )
        for point in section.get("points", []):
            ref_chunk_ids = point.get("reference_chunk_ids", [])
            blocks_content = get_best_docs_content(
                ref_chunk_ids,
                user_query,
                all_chunks,
                all_documents,
                token_calculator,
                max_context_length,
            )
            detail_prompt_str = detail_answer_prompt.format(
                user_query=user_query,
                outline_str=outline_str,
                section_index=section.get("section_index"),
                section=section.get("section"),
                point_index=point.get("point_index"),
                point=point.get("point"),
                blocks_content=blocks_content,
            )
            detail_answer = chat_no_tool(
                api_key=api_key,
                base_url=base_url,
                model=chat_model,
                system_content=detail_answer_system_prompt,
                user_content=detail_prompt_str,
            )
            answer_parts.append(detail_answer.strip())

    return "\n\n".join(answer_parts) if answer_parts else "未检索到相关内容，无法回答。"
