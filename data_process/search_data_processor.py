
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from financial_report.search_tools.search_tools import bing_search_with_cache
from financial_report.llm_calls.company_outline_search_queries import generate_search_queries
from financial_report.llm_calls.content_assessor import assess_content_quality_hybrid
from data_process.content_summarizer import generate_summaries_for_collected_data
from data_process.outline_data_allocator import allocate_data_to_outline_sync


# 最小内容长度常量
MIN_CONTENT_LENGTH = 50


class SearchDataProcessor:
    """搜索数据处理器类 - 封装所有相关功能"""
    
    def __init__(self, 
                 api_key: str,
                 base_url: str,
                 model: str,
                 summary_api_key: str,
                 summary_base_url: str,
                 summary_model: str):
        """
        初始化搜索数据处理器
        
        Args:
            api_key: 质量评估API密钥
            base_url: 质量评估API基础URL
            model: 质量评估模型名称
            summary_api_key: 摘要生成API密钥
            summary_base_url: 摘要生成API基础URL
            summary_model: 摘要生成模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.summary_api_key = summary_api_key
        self.summary_base_url = summary_base_url
        self.summary_model = summary_model
    
    @staticmethod
    def format_search_results_to_flattened_data(
        search_results: List[Dict[str, Any]], 
        company_name: str = "",
        search_query: str = "",
        start_id: int = 1
    ) -> List[Dict[str, Any]]:
        """
        将搜索结果格式化为与展平数据一致的格式
        
        Args:
            search_results: bing_search_with_cache返回的搜索结果
            company_name: 公司名称
            search_query: 搜索查询
            start_id: 起始ID（用于避免与现有数据ID冲突）
            
        Returns:
            格式化后的数据列表，与flattened_tonghuashun_data格式一致
        """
        if not search_results:
            return []
        
        flattened_results = []
        
        for i, result in enumerate(search_results):
            # 基本格式化，与展平数据保持一致
            flattened_record = {
                "id": str(start_id + i),
                "company_name": company_name,
                "company_code": "",
                "market": "",
                "tonghuashun_total_code": "",
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "data_source_type": result.get("data_source_type", "html"),
                "content": result.get("md", ""),
                "search_query": search_query,
                "data_source": "search_result"
            }
            flattened_results.append(flattened_record)
        
        return flattened_results
    
    def _log_progress(self, current: int, total: int, message: str, result: str = ""):
        """统一的进度日志输出"""
        prefix = f"   🔄 [{current}/{total}]" if result == "" else f"   {result} [{current}/{total}]"
        print(f"{prefix} {message}")
    
    def assess_search_results_quality(
        self,
        search_results: List[Dict[str, Any]],
        company_name: str,
        section_title: str,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """
        对搜索结果进行质量评估，过滤低质量内容
        
        Args:
            search_results: 搜索结果列表
            company_name: 公司名称
            section_title: 章节标题（用于构建查询目标）
            max_concurrent: 最大并发数
            
        Returns:
            质量评估后的搜索结果列表（只包含高质量内容）
        """
        if not search_results:
            return []
        
        print(f"🔍 开始对 {len(search_results)} 个搜索结果进行质量评估（并发数: {max_concurrent}）...")
        
        # 构建查询目标
        query_objective = f"{company_name} {section_title}"
        
        # 使用异步并发处理
        return asyncio.run(self._assess_quality_concurrent(
            search_results, query_objective, max_concurrent
        ))
    
    async def _assess_quality_concurrent(
        self,
        search_results: List[Dict[str, Any]],
        query_objective: str,
        max_concurrent: int
    ) -> List[Dict[str, Any]]:
        """异步并发质量评估"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def assess_single_result(i: int, result: Dict) -> Optional[Dict]:
            async with semaphore:
                try:
                    url = result.get("url", "")
                    content = result.get("md", "")
                    title = result.get("title", "")
                    
                    # 预过滤：检查内容长度
                    if not content or len(content.strip()) < MIN_CONTENT_LENGTH:
                        self._log_progress(i+1, len(search_results), f"跳过空内容: {title[:50]}...", "⚠️")
                        return None
                    
                    self._log_progress(i+1, len(search_results), f"评估: {title[:50]}...")
                    
                    # 在异步上下文中运行同步的质量评估
                    loop = asyncio.get_event_loop()
                    assessment = await loop.run_in_executor(
                        None,
                        lambda: assess_content_quality_hybrid(
                            cleaned_text=content,
                            url=url,
                            query_objective=query_objective,
                            chat_model=self.model,
                            api_key=self.api_key,
                            base_url=self.base_url
                        )
                    )
                    
                    is_high_quality = assessment.get("is_high_quality", False)
                    reason = assessment.get("reason", "未知原因")
                    source = assessment.get("source", "unknown")
                    
                    if is_high_quality:
                        # 添加质量评估信息
                        result["quality_assessment"] = {
                            "is_high_quality": True,
                            "reason": reason,
                            "source": source,
                            "assessed_for": query_objective
                        }
                        self._log_progress(i+1, len(search_results), f"高质量内容 ({source}): {reason[:50]}...", "✅")
                        return result
                    else:
                        self._log_progress(i+1, len(search_results), f"低质量内容 ({source}): {reason[:50]}...", "❌")
                        return None
                        
                except Exception as e:
                    self._log_progress(i+1, len(search_results), f"评估失败: {e}", "⚠️")
                    return None
        
        # 并发执行所有评估任务
        tasks = [assess_single_result(i, result) for i, result in enumerate(search_results)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤出高质量结果和统计信息
        high_quality_results = []
        stats = {"low_quality": 0, "error": 0}
        
        for result in results:
            if isinstance(result, Exception):
                stats["error"] += 1
            elif result is None:
                stats["low_quality"] += 1
            else:
                high_quality_results.append(result)
        
        # 输出统计信息
        self._print_quality_stats(high_quality_results, stats, len(search_results))
        return high_quality_results
    
    def _print_quality_stats(self, high_quality_results: List, stats: Dict, total: int):
        """输出质量评估统计信息"""
        print(f"📊 质量评估完成:")
        print(f"   ✅ 高质量内容: {len(high_quality_results)}")
        print(f"   ❌ 低质量内容: {stats['low_quality']}")
        print(f"   ⚠️  评估失败: {stats['error']}")
        print(f"   📈 质量通过率: {len(high_quality_results)/total*100:.1f}%")
    
    def process_search_results_with_summary(
        self,
        search_results: List[Dict[str, Any]],
        company_name: str,
        search_query: str,
        section_title: str,
        start_id: int,
        chat_max_token_length: int = 128 * 1024,
        max_summary_length: int = 800,
        max_concurrent_summary: int = 10,
        max_concurrent_assessment: int = 5,
        enable_quality_assessment: bool = True
    ) -> List[Dict[str, Any]]:
        """
        将搜索结果格式化、质量评估并生成摘要
        一站式处理函数，替代原来的generate_search_results_with_summary
        """
        print(f"🔄 开始处理搜索结果...")
        
        if not search_results:
            print("⚠️  搜索结果为空")
            return []
        
        # 1. 质量评估（可选）
        if enable_quality_assessment:
            print(f"🔍 启用质量评估...")
            processed_results = self.assess_search_results_quality(
                search_results=search_results,
                company_name=company_name,
                section_title=section_title,
                max_concurrent=max_concurrent_assessment
            )
            
            if not processed_results:
                print("❌ 没有通过质量评估的内容")
                return []
                
            print(f"✅ 质量评估完成，保留 {len(processed_results)}/{len(search_results)} 个高质量结果")
        else:
            print(f"⚠️  跳过质量评估")
            processed_results = search_results
        
        # 2. 格式化搜索结果
        print(f"📋 格式化 {len(processed_results)} 个搜索结果...")
        
        flattened_results = self.format_search_results_to_flattened_data(
            search_results=processed_results,
            company_name=company_name,
            search_query=search_query,
            start_id=start_id
        )
        
        print(f"📋 已格式化 {len(flattened_results)} 条搜索结果")
        
        # 3. 生成摘要
        if flattened_results:
            print(f"🔄 开始为搜索结果生成摘要...")
            try:
                flattened_results = generate_summaries_for_collected_data(
                    data_items=flattened_results,
                    api_key=self.summary_api_key,
                    base_url=self.summary_base_url,
                    model=self.summary_model,
                    chat_max_token_length=chat_max_token_length,
                    max_summary_length=max_summary_length,
                    max_concurrent=max_concurrent_summary
                )
                print(f"✅ 搜索结果摘要生成完成！")
            except Exception as e:
                print(f"❌ 搜索结果摘要生成失败: {e}")
                print("📋 将返回不含摘要的搜索结果...")
        
        return flattened_results
    
    def _execute_single_search(
        self, 
        query: str, 
        search_api_url: str, 
        max_results: int
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """执行单次搜索"""
        try:
            search_results = bing_search_with_cache(
                query=query,
                search_api_url=search_api_url,
                total=max_results,
                force_refresh=False
            )
            
            if not search_results:
                print(f"   ⚠️  搜索无结果")
                return False, []
                
            print(f"   📊 搜索到 {len(search_results)} 个结果")
            return True, search_results
            
        except Exception as e:
            print(f"   ❌ 搜索失败: {e}")
            return False, []
    
    def _test_data_matching(
        self, 
        section: Dict[str, Any], 
        formatted_results: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> Tuple[bool, List[str]]:
        """测试数据是否能匹配到章节"""
        print(f"   🔗 测试数据匹配...")
        
        # 创建临时大纲数据进行匹配测试
        temp_outline = {"reportOutline": [section]}
        
        try:
            temp_allocation = allocate_data_to_outline_sync(
                outline_data=temp_outline,
                flattened_data=formatted_results,
                api_key=self.summary_api_key,
                base_url=self.summary_base_url,
                model=self.summary_model,
                max_concurrent=max_concurrent
            )
            
            # 检查是否有数据匹配到这个章节
            allocated_sections = temp_allocation.get("outline_with_allocations", {}).get("reportOutline", [])
            if allocated_sections and allocated_sections[0].get("allocated_data_ids"):
                matched_ids = allocated_sections[0]["allocated_data_ids"]
                print(f"   ✅ 匹配成功！匹配了 {len(matched_ids)} 个数据项")
                return True, matched_ids
            else:
                print(f"   ❌ 本轮搜索未匹配，继续下一个查询...")
                return False, []
                
        except Exception as e:
            print(f"   ❌ 匹配测试失败: {e}")
            return False, []
    
    def smart_search_for_empty_sections(
        self,
        empty_sections: List[Dict[str, Any]],
        company_name: str,
        existing_flattened_data: List[Dict[str, Any]],
        search_api_url: str,
        chat_max_token_length: int = 128 * 1024,
        max_searches_per_section: int = 3,
        max_results_per_search: int = 10,
        max_concurrent_summary: int = 10
    ) -> Dict[str, Any]:
        """
        为没有匹配数据的章节智能搜索相关内容
        """
        print(f"\n🔍 开始为 {len(empty_sections)} 个无数据章节智能搜索...")
        
        all_new_data = []
        section_search_results = {}
        current_max_id = max([int(item["id"]) for item in existing_flattened_data], default=0)
        
        for section_idx, section in enumerate(empty_sections):
            result = self._process_single_section(
                section, section_idx, len(empty_sections), company_name, 
                search_api_url, current_max_id, max_searches_per_section,
                max_results_per_search, chat_max_token_length, max_concurrent_summary
            )
            
            section_search_results[section["title"]] = result["summary"]
            if result["matched"]:
                all_new_data.extend(result["data"])
                current_max_id = result["new_max_id"]
        
        # 汇总结果
        return self._generate_final_search_summary(empty_sections, section_search_results, all_new_data)
    
    def _process_single_section(
        self, section: Dict[str, Any], section_idx: int, total_sections: int,
        company_name: str, search_api_url: str, current_max_id: int,
        max_searches_per_section: int, max_results_per_search: int,
        chat_max_token_length: int, max_concurrent_summary: int
    ) -> Dict[str, Any]:
        """处理单个章节的搜索"""
        section_title = section["title"]
        section_points = section.get("points", [])
        
        print(f"\n📋 处理章节 {section_idx + 1}/{total_sections}: {section_title}")
        print(f"   📝 章节要点数量: {len(section_points)}")
        
        # 1. 生成搜索查询
        try:
            search_queries = generate_search_queries(
                company=company_name,
                section_title=section_title,
                section_points=section_points,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                max_queries=max_searches_per_section
            )
            print(f"   ✅ 生成了 {len(search_queries)} 个搜索查询")
        except Exception as e:
            print(f"   ❌ 搜索查询生成失败: {e}")
            return {"matched": False, "data": [], "new_max_id": current_max_id, 
                   "summary": {"matched": False, "queries_used": 0, "data_found": 0}}
        
        # 2. 执行搜索并检查匹配
        section_matched = False
        section_new_data = []
        
        for query_idx, query in enumerate(search_queries):
            if section_matched:
                print(f"   ⏭️  章节已匹配，跳过剩余查询")
                break
                
            print(f"   🌐 执行搜索 {query_idx + 1}/{len(search_queries)}: {query[:50]}...")
            
            # 执行搜索
            success, search_results = self._execute_single_search(query, search_api_url, max_results_per_search)
            if not success:
                continue
            
            # 格式化搜索结果并生成摘要
            # 使用当前最大ID+1作为起始ID，确保不冲突
            next_start_id = current_max_id + 1
            formatted_results = self.process_search_results_with_summary(
                search_results=search_results,
                company_name=company_name,
                search_query=query,
                section_title=section_title,
                start_id=next_start_id,
                chat_max_token_length=chat_max_token_length,
                max_concurrent_summary=max_concurrent_summary,
                max_concurrent_assessment=5,
                enable_quality_assessment=True
            )
            
            if not formatted_results:
                print(f"   ⚠️  格式化结果为空")
                continue
            
            # 更新ID计数器到最新的最大值
            if formatted_results:
                max_result_id = max([int(item["id"]) for item in formatted_results])
                current_max_id = max_result_id
                print(f"   🔢 更新ID计数器: {current_max_id}")
            
            # 测试数据匹配
            matched, matched_ids = self._test_data_matching(section, formatted_results, max_concurrent_summary)
            if matched:
                section_matched = True
                section_new_data.extend(formatted_results)
                break
        
        result_summary = {
            "matched": section_matched,
            "queries_used": len(search_queries),
            "data_found": len(section_new_data)
        }
        
        if section_matched:
            print(f"   🎉 章节 '{section_title}' 搜索成功，找到 {len(section_new_data)} 个相关数据")
        else:
            print(f"   😔 章节 '{section_title}' 未找到匹配数据")
        
        return {
            "matched": section_matched,
            "data": section_new_data,
            "new_max_id": current_max_id,
            "summary": result_summary
        }
    
    def _generate_final_search_summary(
        self, empty_sections: List, section_search_results: Dict, all_new_data: List
    ) -> Dict[str, Any]:
        """生成最终搜索汇总"""
        total_matched = sum(1 for result in section_search_results.values() if result["matched"])
        total_data_found = len(all_new_data)
        
        print(f"\n📊 智能搜索完成汇总:")
        print(f"   📋 处理章节: {len(empty_sections)}")
        print(f"   ✅ 成功匹配: {total_matched}")
        print(f"   📄 新增数据: {total_data_found}")
        print(f"   💔 仍无数据: {len(empty_sections) - total_matched}")
        
        return {
            "new_search_data": all_new_data,
            "search_results_summary": section_search_results,
            "stats": {
                "total_sections_processed": len(empty_sections),
                "sections_matched": total_matched,
                "sections_still_empty": len(empty_sections) - total_matched,
                "total_new_data": total_data_found
            }
        }
    
    @staticmethod
    def merge_search_data_with_existing(
        existing_flattened_data: List[Dict[str, Any]],
        new_search_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        将新搜索的数据与现有数据合并，确保ID不冲突
        """
        print(f"🔗 合并数据：现有 {len(existing_flattened_data)} 条 + 新增 {len(new_search_data)} 条")
        
        if not new_search_data:
            print(f"⚠️  没有新数据需要合并")
            return existing_flattened_data.copy()
        
        # 1. 找到现有数据中的最大ID
        existing_ids = [int(item["id"]) for item in existing_flattened_data if item.get("id")]
        max_existing_id = max(existing_ids) if existing_ids else 0
        
        print(f"🔢 现有数据最大ID: {max_existing_id}")
        
        # 2. 为新数据重新分配ID，确保不与现有ID冲突
        reassigned_new_data = []
        new_id_start = max_existing_id + 1
        
        for i, item in enumerate(new_search_data):
            new_item = item.copy()  # 创建副本避免修改原数据
            old_id = new_item.get("id", "unknown")
            new_id = str(new_id_start + i)
            new_item["id"] = new_id
            reassigned_new_data.append(new_item)
            
            # 记录ID映射用于调试
            if i < 5:  # 只显示前5个的映射
                print(f"   🔄 ID重新分配: {old_id} → {new_id}")
        
        if len(new_search_data) > 5:
            print(f"   ... 还有 {len(new_search_data) - 5} 个数据的ID被重新分配")
        
        # 3. 合并数据
        merged_data = existing_flattened_data.copy()
        merged_data.extend(reassigned_new_data)
        
        # 4. 验证ID唯一性
        all_ids = [item["id"] for item in merged_data]
        unique_ids = set(all_ids)
        
        if len(all_ids) != len(unique_ids):
            duplicate_ids = [id for id in all_ids if all_ids.count(id) > 1]
            print(f"⚠️  警告：发现重复ID: {set(duplicate_ids)}")
        else:
            print(f"✅ ID唯一性验证通过")
        
        print(f"✅ 合并完成，总计 {len(merged_data)} 条数据")
        print(f"📊 ID范围: 1 - {max([int(item['id']) for item in merged_data])}")
        
        return merged_data







