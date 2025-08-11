import json

from financial_report.utils.extract_json_array import extract_json_array
from financial_report.utils.chat import chat_no_tool


def generate_default_company_queries(company_name: str, stock_code: str = None) -> list:
    """
    生成默认的公司搜索查询列表
    
    Args:
        company_name: 公司名称
        stock_code: 股票代码（可选）
        
    Returns:
        默认查询列表
    """
    # 构建基础查询词
    base_queries = [
        f"{company_name} 年报 财务报表 主营业务 核心竞争力",
        f"{company_name} 研究报告 投资价值 行业地位",
        f"{company_name} 财务分析 ROE 毛利率 现金流",
        f"{company_name} 竞争对手 行业对比 市场份额",
        f"{company_name} 估值分析 投资建议 目标价格",
        f"{company_name} 管理层 公司治理 发展战略",
        f"{company_name} 业务结构 收入构成 盈利模式",
        f"{company_name} 风险因素 投资风险 经营风险"
    ]
    
    # 如果有股票代码，增加代码相关查询
    if stock_code:
        base_queries.extend([
            f"{stock_code} {company_name} 股票分析 投资价值",
            f"{stock_code} 财务数据 业绩预测 估值水平"
        ])
    
    return base_queries


def generate_company_search_queries(
    company_name: str,
    stock_code: str = None,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 4096,
    temperature: float = 0.6
) -> list:
    """
    为公司研报生成搜索查询词
    
    Args:
        company_name: 公司名称
        stock_code: 股票代码（可选，如：06682.HK）
        api_key: API密钥
        base_url: API基础URL
        model: 使用的模型
        max_tokens: 最大token数
        temperature: 生成温度
    
    Returns:
        搜索查询字符串列表
    """
    
    system_prompt = """
你是一名专家级证券研究分析师和信息检索策略师。请根据用户的公司研究需求，直接输出一组高质量、覆盖全面的搜索引擎查询语句。

要求：
- 查询语句需优先中国大陆权威金融信息源，充分利用 site:、filetype:、OR、引号等高级搜索操作符。
- 查询需覆盖以下核心维度：
  * 财务报表与会计数据（三大报表、财务比率、现金流）
  * 主营业务与核心竞争力分析
  * 行业地位与竞争对手对比
  * 估值分析与投资建议
  * 公司治理与管理层评估
  * 发展战略与业务前景
  * 风险因素与投资风险
  * 股权结构与股东信息
- 生成12-18条查询语句，从非常细致的专业查询到粗糙的基础查询，确保全面覆盖。
- 输出格式为一个包含 query_set 字段的 JSON 对象，query_set 为查询字符串数组。

示例输入："4Paradigm（06682.HK）"
示例输出：
{
  "query_set": [
    "\"4Paradigm\" \"06682.HK\" (年报 OR 财务报表 OR 业绩公告) filetype:pdf site:hkexnews.hk OR site:eastmoney.com OR site:cninfo.com.cn",
    "\"4Paradigm\" \"第四范式\" (研究报告 OR 投资分析 OR 深度报告) (\"中金公司\" OR \"中信证券\" OR \"国泰君安\" OR \"华泰证券\" OR \"招银国际\" OR \"中银国际\") filetype:pdf",
    "\"4Paradigm\" \"第四范式\" (ROE OR 毛利率 OR 现金流 OR 财务比率 OR 盈利能力) site:eastmoney.com OR site:choice.com OR site:wind.com.cn",
    "\"4Paradigm\" \"第四范式\" (竞争对手 OR 行业对比 OR 市场份额 OR 行业地位) (人工智能 OR AI OR 机器学习)",
    "\"4Paradigm\" \"第四范式\" (估值分析 OR 投资建议 OR 目标价 OR DCF OR PE OR PB) site:eastmoney.com OR site:cnstock.com",
    "\"4Paradigm\" \"第四范式\" (管理层 OR 公司治理 OR 董事会 OR 股权结构) site:hkexnews.hk OR site:cninfo.com.cn",
    "\"4Paradigm\" \"第四范式\" (发展战略 OR 业务前景 OR 商业模式 OR 核心技术) filetype:pdf",
    "\"4Paradigm\" \"第四范式\" (风险因素 OR 投资风险 OR 经营风险 OR 技术风险)",
    "\"06682.HK\" (股票分析 OR 投资价值 OR 技术分析 OR 基本面分析) site:eastmoney.com OR site:sina.com.cn OR site:163.com",
    "\"第四范式\" 人工智能 (主营业务 OR 核心产品 OR 业务结构 OR 收入构成)",
    "\"4Paradigm\" \"第四范式\" (同花顺 OR 财务数据 OR 业绩预测 OR 分析师预期) site:10jqka.com.cn OR site:iwencai.com",
    "\"4Paradigm\" 人工智能平台 (技术优势 OR 核心竞争力 OR 护城河 OR 技术壁垒)",
    "\"第四范式\" (IPO OR 上市 OR 招股书 OR 招股说明书) filetype:pdf site:hkexnews.hk",
    "\"4Paradigm\" (客户结构 OR 下游客户 OR 应用场景 OR 商业落地)",
    "人工智能 机器学习平台 (\"4Paradigm\" OR \"第四范式\") 行业分析",
    "\"第四范式\" 财报 业绩 营收"
  ]
}
"""

    # 构建用户提示词
    stock_info = f"（{stock_code}）" if stock_code else ""
    user_prompt = f"""
请为"{company_name}{stock_info}"生成一组高质量、覆盖全面的公司研究搜索查询语句。

公司背景信息：
- 公司名称：{company_name}
- 股票代码：{stock_code if stock_code else "未提供"}
- 研究重点：财务分析、竞争力评估、估值分析、投资建议

要求：
- 查询语句需优先中国大陆和香港权威金融信息源，充分利用 site:、filetype:、OR、引号等高级搜索操作符。
- 查询需覆盖财务报表、主营业务、行业地位、估值分析、公司治理、发展战略、风险因素等核心维度。
- 包含同花顺等财经数据平台的查询。
- 输出格式为一个包含 query_set 字段的 JSON 对象，query_set 为查询字符串数组。
"""

    try:
        result = chat_no_tool(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}],
            api_key=api_key,
            base_url=base_url,
            user_content=user_prompt,
            system_content=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
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
                    return generate_default_company_queries(company_name, stock_code)
            except json.JSONDecodeError:
                print("⚠️ JSON解析失败，使用默认查询")
                return generate_default_company_queries(company_name, stock_code)
        else:
            print("⚠️ 未能提取JSON，使用默认查询")
            return generate_default_company_queries(company_name, stock_code)
        
    except Exception as e:
        print(f"⚠️ 搜索查询生成失败，使用默认查询: {e}")
        return generate_default_company_queries(company_name, stock_code)
