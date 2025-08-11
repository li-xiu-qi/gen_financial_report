"""
递归文本分割器
基于不同的分隔符进行递归分割，确保文本块的大小符合要求
"""

import re
from typing import List, Optional, Callable, Any


def split_text_by_symbols(
    text: str,
    chunk_size: int = 4000,
    chunk_overlap: int = 0
) -> List[str]:
    """
    基于中文和英文符号递归分割文本
    
    Args:
        text: 要分割的文本
        chunk_size: 每个文本块的最大大小
        chunk_overlap: 文本块之间的重叠大小
        
    Returns:
        分割后的文本块列表
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    # 分隔符优先级：中文符号 > 英文符号 > 空白字符 > 字符级
    separators = [
        "。", "！", "？", "；",  # 中文句号符号
        ".", "!", "?", ";",     # 英文句号符号
        "，", "、",             # 中文逗号符号
        ",",                   # 英文逗号
        "\n\n", "\n",          # 换行符
        " ",                   # 空格
        ""                     # 字符级分割
    ]
    
    return _recursive_split(text, separators, chunk_size, chunk_overlap)


def _recursive_split(
    text: str, 
    separators: List[str], 
    chunk_size: int, 
    chunk_overlap: int
) -> List[str]:
    """递归分割文本的核心函数"""
    if not separators:
        return _force_split(text, chunk_size, chunk_overlap)
    
    separator = separators[0]
    remaining_separators = separators[1:]
    
    # 分割文本
    if separator == "":
        splits = list(text)
    else:
        splits = [s for s in text.split(separator) if s.strip()]
    
    # 如果没有分割出多个部分，尝试下一个分隔符
    if len(splits) <= 1:
        return _recursive_split(text, remaining_separators, chunk_size, chunk_overlap)
    
    # 合并小块
    chunks = []
    current_chunk = ""
    
    for split in splits:
        # 如果单个分割就超过大小，递归处理
        if len(split) > chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            
            sub_chunks = _recursive_split(split, remaining_separators, chunk_size, chunk_overlap)
            chunks.extend(sub_chunks)
            continue
        
        # 检查是否可以添加到当前块
        test_chunk = current_chunk + separator + split if current_chunk else split
        
        if len(test_chunk) <= chunk_size:
            current_chunk = test_chunk
        else:
            # 保存当前块并开始新块
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = split
    
    # 添加最后一块
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # 处理重叠
    if chunk_overlap > 0 and len(chunks) > 1:
        chunks = _add_overlap(chunks, chunk_overlap)
    
    return [chunk for chunk in chunks if chunk]


def _force_split(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """强制按字符数分割"""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        
        if chunk:
            chunks.append(chunk)
        
        start = end - chunk_overlap
        if start >= len(text):
            break
    
    return chunks


def _add_overlap(chunks: List[str], overlap_size: int) -> List[str]:
    """为文本块添加重叠部分"""
    if len(chunks) <= 1:
        return chunks
    
    overlapped_chunks = [chunks[0]]
    
    for i in range(1, len(chunks)):
        prev_chunk = chunks[i-1]
        current_chunk = chunks[i]
        
        # 获取前一块的尾部作为重叠
        if len(prev_chunk) > overlap_size:
            overlap = prev_chunk[-overlap_size:]
            overlapped_chunk = overlap + current_chunk
        else:
            overlapped_chunk = current_chunk
        
        overlapped_chunks.append(overlapped_chunk)
    
    return overlapped_chunks
