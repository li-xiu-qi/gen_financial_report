# -*- coding: utf-8 -*-
# @FileName: image_description_generator.py
# @Author: Kiro
# @Time: 2025-01-23
# @Description: 为图片生成详细的描述，用于多模态内容组装

import json
from typing import Dict, Any
from financial_report.utils.chat import chat_no_tool

# 系统提示词
SYSTEM_PROMPT = """你是一位专业的金融数据可视化分析师，擅长为图表和信息图生成准确、详细的描述。

你的任务是为即将生成的图表提供一个专业、准确的文字描述，这个描述将与原始文本内容结合，形成完整的多模态报告。"""

# 用户提示词模板
USER_PROMPT_TEMPLATE = """
请为以下即将生成的图表提供一个专业的描述：

【原始文本内容】
{original_text}

【图表信息】
- 图表类型：{chart_type}
- 图表标题：{chart_title}
- 数据内容：{chart_data}

【要求】
1. 描述要准确反映图表所展示的数据和趋势
2. 使用专业的金融分析语言
3. 突出关键的数据洞察和趋势
4. 描述长度控制在100-200字
5. 不要重复原始文本的内容，而是从图表角度提供补充性的分析

请直接输出图表描述，不需要其他格式。
"""


def generate_image_description(
    original_text: str,
    chart_type: str,
    chart_title: str,
    chart_data: Dict[str, Any],
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 1000,
    temperature: float = 0.3,
) -> str:
    """
    为图表生成专业的文字描述
    
    Args:
        original_text: 原始文本内容
        chart_type: 图表类型 (bar, line, pie, etc.)
        chart_title: 图表标题
        chart_data: 图表数据结构
        api_key: LLM API Key
        base_url: LLM Base URL
        model: 使用的LLM模型
        max_tokens: 最大生成token数
        temperature: 生成温度
    
    Returns:
        图表的文字描述
    """
    # 将图表数据转换为可读格式
    data_str = json.dumps(chart_data, ensure_ascii=False, indent=2)
    
    user_content = USER_PROMPT_TEMPLATE.format(
        original_text=original_text,
        chart_type=chart_type,
        chart_title=chart_title,
        chart_data=data_str
    )
    
    try:
        description = chat_no_tool(
            system_content=SYSTEM_PROMPT,
            user_content=user_content,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        return description.strip()
        
    except Exception as e:
        print(f"Error generating image description: {e}")
        return f"图表展示了{chart_title}的相关数据分析结果。"