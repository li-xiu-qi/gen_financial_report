import sys
import os
import json
from urllib.parse import quote
import requests
import concurrent.futures  # 用于并发执行



from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

# --- 核心函数 ---

def get_code_info(
    name: str, search_api_url: str, chat_model: str, api_key: str, base_url: str
):
    """
    通过搜索引擎和LLM获取单个公司的详细股票信息（包含tonghuashun_total_code）。

    :param name: 公司名称
    :param search_api_url: 搜索API的URL
    :param chat_model: 大模型名称
    :param api_key: 大模型API KEY
    :param base_url: 大模型API BASE URL
    :return: 包含公司详细信息的字典，或在失败时返回 None
    """
    print(f"\n正在为 [{name}] 获取详细股票信息...")
    # 使用更精确的搜索查询
    query = f"site:basic.10jqka.com.cn 公司资料 股票代码 \"{name}\""
    query_enc = quote(query)
    search_url = f"{search_api_url}/bing?query={query_enc}&total=5&cn=1"
    
    try:
        response = requests.get(search_url)
        response.raise_for_status() 
        results = response.json()
        
        # 筛选出最相关的同花顺链接
        thsg_results = [item for item in results if "10jqka.com.cn" in item.get("url", "")]

        if not thsg_results:
            print(f"❌ 未能为 [{name}] 找到同花顺相关链接。")
            return None

        context_text = "\n".join([f"标题: {x.get('title', '')}, 链接: {x.get('url', '')}" for x in thsg_results])
        
        # 更新后的Prompt，使用三引号字符串
        user_content = f"""请根据以下同花顺网页的标题和链接，判断'{name}'的股票信息。
请只返回一个JSON对象，包含且仅包含以下四个字段：market, company_name, company_code, tonghuashun_total_code。
要求：
1. `company_name`应为公司在交易所的官方名称（例如'商汤-W'）。
2. `tonghuashun_total_code`必须是带有交易所前缀的完整代码（例如'HK0020'或'688327'）。
3. `market`字段请统一为 'A' (A股) 或 'HK' (港股)。
上下文信息如下：
{context_text}

格式示例：
```json
{{
  "market": "HK",
  "company_name": "商汤-W",
  "company_code": "0020",
  "tonghuashun_total_code": "HK0020"
}}
```"""
        
        messages = [{"role": "user", "content": user_content}]
        code_result_str = chat_no_tool(
            model=chat_model,
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            user_content=user_content,
            system_content="你是一个精准的金融信息提取助手，严格按照用户的JSON格式要求返回数据。",
            temperature=0.0,
            max_tokens=256,
        )
        
        json_text = extract_json_array(code_result_str, mode='auto')
        if json_text:
            try:
                code_info = json.loads(json_text)
                # 校验关键字段是否存在且不为空
                if all(code_info.get(k) for k in ['market', 'company_name', 'company_code', 'tonghuashun_total_code']):
                    print(f"✅ 成功获取 [{name}] 的股票信息。")
                    return code_info
                else:
                    print(f"❌ 解析到的JSON缺少关键字段或值为空: {code_info}")
                    return None
            except json.JSONDecodeError as e:
                print(f"❌ 解析 [{name}] 的JSON失败: {e}\n原始回复: {code_result_str}")
                return None
    except requests.RequestException as e:
        print(f"❌ 为 [{name}] 进行网络请求失败: {e}")
        return None
    except Exception as e:
        print(f"❌ 处理 [{name}] 时发生未知错误: {e}")
        return None
    
    return None


def find_competitors(
    name: str,
    more_than: int = 3,
    cache_dir: str = None,
    search_api_url: str = None,
    chat_model: str = None,
    api_key: str = None,
    base_url: str = None,
    max_concurrent: int = 5  # 最大并发数
):
    """
    查询目标公司在大陆及香港交易所的同行业竞争对手信息，
    并为所有公司获取包含`tonghuashun_total_code`的详细信息。
    """
    # 1. 获取竞争对手名称列表
    # 更新后的Prompt，使用三引号字符串
    prompt = f"""请列举'{name}'在A股和港股上市的、最重要的竞争对手公司（不包括'{name}'自身）。
返回不少于{more_than}个。
请只返回一个JSON数组，每个对象仅包含一个'name'字段。
格式示例：
```json
[
  {{"name": "科大讯飞"}},
  {{"name": "海康威视"}}
]
```"""
    
    messages = [{"role": "user", "content": prompt}]
    
    result_str = chat_no_tool(
        model=chat_model,
        messages=messages,
        api_key=api_key,
        base_url=base_url,
        user_content=prompt,
        system_content="你是一个专业的行业分析师，请精准返回JSON格式的数据。",
        temperature=0.2,
        max_tokens=512,
    )
    
    competitor_names = []
    json_text = extract_json_array(result_str, mode='auto')
    if json_text:
        try:
            competitors_list = json.loads(json_text)
            competitor_names = [item['name'] for item in competitors_list if 'name' in item]
            print(f"初步找到的竞争对手: {competitor_names}")
        except Exception as e:
            print(f"❌ 解析竞争对手列表失败: {e}\n原始回复: {result_str}")
            
    # 2. 将目标公司和竞争对手合并，并去重
    all_company_names = [name] + competitor_names
    unique_company_names = list(dict.fromkeys(all_company_names))
    
    # 3. 并发获取每个公司详细信息
    final_result_list = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        # 提交所有任务
        futures = [
            executor.submit(
                get_code_info,
                company_name,
                search_api_url,
                chat_model,
                api_key,
                base_url
            )
            for company_name in unique_company_names
        ]
        # 收集结果
        for future in concurrent.futures.as_completed(futures):
            info = future.result()
            if info:
                final_result_list.append(info)
    return final_result_list
