"""
行业搜索查询生成器
根据行业名称生成搜索查询
"""

import json

from financial_report.utils.extract_json_array import extract_json_array
from financial_report.utils.chat import chat_no_tool


def generate_default_industry_queries(industry_name: str) -> list:
    """
    生成默认的行业搜索查询列表
    
    Args:
        industry_name: 行业名称
        
    Returns:
        默认查询列表
    """
    return [
        f"中国{industry_name} 行业研究报告 市场规模 发展趋势",
        f"{industry_name} 产业链分析 竞争格局 主要企业",
        f"中国{industry_name} 政策支持 发展规划 投资机会",
        f"{industry_name} 技术发展 创新应用 未来前景",
        f"中国{industry_name} 市场份额 增长率 统计数据",
        f"{industry_name} 行业分析 发展现状 挑战机遇",
        f"中国{industry_name} 重点企业 融资情况 商业模式",
        f"{industry_name} 产业发展报告 市场前景分析"
    ]


def generate_industry_search_queries(
    industry_name: str,
    api_key: str,
    base_url: str,
    model: str,
    outline: dict = None,
    max_output_tokens: int = 4096,
    max_tokens: int = None,
    temperature: float = 0.6
) -> list:
    """
    为行业研报生成搜索查询词
    
    Args:
        industry_name: 行业名称
        api_key: API密钥
        base_url: API基础URL
        model: 使用的模型
        outline: 行业大纲信息（可选）
        max_output_tokens: 最大token数
        max_tokens: 最大token数（与max_output_tokens相同，兼容性参数）
        temperature: 温度参数
    
    Returns:
        搜索查询字符串列表
    """
    
    system_prompt = """
你是一名专家级信息检索策略师。请根据用户的行业需求，直接输出一组高质量、覆盖全面的搜索引擎查询语句。
要求：
- 查询语句需优先中国大陆权威免费信息源，充分利用 site:、filetype:、OR、引号等高级搜索操作符。
- 查询需覆盖行业规模、发展趋势、竞争格局、产业链、政策技术、投资策略等核心维度。
- 生成10-15条查询语句，从非常细致的专业查询到粗糙的基础查询，确保全面覆盖。
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

示例输入："获取中国智能服务机器人产业的信息。"
示例输出：
{
  "query_set": [
    "中国智能服务机器人产业 (政策 OR 规划 OR 数据) site:gov.cn OR site:miit.gov.cn OR site:ndrc.gov.cn OR site:stats.gov.cn filetype:pdf",
    "\\"中国智能服务机器人\\" \\"产业链分析\\" \\"市场规模\\" \\"竞争格局\\" filetype:pdf site:eastmoney.com OR site:caixin.com",
    "(中国机器人产业发展报告 OR 世界机器人报告) \\"智能服务机器人\\" (中国 OR 市场) site:ifr.org OR site:cmes.org OR site:leiphone.com OR site:jiqizhixin.com filetype:pdf OR filetype:html",
    "\\"中国智能服务机器人\\" (\\"行业研究报告\\" OR \\"深度报告\\" OR \\"产业链分析\\" OR \\"市场前景\\") filetype:pdf (\\"中金公司\\" OR \\"中信证券\\" OR \\"国泰君安\\" OR \\"华泰证券\\" OR \\"艾瑞咨询\\" OR \\"IDC\\")",
    "中国智能服务机器人 (技术趋势 OR 创新应用 OR 发展前景 OR 核心技术) site:leiphone.com OR site:jiqizhixin.com OR site:cie.org.cn OR site:edu",
    "中国智能服务机器人 (头部企业 OR 市场份额 OR 竞争格局 OR 融资 OR 关键厂商) site:qichacha.com OR site:tianyancha.com OR site:eastmoney.com OR site:iwencai.com OR site:caixin.com OR site:cnstock.com",
    "\\"智能服务机器人\\" \\"产业政策\\" \\"十四五规划\\" site:gov.cn OR site:miit.gov.cn",
    "中国服务机器人 市场规模 增长率 统计数据 site:stats.gov.cn OR site:cei.cn",
    "智能服务机器人 行业分析 发展现状",
    "服务机器人产业 中国市场 发展趋势",
    "中国机器人行业报告"
  ]
}
"""

    # 处理兼容性参数 - 统一使用max_output_tokens
    if max_tokens is not None:
        max_output_tokens = max_tokens
    
    # 如果提供了outline信息，可以在这里使用来优化搜索查询
    # 目前保持现有逻辑，未来可以根据outline内容生成更精准的查询
    
    user_prompt = f"""
请为"中国{industry_name}"生成一组高质量、覆盖全面的行业搜索查询语句。
要求：
- 查询语句需优先中国大陆权威免费信息源，充分利用 site:、filetype:、OR、引号等高级搜索操作符。
- 查询需覆盖行业规模、发展趋势、竞争格局、产业链、政策技术、投资策略等核心维度。
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
                    return generate_default_industry_queries(industry_name)
            except json.JSONDecodeError:
                print("⚠️ JSON解析失败，使用默认查询")
                return generate_default_industry_queries(industry_name)
        else:
            print("⚠️ 未能提取JSON，使用默认查询")
            return generate_default_industry_queries(industry_name)
        
    except Exception as e:
        print(f"⚠️ 搜索查询生成失败，使用默认查询: {e}")
        return generate_default_industry_queries(industry_name)
