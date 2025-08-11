import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

search_strategy_industry_user_prompt = """

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
     * **必须优先选择中国大陆免费公开的信息源，尤其是权威网站（如政府、交易所、主流财经媒体等），如无则再考虑国际或付费资源。**
       * **优质行业数据源（中国免费优先，通用及中国智能服务机器人产业示例）**:
        * **政府部门和行业协会（中国免费优先）**:
            * 中国政府网 (www.gov.cn): 发布政府规划、政策文件、部分统计数据。
            * 工业和信息化部 (www.miit.gov.cn): 产业政策、发展规划（如“十四五”机器人产业发展规划）、数据统计。
            * 国家发展和改革委员会 (www.ndrc.gov.cn): 宏观行业运行数据、政策发布。
            * 国家统计局 (www.stats.gov.cn): 行业及宏观统计数据。
            * 中国机器人产业联盟 (CRIA): 官方公众号或合作媒体发布年度报告摘要或部分内容（如中国机器人产业发展报告）。
            * 中国电子学会 (www.cie.org.cn): 发布技术白皮书或行业分析。
            * 国际机器人联合会 (IFR) (www.ifr.org): 发布《世界机器人报告》，包含服务机器人部分（新闻稿和报告摘要免费）。
        * **学术机构与科技媒体**:
            * 高校与科研机构官网 (例如：清华大学、浙江大学、中国科学院自动化研究所): 论文、学术报告、研究进展。
            * 雷锋网 (www.leiphone.com): 行业新闻、深度分析、报告解读。
            * 新智元 (www.jiqizhixin.com): 行业新闻、深度分析、报告解读。
            * 机器之心 (www.jiqizhixin.com): 行业新闻、深度分析、报告解读。
        * **企业信息查询平台（中国免费优先）**:
            * 企查查 (www.qichacha.com), 天眼查 (www.tianyancha.com): 企业工商信息、法律诉讼、融资情况、知识产权。
            * 东方财富 (www.eastmoney.com), 同花顺 (www.iwencai.com): 上市公司财报、股市行情、新闻资讯。
        * **专业研究机构/咨询公司（中国免费优先）**: (通常部分内容免费，深度报告我们通过联网搜索filetype:pdf有概率可以免费获取)
            * 艾瑞咨询 (iResearch): 互联网及新经济领域研究报告。
            * IDC (International Data Corporation): 全球信息技术、电信和消费科技市场研究。
            * Gartner: 信息技术研究和咨询公司。
            * 知名券商研究所 (如中金公司、中信证券、国泰君安、华泰证券): 发布各行业深度研究报告。
          
3.  **第三步：查询策略构建 (Query Construction Strategy)**

      * 基于意图和信源，设计一个包含3-5条查询语句的“查询组合（Query Portfolio）”。
      * 这个组合应该体现出**由浅入深、由宏观到微观**的逻辑。
      * **必须优先使用中国大陆免费权威网站，并优先使用高级搜索操作符（`site:`, `filetype:`, `""`, `OR`, `()`）来确保查询的精准性，如无则再考虑国际或付费资源。**
      * **策略原则**:
          * **首查中国免费源头**: 第一条查询通常是定位中国最原始、最权威的免费信源或报告。
          * **次查解读**: 后续查询用于查找对源头信息的深度解读、市场分析或专家观点。
          * **交叉验证**: 通过不同关键词和信源组合，从多个角度验证信息。

4.  **第四步：结构化输出 (Structured Output)**

      * 将你的分析过程和最终的查询组合，封装在一个我们统一的、清晰的JSON对象中。这不仅提供了答案，还展示了“如何得到答案”。所有查询和信源必须优先中国大陆免费权威资源。

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
“获取中国智能服务机器人产业的信息。”

对应输出JSON：

```json
{
  "analysis": {
    "queryType": "行业分析",
    "strategySummary": "构建多层次查询策略，首先聚焦政府官方和行业协会发布的基础数据与政策，随后深入主流财经媒体和科技媒体获取深度解读与趋势分析，最后辅助以企业信息查询平台和学术资源进行补充验证。",
    "primarySources": [
      "中国政府网 (gov.cn)",
      "工业和信息化部 (miit.gov.cn)",
      "国家发展和改革委员会 (ndrc.gov.cn)",
      "国家统计局 (stats.gov.cn)",
      "中国机器人产业联盟 (CRIA)",
      "国际机器人联合会 (ifr.org)",
      "知名券商研究报告",
      "科技媒体 (如雷锋网、新智元、机器之心)",
      "学术机构与科研机构官网",
      "财经媒体 (如财新网、中国证券报、东方财富)"
    ]
  },
  "querySet": [
    {
      "id": 1,
      "objective": "获取中国智能服务机器人产业的官方政策、发展规划及宏观统计数据",
      "query": "中国智能服务机器人产业 (政策 OR 规划 OR 数据) site:gov.cn OR site:miit.gov.cn OR site:ndrc.gov.cn OR site:stats.gov.cn filetype:pdf",
      "explanation": "通过指定政府官方网站、工信部、发改委和国家统计局，获取最权威的产业政策文件、发展规划和官方统计数据，为行业分析奠定基础。"
    },
    {
      "id": 2,
      "objective": "查找中国机器人产业联盟 (CRIA) 和国际机器人联合会 (IFR) 发布的年度报告摘要和行业发展概况",
      "query": "(中国机器人产业发展报告 OR 世界机器人报告) \"智能服务机器人\" (中国 OR 市场) site:ifr.org OR site:cmes.org OR site:leiphone.com OR site:jiqizhixin.com filetype:pdf OR filetype:html",
      "explanation": "聚焦行业权威协会的报告，旨在获取行业整体概况、市场规模、增长趋势等核心数据，尤其关注免费公开的报告摘要和新闻稿，以了解行业基本面。"
    },
    {
      "id": 3,
      "objective": "获取知名券商、咨询机构或专业研究平台发布的中国智能服务机器人行业深度研究报告和产业链分析",
      "query": "\"中国智能服务机器人\" (\"行业研究报告\" OR \"深度报告\" OR \"产业链分析\" OR \"市场前景\") filetype:pdf (\"中金公司\" OR \"中信证券\" OR \"国泰君安\" OR \"华泰证券\" OR \"艾瑞咨询\" OR \"IDC\")",
      "explanation": "检索头部券商和专业咨询机构发布的深度研报，这些报告通常包含详细的财务模型、行业对比、产业链上下游分析、竞争格局和投资建议，有助于深入理解行业生命周期和结构。"
    },
    {
      "id": 4,
      "objective": "了解中国智能服务机器人产业的最新技术发展、创新应用场景及未来趋势预测",
      "query": "中国智能服务机器人 (技术趋势 OR 创新应用 OR 发展前景 OR 核心技术) site:leiphone.com OR site:jiqizhixin.com OR site:cie.org.cn OR site:edu",
      "explanation": "通过科技媒体和教育/学术机构网站，查找关于智能服务机器人领域的技术突破、新兴应用、行业痛点及未来3-5年的发展情景预测，涵盖政策影响、技术演进等外部变量。"
    },
    {
      "id": 5,
      "objective": "收集中国智能服务机器人产业链上下游关键企业信息，包括市场份额、竞争格局、融资动态及主要厂商",
      "query": "中国智能服务机器人 (头部企业 OR 市场份额 OR 竞争格局 OR 融资 OR 关键厂商) site:qichacha.com OR site:tianyancha.com OR site:eastmoney.com OR site:iwencai.com OR site:caixin.com OR site:cnstock.com",
      "explanation": "利用企业信息查询平台和财经媒体，获取行业内主要公司的经营状况、股权结构、融资事件，以及通过新闻报道分析其在产业链中的地位和市场份额，以支持竞争格局和集中度分析。"
    }
  ]
}
```

**# 开始执行 (Begin Execution)**
请根据以上所有要求，为以下输入生成一个完整的JSON格式的搜索指令集：

"""


def search_strategy_industry(
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
    user_content = f"{search_strategy_industry_user_prompt}\n" + search_query
    outline = chat_no_tool(
        user_content=user_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(extract_json_array(outline))
