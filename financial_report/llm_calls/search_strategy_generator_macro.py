import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

search_strategy_macro_user_prompt = """

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
 * **必须优先选择中国大陆免费公开的信息源，尤其是权威网站（如政府、央行、主流财经媒体等），如无则再考虑国际或付费资源。**
 * **优质宏观经济/策略数据源（中国免费优先，通用及“人工智能+”政策评估示例）**:

        * **中国宏观经济核心指标与政策数据（中国免费优先）**:

            * 国家统计局 (National Bureau of Statistics of China, NBS) (http://data.stats.gov.cn/): 最权威、最全面的中国宏观经济数据平台。

            * 中国人民银行 (People's Bank of China, PBOC) (http://www.pbc.gov.cn/): 货币政策、利率、汇率、货币供应量等金融数据。

            * 国家外汇管理局 (State Administration of Foreign Exchange, SAFE) (http://www.safe.gov.cn/): 国际收支、外汇储备、外债等外汇相关数据。

            * 中国政府网 (http://www.gov.cn/): 国务院发布的各项政策文件、政府工作报告、发展规划。

            * 各部委官方网站 (例如：国家发展和改革委员会 (NDRC): https://www.ndrc.gov.cn/, 财政部: http://www.mof.gov.cn/, 商务部: http://www.mofcom.gov.cn/, 工业和信息化部 (MIIT): https://www.miit.gov.cn/): 提供其主管领域的详细政策文件、规划和相关统计数据。

        * **国际宏观经济与金融数据（如无中国免费资源时）**:

            * 国际货币基金组织 (International Monetary Fund, IMF) (https://www.imf.org/en/Data): 提供全球及各成员国的宏观经济数据和预测。

            * 世界银行 (World Bank) (https://data.worldbank.org/): 丰富的全球发展指标数据库。

            * 经济合作与发展组织 (Organisation for Economic Co-operation and Development, OECD) (https://data.oecd.org/): 提供OECD成员国及部分非成员国的宏观经济、社会、环境等多元数据。

            * 美联储 (Federal Reserve System) (https://www.federalreserve.gov/): 获取美国货币政策、联邦基金利率、资产负债表等核心数据。

        * **“人工智能+”政策评估相关数据（中国免费优先）**:

            * 行业协会和智库报告 (例如：中国人工智能产业发展联盟 (AIIA)、中国信通院): 发布人工智能相关的白皮书、发展报告和指数。

            * 斯坦福大学AI Index Report (https://aiindex.stanford.edu/): 全球人工智能发展的重要参考，提供投资、研究、人才等数据。

            * 特定领域数据: 根据“人工智能+”的具体应用领域，查找相关行业的主管部门或行业协会的数据和报告。

            * 学术论文和研究 (例如：中国知网 (CNKI): https://www.cnki.net/, Google Scholar: https://scholar.google.com/): 用于查找关于政策评估的学术研究和方法论。

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
    "queryType": "宏观/策略分析",
    "strategySummary": "采用“官方宏观数据 -> 政策解读与传导机制 -> 行业应用与效果评估 -> 国际影响与风险预警”的多层次查询策略。首先获取最权威的宏观经济指标和政策原文，再通过专业分析和学术研究深入理解政策传导路径和实际效果，并考虑国际宏观环境影响。",
    "primarySources": [
      "国家统计局 (data.stats.gov.cn)",
      "中国人民银行 (pbc.gov.cn)",
      "国家外汇管理局 (safe.gov.cn)",
      "中国政府网 (gov.cn)",
      "工业和信息化部 (miit.gov.cn)",
      "国家发展和改革委员会 (ndrc.gov.cn)",
      "国际货币基金组织 (IMF) (imf.org)",
      "世界银行 (World Bank) (worldbank.org)",
      "美联储 (Federal Reserve System) (federalreserve.gov)",
      "中国人工智能产业发展联盟 (AIIA)",
      "中国信通院",
      "斯坦福大学AI Index Report"
    ]
  },
  "querySet": [
    {
      "id": 1,
      "objective": "获取中国宏观经济核心指标（GDP, CPI, 利率, 汇率）的官方数据及最新政策报告",
      "query": "中国宏观经济数据 OR 中国经济指标 (GDP OR CPI OR 利率 OR 汇率) site:data.stats.gov.cn OR site:pbc.gov.cn OR site:safe.gov.cn OR site:gov.cn filetype:pdf",
      "explanation": "直接从国家统计局、央行、外管局和中国政府网获取最权威的宏观经济数据和政策原文，确保数据的原始性和准确性。"
    },
    {
      "id": 2,
      "objective": "评估国家级“人工智能+”政策（2023-2025）的实施效果、影响及相关产业数据",
      "query": "人工智能+ OR AI+ 政策评估 (2023 OR 2024 OR 2025) (效果 OR 影响 OR 产业数据) site:miit.gov.cn OR site:ndrc.gov.cn OR site:aiia.org.cn OR site:caict.ac.cn filetype:pdf",
      "explanation": "聚焦工信部、发改委、中国人工智能产业发展联盟和中国信通院等机构，获取人工智能相关政策的实施报告、评估文件及产业数据，分析政策传导路径和实际效果。"
    },
    {
      "id": 3,
      "objective": "查找关于中国宏观经济政策（如降准、财政政策）对出口、CPI等具体指标传导路径的深度分析",
      "query": "中国宏观政策 (降准 OR 财政政策) (出口 OR CPI) 传导路径 OR 影响分析 filetype:pdf (中金公司 OR 中信证券 OR 学术论文)",
      "explanation": "检索券商研报和学术论文，深入理解特定宏观政策（如降准）如何影响经济中的具体变量（如出口和CPI），构建政策联动分析模型。"
    },
    {
      "id": 4,
      "objective": "评估美联储利率变动对中国及全球资本流动、汇率和经济增长的潜在影响",
      "query": "美联储利率 OR Fed rate (中国 OR 全球) (资本流动 OR 汇率 OR 经济增长) site:federalreserve.gov OR site:imf.org OR site:worldbank.org OR site:oecd.org filetype:pdf",
      "explanation": "结合美联储、IMF、世界银行和OECD的数据和报告，模拟全球宏观变量（如美联储利率）对中国乃至全球经济的传导效应，支持全球视野的模拟建模。"
    },
    {
      "id": 5,
      "objective": "识别中国宏观经济中潜在的“灰犀牛”事件风险，并寻找相关的预警指标或分析",
      "query": "中国宏观经济 灰犀牛 (风险预警 OR 潜在风险 OR 指标设计) filetype:pdf (金融风险 OR 债务风险 OR 房地产风险)",
      "explanation": "搜索关于中国宏观经济潜在重大风险事件（“灰犀牛”）的分析报告，识别关键风险指标和预警机制，增强风险预判能力。"
    }
  ]
}
```

**# 开始执行 (Begin Execution)**
请根据以上所有要求，为以下输入生成一个完整的JSON格式的搜索指令集：

"""


def search_strategy_macro(
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
    user_content = f"{search_strategy_macro_user_prompt}\n" + search_query
    outline = chat_no_tool(
        user_content=user_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(extract_json_array(outline))
