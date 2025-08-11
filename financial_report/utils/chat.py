import json
from urllib import response
from openai import OpenAI
from dotenv import load_dotenv
import os
from diskcache import Cache
import hashlib
from typing import List, Dict

# 加载 .env 文件中的环境变量
load_dotenv()

# 创建缓存实例
cache = Cache("./caches/chat_cache")


def generate_cache_key(
    messages: List[Dict],
    tools: list = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
) -> str:
    """生成缓存键，基于messages和其他参数

    Args:
        messages: 消息列表
        tools: 工具列表
        temperature: 温度参数
        max_tokens: 最大token数

    Returns:
        str: 缓存键的哈希值
    """
    # 序列化messages以确保一致性
    key_content = json.dumps(messages, sort_keys=True)
    # 添加其他可能影响输出的参数
    key_content += f"{str(tools)}{temperature}{max_tokens}"
    return hashlib.md5(key_content.encode()).hexdigest()




# --- 主程序 ---
def chat_with_auto_tool(
    messages: List[Dict] = None,
    user_content: str = None,
    system_content: str = "你是一个有用的人工智能助手。",
    tools: list = None,
    api_key: str = None,
    base_url: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    model: str = None,
    use_cache: bool = False,
    response_format: dict = None,
    **kwargs,
):
    """全自动处理用户对话，自动调用工具并返回最终AI回复

    Args:
        messages (List[Dict], optional): 完整的消息列表，如果提供则忽略 user_content 和 system_content
        user_content (str, optional): 用户输入内容
        system_content (str, optional): 系统提示内容
        use_cache (bool, optional): 是否启用缓存. Defaults to False.
    """
    messages = _validate_and_build_messages(messages, user_content, system_content)

    # 如果启用缓存，先尝试从缓存中获取结果
    if use_cache:
        cache_key = generate_cache_key(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return cached_response

    client = OpenAI(api_key=api_key, base_url=base_url)
    _model = model if model is not None else globals().get("model")
    # 第一步：让模型决定需要调用哪些工具
    first_response = client.chat.completions.create(
        model=_model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=temperature,
        max_tokens=max_tokens,
        response_format=response_format,
        **kwargs,
    )
    response_message = first_response.choices[0].message
    messages.append({"role": "assistant", "content": response_message.content})
    # 处理工具调用并获取最终响应
    final_response = (
        _handle_tool_calls(
            messages,
            response_message.tool_calls,
            tools,
            temperature,
            max_tokens,
            client,
            **kwargs,
        )
        if response_message.tool_calls
        else response_message.content
    )
    # 如果启用缓存，将结果存入缓存
    if use_cache:
        cache_key = generate_cache_key(
            messages=messages,  # 包含了所有工具调用的完整消息历史
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cache.set(cache_key, final_response)
    return final_response


def chat(
    messages: List[Dict] = None,
    user_content: str = None,
    system_content: str = "你是一个有用的人工智能助手。",
    api_key: str = None,
    base_url: str = None,
    tools: list = None,
    temperature: float = 0.6,
    max_tokens: int = 8192,
    model: str = None,
    response_format: dict = None,
    **kwargs,
):
    """只是简单的封装openai的chat接口，适用于不需要自动调用工具的场景，不带缓存

    Args:
        messages (List[Dict], optional): 完整的消息列表，如果提供则忽略 user_content 和 system_content
        user_content (str, optional): 用户输入内容
        system_content (str, optional): 系统提示内容
        tools (list, optional): 工具列表，默认为None
        temperature (float, optional): 温度参数，默认为0.7
        max_tokens (int, optional): 最大token数，默认为8192
        **kwargs: 其他可选参数
    """
    messages = _validate_and_build_messages(messages, user_content, system_content)
    client = OpenAI(api_key=api_key, base_url=base_url)
    # 优先使用传入的model参数，否则用全局model
    _model = model if model is not None else globals().get("model")
    response = client.chat.completions.create(
        model=_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice="auto",
        response_format=response_format,
        **kwargs,
    )
    return response


def chat_no_tool(
    model: str = None,
    messages: List[Dict] = None,
    user_content: str = None,
    system_content: str = "你是一个有用的人工智能助手。",
    api_key: str = None,
    base_url: str = None,
    tools: list = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    use_cache: bool = False,
    response_format: dict = None,
    **kwargs,
):
    """仅进行普通对话，不自动调用工具，但可传入 tools 参数（如 function schema）

    Args:
        messages (List[Dict], optional): 完整的消息列表，如果提供则忽略 user_content 和 system_content
        user_content (str, optional): 用户输入内容
        system_content (str, optional): 系统提示内容
        use_cache (bool, optional): 是否启用缓存. Defaults to False.
    """
    messages = _validate_and_build_messages(messages, user_content, system_content)
    print(f"messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
    # 如果启用缓存，先尝试从缓存中获取结果
    if use_cache:
        cache_key = generate_cache_key(
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return cached_response

    client = OpenAI(api_key=api_key, base_url=base_url)
    _model = model if model is not None else globals().get("model")
    response_format = None  # 硅基流动的response_format似乎有bug，禁用下
    response = client.chat.completions.create(
        model=_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        tools=tools,
        tool_choice="auto",
        response_format=response_format,
        **kwargs,
    )
    result = response.choices[0].message.content
    # 如果启用缓存，将结果存入缓存
    if use_cache:
        cache.set(cache_key, result)
    # 打印响应结果
    print(f"AI回复: {result}")
    return result


# --- 常量定义 ---
INVALID_PARAMS_ERROR = "必须提供 messages 或同时提供 user_content。"
DEFAULT_SYSTEM_CONTENT = "你是一个有用的人工智能助手。"


def _validate_and_build_messages(messages, user_content, system_content=DEFAULT_SYSTEM_CONTENT):
    """验证并构建消息列表

    Args:
        messages (List[Dict]): 完整的消息列表
        user_content (str): 用户输入内容
        system_content (str): 系统提示内容

    Returns:
        List[Dict]: 构建好的消息列表
    """
    if messages is None and (user_content is None ):
        raise ValueError(INVALID_PARAMS_ERROR)

    if messages is None:
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    return messages


def _handle_tool_calls(
    messages, tool_calls, model, tools, temperature, max_tokens, client, **kwargs
):
    """处理工具调用

    Args:
        messages (List[Dict]): 消息列表
        tool_calls: 工具调用列表
        tools (list): 工具列表
        temperature (float): 温度参数
        max_tokens (int): 最大token数
        client: OpenAI客户端实例
        **kwargs: 其他参数

    Returns:
        str: 处理结果
    """
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        try:
            function_args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError:
            continue
        try:
            function_response = eval(function_name)(**function_args)
        except Exception as e:
            function_response = f"错误：工具调用 '{function_name}' 失败，原因：{e}"
        print(
            f"工具id：{tool_call.id}，调用函数：{function_name}，参数：{function_args}，返回结果：{function_response}"
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": function_name,
                "content": function_response,
            }
        )

    second_response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    return second_response.choices[0].message.content

