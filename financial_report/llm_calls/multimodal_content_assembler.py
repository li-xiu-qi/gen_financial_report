# -*- coding: utf-8 -*-
# @FileName: multimodal_content_assembler.py
# @Author: Kiro
# @Time: 2025-01-23
# @Description: 将文本内容、图片描述和图片路径组装成完整的多模态内容

from typing import List, Dict, Any
from financial_report.utils.chat import chat_no_tool

# 系统提示词
SYSTEM_PROMPT = """你是一位专业的金融报告编辑，擅长将文本内容与可视化图表有机结合，创作出逻辑清晰、结构完整的专业报告。

你的任务是将原始文本内容与相关的图表描述进行智能组装，形成一份结构化、专业化的完整报告段落。"""

# 用户提示词模板
USER_PROMPT_TEMPLATE = """
请将以下内容组装成一个完整、专业的报告段落：

【原始文本内容】
{original_text}

【相关图表信息】
{chart_info}

【组装要求】
1. 保持原始文本的核心信息和专业性
2. 自然地融入图表描述，增强内容的说服力
3. 确保逻辑流畅，避免重复表述
4. 使用专业的金融分析语言
5. 在适当位置提及图表，如"如图所示"、"图表显示"等
6. 整体结构要完整，有开头、分析和小结

请输出组装后的完整段落内容。
"""


def assemble_multimodal_content(
    original_text: str,
    chart_descriptions: List[str],
    image_paths: List[str] = None,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 2000,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    将文本内容与图表描述组装成完整的多模态内容
    
    Args:
        original_text: 原始文本内容
        chart_descriptions: 图表描述列表
        image_paths: 图片路径列表（可选）
        api_key: LLM API Key
        base_url: LLM Base URL
        model: 使用的LLM模型
        max_tokens: 最大生成token数
        temperature: 生成温度
    
    Returns:
        包含组装后内容的字典
    """
    # 构建图表信息字符串
    chart_info_parts = []
    for i, desc in enumerate(chart_descriptions, 1):
        chart_info_parts.append(f"图表{i}：{desc}")
    
    chart_info = "\n".join(chart_info_parts)
    
    user_content = USER_PROMPT_TEMPLATE.format(
        original_text=original_text,
        chart_info=chart_info
    )
    
    try:
        assembled_content = chat_no_tool(
            system_content=SYSTEM_PROMPT,
            user_content=user_content,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        result = {
            "assembled_text": assembled_content.strip(),
            "original_text": original_text,
            "chart_descriptions": chart_descriptions,
            "image_paths": image_paths or [],
            "has_visualizations": len(chart_descriptions) > 0
        }
        
        return result
        
    except Exception as e:
        print(f"Error assembling multimodal content: {e}")
        return {
            "assembled_text": original_text,
            "original_text": original_text,
            "chart_descriptions": chart_descriptions,
            "image_paths": image_paths or [],
            "has_visualizations": False,
            "error": str(e)
        }