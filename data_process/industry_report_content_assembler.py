"""
行业研报内容组装器
负责组装最终的报告内容和参考文献管理
支持两轮内容生成：基础内容 + 可视化增强内容
"""

from typing import Dict
from data_process.base_report_content_assembler import BaseReportContentAssembler


class IndustryReportContentAssembler(BaseReportContentAssembler):
    """行业研报内容组装器 - 负责内容组装和格式化"""
    
    def __init__(self):
        """初始化内容组装器"""
        super().__init__()
    
    def get_report_title(self, subject_name: str) -> str:
        """获取行业研究报告标题"""
        return f"{subject_name}行业研究报告"
    
    def get_default_section_mapping(self) -> Dict[str, str]:
        """
        获取行业研报的章节映射关系
        
        Returns:
            行业研报专用的章节映射字典
        """
        return {
            "一": "一、行业概况与发展现状",
            "二": "二、市场规模与增长趋势", 
            "三": "三、竞争格局与关键厂商",
            "四": "四、技术趋势与创新动向",
            "五": "五、投资机会与风险分析"
        }
