"""
宏观搜索查询生成器
根据宏观主题生成搜索查询
"""

import json

from financial_report.utils.extract_json_array import extract_json_array
from financial_report.utils.chat import chat_no_tool


def generate_default_macro_queries(macro_theme: str) -> list:
    """
    生成默认的宏观搜索查询列表
    
    Args:
        macro_theme: 宏观主题
        
    Returns:
        默认查询列表
    """
    # 解析主题中的关键信息
    theme_keywords = macro_theme.replace("宏观：", "").strip()
    
    return [
        # 1. 宏观经济核心指标与政策传导
        f"{theme_keywords} GDP CPI 利率 汇率 宏观指标 政策传导 site:stats.gov.cn OR site:pbc.gov.cn filetype:pdf",
        f"{theme_keywords} 经济增长 通胀 就业 投资 消费 (政策效应 OR 影响评估) site:gov.cn",
        f"{theme_keywords} 货币政策 财政政策 产业政策 (协调 OR 联动) 宏观调控",
        
        # 2. 政策落地实施与效果评估
        f"{theme_keywords} 政策实施 落地情况 执行效果 (试点 OR 示范) site:gov.cn filetype:pdf",
        f"{theme_keywords} 产业发展 技术创新 市场规模 (增长率 OR 渗透率) 统计数据",
        f"{theme_keywords} 企业应用 商业模式 产业链 (上中下游 OR 生态圈) 发展报告",
        
        # 3. 区域对比与政策联动
        f"{theme_keywords} 区域差异 省市对比 (东部 OR 中部 OR 西部) 发展不平衡 site:gov.cn",
        f"{theme_keywords} 城市群 经济圈 协同发展 (京津冀 OR 长三角 OR 粤港澳) 政策联动",
        f"{theme_keywords} 地方政策 配套措施 因地制宜 (北京 OR 上海 OR 深圳 OR 杭州)",
        
        # 4. 国际比较与全球影响
        f"{theme_keywords} 国际比较 全球竞争 (中美 OR 中欧) 技术竞争 政策对比",
        f"{theme_keywords} 全球供应链 国际合作 外溢效应 跨境投资 site:oecd.org OR site:worldbank.org",
        f"{theme_keywords} 贸易影响 出口竞争力 (制造业 OR 服务业) 国际市场份额",
        
        # 5. 风险预警与挑战识别
        f"{theme_keywords} 风险预警 挑战问题 (数据安全 OR 就业替代 OR 技术风险) 监管政策",
        f"{theme_keywords} 系统性风险 灰犀牛 (泡沫 OR 过热 OR 结构性问题) 宏观审慎",
        f"{theme_keywords} 可持续发展 长期影响 (环境 OR 社会 OR 伦理) 治理机制"
    ]


def generate_macro_search_queries(
    macro_theme: str,
    outline: dict,
    api_key: str,
    base_url: str,
    model: str,
    max_output_tokens: int = 4096,
    temperature: float = 0.6
) -> list:
    """
    为宏观经济/策略报告生成搜索查询词
    
    Args:
        macro_theme: 宏观主题
        outline: 报告大纲（可选，用于优化查询）
        api_key: API密钥
        base_url: API基础URL
        model: 使用的模型
        max_output_tokens: 最大token数
        temperature: 温度参数
    
    Returns:
        搜索查询字符串列表
    """
    
    system_prompt = """
你是一名专家级宏观经济信息检索策略师。请根据用户的宏观主题，生成一组系统性、覆盖全面的搜索引擎查询语句。

**核心要求：**
1. **宏观经济核心指标传导分析**：重点关注政策对GDP、CPI、利率、汇率、就业、投资、消费等指标的具体影响路径和传导机制
2. **政策落地实施情况**：深入挖掘政策的具体执行情况、试点项目、示范应用、产业发展、技术创新等实际效果
3. **政策联动与区域对比**：分析不同地区政策实施差异、协调联动效应、城市群发展、区域经济影响
4. **全球视野影响评估**：国际比较、全球供应链影响、贸易效应、技术竞争、外溢效应
5. **风险预警与挑战识别**：系统性风险、灰犀牛事件、可持续性挑战、监管风险

**技术要求：**
- 优先使用中国官方权威数据源：site:gov.cn、site:stats.gov.cn、site:pbc.gov.cn、site:ndrc.gov.cn等
- 充分利用高级搜索操作符：site:、filetype:、OR、引号、括号等
- 生成15-20条查询语句，覆盖从宏观到微观、从定量到定性的全维度分析
- 每个查询应针对特定分析维度，避免泛泛而谈
- 输出格式为一个包含 query_set 字段的 JSON 对象，query_set 为查询字符串数组。
- 关键：输出的JSON必须是有效的JSON格式，所有特殊字符必须正确转义：
  * 双引号: \\"
  * 反斜杠: \\\\
  * 换行符: \\n
  * 制表符: \\t
  * 回车符: \\r
  * 退格符: \\b
  * 换页符: \\f
  * 其他控制字符也要相应转义

**示例输入：**"国家级'人工智能+'政策效果评估 (2023-2025)"

**示例输出：**
{
  "query_set": [
    "\\"人工智能+\\" 政策 GDP CPI 利率 (经济增长 OR 通胀影响) 传导机制 site:stats.gov.cn OR site:pbc.gov.cn filetype:pdf",
    "\\"人工智能+\\" 产业发展 制造业 服务业 (产值 OR 增加值 OR 就业) 统计数据 site:stats.gov.cn",
    "\\"人工智能+\\" 试点示范 落地应用 (成功案例 OR 实施效果) 2023 2024 2025 site:gov.cn filetype:pdf",
    "\\"人工智能+\\" 区域发展 (京津冀 OR 长三角 OR 粤港澳) 政策联动 协同效应 site:gov.cn",
    "\\"人工智能+\\" 投资 融资 (风险投资 OR 产业基金 OR 政府投入) 资本市场影响",
    "\\"人工智能+\\" 国际竞争 (中美 OR 中欧) 技术出口 全球供应链 site:mofcom.gov.cn",
    "\\"人工智能+\\" 就业影响 (岗位替代 OR 新增就业 OR 技能需求) 劳动力市场 site:mohrss.gov.cn",
    "\\"人工智能+\\" 风险预警 (数据安全 OR 技术风险 OR 市场泡沫) 监管政策 site:cac.gov.cn"
  ]
}
"""

    user_prompt = f"""
请为宏观主题"{macro_theme}"生成一组系统性、覆盖全面的宏观经济搜索查询语句。

**分析重点：**
1. **宏观指标传导**：该政策对GDP、CPI、利率、汇率、就业、投资、消费等核心指标的具体影响机制
2. **政策落地效果**：具体实施情况、试点项目、产业发展、技术创新、市场变化等实际效果
3. **区域差异分析**：不同地区实施情况、政策联动、协调发展、区域经济影响
4. **国际影响评估**：全球竞争力、贸易影响、技术出口、国际合作等
5. **风险与挑战**：潜在风险、监管挑战、可持续性问题、灰犀牛事件

**输出要求：**
- 15-20条高质量搜索查询语句
- 优先使用官方权威数据源
- 运用高级搜索操作符提高精准度
- 覆盖定量分析和定性评估
- 输出格式为一个包含 query_set 字段的 JSON 对象，query_set 为查询字符串数组。
- 关键：输出的JSON必须是有效的JSON格式，所有特殊字符必须正确转义：
  * 双引号: \\"
  * 反斜杠: \\\\
  * 换行符: \\n
  * 制表符: \\t
  * 回车符: \\r
  * 退格符: \\b
  * 换页符: \\f
  * 其他控制字符也要相应转义
- 确保输出的JSON字符串可以被Python的json.loads()正确解析。
"""

    try:
        result = chat_no_tool(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            api_key=api_key,
            base_url=base_url,
            user_content=user_prompt,
            system_content=system_prompt,
            temperature=temperature,
            max_tokens=max_output_tokens
        )
        
        # 只解析 JSON 对象中的 query_set 数组
        json_text = extract_json_array(result, mode='auto')
        if json_text:
            try:
                # 尝试解析为完整 JSON 对象
                json_obj = json.loads(json_text)
                if isinstance(json_obj, dict) and 'query_set' in json_obj:
                    return json_obj['query_set']
                elif isinstance(json_obj, list):
                    # 兼容旧格式：如果是数组直接返回
                    return json_obj
                else:
                    print("⚠️ JSON格式不正确，使用默认查询")
                    return generate_default_macro_queries(macro_theme)
            except json.JSONDecodeError:
                print("⚠️ JSON解析失败，使用默认查询")
                return generate_default_macro_queries(macro_theme)
        else:
            print("⚠️ 未能提取JSON，使用默认查询")
            return generate_default_macro_queries(macro_theme)
        
    except Exception as e:
        print(f"⚠️ 搜索查询生成失败，使用默认查询: {e}")
        return generate_default_macro_queries(macro_theme)
