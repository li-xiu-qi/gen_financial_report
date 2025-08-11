import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array


def generate_search_queries(
    company: str,
    section_title: str,
    section_points: list,
    api_key: str,
    base_url: str,
    model: str,
    max_queries: int = 3,
    max_tokens: int = 2048,
    temperature: float = 0.7
) -> list:
    """
    为特定章节生成搜索查询
    
    Args:
        company: 公司名称
        section_title: 章节标题
        section_points: 章节要点列表
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        max_queries: 最大查询数量
        max_tokens: 最大token数
        temperature: 温度参数
        
    Returns:
        搜索查询列表
    """
    points_text = "\n".join([f"- {point}" for point in section_points[:5]])  # 最多取前5个要点
    
    prompt = f"""你是一个专业的搜索策略专家，需要为公司研究报告的特定章节生成精准的搜索查询。

**目标公司**: {company}
**章节标题**: {section_title}
**章节要点**: 
{points_text}

**任务要求**:
1. 分析章节内容需求，生成 {max_queries} 个不同角度的搜索查询
2. 每个查询都要包含公司名称
3. 查询要针对章节的核心信息需求
4. 使用多样化的关键词组合
5. 适合中文搜索引擎的查询格式

**查询生成策略**:
- 第1个查询：直接针对章节主题
- 第2个查询：从细分角度或具体要点出发  
- 第3个查询：从行业对比或发展趋势角度

**输出格式**:
请严格按照JSON数组格式输出，不要包含任何其他文本：

[
  "查询语句1",
  "查询语句2", 
  "查询语句3"
]

现在请生成搜索查询："""

    try:
        response = chat_no_tool(
            user_content=prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        queries = extract_json_array(response)
        if queries is None:
            return []
            
        parsed_queries = json.loads(queries)
        
        # 确保返回的查询数量不超过max_queries
        return parsed_queries[:max_queries] if isinstance(parsed_queries, list) else []
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"搜索查询生成失败: {e}")
        # 生成备用查询
        fallback_queries = [
            f"{company} {section_title}",
            f"{company} {section_title} 分析",
            f"{company} {section_title} 发展"
        ]
        return fallback_queries[:max_queries]


def company_outline_search_queries(company_name, unmatched_fields, api_key=None, base_url=None, model=None, max_tokens=1000, temperature=0.5):
    """
    利用大模型，根据公司名和未匹配字段生成搜索引擎查询语句。
    Args:
        company_name (str): 公司名称。
        unmatched_fields (list): 未匹配的字段列表。
        api_key, base_url, model, max_tokens, temperature: 大模型参数。
    Returns:
        list: 搜索语句列表。
    """
    prompt = f"""
**# 角色 (Role)**\n你是一个全能的、专家级的“信息检索策略师”（Master Information Retrieval Strategist）。
你的任务是针对公司“{company_name}”的未匹配字段，生成结构化、精准的搜索引擎查询语句。
\n\n**# 工作流程 (Workflow)**\n
1. 意图解析：理解每个字段的核心信息需求。
\n2. 权威信源优先：所有查询必须优先使用国内免费权威网站（如cninfo.com.cn、hkexnews.hk等）。\n
3. 查询语句生成：每个字段生成一条适合搜索引擎的查询语句，结合公司名和字段，使用site:等高级搜索操作符。\n
4. 结构化输出：所有结果以JSON数组输出，每个元素为一条查询语句。\n\n
**# 输入字段列表**\n{unmatched_fields}\n\n
**# 输出格式要求 (Output Format Requirements)**
\n只输出一个JSON数组，每个元素为一条查询语句。
例如：
\n[\n  \"主营业务 site:cninfo.com.cn OR site:hkexnews.hk\",\n  
\"核心团队 site:cninfo.com.cn OR site:hkexnews.hk\"\n]
\n不要输出除JSON数组以外的任何内容。\n\n**# 开始执行 (Begin Execution)**\n"""
    response = chat_no_tool(
        user_content=prompt,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    queries = extract_json_array(response)
    if queries is None:
        return []
    try:
        return json.loads(queries)
    except json.JSONDecodeError:
        return []
