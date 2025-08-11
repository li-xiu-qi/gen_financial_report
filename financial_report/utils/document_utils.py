# document_utils.py
import asyncio
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import asdict
from .document_types import PreDoc, Doc

# 2. 生成摘要（使用 info_description.generate_full_content_description，分块处理）
from ..llm_calls.info_description import generate_full_content_description, async_generate_full_content_description
from .calculate_tokens import TokenCalculator, OpenAITokenCalculator


async def _generate_summary_async(
    content: str,
    api_key: str,
    base_url: str,
    model: str,
    semaphore: asyncio.Semaphore,
    progress_counter: dict = None,
    task_id: str = ""
) -> str:
    """异步生成摘要，带并发控制和进度显示"""
    async with semaphore:
        if progress_counter:
            print(f"   🔄 [{progress_counter['current']}/{progress_counter['total']}] 正在生成摘要: {task_id[:50]}...")
        
        # 使用真正的异步函数
        try:
            result = await async_generate_full_content_description(
                content=content,
                api_key=api_key,
                base_url=base_url,
                model=model
            )
            
            if progress_counter:
                progress_counter['current'] += 1
                progress_counter['completed'] += 1
                print(f"   ✅ [{progress_counter['current']}/{progress_counter['total']}] 摘要生成完成: {task_id[:50]}...")
            
            return result
        except Exception as e:
            if progress_counter:
                progress_counter['current'] += 1
                progress_counter['failed'] += 1
                print(f"   ❌ [{progress_counter['current']}/{progress_counter['total']}] 摘要生成失败: {task_id[:50]}... (错误: {str(e)[:100]})")
            raise e


async def _calculate_tokens_async(
    docs: List[PreDoc],
    token_calculator: TokenCalculator,
    max_concurrent: int = 100
):
    """异步并发计算所有文档的token数量"""
    print("🔢 并发计算文档token数量...")
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def _calculate_single_doc_tokens(doc: PreDoc, index: int, total: int):
        async with semaphore:
            # 在线程池中执行token计算（因为tokenizer通常是CPU密集型）
            loop = asyncio.get_event_loop()
            
            # 只计算还没有token数量的字段
            tasks = []
            
            if doc.content and doc.content_tokens is None:
                tasks.append(('content', loop.run_in_executor(None, token_calculator.count_tokens, doc.content)))
            
            if doc.summary and doc.summary_tokens is None:
                tasks.append(('summary', loop.run_in_executor(None, token_calculator.count_tokens, doc.summary)))
            
            if doc.raw_content and doc.raw_content_tokens is None:
                tasks.append(('raw_content', loop.run_in_executor(None, token_calculator.count_tokens, doc.raw_content)))
            
            # 并发执行所有token计算任务
            if tasks:
                results = await asyncio.gather(*[task[1] for task in tasks])
                for (field_name, _), token_count in zip(tasks, results):
                    if field_name == 'content':
                        doc.content_tokens = token_count
                    elif field_name == 'summary':
                        doc.summary_tokens = token_count
                    elif field_name == 'raw_content':
                        doc.raw_content_tokens = token_count
            
            # 显示进度
            if (index + 1) % 20 == 0 or (index + 1) == total:
                print(f"   🔢 [{index + 1}/{total}] Token计算进度: {((index + 1)/total*100):.1f}%")
    
    # 创建所有token计算任务
    tasks = [
        _calculate_single_doc_tokens(doc, i, len(docs))
        for i, doc in enumerate(docs)
    ]
    
    # 并发执行所有任务
    await asyncio.gather(*tasks)
    
    # 统计结果
    calculated_count = sum(1 for doc in docs if doc.content_tokens is not None)
    print(f"   ✅ Token计算完成: {calculated_count}/{len(docs)} 个文档")


async def _process_summaries_async(
    unique_predocs: List[PreDoc],
    api_key: str,
    base_url: str,
    chat_model: str,
    max_embedding_length: int,
    max_token_per_block: int,
    token_calculator: TokenCalculator,
    max_concurrent: int = 50
):
    """异步处理所有文档的摘要生成，带并发控制和内容去重"""
    print(f"\n📝 开始处理 {len(unique_predocs)} 个文档的摘要生成...")
    print(f"🔧 配置: 最大并发={max_concurrent}, 模型={chat_model}")
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    # 第一步：收集所有需要生成摘要的内容，并进行去重
    print("🔍 第一步: 分析文档内容并进行去重...")
    print("   📊 正在计算token数量和分块...")
    
    content_to_docs = {}  # content_hash -> list of docs
    content_to_blocks = {}  # content_hash -> list of (doc, block_index, block_content)
    
    # 统计变量
    docs_need_summary = [doc for doc in unique_predocs if not doc.summary]
    total_docs_to_analyze = len(docs_need_summary)
    analyzed_count = 0
    long_docs_count = 0
    total_blocks_created = 0
    
    for doc in docs_need_summary:
        analyzed_count += 1
        content = doc.content
        
        # 显示token计算进度
        if analyzed_count % 10 == 0 or analyzed_count == total_docs_to_analyze:
            print(f"   🔢 [{analyzed_count}/{total_docs_to_analyze}] Token计算进度: {(analyzed_count/total_docs_to_analyze*100):.1f}%")
        
        token_count = token_calculator.count_tokens(content)
        
        if token_count <= max_token_per_block:
            # 内容不超限，直接生成摘要
            content_hash = hash(content)
            if content_hash not in content_to_docs:
                content_to_docs[content_hash] = []
            content_to_docs[content_hash].append(doc)
        else:
            # 内容超限，分块处理
            long_docs_count += 1
            blocks = []
            start = 0
            content_len = len(content)
            
            print(f"   📄 文档过长需分块: {doc.source[:50] if doc.source else 'unknown'}... (tokens: {token_count})")
            # 如果token超过25w就丢弃
            if token_count > 25 * 10000:
                continue
            # 使用高性能分块器
            from .fast_token_splitter import FastTokenSplitter
            splitter = FastTokenSplitter(
                token_calculator=token_calculator,
                chunk_size=max_token_per_block,
                chunk_overlap=50  # 小的重叠以保持上下文
            )
            blocks = splitter.split_text(content)
            
            total_blocks_created += len(blocks)
            print(f"   ✂️  分块完成: 创建了 {len(blocks)} 个块")
            
            # 对每个块进行去重
            for block_index, block in enumerate(blocks):
                block_hash = hash(block)
                if block_hash not in content_to_blocks:
                    content_to_blocks[block_hash] = []
                content_to_blocks[block_hash].append((doc, block_index, block))
    
    print(f"   📈 Token分析完成统计:")
    print(f"      - 分析文档总数: {total_docs_to_analyze}")
    print(f"      - 需要分块的长文档: {long_docs_count}")
    print(f"      - 创建的总块数: {total_blocks_created}")
    print(f"      - 平均每个长文档分块: {(total_blocks_created/long_docs_count):.1f}" if long_docs_count > 0 else "      - 平均每个长文档分块: 0")
    
    # 统计去重效果
    total_docs = len([doc for doc in unique_predocs if not doc.summary])
    unique_contents = len(content_to_docs)
    unique_blocks = len(content_to_blocks)
    total_unique_tasks = unique_contents + unique_blocks
    
    print(f"📊 去重统计:")
    print(f"   - 需要处理的文档: {total_docs}")
    print(f"   - 去重后的完整内容: {unique_contents}")
    print(f"   - 去重后的分块内容: {unique_blocks}")
    print(f"   - 总计需要生成摘要: {total_unique_tasks}")
    if total_docs > 0:
        print(f"   - 去重效率: {((total_docs - total_unique_tasks) / total_docs * 100):.1f}%")
    
    # 第二步：为去重后的内容创建异步任务
    print("🚀 第二步: 创建异步任务...")
    
    # 初始化进度计数器
    progress_counter = {
        'current': 0,
        'total': total_unique_tasks,
        'completed': 0,
        'failed': 0
    }
    
    unique_content_tasks = {}  # content_hash -> task
    unique_block_tasks = {}   # block_hash -> task
    
    # 处理完整文档内容
    for content_hash, docs in content_to_docs.items():
        content = docs[0].content  # 所有doc的content都相同，取第一个
        # 生成任务ID用于进度显示
        task_id = f"完整文档-{docs[0].source if docs[0].source else 'unknown'}"
        task = _generate_summary_async(
            content, api_key, base_url, chat_model, semaphore, progress_counter, task_id
        )
        unique_content_tasks[content_hash] = task
    
    # 处理分块内容
    for block_hash, block_infos in content_to_blocks.items():
        block_content = block_infos[0][2]  # 所有block内容都相同，取第一个
        doc, block_index, _ = block_infos[0]
        # 生成任务ID用于进度显示
        task_id = f"分块{block_index}-{doc.source if doc.source else 'unknown'}"
        task = _generate_summary_async(
            block_content, api_key, base_url, chat_model, semaphore, progress_counter, task_id
        )
        unique_block_tasks[block_hash] = task
    
    # 第三步：执行所有去重后的任务
    print(f"⚡ 第三步: 并发执行 {total_unique_tasks} 个摘要生成任务...")
    print(f"   📊 实时进度显示:")
    
    try:
        # 合并所有任务到一个列表中，以便统一处理进度
        all_tasks = []
        task_to_hash = {}
        
        # 添加完整文档任务
        for content_hash, task in unique_content_tasks.items():
            all_tasks.append(task)
            task_to_hash[task] = ('content', content_hash)
        
        # 添加分块任务
        for block_hash, task in unique_block_tasks.items():
            all_tasks.append(task)
            task_to_hash[task] = ('block', block_hash)
        
        # 并发执行所有任务
        if all_tasks:
            all_results = await asyncio.gather(*all_tasks, return_exceptions=True)
            
            # 将结果分配回对应的字典
            content_hash_to_result = {}
            block_hash_to_result = {}
            
            for task, result in zip(all_tasks, all_results):
                task_type, task_hash = task_to_hash[task]
                if task_type == 'content':
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
        
        # 第四步：将结果分配给相应的文档
        print("📋 第四步: 分配摘要结果到文档...")
        
        # 统计成功和失败的任务
        success_count = 0
        error_count = 0
        
        # 处理完整文档
        for content_hash, docs in content_to_docs.items():
            result = content_hash_to_result.get(content_hash)
            if isinstance(result, Exception):
                summary = docs[0].content[:max_embedding_length]
                error_count += 1
            else:
                summary = result[:max_embedding_length] if result else docs[0].content[:max_embedding_length]
                success_count += 1
            
            # 将相同内容的摘要分配给所有相关文档
            for doc in docs:
                doc.summary = summary
        
        # 处理分块文档
        doc_block_summaries = {}  # doc -> {block_index: summary}
        for block_hash, block_infos in content_to_blocks.items():
            result = block_hash_to_result.get(block_hash)
            if isinstance(result, Exception):
                summary = block_infos[0][2][:max_embedding_length]  # 使用原始块内容
                error_count += 1
            else:
                summary = result if result else block_infos[0][2][:max_embedding_length]
                success_count += 1
            
            # 将相同块内容的摘要分配给所有相关文档的对应块
            for doc, block_index, block_content in block_infos:
                if doc not in doc_block_summaries:
                    doc_block_summaries[doc] = {}
                doc_block_summaries[doc][block_index] = summary
        
        # 合并每个文档的所有块摘要
        for doc, block_summaries in doc_block_summaries.items():
            # 按块索引排序并合并
            sorted_summaries = [block_summaries[i] for i in sorted(block_summaries.keys())]
            doc.summary = '\n'.join(sorted_summaries)[:max_embedding_length]
        
        # 打印最终统计
        print(f"📈 摘要生成完成统计:")
        print(f"   - 成功生成: {success_count}")
        print(f"   - 失败回退: {error_count}")
        print(f"   - 成功率: {(success_count / (success_count + error_count) * 100):.1f}%" if (success_count + error_count) > 0 else "   - 成功率: 100%")
            
    except Exception as e:
        print(f"❌ 摘要生成过程出现异常: {e}")
        # 如果整个过程失败，为所有未处理的文档使用原始内容
        for doc in unique_predocs:
            if not doc.summary:
                doc.summary = doc.content[:max_embedding_length]


def process_and_add_documents(
    docs: List[PreDoc],
    content_pool,
    url_hash_set: Set[int],
    raw_content_hash_set: Set[int],
    api_key: str,
    base_url: str,
    chat_model: str,
    chat_max_token_length: int,  # Chat模型的最大token长度，用于分块
    embedding_model: str,
    embedding_model_api_key: str,
    embedding_model_base_url: str,
    max_embedding_length: int,  # 用于摘要截断，不是分块
    get_text_embedding_fn,
    max_concurrent: int = 50
) -> Tuple[Set[int], Set[int]]:
    """
    处理并添加文档到内容池，返回更新后的去重哈希集。
    这是一个纯函数，不修改类状态，只操作传入的参数。
    需要外部传入 chat_no_tool_fn, get_text_embedding_fn。
    """
    print(f"\n🚀 开始处理文档导入流程...")
    print(f"📥 输入文档数量: {len(docs)}")
    
    # 1. 去重
    print("🔍 步骤1: 文档去重...")
    unique_predocs = []
    duplicate_count = 0
    
    for doc in docs:
        url_hash = hash(doc.source)
        raw_content_hash = hash(doc.raw_content)
        if url_hash in url_hash_set or raw_content_hash in raw_content_hash_set:
            duplicate_count += 1
            continue
        url_hash_set.add(url_hash)
        raw_content_hash_set.add(raw_content_hash)
        unique_predocs.append(doc)
    
    print(f"   - 去重后文档数量: {len(unique_predocs)}")
    print(f"   - 重复文档数量: {duplicate_count}")
    
    if not unique_predocs:
        print("⚠️  没有新文档需要处理，跳过后续步骤")
        return url_hash_set, raw_content_hash_set

    # 默认用 OpenAITokenCalculator，可根据实际情况替换
    token_calculator = OpenAITokenCalculator()
    # 使用chat模型的token限制来计算分块大小，预留一些空间给prompt
    max_token_per_block = int(chat_max_token_length * 0.6)  # 使用chat token限制的60%作为分块大小
    
    print(f"🔧 分块配置:")
    print(f"   - Chat模型最大token: {chat_max_token_length}")
    print(f"   - 每块最大token: {max_token_per_block}")
    print(f"   - 摘要截断长度: {max_embedding_length}")

    # 2. 异步生成摘要（使用并发控制）
    asyncio.run(_process_summaries_async(
        unique_predocs=unique_predocs,
        api_key=api_key,
        base_url=base_url,
        chat_model=chat_model,
        max_embedding_length=max_embedding_length,
        max_token_per_block=max_token_per_block,
        token_calculator=token_calculator,
        max_concurrent=max_concurrent
    ))

    # 3. 自动Embedding
    print("🔗 步骤3: 生成向量嵌入...")
    docs_to_embed = [doc.summary for doc in unique_predocs if doc.vector is None]
    print(f"   - 需要生成向量的文档: {len(docs_to_embed)}")
    
    if docs_to_embed:
        print(f"   - 使用模型: {embedding_model}")
        vectors = get_text_embedding_fn(
            docs_to_embed,
            api_key=embedding_model_api_key,
            base_url=embedding_model_base_url,
            embedding_model=embedding_model,
        )
        print(f"   - 生成向量数量: {len(vectors)}")
        
        # 将生成的向量赋回给相应的文档
        vec_idx = 0
        for doc in unique_predocs:
            if doc.vector is None:
                doc.vector = vectors[vec_idx]
                vec_idx += 1
        print("   ✅ 向量嵌入完成")
    else:
        print("   ⚠️  所有文档已有向量，跳过向量生成")

    # 4. 格式化并入库
    print("💾 步骤4: 格式化并入库...")
    doc_objs = []
    for doc in unique_predocs:
        if doc.vector is not None:
            payload = {
                "content": doc.content,
                "source": doc.source,
                "summary": doc.summary,
                "data_source_type": doc.data_source_type,
                **doc.others
            }
            # id 传递到 Doc 对象和 payload
            doc_objs.append(Doc(id=doc.id, vector=doc.vector, payload=payload))
    
    print(f"   - 准备入库的文档: {len(doc_objs)}")
    if doc_objs:
        content_pool.insert_contents([asdict(d) for d in doc_objs])
        print("   ✅ 文档入库完成")
    else:
        print("   ⚠️  没有文档需要入库")

    print(f"🎉 文档导入流程完成！")
    print(f"   - 总处理文档: {len(unique_predocs)}")
    print(f"   - 成功入库: {len(doc_objs)}")
    
    return url_hash_set, raw_content_hash_set
