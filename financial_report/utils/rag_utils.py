# rag_utils.py

import json
import warnings
from typing import List, Callable, Any, Tuple

from .calculate_tokens import TransformerTokenCalculator
from .recursive_text_splitter import split_text_by_symbols


def parse_json_with_retry(
    json_str_or_fn: Callable[[], str] | str, max_retry: int = 3, default: Any = None
) -> Any:
    """
    通用的json解析重试函数，支持传入字符串或生成字符串的函数。
    每次重试都重新调用该函数获取新字符串，超出重试次数返回default。
    """
    for attempt in range(max_retry):
        try:
            json_str = json_str_or_fn() if callable(json_str_or_fn) else json_str_or_fn
            return json.loads(json_str) if json_str else default
        except Exception as e:
            if attempt == max_retry - 1:
                warnings.warn(f"JSON解析失败 ({attempt + 1}/{max_retry}): {e}")
                return default
            continue


def chunk_id_sort_key(cid: str) -> tuple:
    """
    为 chunk_id (例如 "1-2", "12-3") 生成排序键。
    按 (文献id, 分块序号) 进行排序。
    """
    parts = cid.split("-", 1)
    if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
        return (int(parts[0]), int(parts[1]))
    return (parts[0], parts[1] if len(parts) == 2 else "")


def build_context(
    user_query: str,
    documents: List[dict],
    token_calculator: TransformerTokenCalculator,
    max_context_length: int,
) -> str:
    """
    根据最大token数拼接上下文，用于LLM调用。
    """
    content_list: List[str] = []
    context_token_count = token_calculator.count_tokens(text=user_query)
    for i, doc in enumerate(documents):
        doc_id = doc.get("chunk_id") or doc.get("id", "")
        doc_content = doc.get("content", "")
        content = f"【第{i+1}篇开始】\n当前篇文献id为：{doc_id}\n{doc_content}\n【第{i+1}篇结束】"

        count_token_i = token_calculator.count_tokens(text=content)
        if context_token_count + count_token_i > max_context_length:
            break
        content_list.append(content)
        context_token_count += count_token_i
    return "\n".join(content_list)


def split_and_batch_documents(
    user_query: str,
    documents: list,
    token_calculator: TransformerTokenCalculator,
    max_context_length: int,
    chunk_size_chars: int = 2000,
) -> Tuple[List[dict], List[List[dict]]]:
    """
    将原始文档分割成更小的文本块，并根据token限制将这些块分批。
    返回 (所有新生成的块, 分批后的块列表)。
    """
    # 统一将 dataclass（如 HybridSearchResult）转换为 dict，优先用 payload
    normalized_docs = []
    for doc in documents:
        # 只处理 HybridSearchResult（或类似 dataclass），直接用属性
        doc_id = doc.id
        payload = doc.payload
        doc_content = payload.get("content", "")
        doc_source = payload.get("source", "")
        normalized_docs.append({
            "id": doc_id,
            "content": doc_content,
            "source": doc_source
        })
    documents = normalized_docs

    all_new_chunks = []
    for doc in documents:
        chunks = split_text_by_symbols(doc["content"], chunk_size=chunk_size_chars)
        for idx, chunk_content in enumerate(chunks):
            chunk_id = f"{doc['id']}-{idx+1}"
            all_new_chunks.append({
                "chunk_id": chunk_id,
                "content": chunk_content,
                "source": doc["source"],
                "id": doc["id"],
            })

    batches = []
    current_batch = []
    current_tokens = token_calculator.count_tokens(user_query)
    for chunk in all_new_chunks:
        chunk_tokens = token_calculator.count_tokens(chunk["content"])
        if current_tokens + chunk_tokens > max_context_length and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = token_calculator.count_tokens(user_query)
        current_batch.append(chunk)
        current_tokens += chunk_tokens
    if current_batch:
        batches.append(current_batch)

    return all_new_chunks, batches


def get_best_docs_content(
    chunk_ids: List[str],
    user_query: str,
    all_chunks: List[dict],
    all_documents: List[dict],
    token_calculator: TransformerTokenCalculator,
    max_context_length: int,
) -> str:
    """
    根据给定的chunk_ids，智能构建上下文，优先补齐引用区间，并填充额外信息。
    """
    ref_doc_ids = set(str(cid).split("-", 1)[0] for cid in chunk_ids)
    doc_stats = []
    for doc in all_documents:
        doc_id = str(doc.get("id", ""))
        if doc_id in ref_doc_ids:
            chunks = [c for c in all_chunks if str(c.get("id")) == doc_id]
            doc_stats.append((doc_id, chunks))

    selected_chunks = []
    selected_chunk_ids = set()
    total_tokens = token_calculator.count_tokens(user_query)

    initial_chunks = [c for c in all_chunks if c.get("chunk_id") in chunk_ids]
    for chunk in initial_chunks:
        if chunk["chunk_id"] not in selected_chunk_ids:
            chunk_token = token_calculator.count_tokens(chunk["content"])
            if total_tokens + chunk_token <= max_context_length:
                selected_chunks.append(chunk)
                selected_chunk_ids.add(chunk["chunk_id"])
                total_tokens += chunk_token

    for doc_id, chunks_in_doc in doc_stats:
        # 补全逻辑：尝试填充引用块之间的块
        ref_indices_in_doc = sorted(
            [
                int(str(cid).split("-")[1])
                for cid in chunk_ids
                if str(cid).startswith(f"{doc_id}-")
                and str(cid).split("-")[1].isdigit()
            ]
        )
        if len(ref_indices_in_doc) > 1:
            min_idx, max_idx = ref_indices_in_doc[0], ref_indices_in_doc[-1]
            for i in range(min_idx, max_idx + 1):
                chunk_id_to_add = f"{doc_id}-{i}"
                if chunk_id_to_add not in selected_chunk_ids:
                    chunk_to_add = next(
                        (
                            c
                            for c in chunks_in_doc
                            if c.get("chunk_id") == chunk_id_to_add
                        ),
                        None,
                    )
                    if chunk_to_add:
                        chunk_token = token_calculator.count_tokens(
                            chunk_to_add["content"]
                        )
                        if total_tokens + chunk_token <= max_context_length:
                            selected_chunks.append(chunk_to_add)
                            selected_chunk_ids.add(chunk_id_to_add)
                            total_tokens += chunk_token

    # 排序并生成最终内容
    selected_chunks = sorted(
        selected_chunks, key=lambda c: chunk_id_sort_key(c["chunk_id"])
    )
    return "\n".join(
        [
            f"【文献id:{chunk['chunk_id']}】{chunk['content']}"
            for chunk in selected_chunks
        ]
    )
