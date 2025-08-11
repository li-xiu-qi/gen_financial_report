# document_types.py
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class PreDoc:
    """
    预处理文档结构，便于批量embedding和去重。
    """
    id: Optional[str] = None
    content: str = ""
    source: str = ""
    others: Dict[str, Any] = field(default_factory=dict)
    vector: Optional[List[float]] = None
    raw_content: str = ""
    summary: str = ""
    data_source_type: str = "html"
    # 新增token相关字段
    content_tokens: Optional[int] = None  # 内容的token数量
    summary_tokens: Optional[int] = None  # 摘要的token数量
    raw_content_tokens: Optional[int] = None  # 原始内容的token数量
    
    def __hash__(self):
        """使PreDoc对象可哈希，基于内容和来源"""
        return hash((self.content, self.source, self.raw_content))
    
    def __eq__(self, other):
        """定义相等性比较"""
        if not isinstance(other, PreDoc):
            return False
        return (self.content == other.content and 
                self.source == other.source and 
                self.raw_content == other.raw_content)  

@dataclass
class Doc:
    """
    实际存入数据库的文档结构。
    id: Optional[str] = None
    vector: Optional[List[float]] = None
    payload: Dict[str, Any] = field(default_factory=dict)
        - content: 文档内容
        - source: 文档来源
        - summary: 文档描述摘要
        - data_source_type: 数据源类型
        - **others: 其他附加信息
    """
    id: Optional[str] = None
    vector: Optional[List[float]] = None
    payload: Dict[str, Any] = field(default_factory=dict)
