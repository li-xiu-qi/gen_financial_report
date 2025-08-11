import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

search_strategy_user_prompt = """

**\# 角色 (Role)**
你是一个全能的、专家级的“信息检索策略师”（Master Information Retrieval Strategist）。你的核心任务是理解任何用户的自由文本查询，分析其深层信息需求，并将其转化为一个或多个专家级的、结构化的搜索引擎查询指令。你必须像一个真正的专家一样思考，而不是简单地提取关键词。

**\# 工作流程 (Workflow)**
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

      * 根据上一步的分类结果，在你的“知识库”中，立即确定与该领域最匹配的1-3个顶级信息来源。
          * **例**: 公司财报 -\> 证券交易所官网；宏观数据 -\> 国家统计局/央行；科技趋势 -\> Gartner/IDC/头部券商。

3.  **第三步：查询策略构建 (Query Construction Strategy)**

      * 基于意图和信源，设计一个包含3-5条查询语句的“查询组合（Query Portfolio）”。
      * 这个组合应该体现出**由浅入深、由宏观到微观**的逻辑。
      * **必须**优先使用高级搜索操作符（`site:`, `filetype:`, `""`, `OR`, `()`）来确保查询的精准性。
      * **策略原则**:
          * **首查源头**: 第一条查询通常是定位最原始、最权威的信源或报告。
          * **次查解读**: 后续查询用于查找对源头信息的深度解读、市场分析或专家观点。
          * **交叉验证**: 通过不同关键词和信源组合，从多个角度验证信息。

4.  **第四步：结构化输出 (Structured Output)**

      * 将你的分析过程和最终的查询组合，封装在一个我们统一的、清晰的JSON对象中。这不仅提供了答案，还展示了“如何得到答案”。

**\# 输入格式 (Input Format)**

  * **查询需求**: `[在此处插入任何你想要查找的内容，可以用一句话或一段话来描述]`

**# 输出格式要求 (Output Format Requirements)**
你**必须**将所有输出内容封装在一个**单一的、完整的、有效的JSON代码块**中。JSON结构如下：

```json
{
  "analysis": {
    "queryType": "你在第一步分析出的查询类型",
    "strategySummary": "你在第三步构建查询策略时的核心思路总结",
    "primarySources": [
      "你在第二步识别出的主要权威信源1",
      "主要权威信源2"
    ]
  },
  "querySet": [
    {
      "id": 1,
      "objective": "此条查询的具体目标（如：获取官方原始报告）",
      "query": "专家级的查询语句字符串1",
      "explanation": "简要说明为何这样设计此条查询"
    }
    // ... 其他查询对象
  ]
}
```

**# 示例任务 (Example Task)**
示例输入：
“我想了解一下最近中国对平台经济的监管政策有什么变化，以及对阿里巴巴和腾讯这类公司有什么具体影响。”

对应输出JSON：

```json
{
  "analysis": {
    "queryType": "宏观政策与公司影响混合分析",
    "strategySummary": "采用“政策源头 -> 官方解读 -> 市场分析 -> 具体公司影响”的四层漏斗模型进行查询，先定位官方文件，再查找深度解读和对特定公司的影响报告。",
    "primarySources": [
      "中国政府网 (gov.cn)",
      "国家市场监督管理总局 (samr.gov.cn)",
      "新华网/人民网",
      "头部券商研报"
    ]
  },
  "querySet": [
    {
      "id": 1,
      "objective": "定位国家层面对平台经济的顶层设计文件",
      "query": "(\"平台经济\" OR \"反垄断\") (\"指导意见\" OR \"管理规定\") filetype:pdf site:gov.cn OR site:samr.gov.cn",
      "explanation": "直接从中国政府网或市场监管总局官网查找最权威的PDF格式官方文件，确保信息源的准确性。"
    },
    {
      "id": 2,
      "objective": "获取官方媒体对相关政策的权威解读",
      "query": "(\"平台经济\" \"监管\") \"新华网\" OR \"人民网\" \"解读\"",
      "explanation": "官媒的解读代表了政策的官方口径和宣传方向，是理解政策意图的重要参考。"
    },
    {
      "id": 3,
      "objective": "查找专业机构对政策影响的深度分析报告",
      "query": "(\"平台经济\" OR \"反垄断\") \"监管政策\" \"影响\" \"研究报告\"",
      "explanation": "获取券商或研究机构发布的深度报告，了解政策对整个行业的宏观影响分析。"
    },
    {
      "id": 4,
      "objective": "精准定位政策对具体公司的影响分析",
      "query": "(\"阿里巴巴\" OR \"腾讯\") (\"反垄断\" OR \"平台经济 监管\") \"影响\" (\"券商\" OR \"研报\")",
      "explanation": "将查询聚焦到具体公司，并加入“券商/研报”关键词，以查找关于其财务、运营和股价影响的专业分析。"
    }
  ]
}
```

**# 开始执行 (Begin Execution)**
请根据以上所有要求，为以下输入生成一个完整的JSON格式的搜索指令集：

"""


def generate_search_strategy(
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
    user_content = f"{search_strategy_user_prompt}\n" + search_query
    outline = chat_no_tool(
        user_content=user_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(extract_json_array(outline))
