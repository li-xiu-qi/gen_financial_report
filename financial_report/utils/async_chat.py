import json
import hashlib
import asyncio
from typing import List, Dict, Optional
import aiohttp
from dotenv import load_dotenv
import os
from diskcache import Cache

# 加载 .env 文件中的环境变量
load_dotenv()

# 创建缓存实例
cache = Cache("./caches/chat_cache")


def generate_cache_key(
    messages: List[Dict],
    tools: list = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    model: str = None,
) -> str:
    """生成缓存键，基于messages和其他参数

    Args:
        messages: 消息列表
        tools: 工具列表
        temperature: 温度参数
        max_tokens: 最大token数
        model: 模型名称

    Returns:
        str: 缓存键的哈希值
    """
    # 序列化messages以确保一致性
    key_content = json.dumps(messages, sort_keys=True)
    # 添加其他可能影响输出的参数
    key_content += f"{str(tools)}{temperature}{max_tokens}{model}"
    return hashlib.md5(key_content.encode()).hexdigest()


def _validate_and_build_messages(messages, user_content, system_content="你是一个有用的人工智能助手。"):
    """验证并构建消息列表

    Args:
        messages (List[Dict]): 完整的消息列表
        user_content (str): 用户输入内容
        system_content (str): 系统提示内容

    Returns:
        List[Dict]: 构建好的消息列表
    """
    if messages is None and (user_content is None or system_content is None):
        raise ValueError("必须提供 messages 或同时提供 user_content 和 system_content")

    if messages is None:
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    return messages


async def async_chat_no_tool(
    model: str = None,
    messages: List[Dict] = None,
    user_content: str = None,
    system_content: str = "你是一个有用的人工智能助手。",
    api_key: str = None,
    base_url: str = None,
    temperature: float = 0.7,
    max_tokens: int = 8192,
    use_cache: bool = True,
    timeout: int = 60,
    **kwargs,
) -> str:
    """异步版本的 chat_no_tool 函数，支持并发调用

    Args:
        model: 模型名称
        messages: 完整的消息列表，如果提供则忽略 user_content 和 system_content
        user_content: 用户输入内容
        system_content: 系统提示内容
        api_key: API密钥
        base_url: API基础URL
        temperature: 温度参数，默认为0.7
        max_tokens: 最大token数，默认为8192
        use_cache: 是否启用缓存，默认为True
        timeout: 请求超时时间（秒），默认为60
        **kwargs: 其他参数

    Returns:
        str: AI回复内容
    """
    messages = _validate_and_build_messages(messages, user_content, system_content)
    
    # 如果启用缓存，先尝试从缓存中获取结果
    if use_cache:
        cache_key = generate_cache_key(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            model=model,
        )
        cached_response = cache.get(cache_key)
        if cached_response is not None:
            return cached_response

    # 构建请求数据
    request_data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        **kwargs
    }

    # 构建请求头
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # 确保base_url以正确的格式结尾
    if not base_url.endswith('/'):
        base_url += '/'
    
    # 构建完整的API URL
    api_url = f"{base_url}chat/completions"

    try:
        # 创建异步HTTP会话并发送请求
        timeout_config = aiohttp.ClientTimeout(total=timeout)
        async with aiohttp.ClientSession(timeout=timeout_config) as session:
            async with session.post(
                api_url,
                json=request_data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API请求失败，状态码: {response.status}, 错误信息: {error_text}")
                
                response_data = await response.json()
                
                # 提取AI回复内容
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    result = response_data['choices'][0]['message']['content']
                else:
                    raise Exception(f"API响应格式异常: {response_data}")

                # 如果启用缓存，将结果存入缓存
                if use_cache:
                    cache.set(cache_key, result)

                return result

    except asyncio.TimeoutError:
        raise Exception(f"请求超时 ({timeout}秒)")
    except aiohttp.ClientError as e:
        raise Exception(f"网络请求错误: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"JSON解析错误: {str(e)}")
    except Exception as e:
        raise Exception(f"异步聊天请求失败: {str(e)}")


async def batch_async_chat_no_tool(
    requests: List[Dict],
    max_concurrent: int = 50,
    **common_kwargs
) -> List[str]:
    """批量异步调用 chat_no_tool，支持并发控制

    Args:
        requests: 请求列表，每个请求是一个包含参数的字典
        max_concurrent: 最大并发数，默认50
        **common_kwargs: 所有请求共用的参数

    Returns:
        List[str]: 按顺序返回的AI回复列表
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _single_request(request_params):
        async with semaphore:
            # 合并通用参数和单个请求参数
            merged_params = {**common_kwargs, **request_params}
            return await async_chat_no_tool(**merged_params)
    
    # 创建所有任务
    tasks = [_single_request(req) for req in requests]
    
    # 并发执行所有任务
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 处理异常结果
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"请求 {i} 失败: {str(result)}")
            processed_results.append(f"错误: {str(result)}")
        else:
            processed_results.append(result)
    
    return processed_results


# 为了兼容性，提供一个同步包装器
def sync_async_chat_no_tool(*args, **kwargs) -> str:
    """同步包装器，用于在同步代码中调用异步函数"""
    return asyncio.run(async_chat_no_tool(*args, **kwargs))


# 测试函数
async def test_async_chat():
    """测试异步聊天功能"""
    api_key = os.getenv("ZHIPU_API_KEY")
    base_url = os.getenv("ZHIPU_BASE_URL")
    model = os.getenv("ZHIPU_FREE_TEXT_MODEL")
    
    if not all([api_key, base_url, model]):
        print("请设置环境变量: ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_FREE_TEXT_MODEL")
        return
    
    print("测试单个异步请求...")
    result = await async_chat_no_tool(
        user_content="你好，请简单介绍一下人工智能。",
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=100
    )
    print(f"单个请求结果: {result[:100]}...")
    
    print("\n测试批量异步请求...")
    requests = [
        {"user_content": "什么是机器学习？"},
        {"user_content": "什么是深度学习？"},
        {"user_content": "什么是神经网络？"},
    ]
    
    results = await batch_async_chat_no_tool(
        requests=requests,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=100,
        max_concurrent=3
    )
    
    for i, result in enumerate(results):
        print(f"批量请求 {i+1} 结果: {result[:100]}...")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(test_async_chat())