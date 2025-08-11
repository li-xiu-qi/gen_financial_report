"""
基础报告内容组装器 - 重构版本

此文件已重构，将大文件分解为多个子模块：
- templates.py: 提示词模板和常量
- utils.py: 工具类和辅助函数  
- base_assembler.py: 基础组装器类

为了向后兼容，此文件重新导出所有原有接口
"""

# 重新导出所有接口以保持向后兼容
from .assembler import (
    BaseReportContentAssembler,
    VISUALIZATION_ENHANCEMENT_PROMPT_TEMPLATE,
    CHART_RESOURCE_TEMPLATE,
    CHART_USAGE_REQUIREMENTS,
    TEXT_VISUALIZATION_QUERY_TEMPLATE,
    PathUtils,
    ChartValidator,
    HtmlContentReader,
    TitleValidator
)

# 为了兼容性，保留原有的导入方式
__all__ = [
    'BaseReportContentAssembler',
    'VISUALIZATION_ENHANCEMENT_PROMPT_TEMPLATE',
    'CHART_RESOURCE_TEMPLATE', 
    'CHART_USAGE_REQUIREMENTS',
    'TEXT_VISUALIZATION_QUERY_TEMPLATE',
    'PathUtils',
    'ChartValidator',
    'HtmlContentReader',
    'TitleValidator'
]
