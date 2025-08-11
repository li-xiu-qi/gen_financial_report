import json
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

generate_keywords_user_prompt = """你将会收到一个关键词生成的请求。
你按照要求以及当前query生成一个3-5个关键词的json格式的列表：
输出格式示例：
```json
[
    "关键词1",
    "关键词2",
    "关键词3"
]
```
"""


def generate_keywords(
    query,
    background: str = None,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
):
    """
    使用指定的提示词生成公司研报大纲。
    """
    background = "**需要查询资料的背景信息：**\n{request}"

    user_content = background + query if background else query
    outline = chat_no_tool(
        user_content=generate_keywords_user_prompt + user_content,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return json.loads(extract_json_array(outline))
