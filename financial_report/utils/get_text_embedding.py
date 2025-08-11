from http import client
from openai import OpenAI
from dotenv import load_dotenv 
import os
import hashlib
from diskcache import Cache
from typing import List, Dict, Optional, Tuple
import json

# LOCAL_API_KEY,LOCAL_BASE_URL,LOCAL_TEXT_MODEL,LOCAL_EMBEDDING_MODEL

load_dotenv()  # 加载环境变量（可选，用户可自行读取）

# 创建缓存目录，并设置最大缓存大小为 10GB
cache_dir = os.path.join(os.path.dirname(__file__), 'caches')
cache = Cache(cache_dir, size_limit=10 * 1024 ** 3)  # 10GB

def get_openai_client(api_key: str, base_url: str) -> OpenAI:
    """
    获取 OpenAI 客户端，必须传递 api_key 和 base_url
    """
    if not api_key or not base_url:
        raise ValueError("api_key 和 base_url 必须显式传递！")
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

def get_cache_key(text: str) -> str:
    """
    为文本生成缓存键
    :param text: 输入文本
    :return: 缓存键
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def batch_get_embeddings(
    texts: List[str],
    batch_size: int = 64,
    api_key: str = None,
    base_url: str = None,
    embedding_model: str = None
) -> List[List[float]]:
    """
    批量获取文本的嵌入向量
    :param texts: 文本列表
    :param batch_size: 批处理大小
    :param api_key: 可选，自定义 API KEY
    :param base_url: 可选，自定义 BASE URL
    :param embedding_model: 可选，自定义嵌入模型
    :return: 嵌入向量列表
    """
    if not api_key or not base_url or not embedding_model:
        raise ValueError("api_key、base_url、embedding_model 必须显式传递！")
    all_embeddings = []
    client = get_openai_client(api_key, base_url)
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        response = client.embeddings.create(
            model=embedding_model,
            input=batch_texts
        )
        batch_embeddings = [embedding.embedding for embedding in response.data]
        all_embeddings.extend(batch_embeddings)
    return all_embeddings

def get_cached_embeddings(texts: List[str]) -> Tuple[List[Tuple[int, List[float]]], List[Tuple[int, str]]]:
    """
    从缓存中获取embeddings，返回已缓存的结果和未缓存的索引及文本
    :param texts: 文本列表
    :return: (已缓存的(索引,embedding)列表, 未缓存的(索引,文本)列表)
    """
    cached_results = []
    uncached_items = []
    
    for idx, text in enumerate(texts):
        cache_key = get_cache_key(text)
        cached_embedding = cache.get(cache_key)
        if cached_embedding is not None:
            cached_results.append((idx, cached_embedding))
        else:
            uncached_items.append((idx, text, cache_key))
            
    return cached_results, [(idx, text) for idx, text, _ in uncached_items], [key for _, _, key in uncached_items]

def get_text_embedding(
    texts: List[str],
    api_key: str = None,
    base_url: str = None,
    embedding_model: str = None,
    batch_size: int = 64
) -> List[List[float]]:
    """
    获取文本的嵌入向量，支持批次处理和缓存，保持输出顺序与输入顺序一致
    :param texts: 文本列表
    :param api_key: 可选，自定义 API KEY
    :param base_url: 可选，自定义 BASE URL
    :param embedding_model: 可选，自定义嵌入模型
    :param batch_size: 批处理大小
    :return: 嵌入向量列表
    """
    if not api_key or not base_url or not embedding_model:
        raise ValueError("api_key、base_url、embedding_model 必须显式传递！")
    # 1. 检查缓存并获取未缓存的项
    cached_results, uncached_items, cache_keys = get_cached_embeddings(texts)
    result_embeddings = cached_results.copy()
    # 2. 如果有未缓存的项，批量获取它们的embeddings
    if uncached_items:
        uncached_texts = [text for _, text in uncached_items]
        uncached_indices = [idx for idx, _ in uncached_items]
        # 获取新的embeddings
        new_embeddings = batch_get_embeddings(
            uncached_texts,
            batch_size=batch_size,
            api_key=api_key,
            base_url=base_url,
            embedding_model=embedding_model
        )
        # 保存到缓存并添加到结果中
        for idx, embedding, cache_key in zip(uncached_indices, new_embeddings, cache_keys):
            cache.set(cache_key, embedding)
            result_embeddings.append((idx, embedding))
    # 3. 按原始顺序排序并返回结果
    return [embedding for _, embedding in sorted(result_embeddings, key=lambda x: x[0])]


    
