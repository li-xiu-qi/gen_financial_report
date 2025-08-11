"""
基础可视化数据增强器
提供公共的可视化数据增强功能，支持公司和行业两种不同的使用场景
"""

import json
import asyncio
from abc import ABC, abstractmethod
import sys
from typing import List, Dict, Any, Optional
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array
from data_process.data_collector import DataCollector


class BaseVisualDataEnhancer(ABC):
    """基础可视化数据增强器抽象类"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        data_collector: Optional[DataCollector] = None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.data_collector = data_collector or DataCollector(api_key, base_url, model)
        self.outline_data = None  # 存储大纲数据
    
    @abstractmethod
    def get_target_name_field(self) -> str:
        """获取目标名称字段（公司用company_name，行业用industry_name）"""
        pass
    
    @abstractmethod
    def get_analysis_system_prompt(self) -> str:
        """获取可视化分析的系统提示词"""
        pass
    
    @abstractmethod
    def get_analysis_user_prompt(
        self, 
        target_name: str, 
        batch_index: int, 
        total_batches: int, 
        data_summaries: List[Dict[str, Any]]
    ) -> str:
        """获取可视化分析的用户提示词"""
        pass
    
    def set_outline_data(self, outline_data: Dict[str, Any]):
        """设置大纲数据"""
        self.outline_data = outline_data
    
    def analyze_visualizable_data_groups(
        self,
        flattened_data: List[Dict[str, Any]],
        max_items_per_batch: int = 50,
        target_name: str = ""
    ) -> Dict[str, Any]:
        """
        分析展平数据，识别适合可视化的数据组合
        
        Args:
            flattened_data: 展平的数据列表（包含摘要）
            max_items_per_batch: 每批最大处理项目数
            target_name: 目标名称（公司名称或行业名称）
            
        Returns:
            包含可视化数据组合建议的字典
        """
        print(f"🔍 开始分析可视化数据组合...")
        print(f"   📊 总数据项: {len(flattened_data)}")
        print(f"   📦 每批处理: {max_items_per_batch} 项")
        
        # 创建数据批次
        batches = self._create_analysis_batches(flattened_data, max_items_per_batch)
        print(f"   🗂️ 分为 {len(batches)} 个批次")
        
        all_suggestions = []
        
        for i, batch in enumerate(batches):
            print(f"\n   🔄 分析第 {i+1}/{len(batches)} 批次...")
            try:
                batch_suggestions = self._analyze_batch_for_visualization(
                    batch, target_name, i+1, len(batches)
                )
                
                # 确保 batch_suggestions 是列表且包含字典
                if isinstance(batch_suggestions, list):
                    valid_suggestions = [s for s in batch_suggestions if isinstance(s, dict)]
                    all_suggestions.extend(valid_suggestions)
                    print(f"   ✅ 第 {i+1} 批次完成，发现 {len(valid_suggestions)} 个可视化建议")
                else:
                    print(f"   ⚠️ 第 {i+1} 批次返回了非列表结果: {type(batch_suggestions)}")
            except Exception as e:
                print(f"   ❌ 第 {i+1} 批次分析失败: {e}")
                continue
        
        # 合并和去重建议
        merged_suggestions = self._merge_and_deduplicate_suggestions(all_suggestions)
        
        result = {
            self.get_target_name_field(): target_name,
            "analysis_time": "2025-01-23",
            "total_data_items": len(flattened_data),
            "batches_processed": len(batches),
            "visualization_suggestions": merged_suggestions,
            "suggestion_count": len(merged_suggestions)
        }
        
        print(f"\n✅ 可视化分析完成！")
        print(f"   📈 发现 {len(merged_suggestions)} 个可视化建议")
        
        return result
    
    def _create_analysis_batches(
        self, 
        data_items: List[Dict[str, Any]], 
        max_items_per_batch: int
    ) -> List[List[Dict[str, Any]]]:
        """将数据分批进行分析"""
        batches = []
        for i in range(0, len(data_items), max_items_per_batch):
            batch = data_items[i:i + max_items_per_batch]
            batches.append(batch)
        return batches
    
    def _analyze_batch_for_visualization(
        self,
        data_batch: List[Dict[str, Any]],
        target_name: str,
        batch_index: int,
        total_batches: int
    ) -> List[Dict[str, Any]]:
        """分析一批数据，识别可视化机会"""
        
        # 构建数据摘要列表
        data_summaries = []
        for item in data_batch:
            summary_info = {
                "id": item["id"],
                self.get_target_name_field(): item.get(self.get_target_name_field(), ""),
                "title": item.get("title", ""),
                "summary": item.get("summary", "")[:500] + "..." if len(item.get("summary", "")) > 500 else item.get("summary", "")
            }
            data_summaries.append(summary_info)
        
        system_prompt = self.get_analysis_system_prompt()
        user_prompt = self.get_analysis_user_prompt(target_name, batch_index, total_batches, data_summaries)

        try:
            if not system_prompt:
                system_prompt = "你是一个有用的人工智能助手。"
            response = chat_no_tool(
                user_content=user_prompt,
                system_content=system_prompt,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,
                max_tokens=8192
            )
            
            # 提取JSON
            json_str = extract_json_array(response)
            if not json_str:
                print(f"     ❌ 无法从响应中提取有效的JSON: {response[:200]}...")
                return []
            
            try:
                suggestions = json.loads(json_str)
            except json.JSONDecodeError as je:
                print(f"     ❌ JSON解析失败: {je}, JSON字符串: {json_str[:200]}...")
                return []
            
            # 确保返回的是列表，且每个元素都是字典
            if isinstance(suggestions, dict):
                suggestions = [suggestions]
            elif not isinstance(suggestions, list):
                print(f"     ❌ 解析结果不是列表或字典: {type(suggestions)}")
                return []
            
            # 过滤掉非字典元素
            valid_suggestions = []
            for item in suggestions:
                if isinstance(item, dict):
                    valid_suggestions.append(item)
                else:
                    print(f"     ⚠️ 跳过非字典元素: {type(item)} - {item}")
            
            return valid_suggestions
            
        except Exception as e:
            print(f"     ❌ 批次分析异常: {e}")
            return []
    
    def _merge_and_deduplicate_suggestions(
        self, 
        all_suggestions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """合并和去重建议"""
        if not all_suggestions:
            return []
        
        # 简单的去重逻辑：基于data_ids的组合
        seen_combinations = set()
        unique_suggestions = []
        
        for suggestion in all_suggestions:
            # 确保 suggestion 是字典类型
            if not isinstance(suggestion, dict):
                print(f"⚠️ 跳过非字典建议: {type(suggestion)} - {suggestion}")
                continue
                
            data_ids = suggestion.get("data_ids", [])
            if not data_ids:
                continue
                
            # 创建组合的标识符
            combo_key = tuple(sorted(data_ids))
            
            if combo_key not in seen_combinations:
                seen_combinations.add(combo_key)
                unique_suggestions.append(suggestion)
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        unique_suggestions.sort(
            key=lambda x: priority_order.get(x.get("priority", "medium"), 1) if isinstance(x, dict) else 2
        )
        
        return unique_suggestions
    
    def collect_and_visualize_data(
        self,
        visualization_suggestions: List[Dict[str, Any]],
        all_data: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> Dict[str, Any]:
        """
        根据可视化建议收集数据并进行可视化处理
        
        Args:
            visualization_suggestions: 可视化建议列表
            all_data: 所有原始数据
            
        Returns:
            包含可视化结果的字典
        """
        print(f"\n📊 开始收集和处理可视化数据...")
        print(f"   🎯 处理建议数: {len(visualization_suggestions)}")
        
        # 使用异步并发处理
        return asyncio.run(self._collect_and_visualize_data_async(visualization_suggestions, all_data, max_concurrent))
    
    async def _collect_and_visualize_data_async(
        self,
        visualization_suggestions: List[Dict[str, Any]],
        all_data: List[Dict[str, Any]],
        max_concurrent: int = 10
    ) -> Dict[str, Any]:
        """异步并发处理可视化建议"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 创建异步任务
        tasks = []
        for i, suggestion in enumerate(visualization_suggestions):
            task = self._process_single_suggestion_async(suggestion, i, all_data, semaphore)
            tasks.append(task)
        
        # 并发执行所有任务
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 过滤掉异常和None结果
            successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
        else:
            successful_results = []
        
        print(f"\n✅ 可视化数据处理完成！")
        print(f"   📈 成功处理: {len(successful_results)} 个可视化项目")
        
        return {
            "processing_time": "2025-01-23",
            "total_suggestions_processed": len(visualization_suggestions),
            "successful_visualizations": len(successful_results),
            "visualization_results": successful_results
        }
    
    async def _process_single_suggestion_async(
        self,
        suggestion: Dict[str, Any],
        index: int,
        all_data: List[Dict[str, Any]],
        semaphore: asyncio.Semaphore
    ) -> Optional[Dict[str, Any]]:
        """异步处理单个可视化建议"""
        async with semaphore:
            print(f"\n   🔄 处理第 {index+1} 个建议: {suggestion.get('chart_title', 'Unknown')}")
            
            try:
                # 1. 收集相关数据
                data_ids = suggestion.get("data_ids", [])
                print(f"      📋 收集数据ID: {data_ids}")
                
                collected_data = self.data_collector.get_data_by_ids(data_ids, all_data)
                print(f"      ✅ 成功收集 {len(collected_data)} 个数据项")
                
                if not collected_data:
                    print(f"      ⚠️ 未找到相关数据，跳过")
                    return None
                
                # 2. 直接将建议作为成功的可视化结果（前面已经筛选过了）
                print(f"      ✅ 可视化建议处理成功: {suggestion.get('chart_title', 'Unknown')}")
                
                result_item = {
                    "suggestion_index": index + 1,
                    "original_suggestion": suggestion,
                    "collected_data_count": len(collected_data),
                    "data_ids": data_ids
                }
                return result_item
                    
            except Exception as e:
                print(f"      ❌ 处理失败: {e}")
                return None
    
    def run_full_enhancement_process(
        self,
        flattened_data: List[Dict[str, Any]],
        target_name: str = "",
        max_concurrent: int = 10
    ) -> Dict[str, Any]:
        """
        运行完整的数据增强流程
        
        Args:
            flattened_data: 展平的数据（包含摘要）
            target_name: 目标名称
            max_suggestions: 最大处理建议数
            
        Returns:
            完整的处理结果
        """
        print(f"🚀 启动完整的可视化数据增强流程...")
        
        # 步骤1: 分析可视化数据组合
        analysis_result = self.analyze_visualizable_data_groups(
            flattened_data=flattened_data,
            target_name=target_name
        )
        
        # 步骤2: 收集和可视化数据
        if analysis_result["suggestion_count"] > 0:
            visualization_result = self.collect_and_visualize_data(
                visualization_suggestions=analysis_result["visualization_suggestions"],
                all_data=flattened_data,
                max_concurrent=max_concurrent
            )
        else:
            print("⚠️ 未发现可视化建议，跳过数据收集步骤")
            visualization_result = {
                "processing_time": "2025-01-23",
                "total_suggestions_processed": 0,
                "successful_visualizations": 0,
                "visualization_results": []
            }
        
        # 合并结果
        final_result = {
            "enhancement_process": "complete",
            self.get_target_name_field(): target_name,
            "analysis_phase": analysis_result,
            "visualization_phase": visualization_result,
            "summary": {
                "total_data_analyzed": len(flattened_data),
                "suggestions_generated": analysis_result["suggestion_count"],
                "successful_visualizations": visualization_result["successful_visualizations"]
            }
        }
        
        print(f"\n🎉 完整流程执行完毕！")
        print(f"   📊 分析数据: {len(flattened_data)} 项")
        print(f"   💡 生成建议: {analysis_result['suggestion_count']} 个")
        print(f"   📈 成功可视化: {visualization_result['successful_visualizations']} 个")
        
        return final_result


def save_enhancement_results(results: Dict[str, Any], output_path: str):
    """保存增强结果到文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"📁 增强结果已保存到: {output_path}")
