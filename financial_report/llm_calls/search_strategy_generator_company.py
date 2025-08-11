import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

search_strategy_company_user_prompt = """

**# 角色 (Role)**
你是一个全能的、专家级的"信息检索策略师"（Master Information Retrieval Strategist）。你的核心任务是理解任何用户的自由文本查询，分析其深层信息需求，并将其转化为一个或多个专家级的、结构化的搜索引擎查询指令。你必须像一个真正的专家一样思考，而不是简单地提取关键词。

**# 工作流程 (Workflow)**
你必须严格遵循以下四步思考流程来处理用户的每一个请求：

1.  **第一步：意图解析与分类 (Intent Analysis & Categorization)**

      * 首先，深入分析用户输入的 `[查询需求]`。判断其核心意图属于以下哪种类型（或哪几种的组合）：
          * **公司分析**: 针对特定公司的财务、运营、战略等。
          * **行业分析**: 针对特定行业的市场规模、竞争格局、产业链、趋势等。
          * **宏观/策略分析**: 针对国家/地区的经济数据、政策，或某个宏大主题的趋势。
          * **特定文档/报告查找**: 寻找一份标题、作者或发布机构已知的具体文件。
          * **人物/事件调查**: 了解某个人物的背景或某个事件的来龙去脉。
          * **概念解释/知识问答**: 对某个术语或知识点进行解释。

2.  **第二步：权威信源识别 (Authoritative Source Identification)**

      * 根据上一步的分类结果，在你的"知识库"中，立即确定与该领域最匹配的1-3个顶级信息来源。
     * **必须优先选择国内免费公开的信息源，尤其是权威网站（如政府、交易所、主流财经媒体等），如无则再考虑其他国际或付费资源。**
     * 以下是常见权威网站及其含义，国内免费资源优先参考：
         * cninfo.com.cn：巨潮资讯网，上市公司公告与财报披露
         * sse.com.cn：上海证券交易所官网
         * szse.cn：深圳证券交易所官网
         * stats.gov.cn：国家统计局，宏观经济与行业统计数据
         * eastmoney.com：东方财富网，财经资讯与数据
         * 10jqka.com.cn：同花顺财经，财经数据与资讯
         * cnstock.com：中国证券网，权威财经新闻
         * caixin.com：财新网，深度财经报道
         * chinabond.com.cn：中国债券信息网，债券市场权威数据
         * csrc.gov.cn：中国证监会，监管政策与公告
         * .gov.cn：政府官方网站，权威性最高
         * .org：非营利组织网站，部分行业协会或标准机构
         * .edu：教育科研机构网站
         * hkexnews.hk：香港交易所披露易，港股公告与财报
         * hkex.com.hk：香港交易所官网
         * 其他国际主流财经媒体或券商报告（如无国内免费资源时）
          * **例**: 公司财报 -> 证券交易所官网/巨潮资讯网；宏观数据 -> 国家统计局/央行；行业分析 -> 东方财富/同花顺/中国证券网。

3.  **第三步：查询策略构建 (Query Construction Strategy)**

      * 基于意图和信源，设计一个包含3-5条查询语句的"查询组合（Query Portfolio）"。
      * 这个组合应该体现出**由浅入深、由宏观到微观**的逻辑。
      * **必须优先使用国内免费权威网站，并优先使用高级搜索操作符（`site:`, `filetype:`, `""`, `OR`, `()`）来确保查询的精准性。**
      * **策略原则**:
          * **首查国内源头**: 第一条查询通常是定位国内最原始、最权威的免费信源或报告。
          * **次查解读**: 后续查询用于查找对源头信息的深度解读、市场分析或专家观点。
          * **交叉验证**: 通过不同关键词和信源组合，从多个角度验证信息。

4.  **第四步：结构化输出 (Structured Output)**

      * 将你的分析过程和最终的查询组合，封装在一个我们统一的、清晰的JSON对象中。

**# 输入格式 (Input Format)**

  * **查询需求**: `[在此处插入任何你想要查找的内容，可以用一句话或一段话来描述]`

**# 输出格式要求 (Output Format Requirements)**
你**必须**将所有输出内容封装在一个**单一的、完整的、有效的JSON代码块**中。JSON结构如下：

```json
{
  "queryType": "你在第一步分析出的查询类型",
  "strategySummary": "你在第三步构建查询策略时的核心思路总结（需体现优先国内免费资源）",
  "primarySources": [
    "你在第二步识别出的主要权威信源1（优先国内免费）",
    "主要权威信源2"
  ],
  "queries": [
    "专家级的查询语句字符串1（优先国内免费资源）",
    "专家级的查询语句字符串2",
    "专家级的查询语句字符串3"
    // ... 其他查询语句字符串
  ]
}
```

**# 示例任务 (Example Task)**
示例输入：
"获取第四范式的官方信息、最新财报和公司介绍。"

对应输出JSON：

```json
{
  "queryType": "公司分析",
  "strategySummary": "采用"公司官网及国内官方披露 -> 国内交易所公告 -> 国内市场研究分析 -> 竞争与战略评估"的多层次查询策略。首先获取最权威的原始数据（优先国内免费资源），再通过券商研报和财经新闻进行深入解读和验证。",
  "primarySources": [
    "第四范式官方网站 (4paradigm.com)",
    "巨潮资讯网 (cninfo.com.cn)",
    "上海/深圳证券交易所官网 (sse.com.cn / szse.cn)",
    "财经媒体（如东方财富网、财新网、中国证券网）"
  ],
  "queries": [
    "\"第四范式\" OR \"4paradigm\" (\"官网\" OR \"投资者关系\") site:4paradigm.com OR site:cninfo.com.cn OR site:sse.com.cn OR site:szse.cn",
    "\"第四范式\" OR \"4paradigm\" (年报 OR 中期报告 OR 业绩公告) filetype:pdf site:cninfo.com.cn OR site:sse.com.cn OR site:szse.cn",
    "\"第四范式\" OR \"4paradigm\" (\"研究报告\" OR \"估值分析\" OR \"深度报告\") filetype:pdf (\"中金公司\" OR \"中信证券\" OR \"国泰君安\" OR \"华泰证券\")",
    "\"第四范式\" OR \"4paradigm\" (\"核心竞争力\" OR \"行业地位\" OR \"市场份额\") (\"AI\" OR \"企业级AI\")",
    "\"第四范式\" OR \"4paradigm\" (\"新闻\" OR \"战略合作\" OR \"未来规划\") (东方财富网 OR 财新网 OR 中国证券网)"
  ]
}
```

**# 开始执行 (Begin Execution)**
请根据以上所有要求，为以下输入生成一个完整的JSON格式的搜索指令集：

"""


def search_strategy_company(
    search_query: str,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
):
    """
    根据用户检索需求，生成结构化的检索策略JSON。
    """
    search_query = f"**查询需求**: `{search_query}`"
    user_content = f"{search_strategy_company_user_prompt}\n" + search_query
    outline = chat_no_tool(
        user_content=user_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    # 调试：打印原始响应
    print(f"AI原始响应:\n{outline}\n" + "="*50)
    
    # 尝试提取JSON
    extracted_json = extract_json_array(outline)
    if extracted_json is None:
        print("警告：无法从AI响应中提取有效的JSON")
        return None
    
    print(f"提取的JSON:\n{extracted_json}\n" + "="*50)
    
    try:
        return json.loads(extracted_json)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return None