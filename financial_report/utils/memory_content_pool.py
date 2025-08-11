import numpy as np
import math
from collections import defaultdict
from jieba import lcut
from dataclasses import dataclass, field
from typing import Any, List


# --- 1. 定义用于封装搜索结果的 Dataclass ---
@dataclass
class VectorSearchResult:
    """封装向量搜索结果"""

    id: int
    score: float
    payload: dict = field(default_factory=dict)


@dataclass
class KeywordSearchResult:
    """封装关键词搜索结果"""

    id: int
    bm25_score: float
    rank: int
    payload: dict = field(default_factory=dict)


@dataclass
class HybridSearchResult:
    """封装混合搜索结果"""

    id: int
    rrf_score: float
    payload: dict = field(default_factory=dict)


class MemoryContentPool:
    """
    一个功能完备的内存搜索引擎，集成了向量相似度搜索和关键词搜索（BM25）。

    该实现不依赖外部搜索库（如 FAISS, Whoosh），所有核心算法均由 Python
    手动实现，提供了最大的灵活性。其主要特点包括：

    - **混合搜索**: 支持向量与关键词的混合检索，并使用“互惠排名融合”（RRF）
      算法合并结果。
    - **原生ID排除**: 可以在搜索查询时直接指定需要排除的文档ID，确保返回
      的结果数量不受影响。
    - **中文支持**: 使用 `jieba` 进行中文分词。
    - **自定义BM25参数**: 允许调整 BM25 算法的 `k1` 和 `b` 参数。
    """

    def __init__(
        self,
        vector_size: int,
        text_fields: list[str],
        bm25_k1: float = 1.5,
        bm25_b: float = 0.75,
    ):
        """
        初始化搜索引擎实例。

        :param vector_size: 向量嵌入的维度。
        :param text_fields: 一个列表，包含在`payload`中需要进行全文索引的字段名。
        :param bm25_k1: BM25 算法的调节参数，控制词频缩放。通常在 1.2 到 2.0 之间。
        :param bm25_b: BM25 算法的调节参数，控制文档长度对分数的影响。通常为 0.75。
        """
        # --- 向量搜索相关 ---
        self.vector_size = vector_size

        # --- 全文搜索 (BM25) 相关 ---
        self.text_fields = text_fields
        self.k1 = bm25_k1
        self.b = bm25_b

        # BM25所需的索引结构
        self.inverted_index = defaultdict(list)
        self.tf = defaultdict(lambda: defaultdict(int))
        self.df = defaultdict(int)
        self.doc_len = {}

        # --- 内部数据存储与管理 ---
        self.doc_store = {}
        self.total_docs = 0
        self.avg_doc_len = 0.0
        self.current_max_id = 0

    def insert_contents(self, docs: list[dict]):
        """
        向内容池中插入一批新文档，并为向量和关键词搜索构建索引。

        :param docs: 一个文档列表，每个文档是一个包含 'vector' 和 'payload' 的字典。
        """
        if not docs:
            return

        for doc in docs:
            self.current_max_id += 1
            doc_id = self.current_max_id

            vector = np.array(doc["vector"], dtype="float32").reshape(1, -1)
            norm = np.linalg.norm(vector)
            normalized_vector = (
                (vector / norm).flatten() if norm > 0 else vector.flatten()
            )

            self.doc_store[doc_id] = {
                "id": doc_id,
                "vector": normalized_vector,
                "payload": doc.get("payload", {}),
            }

            full_text = " ".join(
                [doc.get("payload", {}).get(field, "") for field in self.text_fields]
            )
            tokens = lcut(full_text)

            self.doc_len[doc_id] = len(tokens)
            for token in tokens:
                self.tf[doc_id][token] += 1

            for token in set(tokens):
                self.df[token] += 1
                self.inverted_index[token].append(doc_id)

        self.total_docs = len(self.doc_store)
        if self.total_docs > 0:
            self.avg_doc_len = sum(self.doc_len.values()) / self.total_docs

    def _calculate_idf(self, term: str) -> float:
        numerator = self.total_docs - self.df.get(term, 0) + 0.5
        denominator = self.df.get(term, 0) + 0.5
        return math.log(numerator / denominator + 1.0)

    def search_vector(
        self, query_vector: list, limit: int = 5, exclude_ids: list[int] = None
    ) -> List[VectorSearchResult]:
        """
        手动执行向量相似度搜索（内积），原生支持在搜索时排除ID。
        """
        query_vec = np.array(query_vector, dtype="float32").reshape(1, -1)
        norm = np.linalg.norm(query_vec)
        normalized_query_vec = (
            (query_vec / norm).flatten() if norm > 0 else query_vec.flatten()
        )

        exclude_ids_set = set(exclude_ids) if exclude_ids else set()

        scores = []
        for doc_id, doc_data in self.doc_store.items():
            if doc_id in exclude_ids_set:
                continue

            score = np.dot(normalized_query_vec, doc_data["vector"])
            scores.append((score, doc_id))

        scores.sort(key=lambda x: x[0], reverse=True)

        # --- 3. 重构返回结果 ---
        results = []
        for score, doc_id in scores[:limit]:
            results.append(
                VectorSearchResult(
                    id=doc_id,
                    payload=self.doc_store[doc_id]["payload"],
                    score=float(score),
                )
            )
        return results

    def search_keyword(
        self, fuzzy_query: str, limit: int = 5, exclude_ids: list[int] = None
    ) -> List[KeywordSearchResult]:
        """
        手动执行BM25关键词搜索，原生支持在搜索时排除ID。
        """
        exclude_ids_set = set(exclude_ids) if exclude_ids else set()
        query_tokens = lcut(fuzzy_query)
        doc_scores = defaultdict(float)

        for token in query_tokens:
            if token not in self.inverted_index:
                continue

            idf = self._calculate_idf(token)

            for doc_id in self.inverted_index[token]:
                if doc_id in exclude_ids_set:
                    continue

                tf = self.tf[doc_id].get(token, 0)
                doc_length = self.doc_len[doc_id]

                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * doc_length / self.avg_doc_len
                )

                doc_scores[doc_id] += idf * (numerator / denominator)

        sorted_doc_scores = sorted(
            doc_scores.items(), key=lambda item: item[1], reverse=True
        )

        # --- 3. 重构返回结果 ---
        results = []
        for rank, (doc_id, score) in enumerate(sorted_doc_scores[:limit], 1):
            results.append(
                KeywordSearchResult(
                    id=doc_id,
                    payload=self.doc_store[doc_id]["payload"],
                    rank=rank,
                    bm25_score=score,
                )
            )
        return results

    def search_hybrid_rrf(
        self,
        query_vector: list,
        fuzzy_query: str,
        limit: int = 5,
        k: int = 60,
        exclude_ids: list[int] = None,
    ) -> List[HybridSearchResult]:
        """
        执行混合搜索，并使用互惠排名融合(RRF)算法合并结果。
        """
        internal_limit = limit * 5

        vector_results = self.search_vector(
            query_vector, limit=internal_limit, exclude_ids=exclude_ids
        )
        keyword_results = self.search_keyword(
            fuzzy_query, limit=internal_limit, exclude_ids=exclude_ids
        )

        rrf_scores = defaultdict(float)

        for result in vector_results:
            # 假设向量搜索结果的排名就是其在列表中的位置
            rank = vector_results.index(result) + 1
            rrf_scores[result.id] += 1 / (k + rank)

        for result in keyword_results:
            rrf_scores[result.id] += 1 / (k + result.rank)

        if not rrf_scores:
            return []

        sorted_ids = sorted(
            rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True
        )

        # --- 3. 重构返回结果 ---
        final_results = []
        for doc_id in sorted_ids[:limit]:
            final_results.append(
                HybridSearchResult(
                    id=doc_id,
                    payload=self.doc_store[doc_id]["payload"],
                    rrf_score=rrf_scores[doc_id],
                )
            )

        return final_results

    def get_all_ids(self) -> set:
        """
        返回所有已插入文档的 id 集合
        """
        return set(self.doc_store.keys())


if __name__ == "__main__":
    # --- 使用示例 ---
    print("初始化内存搜索引擎...")
    search_pool = MemoryContentPool(vector_size=8, text_fields=["title", "content"])

    # 准备并插入示例文档
    docs_to_insert = [
        {
            "vector": [0.1, 0.1, 0.1, 0.1, 0.9, 0.9, 0.9, 0.9],
            "payload": {
                "title": "A股上市公司财务报表分析",
                "content": "本文深入探讨了财务分析的方法论。",
            },
        },
        {
            "vector": [0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            "payload": {
                "title": "利用Python进行数据科学实践",
                "content": "Python是数据科学领域最流行的编程语言。",
            },
        },
        {
            "vector": [0.1, 0.1, 0.9, 0.9, 0.1, 0.1, 0.1, 0.1],
            "payload": {
                "title": "Python在金融量化交易中的应用",
                "content": "量化交易模型需要复杂的财务知识和编程技巧。",
            },
        },
        {
            "vector": [0.9, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
            "payload": {
                "title": "人工智能如何赋能金融行业",
                "content": "人工智能正在重塑金融服务的未来。",
            },
        },
        {
            "vector": [0.1, 0.8, 0.1, 0.8, 0.1, 0.1, 0.1, 0.1],
            "payload": {
                "title": "深入理解Python编程语言",
                "content": "探讨Python的核心概念与高级技巧。",
            },
        },
    ]
    search_pool.insert_contents(docs_to_insert)
    print(f"成功插入 {len(docs_to_insert)} 条数据。\n")

    # 定义查询条件
    query_vector_python = [0.1, 0.1, 0.8, 0.8, 0.1, 0.1, 0.2, 0.2]
    fuzzy_query_python = "python 金融"
    id_to_exclude = 3

    # --- 4. 更新打印逻辑以使用对象属性访问 ---

    # --- 演示1: 正常的混合搜索 ---
    print("--- 场景1: 正常的混合搜索 (limit=3) ---")
    hybrid_results = search_pool.search_hybrid_rrf(
        query_vector=query_vector_python, fuzzy_query=fuzzy_query_python, limit=3
    )
    for r in hybrid_results:
        print(
            f"  ID: {r.id}, RRF_Score: {r.rrf_score:.4f}, Title: {r.payload['title']}"
        )

    # --- 演示2: 带有ID排除的混合搜索 ---
    print(f"\n--- 场景2: 混合搜索，在搜索时排除 ID: {id_to_exclude} (limit=3) ---")
    hybrid_results_excluded = search_pool.search_hybrid_rrf(
        query_vector=query_vector_python,
        fuzzy_query=fuzzy_query_python,
        limit=3,
        exclude_ids=[id_to_exclude],
    )
    print(f"请求返回 {len(hybrid_results_excluded)} 条结果，验证数量得到保证。")
    for r in hybrid_results_excluded:
        print(
            f"  ID: {r.id}, RRF_Score: {r.rrf_score:.4f}, Title: {r.payload['title']}"
        )

    # --- 演示3: 单独的向量搜索 ---
    print(f"\n--- 场景3: 单独进行向量搜索 (limit=3) ---")
    vector_results = search_pool.search_vector(query_vector_python, limit=3)
    for r in vector_results:
        print(f"  ID: {r.id}, Vector_Score: {r.score:.4f}, Title: {r.payload['title']}")

    print(f"\n--- 场景3.1: 向量搜索，并排除 ID: {id_to_exclude} (limit=3) ---")
    vector_results_excluded = search_pool.search_vector(
        query_vector_python, limit=3, exclude_ids=[id_to_exclude]
    )
    print(f"请求返回 {len(vector_results_excluded)} 条结果，验证数量得到保证。")
    for r in vector_results_excluded:
        print(f"  ID: {r.id}, Vector_Score: {r.score:.4f}, Title: {r.payload['title']}")

    # --- 演示4: 单独的关键词搜索 ---
    print(f"\n--- 场景4: 单独进行关键词搜索 (limit=3) ---")
    keyword_results = search_pool.search_keyword(fuzzy_query_python, limit=3)
    for r in keyword_results:
        print(
            f"  ID: {r.id}, BM25_Score: {r.bm25_score:.4f}, Title: {r.payload['title']}"
        )

    print(f"\n--- 场景4.1: 关键词搜索，并排除 ID: {id_to_exclude} (limit=3) ---")
    keyword_results_excluded = search_pool.search_keyword(
        fuzzy_query_python, limit=3, exclude_ids=[id_to_exclude]
    )
    print(f"请求返回 {len(keyword_results_excluded)} 条结果，验证数量得到保证。")
    for r in keyword_results_excluded:
        print(
            f"  ID: {r.id}, BM25_Score: {r.bm25_score:.4f}, Title: {r.payload['title']}"
        )
