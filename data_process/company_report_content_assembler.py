"""
公司研报内容组装器
负责组装最终的报告内容和参考文献管理
支持两轮内容生成：基础内容 + 可视化增强内容
"""

from typing import Dict
from data_process.base_report_content_assembler import BaseReportContentAssembler


class CompanyReportContentAssembler(BaseReportContentAssembler):
    """公司研报内容组装器 - 负责内容组装和格式化"""
    
    def __init__(self):
        """初始化内容组装器"""
        super().__init__()
    
    def get_report_title(self, subject_name: str) -> str:
        """获取公司研究报告标题"""
        return f"{subject_name}研究报告"
    
    def get_default_section_mapping(self) -> Dict[str, str]:
        """
        获取公司研报的章节映射关系
        
        Returns:
            公司研报专用的章节映射字典
        """
        return {
            "一": "一、投资摘要与核心观点",
            "二": "二、竞争格局与对比分析", 
            "三": "三、公司基本面分析",
            "四": "四、财务状况分析",
            "五": "五、估值分析与投资建议"
        }
