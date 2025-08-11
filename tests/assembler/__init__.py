"""
报告内容组装器模块

重构自 base_report_content_assembler.py，将大文件分解为多个模块：
- templates.py: 提示词模板和常量
- utils.py: 工具类和辅助函数
- base_assembler.py: 基础组装器类
"""

from .base_assembler import BaseReportContentAssembler
from .templates import (
    VISUALIZATION_ENHANCEMENT_PROMPT_TEMPLATE,
    CHART_RESOURCE_TEMPLATE,
    CHART_USAGE_REQUIREMENTS,
    TEXT_VISUALIZATION_QUERY_TEMPLATE
)
from .utils import (
    PathUtils,
    ChartValidator,
    HtmlContentReader,
    TitleValidator
)

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
