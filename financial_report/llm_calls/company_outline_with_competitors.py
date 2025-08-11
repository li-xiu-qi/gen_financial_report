import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array


def company_outline_with_competitors(
    company,
    company_code,
    competitor_names=None, # 添加竞争对手参数
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
):
    """
    使用指定的提示词生成公司研报大纲。
    """
    # 组装 context_info
    context_info = f"""**研报分析要求：**
公司/个股研报应能够自动抽取三大会计报表与股权结构，输出主营业务、核心竞争力与行业地位；
支持财务比率计算与行业对比分析（如ROE分解、毛利率、现金流匹配度），结合同行企业进行横向竞争分析；
构建估值与预测模型，模拟关键变量变化对财务结果的影响（如原材料成本、汇率变动）；
结合公开数据与管理层信息，评估公司治理结构与发展战略，提出投资建议与风险提醒。

**主要竞争对手：**
{', '.join(competitor_names[:4]) if competitor_names else '待分析'}
"""
    
    # 组装 enhanced_prompt
    enhanced_prompt = f"""你是一位顶级的专业金融分析师。你的任务是为给定的目标公司，生成一份结构清晰、内容专业的深度研究报告大纲。

**分析背景信息：**
{context_info}

**核心要求：**
1. **内容框架**: 大纲需全面覆盖公司基本面、财务、估值及风险等维度。
    - 公司/个股研报应能够自动抽取三大会计报表与股权结构，输出主营业务、核心竞争力与行业地位；
    - 支持财务比率计算与行业对比分析（如ROE分解、毛利率、现金流匹配度），结合同行企业进行横向竞争分析；
    - 构建估值与预测模型，模拟关键变量变化对财务结果的影响（如原材料成本、汇率变动）；
    - 结合公开数据与管理层信息，评估公司治理结构与发展战略，提出投资建议与风险提醒。

2. **竞争对手分析重点**: 基于上述竞争对手信息，在大纲中重点体现：
    - 行业竞争格局分析
    - 与主要竞争对手的财务指标对比
    - 竞争优势与劣势分析
    - 市场份额与行业地位评估

3. **内容形式**: 大纲的要点(points)应该是**需要分析的主题或问题**，用于指导写作方向。**请不要在要点中直接填写具体的数据、分析结论或示例性内容。**

**错误示例 (不要这样做):**
- "盈利预测：2024-2026年收入CAGR 25%"
- "计算机视觉市场CR5=32%（2023Q3）"

**正确示例 (请这样做):**
- "未来三至五年核心财务指标预测"
- "行业集中度与竞争格局分析"
- "与主要竞争对手的财务指标横向对比"

4. **输出格式**: 必须严格按照JSON格式输出。禁止在JSON代码块前后添加任何多余的解释、注释或文字。

**输出格式示例**:
```json
{{
    "companyName": "{{target_company}}",
    "companyCode": "{{target_company_code}}",
    "reportOutline": [
        {{
            "title": "一、投资摘要与核心观点",
            "points": [
                "核心推荐逻辑：基于公司在行业中的竞争地位和发展前景",
                "盈利预测与估值概要：未来三年收入、利润预测及目标价",
                "投资评级与目标价",
                "主要风险提示"
            ]
        }},
        {{
            "title": "二、行业竞争格局与公司地位",
            "points": [
                "行业整体竞争格局分析",
                "主要竞争对手业务模式与战略对比",
                "公司在行业中的市场份额与排名",
                "竞争优势与差异化分析"
            ]
        }},
        {{
            "title": "三、公司基本面深度分析",
            "points": [
                "公司简介与发展历程",
                "股权结构与公司治理分析",
                "主营业务结构与盈利模式剖析",
                "核心竞争力与护城河分析"
            ]
        }},
        {{
            "title": "四、财务分析与同业对比",
            "points": [
                "历史财务表现回顾与趋势分析",
                "盈利能力分析及与竞争对手对比",
                "营运能力与现金流质量分析",
                "财务风险评估与债务结构分析"
            ]
        }},
        {{
            "title": "五、估值分析与投资建议",
            "points": [
                "可比公司估值分析（P/E、P/B、EV/EBITDA等）",
                "分部估值法（SOTP）或其他适用估值方法",
                "敏感性分析与估值区间测算",
                "投资建议与目标价设定"
            ]
        }},
        {{
            "title": "六、风险因素分析",
            "points": [
                "行业系统性风险",
                "公司特有经营风险",
                "财务风险与流动性风险",
                "政策监管风险"
            ]
        }}
    ]
}}
""".replace("{{target_company}}", company).replace("{{target_company_code}}", company_code) # 替换占位符


    outline = chat_no_tool(
        user_content=enhanced_prompt, 
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(extract_json_array(outline))