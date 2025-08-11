import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

generate_company_outline_system_content = """你是一位顶级的专业金融分析师。你的任务是为给定的目标公司，生成一份结构清晰、内容专业的深度研究报告大纲。"""
generate_company_outline_user_prompt = """请你按照要求帮我生成一份研报的大纲，为后续的写作提供框架和思路,。
**核心要求：**
1.  **内容框架**: 大纲需全面覆盖公司基本面、财务、估值及风险等维度。
公司/个股研报应能够自动抽取三大会计报表与股权结构，输出主营业务、核心竞争力与行业地位；
支持财务比率计算与行业对比分析（如ROE分解、毛利率、现金流匹配度），结合同行企业进行横向竞争分析；
构建估值与预测模型，模拟关键变量变化对财务结果的影响（如原材料成本、汇率变动）；
结合公开数据与管理层信息，评估公司治理结构与发展战略，提出投资建议与风险提醒。
2.  **内容形式**: 大纲的要点(points)应该是**需要分析的主题或问题**，用于指导写作方向。**请不要在要点中直接填写具体的数据、分析结论或示例性内容。**
**错误示例 (不要这样做):**
- "盈利预测：2024-2026年收入CAGR 25%"
- "计算机视觉市场CR5=32%（2023Q3）"

**正确示例 (请这样做):**
- "未来三至五年核心财务指标预测"
- "行业集中度与竞争格局分析"
3.  **输出格式**: 必须严格按照JSON格式输出。禁止在JSON代码块前后添加任何多余的解释、注释或文字。
**输出格式示例**:
```json
    "companyName": "4Paradigm",
    "companyCode": "06682.HK",
    "reportOutline": [
        {
            "title": "一、投资摘要与核心观点",
            "points": [
                "核心推荐逻辑：基于公司在AI领域的技术领导地位和商业化前景",
                "盈利预测与估值概要：未来三年收入、利润预测及目标价",
                "投资评级：首次覆盖给予“买入”评级",
                "主要风险提示"
            ]
        },
        {
            "title": "二、公司基本面分析：AI领域的领军者",
            "points": [
                "公司简介与发展历程",
                "股权结构与公司治理分析",
                "主营业务剖析：AI平台、智能决策、垂直行业解决方案",
                "核心竞争力与行业地位：技术平台、客户资源、行业壁垒"
            ]
        },
        {
            "title": "三、财务分析与预测",
            "points": [
                "历史财务回顾：三大报表深度分析，收入成本结构变化",
                "盈利能力分析：ROE分解、毛利率趋势、现金流匹配度",
                "营运效率与现金流分析：关键财务比率计算与解读",
                "未来三至五年财务预测：关键变量敏感性分析模型"
            ]
        },
        {
            "title": "四、估值分析与投资建议",
            "points": [
                "可比公司分析：同行企业横向竞争分析与估值对比",
                "分部估值法（SOTP）：各业务板块价值评估",
                "市销率（P/S）与市盈率估值方法",
                "敏感性分析：原材料成本、汇率变动等关键变量影响",
                "估值总结与目标价测算"
            ]
        },
        {
            "title": "五、风险因素分析",
            "points": [
                "技术迭代与AI行业竞争加剧风险",
                "企业数字化转型需求波动风险",
                "客户集中度与行业周期性风险",
                "监管政策变化与数据安全风险"
            ]
        }
    ]
```
我需要生成的研报的目标公司是：
"""


def generate_company_outline(
    company,
    company_code,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
):
    """
    使用指定的提示词生成公司研报大纲。
    """

    user_content = generate_company_outline_user_prompt + company + company_code
    outline = chat_no_tool(
        user_content=generate_company_outline_system_content + user_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(extract_json_array(outline))
