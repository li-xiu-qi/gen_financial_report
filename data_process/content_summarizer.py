"""
内容摘要生成器
为收集的数据生成摘要，基于现有的 financial_report 工具函数实现
"""

import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from financial_report.utils.calculate_tokens import OpenAITokenCalculator
from financial_report.utils.fast_token_splitter import FastTokenSplitter
from financial_report.llm_calls.info_description import (
    async_generate_full_content_description,
)


def _get_content_hash(content: str) -> str:
    """安全地生成内容的哈希值"""
    return hashlib.md5(content.encode("utf-8")).hexdigest()


async def _generate_summary_async(
    content: str,
    api_key: str,
    base_url: str,
    model: str,
    semaphore: asyncio.Semaphore,
    progress_counter: dict = None,
    task_id: str = "",
) -> str:
    """异步生成摘要，带并发控制和进度显示"""
    async with semaphore:
        if progress_counter:
            print(
                f"   🔄 [{progress_counter['current']}/{progress_counter['total']}] 正在生成摘要: {task_id[:50]}..."
            )

        try:
            result = await async_generate_full_content_description(
                content=content, api_key=api_key, base_url=base_url, model=model
            )

            if progress_counter:
                progress_counter["current"] += 1
                progress_counter["completed"] += 1
                print(
                    f"   ✅ [{progress_counter['current']}/{progress_counter['total']}] 摘要生成完成: {task_id[:50]}..."
                )

            return result
        except Exception as e:
            if progress_counter:
                progress_counter["current"] += 1
                progress_counter["failed"] += 1
                print(
                    f"   ❌ [{progress_counter['current']}/{progress_counter['total']}] 摘要生成失败: {task_id[:50]}... (错误: {str(e)[:100]})"
                )
            raise e


def generate_summaries_for_collected_data(
    data_items: List[Dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    chat_max_token_length: int = 8192,
    max_summary_length: int = 500,
    max_concurrent: int = 10,
) -> List[Dict[str, Any]]:
    """
    为收集的数据字典列表生成摘要，基于 md 内容字段

    Args:
        data_items: 数据字典列表，每个字典应包含 'content' 或 'md' 字段
        api_key: API密钥
        base_url: API基础URL
        model: 使用的模型名称
        chat_max_token_length: Chat模型的最大token长度，用于分块
        max_summary_length: 摘要的最大长度
        max_concurrent: 最大并发数

    Returns:
        添加了 'summary' 字段的数据字典列表
    """
    print(f"\n📝 开始为 {len(data_items)} 个数据项生成摘要...")
    print(f"🔧 配置: 最大并发={max_concurrent}, 模型={model}")

    # 初始化token计算器
    token_calculator = OpenAITokenCalculator()
    max_token_per_block = int(chat_max_token_length * 0.6)  # 使用60%作为分块大小

    print(f"🔧 分块配置:")
    print(f"   - Chat模型最大token: {chat_max_token_length}")
    print(f"   - 每块最大token: {max_token_per_block}")
    print(f"   - 摘要截断长度: {max_summary_length}")

    # 运行异步处理
    return asyncio.run(
        _process_summaries_async(
            data_items=data_items,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_summary_length=max_summary_length,
            max_token_per_block=max_token_per_block,
            token_calculator=token_calculator,
            max_concurrent=max_concurrent,
        )
    )


async def _process_summaries_async(
    data_items: List[Dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    max_summary_length: int,
    max_token_per_block: int,
    token_calculator,
    max_concurrent: int = 10,
) -> List[Dict[str, Any]]:
    """异步处理所有数据项的摘要生成，带并发控制和内容去重"""

    semaphore = asyncio.Semaphore(max_concurrent)

    # 第一步：收集所有需要生成摘要的内容，并进行去重
    print("🔍 第一步: 分析数据内容并进行去重...")

    content_to_items = {}  # content_hash -> list of items
    content_to_blocks = (
        {}
    )  # content_hash -> list of (item_index, block_index, block_content)

    # 统计变量
    items_need_summary = []
    items_already_have_summary = 0
    
    for i, item in enumerate(data_items):
        if not item.get("summary"):
            items_need_summary.append((i, item))
        else:
            items_already_have_summary += 1

    total_items_to_analyze = len(items_need_summary)
    
    if items_already_have_summary > 0:
        print(f"📋 跳过已有摘要的数据项: {items_already_have_summary} 个")
    
    if total_items_to_analyze == 0:
        print("✅ 所有数据项都已有摘要，无需生成")
        return data_items
    analyzed_count = 0
    long_items_count = 0
    total_blocks_created = 0

    for item_index, item in items_need_summary:
        analyzed_count += 1

        # 获取内容，优先使用 'content' 字段，其次是 'md' 字段
        content = item.get("content") or item.get("md", "")
        if not content:
            print(f"   ⚠️  跳过空内容项: {item.get('title', 'unknown')}")
            continue

        # 显示token计算进度
        if analyzed_count % 10 == 0 or analyzed_count == total_items_to_analyze:
            print(
                f"   🔢 [{analyzed_count}/{total_items_to_analyze}] Token计算进度: {(analyzed_count/total_items_to_analyze*100):.1f}%"
            )

        token_count = token_calculator.count_tokens(content)

        if token_count <= max_token_per_block:
            # 内容不超限，直接生成摘要
            content_hash = _get_content_hash(content)
            if content_hash not in content_to_items:
                content_to_items[content_hash] = []
            content_to_items[content_hash].append((item_index, item))
        else:
            # 内容超限，分块处理
            long_items_count += 1
            item_title = item.get("title", item.get("url", "unknown"))
            print(f"   📄 内容过长需分块: {item_title[:50]}... (tokens: {token_count})")

            # 如果token超过25万就丢弃
            if token_count > 250000:
                print(
                    f"   ⚠️  内容过长，跳过: {item_title[:50]}... (tokens: {token_count})"
                )
                continue

            # 使用高性能分块器
            splitter = FastTokenSplitter(
                token_calculator=token_calculator,
                chunk_size=max_token_per_block,
                chunk_overlap=50,  # 小的重叠以保持上下文
            )
            blocks = splitter.split_text(content)

            total_blocks_created += len(blocks)
            print(f"   ✂️  分块完成: 创建了 {len(blocks)} 个块")

            # 对每个块进行去重
            for block_index, block in enumerate(blocks):
                block_hash = _get_content_hash(block)
                if block_hash not in content_to_blocks:
                    content_to_blocks[block_hash] = []
                content_to_blocks[block_hash].append((item_index, block_index, block))

    print(f"   📈 Token分析完成统计:")
    print(f"      - 分析数据项总数: {total_items_to_analyze}")
    print(f"      - 需要分块的长内容: {long_items_count}")
    print(f"      - 创建的总块数: {total_blocks_created}")
    if long_items_count > 0:
        print(
            f"      - 平均每个长内容分块: {(total_blocks_created/long_items_count):.1f}"
        )

    # 统计去重效果
    total_items = len(items_need_summary)
    unique_contents = len(content_to_items)
    unique_blocks = len(content_to_blocks)
    total_unique_tasks = unique_contents + unique_blocks

    print(f"📊 去重统计:")
    print(f"   - 需要处理的数据项: {total_items}")
    print(f"   - 去重后的完整内容: {unique_contents}")
    print(f"   - 去重后的分块内容: {unique_blocks}")
    print(f"   - 总计需要生成摘要: {total_unique_tasks}")
    if total_items > 0:
        print(
            f"   - 去重效率: {((total_items - total_unique_tasks) / total_items * 100):.1f}%"
        )

    # 第二步：为去重后的内容创建异步任务
    print("🚀 第二步: 创建异步任务...")

    # 初始化进度计数器
    progress_counter = {
        "current": 0,
        "total": total_unique_tasks,
        "completed": 0,
        "failed": 0,
    }

    unique_content_tasks = {}  # content_hash -> task
    unique_block_tasks = {}  # block_hash -> task

    # 处理完整内容
    for content_hash, item_list in content_to_items.items():
        _, first_item = item_list[0]  # 所有item的content都相同，取第一个
        content = first_item.get("content") or first_item.get("md", "")
        # 生成任务ID用于进度显示
        task_id = (
            f"完整内容-{first_item.get('title', first_item.get('url', 'unknown'))}"
        )
        task = _generate_summary_async(
            content, api_key, base_url, model, semaphore, progress_counter, task_id
        )
        unique_content_tasks[content_hash] = task

    # 处理分块内容
    for block_hash, block_infos in content_to_blocks.items():
        item_index, block_index, block_content = block_infos[
            0
        ]  # 所有block内容都相同，取第一个
        item = data_items[item_index]
        # 生成任务ID用于进度显示
        task_id = f"分块{block_index}-{item.get('title', item.get('url', 'unknown'))}"
        task = _generate_summary_async(
            block_content,
            api_key,
            base_url,
            model,
            semaphore,
            progress_counter,
            task_id,
        )
        unique_block_tasks[block_hash] = task

    # 第三步：执行所有去重后的任务
    print(f"⚡ 第三步: 并发执行 {total_unique_tasks} 个摘要生成任务...")
    print(f"   📊 实时进度显示:")

    try:
        # 合并所有任务到一个列表中，以便统一处理进度
        all_tasks = []
        task_to_hash = {}

        # 添加完整内容任务
        for content_hash, task in unique_content_tasks.items():
            all_tasks.append(task)
            task_to_hash[task] = ("content", content_hash)

        # 添加分块任务
        for block_hash, task in unique_block_tasks.items():
            all_tasks.append(task)
            task_to_hash[task] = ("block", block_hash)

        # 并发执行所有任务
        if all_tasks:
            all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

            # 将结果分配回对应的字典
            content_hash_to_result = {}
            block_hash_to_result = {}

            for task, result in zip(all_tasks, all_results):
                task_type, task_hash = task_to_hash[task]
                if task_type == "content":
                    content_hash_to_result[task_hash] = result
                else:  # block
                    block_hash_to_result[task_hash] = result
        else:
            content_hash_to_result = {}
            block_hash_to_result = {}

        # 打印最终进度统计
        print(f"   📈 任务执行完成:")
        print(f"      - 已完成: {progress_counter['completed']}")
        print(f"      - 已失败: {progress_counter['failed']}")
        print(f"      - 总计: {progress_counter['total']}")

        # 第四步：将结果分配给相应的数据项
        print("📋 第四步: 分配摘要结果到数据项...")

        # 统计成功和失败的任务
        success_count = 0
        error_count = 0

        # 处理完整内容
        for content_hash, item_list in content_to_items.items():
            result = content_hash_to_result.get(content_hash)
            if isinstance(result, Exception):
                _, first_item = item_list[0]
                content = first_item.get("content") or first_item.get("md", "")
                summary = content[:max_summary_length]
                error_count += 1
            else:
                summary = result[:max_summary_length] if result else ""
                success_count += 1

            # 将相同内容的摘要分配给所有相关数据项
            for item_index, item in item_list:
                data_items[item_index]["summary"] = summary

        # 处理分块内容
        item_block_summaries = {}  # item_index -> {block_index: summary}
        for block_hash, block_infos in content_to_blocks.items():
            result = block_hash_to_result.get(block_hash)
            if isinstance(result, Exception):
                summary = block_infos[0][2][:max_summary_length]  # 使用原始块内容
                error_count += 1
            else:
                summary = result if result else block_infos[0][2][:max_summary_length]
                success_count += 1

            # 将相同块内容的摘要分配给所有相关数据项的对应块
            for item_index, block_index, block_content in block_infos:
                if item_index not in item_block_summaries:
                    item_block_summaries[item_index] = {}
                item_block_summaries[item_index][block_index] = summary

        # 合并每个数据项的所有块摘要
        for item_index, block_summaries in item_block_summaries.items():
            # 按块索引排序并合并
            sorted_summaries = [
                block_summaries[i] for i in sorted(block_summaries.keys())
            ]
            data_items[item_index]["summary"] = "\n".join(sorted_summaries)[
                :max_summary_length
            ]

        # 打印最终统计
        print(f"📈 摘要生成完成统计:")
        print(f"   - 成功生成: {success_count}")
        print(f"   - 失败回退: {error_count}")
        if (success_count + error_count) > 0:
            print(
                f"   - 成功率: {(success_count / (success_count + error_count) * 100):.1f}%"
            )

    except Exception as e:
        print(f"❌ 摘要生成过程出现异常: {e}")
        # 如果整个过程失败，为所有未处理的数据项使用原始内容
        for item in data_items:
            if not item.get("summary"):
                content = item.get("content") or item.get("md", "")
                item["summary"] = content[:max_summary_length]

    print(f"🎉 摘要生成流程完成！")
    return data_items
