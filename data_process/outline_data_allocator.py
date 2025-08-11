"""
大纲数据智能分配器
为每个数据chunk智能匹配最合适的大纲章节，优先相关度最高的匹配
"""
import json
import asyncio
from typing import List, Dict, Any
from financial_report.utils.async_chat import async_chat_no_tool


# 单个chunk匹配提示词
CHUNK_MATCHING_PROMPT = """
你是一名专业的金融分析师，擅长为研究报告数据匹配最合适的章节。

## 任务说明：
分析提供的数据内容，从大纲章节列表中找出**最相关**的章节进行匹配。

## 匹配原则：
1. **优先匹配**：即使相关度不是100%，也要找出最相关的章节
2. **最佳匹配**：从所有章节中选择相关度最高的1个章节
3. **极少不匹配**：只有当内容与所有章节都完全无关时才选择不匹配

## 输出格式：
请严格按照以下JSON格式输出：

**匹配章节时：**
```json
{{
  "section_index": 0,
  "section_title": "匹配的章节标题",
  "confidence_score": 0.85,
  "match_reason": "匹配理由说明",
  "content_summary": "数据内容简要描述"
}}
```

**完全不匹配时（极少情况）：**
```json
{{
  "section_index": -1,
  "section_title": "",
  "confidence_score": 0.0,
  "match_reason": "与所有章节都无关的具体原因",
  "content_summary": "数据内容简要描述"
}}
```

---

**研究报告大纲章节列表：**
{outline_sections}

**数据内容 (ID: {data_id})：**
标题: {data_title}
内容摘要: {data_summary}

请分析并返回最佳匹配结果：
"""


async def allocate_data_to_outline_reverse(
    outline_data: Dict[str, Any],
    flattened_data: List[Dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    max_output_tokens: int = 8 * 1024,
    max_concurrent: int = 10
) -> Dict[str, Any]:
    """
    智能匹配：为每个数据chunk找到最合适的大纲章节
    
    Args:
        outline_data: 大纲数据
        flattened_data: 展平后的数据列表
        api_key: API密钥
        base_url: API基础URL
        model: 使用的模型名称
        max_output_tokens: 最大输出tokens
        max_concurrent: 最大并发数
    
    Returns:
        包含分配结果的完整大纲
    """
    print(f"\n📋 开始智能匹配 {len(flattened_data)} 个数据项...")
    
    # 准备大纲章节列表
    outline_sections = _format_outline_sections(outline_data)
    
    print(f"📊 处理统计:")
    print(f"   - 大纲章节数: {len(outline_data.get('reportOutline', []))}")
    print(f"   - 数据项数量: {len(flattened_data)}")
    print(f"   - 最大并发数: {max_concurrent}")
    
    # 创建并发任务
    semaphore = asyncio.Semaphore(max_concurrent)
    tasks = []
    
    for i, data_item in enumerate(flattened_data):
        task = _match_single_chunk(
            data_item=data_item,
            outline_sections=outline_sections,
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_output_tokens=max_output_tokens,
            semaphore=semaphore,
            item_index=i + 1,
            total_items=len(flattened_data)
        )
        tasks.append(task)
    
    print(f"🚀 开始并发处理 {len(tasks)} 个匹配任务...")
    
    # 并发执行所有任务
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        print(f"✅ 所有任务执行完成")
    except Exception as e:
        print(f"❌ 并发执行出现异常: {e}")
        results = []
    
    # 处理结果并构建最终大纲
    final_outline = _build_final_outline(outline_data, results)
    
    # 生成统计信息
    stats = _generate_matching_stats(results, len(flattened_data))
    
    print(f"\n📈 匹配统计:")
    print(f"   - 成功匹配: {stats['matched_count']}")
    print(f"   - 不匹配: {stats['unmatched_count']}")
    print(f"   - 处理失败: {stats['failed_count']}")
    print(f"   - 匹配率: {stats['match_rate']:.1f}%")
    print(f"   - 平均置信度: {stats['avg_confidence']:.2f}")
    
    return {
        "outline_with_allocations": final_outline,
        "allocation_stats": stats
    }


def _format_outline_sections(outline_data: Dict[str, Any]) -> str:
    """格式化大纲章节列表为字符串"""
    lines = []
    
    for i, section in enumerate(outline_data.get('reportOutline', [])):
        lines.append(f"{i}. {section.get('title', '')}")
        # 添加要点信息帮助匹配
        points = section.get('points', [])
        if points:
            for point in points[:3]:  # 只显示前3个要点
                lines.append(f"   - {point}")
    
    return "\n".join(lines)


async def _match_single_chunk(
    data_item: Dict[str, Any],
    outline_sections: str,
    api_key: str,
    base_url: str,
    model: str,
    max_output_tokens: int,
    semaphore: asyncio.Semaphore,
    item_index: int,
    total_items: int
) -> Dict[str, Any]:
    """匹配单个数据chunk到最合适的章节"""
    
    async with semaphore:
        data_id = data_item.get('id', '')
        data_title = data_item.get('title', '')
        data_summary = data_item.get('summary', '')
        
        # 如果没有摘要，使用内容的前300字符
        if not data_summary:
            content = data_item.get('content', '')
            data_summary = content[:300] + "..." if len(content) > 300 else content
        
        # 构建提示词
        prompt = CHUNK_MATCHING_PROMPT.format(
            outline_sections=outline_sections,
            data_id=data_id,
            data_title=data_title,
            data_summary=data_summary
        )
        
        print(f"   🔄 [{item_index}/{total_items}] 处理数据项 ID:{data_id}")
        
        try:
            # 调用AI
            result = await async_chat_no_tool(
                user_content=prompt,
                api_key=api_key,
                base_url=base_url,
                model=model,
                max_tokens=max_output_tokens,
                temperature=0.2,  # 降低温度，提高一致性
                use_cache=False,
                timeout=60
            )
            
            # 解析结果
            match_result = _parse_match_result(result, data_item)
            
            section_index = match_result.get('section_index', -1)
            confidence = match_result.get('confidence_score', 0.0)
            
            if section_index >= 0:
                print(f"   ✅ [{item_index}/{total_items}] ID:{data_id} → 章节[{section_index}] (置信度:{confidence:.2f})")
            else:
                print(f"   ⚪ [{item_index}/{total_items}] ID:{data_id} → 不匹配")
            
            return match_result
            
        except Exception as e:
            print(f"   ❌ [{item_index}/{total_items}] ID:{data_id} 处理失败: {e}")
            return _create_error_result(data_item, str(e))


def _create_error_result(data_item: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
    """创建错误结果格式"""
    summary = data_item.get('summary', '')
    if not summary:
        content = data_item.get('content', '')
        summary = content[:100] + "..." if len(content) > 100 else content
    
    return {
        "data_id": data_item.get('id', ''),
        "section_index": -1,
        "section_title": "",
        "confidence_score": 0.0,
        "match_reason": f"处理失败: {error_msg}",
        "content_summary": summary[:100],
        "error": True
    }


def _parse_match_result(result_text: str, data_item: Dict[str, Any]) -> Dict[str, Any]:
    """解析AI返回的匹配结果"""
    
    try:
        from financial_report.utils.extract_json_array import extract_json_array
        
        # 使用extract_json_array工具提取JSON
        json_text = extract_json_array(result_text, mode='auto')
        
        if json_text:
            parsed_result = json.loads(json_text)
            
            # 验证必要字段并标准化
            section_index = parsed_result.get('section_index', -1)
            section_title = parsed_result.get('section_title', '')
            confidence_score = parsed_result.get('confidence_score', 0.0)
            match_reason = parsed_result.get('match_reason', '')
            content_summary = parsed_result.get('content_summary', '')
            
            return {
                "data_id": data_item.get('id', ''),
                "section_index": section_index,
                "section_title": section_title,
                "confidence_score": confidence_score,
                "match_reason": match_reason,
                "content_summary": content_summary
            }
        
        # 解析失败，返回默认结果
        return _create_error_result(data_item, "AI返回结果解析失败")
        
    except Exception as e:
        return _create_error_result(data_item, f"解析异常: {str(e)}")


def _build_final_outline(outline_data: Dict[str, Any], results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """根据匹配结果构建最终大纲"""
    
    # 初始化大纲 - 复制原始数据的所有字段
    final_outline = {key: value for key, value in outline_data.items() if key != "reportOutline"}
    final_outline["reportOutline"] = []
    
    # 为每个章节初始化分配列表
    sections = outline_data.get("reportOutline", [])
    for section in sections:
        final_section = {
            "title": section.get("title", ""),
            "points": section.get("points", []),
            "allocated_data_ids": [],
            "data_descriptions": {}
        }
        final_outline["reportOutline"].append(final_section)
    
    # 添加不匹配章节
    unmatched_section = {
        "title": "不匹配的数据",
        "points": ["未能匹配到合适章节的数据项"],
        "allocated_data_ids": [],
        "data_descriptions": {}
    }
    final_outline["reportOutline"].append(unmatched_section)
    
    # 根据匹配结果分配数据
    for result in results:
        if isinstance(result, Exception) or result.get('error', False):
            continue
            
        data_id = result.get('data_id', '')
        section_index = result.get('section_index', -1)
        content_summary = result.get('content_summary', '')
        confidence_score = result.get('confidence_score', 0.0)
        match_reason = result.get('match_reason', '')
        
        if section_index >= 0 and section_index < len(sections):
            # 匹配到具体章节
            final_outline["reportOutline"][section_index]["allocated_data_ids"].append(data_id)
            description = f"{content_summary} (置信度: {confidence_score:.2f}, 理由: {match_reason})"
            final_outline["reportOutline"][section_index]["data_descriptions"][data_id] = description
        else:
            # 不匹配，放到最后一个章节
            final_outline["reportOutline"][-1]["allocated_data_ids"].append(data_id)
            description = f"{content_summary} (不匹配原因: {match_reason})"
            final_outline["reportOutline"][-1]["data_descriptions"][data_id] = description
    
    return final_outline


def _generate_matching_stats(results: List[Dict[str, Any]], total_items: int) -> Dict[str, Any]:
    """生成匹配统计信息"""
    
    matched_count = 0
    unmatched_count = 0
    failed_count = 0
    confidence_scores = []
    
    for result in results:
        if isinstance(result, Exception):
            failed_count += 1
        elif result.get('error', False):
            failed_count += 1
        else:
            section_index = result.get('section_index', -1)
            confidence_score = result.get('confidence_score', 0.0)
            
            if section_index >= 0:
                matched_count += 1
                confidence_scores.append(confidence_score)
            else:
                unmatched_count += 1
    
    match_rate = (matched_count / total_items * 100) if total_items > 0 else 0
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    
    return {
        "total_items": total_items,
        "matched_count": matched_count,
        "unmatched_count": unmatched_count,
        "failed_count": failed_count,
        "match_rate": match_rate,
        "avg_confidence": avg_confidence,
        "confidence_distribution": {
            "high": len([c for c in confidence_scores if c >= 0.8]),
            "medium": len([c for c in confidence_scores if 0.5 <= c < 0.8]),
            "low": len([c for c in confidence_scores if c < 0.5])
        }
    }


def allocate_data_to_outline_sync(
    outline_data: Dict[str, Any],
    flattened_data: List[Dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    max_output_tokens: int = 8 * 1024,
    max_concurrent: int = 10,
) -> Dict[str, Any]:
    """
    同步版本的反向匹配函数
    
    Args:
        outline_data: 大纲数据字典
        flattened_data: 展平后的数据列表
        api_key: API密钥
        base_url: API基础URL
        model: 使用的模型名称
        max_output_tokens: 最大输出tokens
        max_concurrent: 最大并发数
        **kwargs: 为了兼容性保留的其他参数（将被忽略）
    
    Returns:
        包含分配结果的字典
    """
    
    return asyncio.run(allocate_data_to_outline_reverse(
        outline_data=outline_data,
        flattened_data=flattened_data,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_output_tokens=max_output_tokens,
        max_concurrent=max_concurrent
    ))


def analyze_outline_coverage(allocation_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    分析大纲数据覆盖情况
    
    Args:
        allocation_result: 数据分配结果
    
    Returns:
        包含覆盖分析的字典
    """
    outline_sections = allocation_result.get("outline_with_allocations", {}).get("reportOutline", [])
    
    filled_sections = []
    empty_sections = []
    
    for section in outline_sections:
        allocated_data_ids = section.get("allocated_data_ids", [])
        if allocated_data_ids:
            filled_sections.append(section)
        else:
            empty_sections.append(section)
    
    total_sections = len(outline_sections)
    filled_count = len(filled_sections)
    empty_count = len(empty_sections)
    coverage_rate = (filled_count / total_sections * 100) if total_sections > 0 else 0
    
    return {
        "total_sections": total_sections,
        "filled_sections": filled_sections,
        "empty_sections": empty_sections,
        "filled_count": filled_count,
        "empty_count": empty_count,
        "coverage_rate": coverage_rate
    }


if __name__ == "__main__":
    # 测试用例
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 使用智谱AI进行测试
    api_key = os.getenv("ZHIPU_API_KEY")
    base_url = os.getenv("ZHIPU_BASE_URL")
    model = os.getenv("ZHIPU_FREE_TEXT_MODEL")
    
    # 读取测试数据
    with open("test_company_datas/company_outline.json", "r", encoding="utf-8") as f:
        outline_data = json.load(f)
    
    with open("test_company_datas/flattened_tonghuashun_data.json", "r", encoding="utf-8") as f:
        flattened_data = json.load(f)
    
    # 测试少量数据
    test_data = flattened_data[:5]  # 只测试前5个
    
    result = allocate_data_to_outline_sync(
        outline_data=outline_data,
        flattened_data=test_data,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_concurrent=3
    )
    
    # 保存结果
    with open("test_company_datas/outline_data_allocation.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print("✅ 测试完成！")
