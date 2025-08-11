# -*- coding: utf-8 -*-
# @FileName: visual_content_identifier.py
# @Author: Gemini
# @Time: 2025-07-22
# @Description: This module analyzes text to identify content suitable for visualization and extracts the relevant data.

import json
from typing import Dict, Any
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_object import extract_json_object

# --- Prompt Definition ---

# 1. 定义系统角色：一个专业的、具有敏锐洞察力的数据可视化专家。
SYSTEM_PROMPT = """你是一名顶级的金融数据分析师和可视化专家，拥有敏锐的洞察力。你能够从复杂的商业和财务文本中，精准地识别出适合通过图表（如ECharts）呈现的数据关系，并将其转化为结构化的、可供程序使用的数据格式。"""

# 2. 构建用户Prompt模板：包含详细的任务指令、核心标准、JSON格式要求和丰富的示例。
USER_PROMPT_TEMPLATE = """
【任务】
请严格按照以下要求，分析【待分析文本】内容：
1.  **判断是否适合可视化**：判断文本中是否包含明确的、可用于生成图表的数据关系。
2.  **提取核心要素**：如果适合，请提取生成图表所需的全部核心要素，包括最恰当的图表类型、一个精炼的图表标题以及完全结构化的数据。
3.  **输出JSON**：必须严格按照指定的JSON格式输出结果，不要添加任何额外的解释或注释。

【核心识别标准】
重点关注并识别以下几种典型的、具有高可视化价值的数据分析场景：
1.  **时间序列分析 (Time Series)**: 数据在连续时间维度上的演变，如历年/季度/月度的财务指标、用户增长等。常用图表: `line` (折线图), `bar` (柱状图)。
2.  **横向对比分析 (Comparison)**: 多个主体在同一指标下的横向比较，如不同公司间的财务比率、不同产品的市场表现等。常用图表: `bar` (柱状图)。
3.  **构成比例分析 (Composition)**: 某个整体由不同部分组成的百分比或数值分布，如公司的业务收入构成、成本结构、行业市场份额等。常用图表: `pie` (饼图), `donut` (环形图)。

【JSON输出格式】
```json
{
  "is_visualizable": true,
  "reason": "此处填写判断理由，如果为false，请说明原因（例如：'文本为定性描述，缺乏可量化的数据。'）",
  "visualization_type": "line",
  "chart_title": "建议的图表标题",
  "extracted_data": {
    "categories": ["类目1", "类目2"],
    "series": [
      {
        "name": "系列名称1",
        "data": [100, 200]
      }
    ]
  }
}
```

---
【示例1：时间序列】
待分析文本: "根据财报，商汤科技的研发投入持续增长，2021年投入为30.5亿元，2022年达到了42.1亿元，而2023年进一步增加至55.8亿元，体现了公司对技术创新的重视。"
预期输出:
```json
{
  "is_visualizable": true,
  "reason": "文本提供了商汤科技连续三年的研发投入数据，是典型的时间序列，适合用柱状图展示其逐年增长的趋势。",
  "visualization_type": "bar",
  "chart_title": "商汤科技2021-2023年研发投入情况",
  "extracted_data": {
    "categories": ["2021年", "2022年", "2023年"],
    "series": [
      {
        "name": "研发投入（亿元）",
        "data": [30.5, 42.1, 55.8]
      }
    ]
  }
}
```

---
【示例2：竞争对手对比】
待分析文本: "在盈利能力方面，云天畅想2023年的毛利率为35%，而行业龙头海康威视和大华股份同期的毛利率分别为42%和45%，显示出公司在成本控制方面与头部企业尚有差距。"
预期输出:
```json
{
  "is_visualizable": true,
  "reason": "文本清晰地对比了三家公司在同一指标（毛利率）下的数据，是典型的横向对比场景，适合使用柱状图。",
  "visualization_type": "bar",
  "chart_title": "2023年主要公司毛利率对比",
  "extracted_data": {
    "categories": ["云天畅想", "海康威视", "大华股份"],
    "series": [
      {
        "name": "毛利率（%）",
        "data": [35, 42, 45]
      }
    ]
  }
}
```

---
【示例3：行业市场份额】
待分析文本: "根据IDC报告，2023年下半年中国AI云服务市场格局保持稳定，其中阿里云市场份额为39.8%，华为云以18.6%位居第二，腾讯云和百度智能云则分别占据12.5%和9.1%的市场份额。"
预期输出:
```json
{
  "is_visualizable": true,
  "reason": "文本描述了多个主体（公司）在整体市场中的占比情况，是典型的构成比例分析，适合用饼图或环形图直观展示。",
  "visualization_type": "pie",
  "chart_title": "2023H2中国AI云服务市场份额分布",
  "extracted_data": {
    "categories": ["阿里云", "华为云", "腾讯云", "百度智能云"],
    "series": [
      {
        "name": "市场份额（%）",
        "data": [39.8, 18.6, 12.5, 9.1]
      }
    ]
  }
}
```

---
【示例4：公司业务构成】
待分析文本: "商汤科技2023年的收入构成为：生成式AI业务贡献了12亿元，占总收入的35%；传统AI业务收入为18亿元，占比52%；而智能汽车相关业务收入为4.8亿元，占比13%。"
预期输出:
```json
{
  "is_visualizable": true,
  "reason": "文本详细列出了公司总收入按不同业务线的构成情况，是构成比例分析的经典场景，适合使用环形图。",
  "visualization_type": "donut",
  "chart_title": "商汤科技2023年收入业务构成",
  "extracted_data": {
    "categories": ["生成式AI", "传统AI", "智能汽车"],
    "series": [
      {
        "name": "收入（亿元）",
        "data": [12, 18, 4.8]
      }
    ]
  }
}
```

---
【待分析文本】
{text_to_analyze}
"""


def identify_visualizable_content(
    text_to_analyze: str,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 2000,
    temperature: float = 0.2,
) -> Dict[str, Any]:
    """
    分析给定文本，判断其是否适合可视化，并提取相关数据。

    Args:
        text_to_analyze: 待分析的文本内容。
        api_key: LLM API Key.
        base_url: LLM Base URL.
        model: 使用的LLM模型。
        max_tokens: 最大生成token数。
        temperature: 生成温度。

    Returns:
        一个包含分析结果的字典，格式遵循Prompt中的定义。
    """
    user_content = USER_PROMPT_TEMPLATE.format(text_to_analyze=text_to_analyze)

    try:
        response_str = chat_no_tool(
            system_content=SYSTEM_PROMPT,
            user_content=user_content,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        response_str = extract_json_object(response_str)
        
        if response_str is None:
            print(f"Warning: No valid JSON object found in LLM response")
            return {"is_visualizable": False, "reason": "Failed to extract JSON from LLM response."}
        
        return json.loads(response_str)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from LLM response: {e}")
        print(f"Raw response: {response_str}")
        return {"is_visualizable": False, "reason": "Failed to parse LLM response as JSON."}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {"is_visualizable": False, "reason": f"An unexpected error occurred: {e}"}
