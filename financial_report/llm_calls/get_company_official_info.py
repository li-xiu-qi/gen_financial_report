import json
import requests
from urllib.parse import quote

from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array
from financial_report.search_tools.search_tools import load_page_with_cache
from financial_report.utils.calculate_tokens import TransformerTokenCalculator

# 增量式长期记忆总结提示词
LONG_TERM_SUMMARY_PROMPT = """
你是一位专业的金融信息Agent，请将以下多轮对话内容进行增量式总结，提炼出对公司权威信息源识别最有价值的知识点、决策依据和已知结论。只需输出简明扼要的总结，不要解释和重复原文。
请严格按照如下格式输出，并用```json```包裹：
```json
{
  "summary": "..."
}
```
对话内容：
{dialogue}
输出格式：
总结：...
"""

def summarize_long_term_memory(dialogue_list, model, api_key, base_url, max_tokens=4096):
    dialogue_text = "\n".join(dialogue_list)
    prompt = LONG_TERM_SUMMARY_PROMPT.format(dialogue=dialogue_text)
    result = chat_no_tool(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        base_url=base_url,
        user_content=prompt,
        system_content="你是一个专业的内容总结助手，只需输出总结。",
        temperature=0.2,
        max_tokens=max_tokens,
    )
    # 统一用extract_json_array提取
    json_text = extract_json_array(result, mode='auto')
    try:
        summary_info = json.loads(json_text) if json_text else {"summary": result.strip()}
    except Exception:
        summary_info = {"summary": result.strip()}
    return summary_info.get("summary", result.strip())

# 构建混合记忆机制

def build_messages(system_content, user_prompt, long_term_memory, short_term_memory, max_total_tokens=128*1024 * 0.7, token_model_name="deepseek-ai/DeepSeek-V3-0324", max_short_term_rounds=10):
    """
    构建混合记忆机制，短期记忆优先保留最近10轮，如token超限则按token限制截断。
    """
    token_calculator = TransformerTokenCalculator(model_name=token_model_name)
    short_msgs = []
    token_count = token_calculator.count_tokens(system_content) + token_calculator.count_tokens(user_prompt)
    # 先保留最近10轮
    short_term_selected = short_term_memory[-max_short_term_rounds:] if len(short_term_memory) > max_short_term_rounds else short_term_memory[:]
    # 再按token限制从后往前截断
    for msg in reversed(short_term_selected):
        msg_tokens = token_calculator.count_tokens(msg['content'])
        if token_count + msg_tokens > max_total_tokens:
            break
        short_msgs.insert(0, msg)
        token_count += msg_tokens
    # 长期记忆直接拼到system_content
    system_content_full = system_content + "\n长期记忆：" + "\n".join([m['content'] for m in long_term_memory])
    messages = [{"role": "system", "content": system_content_full}] + short_msgs + [{"role": "user", "content": user_prompt}]
    return messages

def get_company_official_info(name: str, search_api_url: str, api_key: str = None, base_url: str = None, model: str = None, max_tokens: int = 1024, temperature: float = 0.3, context_history: list = None) -> dict:
    """
    Agent式：通过提示词让大模型动态识别公司官网和权威信息源，并判断官网可访问性。
    若官网不可访问或内容异常，则自动调用搜索引擎（bing接口）重新查找并验证。
    支持传入上下文历史，实在找不到官网则放弃，选其他权威网站。
    输出结构化字典，包含 continue/stop 键。
    """
    # 构建上下文历史
    context_str = "\n".join(context_history) if context_history else ""
    system_content = (
        "你是一位顶级金融信息检索Agent，专注于为目标公司收集权威信息源，包括官网、交易所、国家统计局等。"
        "你的输出必须严格为JSON格式，包含公司名、官网、权威信息源列表。权威信息源需根据公司类型和分析需求动态选择。"
        "背景信息,我们需要撰写一个公司研报，需要进行一个数据源判断，其中的公司研报要求如下：公司/个股研报应能够自动抽取三大会计报表与股权结构，输出主营业务、核心竞争力与行业地位；"
        "支持财务比率计算与行业对比分析（如ROE分解、毛利率、现金流匹配度），结合同行企业进行横向竞争分析；"
        "构建估值与预测模型，模拟关键变量变化对财务结果的影响（如原材料成本、汇率变动）；"
        "结合公开数据与管理层信息，评估公司治理结构与发展战略，提出投资建议与风险提醒。"
        f"\n历史上下文：{context_str}"
    )
    user_prompt = f"""
请为公司“{name}”自动识别并收集权威信息源，包括但不限于：
- 官方网站（官网）（包括目标公司及其主要竞争对手的官网）
- 证券交易所官网（如港交所、上交所、深交所）
- 国家统计局
- 行业权威网站（如同花顺、东方财富、巨潮资讯、巨潮资讯网、财新网、上海/深圳/香港交易所、债券信息网、中国证监会等）
- 其他有助于公司基本面、财务、估值、风险分析的数据源

优先选择免费公开的信息源。以下是常见权威网站及其含义：
- .gov.cn：政府官方网站，权威性最高
- .org：非营利组织网站，部分行业协会或标准机构
- .edu：教育科研机构网站
- cninfo.com.cn：巨潮资讯网，上市公司公告与财报披露
- hkexnews.hk：香港交易所披露易，港股公告与财报
- stats.gov.cn：国家统计局，宏观经济与行业统计数据
- eastmoney.com：东方财富网，财经资讯与数据
- 10jqka.com.cn：同花顺财经，财经数据与资讯
- sse.com.cn：上海证券交易所官网
- szse.cn：深圳证券交易所官网
- hkex.com.hk：香港交易所官网
- cnstock.com：中国证券网，权威财经新闻
- caixin.com：财新网，深度财经报道
- chinabond.com.cn：中国债券信息网，债券市场权威数据
- csrc.gov.cn：中国证监会，监管政策与公告
避免使用需要付费或注册的商业数据库。

输出格式要求：
请严格按照如下格式输出，并用```json```包裹：
```json
{{
  "name": "公司名",
  "website": "官网URL",
  "competitor_websites": [
    {{"name": "竞争对手名称", "url": "..."}},
    ...
  ],
  "authority_sites": [
    {{"name": "权威网站名称", "url": "..."}},
    ...
  ]
}}
```
禁止输出任何解释或注释。
    """
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_prompt}
    ]
    result_str = chat_no_tool(
        model=model,
        messages=messages,
        api_key=api_key,
        base_url=base_url,
        user_content=user_prompt,
        system_content=system_content,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    # 使用extract_json_array提取json内容
    json_text = extract_json_array(result_str, mode='auto')
    try:
        info = json.loads(json_text) if json_text else {"name": name, "website": "", "authority_sites": []}
    except Exception:
        info = {"name": name, "website": "", "authority_sites": []}
    # 判断官网和所有权威网站可访问性
    def is_valid_official_site(url, name):
        try:
            res = load_page_with_cache(url, cache_prefix="official", search_api_url=search_api_url)
            md_content = res.get("md", "") if res else ""
            # 只取前3K字进行判别
            md_content_short = md_content[:3000]
            if md_content_short:
                judge_prompt = (
                    f"你是一位专业的金融信息判别Agent，下面是某个网页的部分内容（仅前3000字），请判断其是否为公司“{name}”的官方网站或权威信息源页面的主要内容。"
                    "只需回答true或false：\n"
                    f"{md_content_short}"
                )
                judge_result = chat_no_tool(
                    model=model,
                    messages=[{"role": "user", "content": judge_prompt}],
                    api_key=api_key,
                    base_url=base_url,
                    user_content=judge_prompt,
                    system_content="你是一个专业的内容判别助手，只需输出true或false。",
                    temperature=0.0,
                    max_tokens=10,
                )
                if "true" in judge_result.lower():
                    return True
        except Exception as e:
            print(f"官网/权威网站访问失败: {e}")
        return False

    # 验证官网
    website = info.get("website", "")
    status = "failed"
    if website and is_valid_official_site(website, name):
        status = "ok"
        info["continue"] = True
    else:
        # 联网搜索重新查找官网（直接用bing接口获取摘要信息）
        query_enc = quote(f"{name} 官网")
        search_url = f"{search_api_url}/bing?query={query_enc}&total=8&cn=1"
        try:
            resp = requests.get(search_url)
            if resp.status_code == 200:
                search_results = resp.json()
                found = False
                for item in search_results:
                    url = item.get("url", "")
                    title = item.get("title", "")
                    # 优先判断标题或url包含“官网”
                    if "官网" in title or "官网" in url or name.lower() in url.lower():
                        if is_valid_official_site(url, name):
                            info["website"] = url
                            status = "ok"
                            found = True
                            info["continue"] = True
                            break
                if not found:
                    info["website"] = ""
                    status = "failed"
                    info["continue"] = False
        except Exception as e:
            print(f"bing接口获取官网失败: {e}")
            info["continue"] = False
    # 验证所有权威网站，优先保留免费权威网站和PDF类权威网站，过滤掉收费类如wind
    valid_authority_sites = []
    paid_domains = ["wind.com.cn", "capitaliq.com"]
    for site in info.get("authority_sites", []):
        site_name = site.get("name", "")
        site_url = site.get("url", "")
        # 过滤掉收费类权威网站
        if any(domain in site_url for domain in paid_domains):
            continue
        # 优先判断是否为PDF
        is_pdf = site_url.lower().endswith(".pdf")
        if site_url and is_valid_official_site(site_url, site_name):
            # 优先插入PDF
            if is_pdf:
                valid_authority_sites.insert(0, site)
            else:
                valid_authority_sites.append(site)
    info["authority_sites"] = valid_authority_sites
    info["status"] = status
    # 如果没有官网，建议停止
    if not info.get("website"):
        info["continue"] = False
        info["stop"] = True
    else:
        info["stop"] = False
    return info
