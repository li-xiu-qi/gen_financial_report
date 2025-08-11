"""
宏观研报内容组装器
负责组装最终的报告内容和参考文献管理
支持两轮内容生成：基础内容 + 可视化增强内容
"""

from typing import Dict
from data_process.base_report_content_assembler import BaseReportContentAssembler


class MacroReportContentAssembler(BaseReportContentAssembler):
    """宏观研报内容组装器 - 负责内容组装和格式化"""
    
    def __init__(self):
        """初始化内容组装器"""
        super().__init__()
    
    def get_report_title(self, subject_name: str) -> str:
        """获取宏观研究报告标题"""
        return f"{subject_name}宏观经济分析报告"
    
    def get_default_section_mapping(self) -> Dict[str, str]:
        """
        获取宏观研报的章节映射关系
        
        Returns:
            宏观研报专用的章节映射字典
        """
        return {
            "一": "一、宏观经济环境概述",
            "二": "二、主要经济指标分析", 
            "三": "三、货币政策与财政政策",
            "四": "四、市场表现与资金流向",
            "五": "五、前景展望与投资策略"
        }
