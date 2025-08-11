import hashlib
import diskcache as dc
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.async_chat import async_chat_no_tool
# 不需要json格式

# 初始化缓存，最大10GB
_cache = dc.Cache('caches/summary_cache', size_limit=10 * 1024 * 1024 * 1024)  # 10GB

# 提示词：用于生成完整内容的整体描述
PROMPT_FULL_CONTENT_DESCRIPTION = """
你是一名专业的文本分析师，擅长对完整内容进行高度凝练和信息丰富的整体描述。

你的任务：
1. 仔细阅读并理解**完整内容**，把握其主题、结构和关键信息。
2. 生成一个高度凝练、信息丰富且能捕获其本质的**“描述性摘要”**。
    
这个“描述性摘要”的目标是：
* **解释该分块的性质或类型**（例如：这是一个表格、一个定义、一个论证段落、一个步骤说明等）。
* **说明该分块的主要作用或目的**（例如：它用于展示数据、它定义了一个概念、它论证了一个观点、它提供了一系列操作步骤等）。
* **指出该分块的主要结构或包含的关键元素**（例如：表格的列名、定义的术语、步骤的概括等）。
* **阐明该分块所包含的关键信息类型或主题**，以及它在**完整的上下文内容**中的**角色和意义**。
要求：
* 只输出整体描述，不要包含任何前缀、后缀或格式化内容。

输出开头格式：

当前内容的描述性摘要如下：

---
**完整内容：**
{content}
当前内容的描述性摘要如下：

"""

# 提示词：用于根据上下文和分块生成描述性摘要
PROMPT_GEN_SUMMARY = """
你是一名专业的文本分析师，擅长在深入理解文档整体语境的基础上，对局部内容进行精准的元信息描述。

你的核心任务是：
1.  首先，仔细阅读并充分理解所提供的**完整的上下文内容**。这段文本代表了当前分块所处的整体语境和“大图景”。
2.  然后，针对给定的**需要描述的当前分块**，生成一个高度凝练、信息丰富且能捕获其本质的**“描述性摘要”**。

这个“描述性摘要”的目标是：
* **解释该分块的性质或类型**（例如：这是一个表格、一个定义、一个论证段落、一个步骤说明等）。
* **说明该分块的主要作用或目的**（例如：它用于展示数据、它定义了一个概念、它论证了一个观点、它提供了一系列操作步骤等）。
* **指出该分块的主要结构或包含的关键元素**（例如：表格的列名、定义的术语、步骤的概括等）。
* **阐明该分块所包含的关键信息类型或主题**，以及它在**完整的上下文内容**中的**角色和意义**。

请直接输出你生成的“描述性摘要”文本，不要包含任何额外的前缀、后缀、格式化文本或原始输入内容。

---

### **示例：**

**示例一：**

**完整的上下文内容：**
本文档详细介绍了公司的年度销售业绩。第一部分概述了总收入，第二部分将深入分析不同产品线的销售表现，包括各产品在不同区域的贡献。下面是一个展示各产品区域销售额的关键表格。最后部分将讨论市场趋势和未来预测。

**需要描述的当前分块：**
| 产品线 | 北美销售额 (百万美元) | 欧洲销售额 (百万美元) | 亚洲销售额 (百万美元) |
|---|---|---|---|
| 智能手机 | 120 | 80 | 150 |
| 笔记本电脑 | 90 | 60 | 110 |
| 平板电脑 | 50 | 30 | 70 |

**期望的输出：**
这是一个年度销售业绩分析报告中的表格，详细列出了智能手机、笔记本电脑和平板电脑这三条产品线在北美、欧洲和亚洲三大区域的具体销售额（单位为百万美元），用于量化展示各产品线在不同市场的表现。

---

**示例二：**

**完整的上下文内容：**
人工智能（AI）正在迅速发展，并在许多领域带来了革命性的变化。它涉及到多个核心概念和技术分支。理解这些基本概念是理解AI应用的关键。除了深度学习，强化学习也日益受到关注，它通过试错和奖励机制来训练智能体。

**需要描述的当前分块：**
深度学习是人工智能领域的一个主要分支，它通过模拟人脑神经网络来处理数据，并在图像识别、自然语言处理等任务中取得了突破。

**期望的输出：**
此分块提供了关于“深度学习”的明确定义，阐述了其作为人工智能主要分支的地位，指明了其核心原理（模拟人脑神经网络），并列举了它在图像识别和自然语言处理等领域的关键应用。

---

**示例三：**

**完整的上下文内容：**
以下是针对新入职员工的远程办公设置指南。指南从设备要求、网络连接、安全协议到日常沟通工具进行了详细说明。第一步是确保你拥有所有必要的硬件。第二步是安装所有必要的软件，包括通讯工具和项目管理软件。

**需要描述的当前分块：**
你需要一台性能良好的笔记本电脑（建议配置i5处理器或更高，8GB内存），一个高清网络摄像头和一套带麦克风的耳机。请确保你的网络连接稳定且速度不低于50Mbps。

**期望的输出：**
该分块是新员工远程办公设置指南的第一步，具体说明了所需的硬件设备（如笔记本电脑、摄像头、耳机）以及对网络连接稳定性和速度的具体要求。

---

输出开头格式：

当前内容的描述性摘要如下：

**请开始处理以下文本：**

**完整的上下文内容：**
{context}
**需要描述的当前分块：**
{block}

当前内容的描述性摘要如下：

"""

# 提示词：用于根据描述性摘要列表生成数据资产能力汇总描述
PROMPT_GEN_DATA_ASSET_SUMMARY = """
你是一名高级数据分析师和知识整合专家。你已经获得了一系列文本块的“描述性摘要”，这些摘要详细说明了每个独立文本块的性质、类型、目的、关键结构和所包含的信息。

你的核心任务是：
基于这些分块的“描述性摘要”集合，生成一份**高层次的、综合性的“数据能力描述”**。这份描述应该回答以下核心问题：

1.  **我们收集了哪些类型的数据？** （概括所有描述性摘要所指向的数据种类和内容范畴。）
2.  **这些数据整体上能进行哪些任务或分析？** （从这些数据中可以提取哪些高价值的信息，或支持哪些业务功能/决策。）
3.  **这些数据整体上能帮助我们做什么？** （阐明这些数据集合的最终用途或价值。）

请确保你的输出是：
* **全面性：** 涵盖所有描述性摘要所反映的数据类型和潜在用途。
* **高层次性：** 避免重复单个摘要的细节，而是进行概括和归类，展现数据集的整体图景。
* **实用性：** 清晰指出这些聚合数据能够支持哪些实际任务、分析或决策。
* **严格约束：** 只能依据提供的“描述性摘要”内容进行汇总描述，不得虚构、推断或编造任何未在摘要中明确出现的信息，禁止扩展或假设额外内容。
* **直接且简洁：** 直接输出汇总描述，不要包含任何额外的提示语、前缀或格式。

---

**以下是所有文本块的“描述性摘要”列表：**
{summaries_list_str}

---

**示例：**

**以下是所有文本块的“描述性摘要”列表：**
* 这是一个年度销售业绩分析报告中的表格，详细列出了智能手机、笔记本电脑和平板电脑这三条产品线在北美、欧洲和亚洲三大区域的具体销售额（单位为百万美元），用于量化展示各产品线在不同市场的表现。
* 此分块提供了关于“深度学习”的明确定义，阐述了其作为人工智能主要分支的地位，指明了其核心原理（模拟人脑神经网络），并列举了它在图像识别和自然语言处理等领域的关键应用。
* 该分块是新员工远程办公设置指南的第一步，具体说明了所需的硬件设备（如笔记本电脑、摄像头、耳机）以及对网络连接稳定性和速度的具体要求。
* 这个分块描述了公司新推出的AI驱动型客户服务机器人CUSTO-AI的技术架构，包括其模块化设计、自然语言处理核心和与现有CRM系统的集成方式。
* 此分块包含了一系列法律文件中关于数据隐私条款的修改建议，详细列举了 GDPR 和 CCPA 合规性要求，并提出了具体的措辞调整。

**期望的输出：**


当前内容的描述性摘要如下：
目前已经获取的数据，主要包括：**详细的财务与销售业绩数据**（按产品线和区域划分的销售额）、**前沿技术概念的定义与应用**（如人工智能深度学习）、**操作性强的内部指南**（如员工远程办公设置要求）、**具体的技术系统架构描述**（如AI客户服务机器人），以及**关键的法律合规性文档**（如数据隐私条款修订建议）。这些数据集合能够用于**全面分析和评估公司运营的各个方面**，包括：**量化业务绩效、理解并应用新兴技术、指导标准化内部流程、优化和部署技术系统，以及确保法律和行业标准的合规性**。

---

**请开始处理以下文本：**

**以下是所有文本块的“描述性摘要”列表：**
{summaries_list_str}

当前内容的描述性摘要如下：
"""


def _generate_cache_key(content: str, model: str, function_name: str) -> str:
    """生成缓存键，基于内容、模型和函数名的哈希"""
    key_data = f"{function_name}:{model}:{content}"
    return hashlib.md5(key_data.encode('utf-8')).hexdigest()


def generate_full_content_description(
    content: str,
    api_key: str,
    base_url: str,
    model: str
) -> str:
    """
    根据完整内容，生成该内容的整体描述。
    参数必须显式传递，不再依赖全局变量。
    带缓存功能，避免重复调用API。
    """
    # 生成缓存键
    cache_key = _generate_cache_key(content, model, "full_content_description")
    
    # 尝试从缓存获取结果
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # 缓存未命中，调用API
    prompt = PROMPT_FULL_CONTENT_DESCRIPTION.format(content=content)
    try:
        result = chat_no_tool(
            user_content=prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        result = result.strip()
        
        # 将结果存入缓存
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        error_msg = f"调用 OpenAI API 时发生错误: {e}"
        # 不缓存错误结果
        return error_msg


def generate_block_summary(
    context: str,
    block: str,
    api_key: str,
    base_url: str,
    model: str
) -> str:
    """
    根据给定的上下文和需要描述的分块，生成一个描述性摘要。
    参数必须显式传递，不再依赖全局变量。
    带缓存功能，避免重复调用API。
    """
    # 生成缓存键，包含上下文和分块内容
    content_for_cache = f"context:{context}|block:{block}"
    cache_key = _generate_cache_key(content_for_cache, model, "block_summary")
    
    # 尝试从缓存获取结果
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # 缓存未命中，调用API
    prompt = PROMPT_GEN_SUMMARY.format(context=context, block=block)
    try:
        summary = chat_no_tool(
            user_content=prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        summary = summary.strip()
        
        # 将结果存入缓存
        _cache.set(cache_key, summary)
        return summary
    except Exception as e:
        error_msg = f"调用 OpenAI API 时发生错误: {e}"
        # 不缓存错误结果
        return error_msg


def generate_data_asset_summary(
    descriptive_summaries: list[str],
    api_key: str,
    base_url: str,
    model: str
) -> str:
    """
    根据给定的描述性摘要列表，生成一份高层次的数据资产能力汇总描述。
    参数必须显式传递，不再依赖全局变量。
    带缓存功能，避免重复调用API。
    """
    # 生成缓存键，基于摘要列表的内容
    summaries_content = "|".join(sorted(descriptive_summaries))  # 排序确保一致性
    cache_key = _generate_cache_key(summaries_content, model, "data_asset_summary")
    
    # 尝试从缓存获取结果
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # 缓存未命中，调用API
    summaries_list_str = "\n".join([f"* {s}" for s in descriptive_summaries])
    prompt_template = PROMPT_GEN_DATA_ASSET_SUMMARY.format(summaries_list_str=summaries_list_str)

    try:
        des = chat_no_tool(
            user_content=prompt_template,
            api_key=api_key,
            base_url=base_url,
            model=model,
        )
        des = des.strip()
        
        # 将结果存入缓存
        _cache.set(cache_key, des)
        return des
    except Exception as e:
        error_msg = f"调用 OpenAI API 时发生错误: {e}"
        # 不缓存错误结果
        return error_msg


# 异步版本的摘要生成函数
async def async_generate_full_content_description(
    content: str,
    api_key: str,
    base_url: str,
    model: str
) -> str:
    """
    异步版本：根据完整内容，生成该内容的整体描述。
    参数必须显式传递，不再依赖全局变量。
    带缓存功能，避免重复调用API。
    """
    # 生成缓存键
    cache_key = _generate_cache_key(content, model, "full_content_description")
    
    # 尝试从缓存获取结果
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # 缓存未命中，调用异步API
    prompt = PROMPT_FULL_CONTENT_DESCRIPTION.format(content=content)
    try:
        result = await async_chat_no_tool(
            user_content=prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            use_cache=False,  # 我们自己管理缓存
            timeout=120  # 2分钟超时
        )
        result = result.strip()
        
        # 将结果存入缓存
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        error_msg = f"调用异步 API 时发生错误: {e}"
        # 不缓存错误结果
        return error_msg


async def async_generate_block_summary(
    context: str,
    block: str,
    api_key: str,
    base_url: str,
    model: str
) -> str:
    """
    异步版本：根据给定的上下文和需要描述的分块，生成一个描述性摘要。
    参数必须显式传递，不再依赖全局变量。
    带缓存功能，避免重复调用API。
    """
    # 生成缓存键，包含上下文和分块内容
    content_for_cache = f"context:{context}|block:{block}"
    cache_key = _generate_cache_key(content_for_cache, model, "block_summary")
    
    # 尝试从缓存获取结果
    cached_result = _cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    # 缓存未命中，调用异步API
    prompt = PROMPT_GEN_SUMMARY.format(context=context, block=block)
    try:
        summary = await async_chat_no_tool(
            user_content=prompt,
            api_key=api_key,
            base_url=base_url,
            model=model,
            use_cache=False,  # 我们自己管理缓存
            timeout=120  # 2分钟超时
        )
        summary = summary.strip()
        
        # 将结果存入缓存
        _cache.set(cache_key, summary)
        return summary
    except Exception as e:
        error_msg = f"调用异步 API 时发生错误: {e}"
        # 不缓存错误结果
        return error_msg


def get_cache_stats():
    """获取缓存统计信息"""
    return {
        "cache_size": len(_cache),
        "cache_volume": _cache.volume(),
        "cache_directory": _cache.directory
    }


def clear_cache():
    """清空缓存"""
    _cache.clear()
    return "缓存已清空"


