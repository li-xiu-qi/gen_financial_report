import re
from typing import List, Optional, Callable, Any, Dict
from abc import ABC, abstractmethod
from .calculate_tokens import TokenCalculator, OpenAITokenCalculator, TransformerTokenCalculator



class RecursiveTokenTextSplitter:
    """
    基于Token数量和分隔符进行递归文本分割。

    该分割器旨在通过结合语义边界（如标点符号）和Token数量限制，
    来创建更有意义的文本块。
    """

    def __init__(
        self,
        token_calculator: TokenCalculator,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: Optional[List[str]] = None
    ):
        """
        初始化分割器。

        Args:
            token_calculator: 一个实现了 count_tokens 方法的Token计算器实例。
            chunk_size: 每个文本块的最大Token数量。
            chunk_overlap: 块之间的重叠字符数。这是一个基于字符的近似值。
            separators: 分隔符列表，按优先级从高到低排列。
        """
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap 必须小于 chunk_size。")

        self.token_calculator = token_calculator
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        # 定义默认的分割符层次结构
        self.separators = separators or [
            # 优先按完整的段落和句子分割
            "\n\n", "。", "！", "？", "；", ". ", "! ", "? ", "; ",
            # 其次按短语或子句
            "\n", "，", "、", ",",
            # 最后按空格和字符
            " ", ""
        ]

    def _get_token_length(self, text: str) -> int:
        """一个计算token长度的辅助方法。"""
        return self.token_calculator.count_tokens(text)

    def split_text(self, text: str) -> List[str]:
        """
        将输入文本分割成多个块。

        Args:
            text: 需要分割的原始文本。

        Returns:
            分割后的文本块列表。
        """
        if not text:
            return []

        final_chunks = self._recursive_split(text, self.separators)

        if self.chunk_overlap > 0 and len(final_chunks) > 1:
            return self._add_overlap(final_chunks)

        return final_chunks

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """递归分割的核心逻辑。"""
        final_chunks = []

        # 如果文本本身已经满足大小要求，则直接返回
        if self._get_token_length(text) <= self.chunk_size:
            return [text]

        # 如果所有分隔符都已用尽，但文本仍然过长，则强制按字符长度分割
        if not separators:
            # 这是一个后备方案，确保即使没有有效的分隔符也能完成分割
            chunks = []
            current_pos = 0
            while current_pos < len(text):
                # 估算下一个块的字符结束位置，这是一个启发式方法
                estimated_end = current_pos + self.chunk_size * 2
                chunk = text[current_pos:estimated_end]

                # 从末尾移除字符直到满足token限制
                while self._get_token_length(chunk) > self.chunk_size:
                    chunk = chunk[:-1]

                if not chunk:  # 避免因单个字符token超长而导致的死循环
                    break

                chunks.append(chunk)
                current_pos += len(chunk)
            return chunks

        # 使用当前最高优先级的分隔符进行分割
        separator = separators[0]
        remaining_separators = separators[1:]

        # 对空字符串分隔符进行特殊处理，表示按单个字符分割
        if separator == "":
            splits = list(text)
        else:
            # 使用正则表达式分割文本并保留分隔符
            splits = re.split(f'({re.escape(separator)})', text)
            # 将分隔符与前面的文本部分合并
            merged_splits = ["".join(i) for i in zip(splits[0::2], splits[1::2])]
            # 如果原始文本不是以分隔符结尾，则最后一个部分会被遗漏，需要加上
            if len(splits) % 2 == 1 and splits[-1]:
                merged_splits.append(splits[-1])
            splits = merged_splits


        # 合并小的文本片段，直到达到chunk_size的限制
        current_chunk = ""
        for split in splits:
            if not split:
                continue

            # 检查添加新片段后是否会超出token限制
            if self._get_token_length(current_chunk + split) <= self.chunk_size:
                current_chunk += split
            else:
                # 如果当前块有内容，则存入最终列表
                if current_chunk:
                    final_chunks.append(current_chunk)

                # 如果单个片段本身就超过了限制，则对其进行递归分割
                if self._get_token_length(split) > self.chunk_size:
                    sub_chunks = self._recursive_split(split, remaining_separators)
                    final_chunks.extend(sub_chunks)
                    current_chunk = ""  # 递归处理后清空当前块
                else:
                    # 否则，这个片段成为新的当前块
                    current_chunk = split

        # 添加最后一个剩余的块
        if current_chunk:
            final_chunks.append(current_chunk)

        return final_chunks

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """为文本块之间添加重叠部分（基于字符）。"""
        if not chunks or len(chunks) <= 1:
            return chunks

        overlapped_chunks = [chunks[0]]

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i-1]
            current_chunk = chunks[i]

            # 从前一个块的尾部获取重叠内容
            if len(prev_chunk) > self.chunk_overlap:
                overlap = prev_chunk[-self.chunk_overlap:]
                overlapped_chunks.append(overlap + current_chunk)
            else:
                # 如果前一个块本身比重叠长度还短，就用整个前一个块作为重叠
                overlapped_chunks.append(prev_chunk + current_chunk)

        return overlapped_chunks

