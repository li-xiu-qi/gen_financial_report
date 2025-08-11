"""
基础可视化数据处理器
提供公共的可视化处理功能，支持公司和行业两种不同的使用场景
"""

import json
import os
import time
import re
import asyncio
import multiprocessing
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor
from financial_report.utils.chat import chat_no_tool
from financial_report.utils.calculate_tokens import OpenAITokenCalculator
from financial_report.utils.fast_token_splitter import FastTokenSplitter
from financial_report.llm_calls.text2infographic_html import text2infographic_html
from financial_report.utils.html2png import html2png_async


def _process_png_task(task_data):
    """
    多进程PNG生成任务的工作函数
    这个函数在独立的进程中运行，避免GIL限制
    
    Args:
        task_data: 包含HTML路径、PNG路径等信息的字典
        
    Returns:
        处理结果字典
    """
    import asyncio
    import os
    import time
    from financial_report.utils.html2png import html2png
    
    try:
        html_path = task_data["html_path"]
        png_path = task_data["png_path"]
        chart_title = task_data["chart_title"]
        
        # 使用同步版本的html2png（因为这是在独立进程中）
        result_png_path = html2png(html_path, png_path, is_file_path=True)
        
        # 验证PNG文件是否生成成功
        if os.path.exists(result_png_path):
            file_size = os.path.getsize(result_png_path)
            return {
                "success": True,
                "png_path": result_png_path,
                "file_size": file_size,
                "chart_title": chart_title,
                "process_id": os.getpid()
            }
        else:
            return {
                "success": False,
                "error": "PNG文件未生成",
                "chart_title": chart_title,
                "process_id": os.getpid()
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "chart_title": task_data.get("chart_title", "Unknown"),
            "process_id": os.getpid()
        }


class BaseVisualizationProcessor(ABC):
    """基础可视化数据处理器抽象类"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        visualization_output_dir: Optional[str] = None,
        assets_output_dir: Optional[str] = None
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        
        # 初始化token计算器和分块器
        self.token_calculator = OpenAITokenCalculator()
        self.text_splitter = None  # 延迟初始化
        
        # 保存路径配置供子类使用
        self._base_visualization_output_dir = visualization_output_dir
        self._base_assets_output_dir = assets_output_dir
        
        # 计算可用的CPU核心数（总核心数 - 2个保留给用户）
        total_cores = multiprocessing.cpu_count()
        self._png_worker_cores = max(1, total_cores - 2)  # 至少保留1个核心用于PNG生成
        print(f"🔧 系统总核心数: {total_cores}, PNG生成将使用: {self._png_worker_cores} 个核心")
        
        # 进程池（延迟初始化，在需要时创建）
        self._png_process_pool = None
    
    def _get_png_process_pool(self):
        """获取PNG生成进程池（延迟初始化）"""
        if self._png_process_pool is None:
            self._png_process_pool = ProcessPoolExecutor(
                max_workers=self._png_worker_cores,
                mp_context=multiprocessing.get_context('spawn')  # Windows兼容性
            )
            print(f"🚀 PNG生成进程池已创建，使用 {self._png_worker_cores} 个进程")
        return self._png_process_pool
    
    def _close_png_process_pool(self):
        """关闭PNG生成进程池"""
        if self._png_process_pool is not None:
            self._png_process_pool.shutdown(wait=True)
            self._png_process_pool = None
            print(f"🔒 PNG生成进程池已关闭")
    
    def __del__(self):
        """析构函数，确保进程池被正确关闭"""
        try:
            self._close_png_process_pool()
        except:
            pass
    
    @abstractmethod
    def get_target_name_field(self) -> str:
        """获取目标名称字段（公司用company_name，行业用industry_name）"""
        pass
    
    @abstractmethod
    def get_visualization_output_dir(self) -> str:
        """获取可视化输出目录（HTML文件，需要与js同级）"""
        pass
    
    @abstractmethod
    def get_assets_output_dir(self) -> str:
        """获取资产文件（PNG和JSON）输出目录"""
        pass
    
    @abstractmethod
    def get_incremental_enhancement_system_prompt(self) -> str:
        """获取增量增强的系统提示词"""
        pass
    
    @abstractmethod
    def get_incremental_enhancement_user_prompt(
        self,
        suggestion: Dict[str, Any],
        data_content: str,
        current_segment: int,
        total_segments: int,
        previous_enhancement: Optional[str] = None
    ) -> str:
        """获取增量增强的用户提示词"""
        pass
    
    def get_data_by_ids(
        self, 
        data_ids: List[str], 
        all_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根据ID列表获取对应的数据项
        
        Args:
            data_ids: 数据ID列表
            all_data: 所有数据的列表
            
        Returns:
            匹配的数据项列表
        """
        id_to_data = {str(item["id"]): item for item in all_data}
        return [id_to_data[data_id] for data_id in data_ids if data_id in id_to_data]
    
    def set_visualization_output_dir(self, output_dir: str) -> None:
        """设置可视化输出目录（子类可覆盖此方法来支持动态配置）"""
        self._base_visualization_output_dir = output_dir
        if hasattr(self, '_visualization_output_dir'):
            self._visualization_output_dir = output_dir
        else:
            raise NotImplementedError("子类需要实现路径配置支持")
    
    def set_assets_output_dir(self, assets_dir: str) -> None:
        """设置资产输出目录（子类可覆盖此方法来支持动态配置）"""
        self._base_assets_output_dir = assets_dir
        if hasattr(self, '_assets_output_dir'):
            self._assets_output_dir = assets_dir
        else:
            raise NotImplementedError("子类需要实现路径配置支持")
    
    def get_current_visualization_output_dir(self) -> Optional[str]:
        """获取当前基类中配置的可视化输出目录"""
        return self._base_visualization_output_dir
    
    def get_current_assets_output_dir(self) -> Optional[str]:
        """获取当前基类中配置的资产输出目录"""
        return self._base_assets_output_dir
    
    @abstractmethod
    def get_chart_query_context(
        self,
        chart_title: str,
        chart_type: str,
        reason: str,
        target_name: str,
        section: str,
        report_value: str,
        data_content: str
    ) -> str:
        """构建图表生成的查询上下文"""
        pass
    
    def process_visualization_results(
        self,
        visual_enhancement_file: str,
        all_flattened_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int = 100000,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        处理可视化增强结果，为每个建议生成图表
        
        Args:
            visual_enhancement_file: 可视化增强结果文件路径
            all_flattened_data: 所有的扁平化数据
            target_name: 目标名称（公司名称或行业名称）
            max_context_tokens: 最大上下文token数
            
        Returns:
            包含生成图表的处理结果
        """
        print(f"🎨 开始处理可视化增强结果...")
        
        # 1. 加载可视化增强结果
        if not os.path.exists(visual_enhancement_file):
            print(f"❌ 可视化增强文件不存在: {visual_enhancement_file}")
            return {"error": "visual_enhancement_file_not_found"}
        
        with open(visual_enhancement_file, "r", encoding="utf-8") as f:
            enhancement_results = json.load(f)
        
        return self.process_visualization_data(
            enhancement_results=enhancement_results,
            all_flattened_data=all_flattened_data,
            target_name=target_name,
            max_context_tokens=max_context_tokens,
            max_concurrent=max_concurrent
        )
    
    def process_visualization_data(
        self,
        enhancement_results: Dict[str, Any],
        all_flattened_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int = 100000,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        直接处理可视化增强结果数据，为每个建议生成图表
        
        Args:
            enhancement_results: 可视化增强结果数据
            all_flattened_data: 所有的扁平化数据
            target_name: 目标名称（公司名称或行业名称）
            max_context_tokens: 最大上下文token数
            max_concurrent: 最大并发数
            
        Returns:
            包含生成图表的处理结果
        """
        print(f"🎨 开始处理可视化增强数据...")
        
        # 2. 提取可视化建议
        analysis_phase = enhancement_results.get("analysis_phase", {})
        visualization_suggestions = analysis_phase.get("visualization_suggestions", [])
        
        print(f"📊 找到 {len(visualization_suggestions)} 个可视化建议")
        
        if not visualization_suggestions:
            print("⚠️  没有找到可视化建议")
            return {"error": "no_visualization_suggestions"}
        
        # 3. 处理所有建议（使用异步并发）
        print(f"🎯 将处理全部 {len(visualization_suggestions)} 个建议")
        
        # 使用异步并发处理
        processed_suggestions = asyncio.run(
            self._process_suggestions_async(visualization_suggestions, all_flattened_data, target_name, max_context_tokens, max_concurrent)
        )
        
        # 4. 批量生成PNG（使用多进程并发）
        print(f"🖼️ 开始批量生成PNG文件...")
        processed_suggestions = asyncio.run(self._batch_generate_pngs(processed_suggestions))
        
        # 5. 生成统一的可视化资产文件
        self._save_unified_visualization_assets(processed_suggestions, target_name)
        
        # 6. 关闭进程池以释放资源
        self._close_png_process_pool()
        
        # 7. 汇总结果
        successful_count = sum(1 for s in processed_suggestions if s.get("success", False))
        failed_count = len(processed_suggestions) - successful_count
        
        result = {
            "processing_summary": {
                "total_suggestions": len(visualization_suggestions),
                "processed_count": len(processed_suggestions),
                "successful_count": successful_count,
                "failed_count": failed_count,
                self.get_target_name_field(): target_name,
                "processing_time": enhancement_results.get("analysis_phase", {}).get("analysis_time", "unknown")
            },
            "processed_suggestions": processed_suggestions,
            "original_enhancement_results": enhancement_results
        }
        
        print(f"\n📊 处理完成!")
        print(f"   📈 总建议数: {len(visualization_suggestions)}")
        print(f"   ✅ 成功处理: {successful_count}")
        print(f"   ❌ 处理失败: {failed_count}")
        
        return result
    
    async def _process_suggestions_async(
        self,
        visualization_suggestions: List[Dict[str, Any]],
        all_flattened_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int,
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """异步并发处理可视化建议"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        # 初始化进度计数器
        progress_counter = {
            "current": 0,
            "total": len(visualization_suggestions),
            "completed": 0,
            "failed": 0,
        }
        
        # 创建异步任务
        tasks = []
        for i, suggestion in enumerate(visualization_suggestions):
            task = self._process_single_suggestion_async(
                suggestion=suggestion,
                index=i,
                all_data=all_flattened_data,
                target_name=target_name,
                max_context_tokens=max_context_tokens,
                semaphore=semaphore,
                progress_counter=progress_counter
            )
            tasks.append(task)
        
        # 并发执行所有任务
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            # 将异常转换为错误结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        "success": False,
                        "error": str(result),
                        "original_suggestion": visualization_suggestions[i]
                    })
                else:
                    processed_results.append(result)
            return processed_results
        else:
            return []
    
    async def _batch_generate_pngs(self, processed_suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成PNG文件，使用多进程并发处理
        
        Args:
            processed_suggestions: 处理过的建议列表
            
        Returns:
            更新后的建议列表（包含PNG信息）
        """
        # 筛选需要生成PNG的成功建议
        successful_suggestions = [s for s in processed_suggestions if s.get("success", False) and s.get("chart_html")]
        
        if not successful_suggestions:
            print("   ⚠️ 没有成功的图表需要生成PNG")
            return processed_suggestions
        
        print(f"   📊 准备为 {len(successful_suggestions)} 个图表生成PNG")
        
        # 准备PNG生成任务
        png_tasks = []
        temp_html_files = []
        
        for suggestion in successful_suggestions:
            try:
                chart_title = suggestion.get("chart_title", "Unknown")
                chart_html = suggestion.get("chart_html", "")
                timestamp = suggestion.get("timestamp", int(time.time() * 1000))
                
                # 创建目录
                assets_dir = self.get_assets_output_dir()
                html_output_dir = self.get_visualization_output_dir()
                os.makedirs(assets_dir, exist_ok=True)
                os.makedirs(html_output_dir, exist_ok=True)
                
                # 生成文件名
                safe_title = "".join(c for c in chart_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title.replace(' ', '_')[:50]
                
                # HTML文件路径（临时）
                html_filename = f"{safe_title}_{timestamp}.html"
                html_path = os.path.join(html_output_dir, html_filename)
                
                # PNG文件路径
                png_filename = f"{safe_title}_{timestamp}.png"
                png_path = os.path.join(assets_dir, png_filename)
                
                # 写入HTML文件
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(chart_html)
                
                # 添加到任务列表
                png_tasks.append({
                    "html_path": html_path,
                    "png_path": png_path,
                    "chart_title": chart_title,
                    "suggestion_index": processed_suggestions.index(suggestion)
                })
                temp_html_files.append(html_path)
                
                print(f"   📄 临时HTML已保存: {chart_title}")
                
            except Exception as e:
                print(f"   ❌ 准备PNG任务失败 {chart_title}: {e}")
                continue
        
        if not png_tasks:
            print("   ⚠️ 没有有效的PNG生成任务")
            return processed_suggestions
        
        print(f"   🚀 开始多进程PNG生成，任务数: {len(png_tasks)}")
        
        # 使用进程池批量处理PNG生成
        try:
            loop = asyncio.get_running_loop()
            executor = self._get_png_process_pool()
            
            # 提交所有任务到进程池
            png_futures = []
            for task in png_tasks:
                future = loop.run_in_executor(executor, _process_png_task, task)
                png_futures.append(future)
            
            # 等待所有PNG生成完成
            start_time = time.time()
            png_results = await asyncio.gather(*png_futures, return_exceptions=True)
            end_time = time.time()
            
            print(f"   ⏱️ PNG生成完成，耗时: {end_time - start_time:.2f}秒")
            
            # 处理PNG生成结果
            successful_png_count = 0
            failed_png_count = 0
            
            for i, (task, result) in enumerate(zip(png_tasks, png_results)):
                suggestion_index = task["suggestion_index"]
                
                if isinstance(result, Exception):
                    print(f"   ❌ PNG生成异常 {task['chart_title']}: {result}")
                    processed_suggestions[suggestion_index].update({
                        "has_png": False,
                        "chart_png_path": None,
                        "png_error": str(result)
                    })
                    failed_png_count += 1
                elif result.get("success", False):
                    print(f"   ✅ PNG生成成功 {task['chart_title']} (进程{result.get('process_id', 'Unknown')})")
                    processed_suggestions[suggestion_index].update({
                        "has_png": True,
                        "chart_png_path": result["png_path"],
                        "png_file_size": result.get("file_size", 0)
                    })
                    successful_png_count += 1
                else:
                    print(f"   ❌ PNG生成失败 {task['chart_title']}: {result.get('error', 'Unknown')}")
                    processed_suggestions[suggestion_index].update({
                        "has_png": False,
                        "chart_png_path": None,
                        "png_error": result.get("error", "Unknown")
                    })
                    failed_png_count += 1
            
            print(f"   📊 PNG生成汇总: 成功 {successful_png_count}, 失败 {failed_png_count}")
            
        except Exception as e:
            print(f"   ❌ 批量PNG生成异常: {e}")
        
        finally:
            # 清理临时HTML文件
            print(f"   🗑️ 清理 {len(temp_html_files)} 个临时HTML文件...")
            for html_file in temp_html_files:
                try:
                    if os.path.exists(html_file):
                        os.remove(html_file)
                except Exception as e:
                    print(f"   ⚠️ 删除临时文件失败 {html_file}: {e}")
        
        return processed_suggestions
    
    async def _process_single_suggestion_async(
        self,
        suggestion: Dict[str, Any], 
        index: int,
        all_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int,
        semaphore: asyncio.Semaphore,
        progress_counter: dict
    ) -> Dict[str, Any]:
        """异步处理单个可视化建议"""
        async with semaphore:
            chart_title = suggestion.get("chart_title", "Unknown")
            
            progress_counter["current"] += 1
            print(f"\n📈 [{progress_counter['current']}/{progress_counter['total']}] 处理建议: {chart_title}")
            
            try:
                # 调用异步处理方法
                result = await self._process_single_suggestion_async_impl(
                    suggestion=suggestion,
                    all_data=all_data,
                    target_name=target_name,
                    max_context_tokens=max_context_tokens
                )
                
                # 显示处理结果
                if result.get("success", False):
                    progress_counter["completed"] += 1
                    print(f"   ✅ 图表生成成功: {chart_title}")
                else:
                    progress_counter["failed"] += 1
                    print(f"   ❌ 图表生成失败: {result.get('error', 'Unknown')}")
                
                return result
                    
            except Exception as e:
                progress_counter["failed"] += 1
                print(f"   ❌ 处理异常: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "original_suggestion": suggestion
                }
    
    async def _process_single_suggestion_async_impl(
        self,
        suggestion: Dict[str, Any],
        all_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int
    ) -> Dict[str, Any]:
        """
        异步处理单个可视化建议，生成对应的图表
        
        Args:
            suggestion: 单个可视化建议
            all_data: 所有数据
            target_name: 目标名称
            max_context_tokens: 最大上下文token数
            
        Returns:
            处理结果，包含生成的图表HTML/PNG
        """
        chart_title = suggestion.get("chart_title", "Unknown")
        chart_type = suggestion.get("visualization_type", "unknown")
        data_ids = suggestion.get("data_ids", [])
        reason = suggestion.get("reason", "")
        priority = suggestion.get("priority", "medium")
        section = suggestion.get("section", "未分类")
        report_value = suggestion.get("report_value", "数据展示")
        
        if not data_ids:
            return {
                "success": False,
                "error": "no_data_ids",
                "original_suggestion": suggestion
            }
        
        print(f"   📋 收集图表数据，数据IDs: {data_ids}")
        
        # 获取原始数据
        raw_data = self.get_data_by_ids(data_ids, all_data)
        if not raw_data:
            return {
                "success": False,
                "error": "no_raw_data_found",
                "original_suggestion": suggestion
            }
        
        print(f"   📊 获取到 {len(raw_data)} 个原始数据项")
        
        # 生成图表
        try:
            chart_html = self._generate_chart(
                chart_title=chart_title,
                chart_type=chart_type,
                reason=reason,
                raw_data=raw_data,
                target_name=target_name,
                max_context_tokens=max_context_tokens,
                section=section,
                report_value=report_value
            )
            
            if not chart_html:
                return {
                    "success": False,
                    "error": "chart_generation_failed",
                    "original_suggestion": suggestion
                }
            
            # 创建参考文献
            references = []
            id_to_ref_num = {}
            
            for i, item in enumerate(raw_data, 1):
                actual_title = item.get("title", "") or f"{item.get(self.get_target_name_field(), '')} 数据"
                ref_info = {
                    "ref_num": i,
                    "data_id": item["id"],
                    "title": actual_title,
                    "url": item.get("url", ""),
                    self.get_target_name_field(): item.get(self.get_target_name_field(), ""),
                    "company_code": item.get("company_code", "")
                }
                references.append(ref_info)
                id_to_ref_num[item["id"]] = i
            
            # 生成图片描述（基于HTML内容）
            print(f"    生成图片描述...")
            image_description = self._generate_image_description(
                chart_html=chart_html,
                chart_title=chart_title,
                chart_type=chart_type,
                reason=reason,
                target_name=target_name,
                section=section,
                report_value=report_value
            )
            
            return {
                "success": True,
                "chart_title": chart_title,
                "visualization_type": chart_type,
                "reason": reason,
                "priority": priority,
                "section": section,
                "report_value": report_value,
                "data_ids": data_ids,
                "chart_html": chart_html,
                "chart_png_path": None,  # 将在批量处理中设置
                "image_description": image_description,
                "has_png": False,  # 将在批量处理中更新
                "raw_data_count": len(raw_data),
                "references": references,
                "id_to_ref_num": id_to_ref_num,
                "processing_method": "text2infographic_multiprocess",
                "original_suggestion": suggestion,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": int(time.time() * 1000)
            }
            
        except Exception as e:
            print(f"   ❌ 图表生成失败: {e}")
            return {
                "success": False,
                "error": f"generation_exception: {str(e)}",
                "original_suggestion": suggestion
            }
    
    def _generate_chart(
        self,
        chart_title: str,
        chart_type: str,
        reason: str,
        raw_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int,
        section: str = "未分类",
        report_value: str = "数据展示"
    ) -> Optional[str]:
        """
        生成图表HTML，支持大文本分块处理
        
        Args:
            chart_title: 图表标题
            chart_type: 图表类型
            reason: 可视化原因
            raw_data: 原始数据
            target_name: 目标名称
            max_context_tokens: 最大上下文token数
            section: 章节
            report_value: 报告价值
            
        Returns:
            生成的图表HTML代码，如果失败则返回None
        """
        print(f"   🎨 开始生成图表...")
        
        # 计算原文内容的总token数
        total_tokens = self._calculate_raw_content_tokens(raw_data)
        print(f"   📊 原文总token数: {total_tokens:,}")
        
        # 为生成留出足够的token空间（提示词 + 响应）
        generation_overhead = 4000  # 预留给提示词和响应的token
        available_tokens = max_context_tokens - generation_overhead
        
        if total_tokens <= available_tokens:
            # 数据量适中，直接生成
            return self._generate_from_complete_data(
                chart_title=chart_title,
                chart_type=chart_type,
                reason=reason,
                raw_data=raw_data,
                target_name=target_name,
                section=section,
                report_value=report_value
            )
        else:
            # 数据量过大，使用分块增量处理
            print(f"   📦 数据量过大，启用分块处理...")
            return self._generate_from_chunked_data(
                chart_title=chart_title,
                chart_type=chart_type,
                reason=reason,
                raw_data=raw_data,
                target_name=target_name,
                max_chunk_tokens=available_tokens,
                section=section,
                report_value=report_value
            )
    
    def _calculate_raw_content_tokens(self, raw_data: List[Dict[str, Any]]) -> int:
        """计算原文内容的总token数，使用完整内容而不是总结"""
        total_content = ""
        for item in raw_data:
            # 使用完整内容而不是summary，避免信息损耗
            content = item.get("content", "") or item.get("md", "")
            if content:
                total_content += f"\n\n【数据{item['id']}】{item.get('title', '')}\n{content}"
        
        return self.token_calculator.count_tokens(total_content)
    
    def _generate_from_complete_data(
        self,
        chart_title: str,
        chart_type: str,
        reason: str,
        raw_data: List[Dict[str, Any]],
        target_name: str,
        section: str = "未分类",
        report_value: str = "数据展示"
    ) -> Optional[str]:
        """从完整数据中一次性生成图表"""
        # 构建完整的数据内容，使用完整内容而不是总结
        data_content = ""
        for item in raw_data:
            # 优先使用content，其次使用md，避免使用summary以减少信息损耗
            content = item.get("content", "") or item.get("md", "")
            if content:
                data_content += f"\n\n【数据{item['id']}】{item.get('title', '')}\n{content}"
        
        # 构建生成请求
        chart_query = self.get_chart_query_context(
            chart_title=chart_title,
            chart_type=chart_type,
            reason=reason,
            target_name=target_name,
            section=section,
            report_value=report_value,
            data_content=data_content
        )

        try:
            return text2infographic_html(
                query=chart_query,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.2,
                max_tokens=4096
            )
        except Exception as e:
            print(f"   ❌ 图表生成失败: {e}")
            return None
    
    def _generate_from_chunked_data(
        self,
        chart_title: str,
        chart_type: str,
        reason: str,
        raw_data: List[Dict[str, Any]],
        target_name: str,
        max_chunk_tokens: int,
        section: str = "未分类",
        report_value: str = "数据展示"
    ) -> Optional[str]:
        """使用增量增强方式生成图表"""
        print(f"   🔄 开始增量增强处理...")
        
        # 初始化分块器
        if self.text_splitter is None:
            self.text_splitter = FastTokenSplitter(
                token_calculator=self.token_calculator,
                chunk_size=max_chunk_tokens,
                chunk_overlap=200
            )
        
        # 收集所有原文内容并分块
        all_text_content = ""
        for item in raw_data:
            # 使用完整内容而不是summary
            content = item.get("content", "") or item.get("md", "")
            if content:
                all_text_content += f"\n\n【数据{item['id']}】{item.get('title', '')}\n{content}"
        
        # 分块处理
        chunks = self.text_splitter.split_text(all_text_content)
        print(f"   📦 数据分为 {len(chunks)} 个块，开始增量增强...")
        
        # 增量增强处理
        enhanced_content = None
        for i, chunk in enumerate(chunks):
            print(f"   🔄 处理第 {i+1}/{len(chunks)} 个数据块...")
            
            # 构建初始建议
            suggestion = {
                "chart_title": chart_title,
                "chart_type": chart_type,
                "reason": reason,
                "section": section,
                "report_value": report_value
            }
            
            try:
                # 调用增量增强
                chunk_enhancement = self._perform_incremental_enhancement(
                    suggestion=suggestion,
                    data_content=chunk,
                    current_segment=i + 1,
                    total_segments=len(chunks),
                    previous_enhancement=enhanced_content,
                    target_name=target_name
                )
                
                if chunk_enhancement:
                    enhanced_content = chunk_enhancement
                    print(f"   ✅ 第 {i+1} 块增强完成")
                else:
                    print(f"   ⚠️ 第 {i+1} 块增强失败，保持上一版本")
                    
            except Exception as e:
                print(f"   ❌ 第 {i+1} 块增强异常: {e}")
                continue
        
        # 基于最终增强结果生成图表
        if enhanced_content:
            print(f"   🎨 基于增强内容生成最终图表...")
            chart_query = self.get_chart_query_context(
                chart_title=chart_title,
                chart_type=chart_type,
                reason=reason,
                target_name=target_name,
                section=section,
                report_value=report_value,
                data_content=enhanced_content
            )

            try:
                return text2infographic_html(
                    query=chart_query,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    temperature=0.1,
                    max_tokens=4096
                )
            except Exception as e:
                print(f"   ❌ 图表生成失败: {e}")
                return None
        else:
            print(f"   ❌ 增量增强失败，无法生成图表")
            return None
    
    def _perform_incremental_enhancement(
        self,
        suggestion: Dict[str, Any],
        data_content: str,
        current_segment: int,
        total_segments: int,
        previous_enhancement: Optional[str],
        target_name: str
    ) -> Optional[str]:
        """
        对单个数据块进行增量增强处理
        
        Args:
            suggestion: 图表建议
            data_content: 当前数据块内容
            current_segment: 当前段数
            total_segments: 总段数
            previous_enhancement: 之前的增强结果
            target_name: 目标名称
            
        Returns:
            增强后的内容，如果失败返回None
        """
        try:
            # 获取增量增强的提示词
            system_prompt = self.get_incremental_enhancement_system_prompt()
            user_prompt = self.get_incremental_enhancement_user_prompt(
                suggestion=suggestion,
                data_content=data_content,
                current_segment=current_segment,
                total_segments=total_segments,
                previous_enhancement=previous_enhancement
            )
            
            # 调用AI进行增量增强
            response = chat_no_tool(
                user_content=user_prompt,
                system_content=system_prompt,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,
                max_tokens=8192
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            print(f"        ❌ 增量增强异常: {e}")
            return None
    
    def _extract_key_data_summary(self, raw_data: List[Dict[str, Any]], target_name: str) -> str:
        """提取关键数据摘要，特别关注数字和时间信息"""
        key_info = []
        
        for item in raw_data:
            content = item.get("content", "") or item.get("md", "")
            title = item.get("title", "")
            
            # 提取年份
            years = re.findall(r'20\d{2}', content)
            if years:
                unique_years = sorted(list(set(years)))
                key_info.append(f"【{title}】包含年份: {', '.join(unique_years[:5])}")
            
            # 提取大额数字（可能是财务数据）
            large_numbers = re.findall(r'[\d,]+\.?\d*(?:万|亿|千万|billion|million)?', content)
            if large_numbers:
                key_numbers = [num for num in large_numbers[:10] if any(char.isdigit() for char in num)]
                if key_numbers:
                    key_info.append(f"【{title}】关键数值: {', '.join(key_numbers[:5])}")
        
        return '\n'.join(key_info) if key_info else f"正在分析{target_name}的相关数据..."
    
    def _generate_image_description(
        self, 
        chart_html: str, 
        chart_title: str, 
        chart_type: str, 
        reason: str, 
        target_name: str, 
        section: str = "未分类", 
        report_value: str = "数据展示"
    ) -> str:
        """基于HTML图表生成图片描述"""
        description_prompt = f"""请基于以下HTML图表代码，生成一段详细的图片描述文本。

图表基本信息：
- 标题：{chart_title}
- 类型：{chart_type}
- 目标：{target_name}
- 研报章节：{section}
- 分析价值：{report_value}
- 分析目的：{reason}

HTML代码：
{chart_html}

请生成一段200-300字的专业图片描述，包含以下内容：
1. 图表的基本信息（标题、类型、主题目标、所属研报章节）
2. 图表展示的主要数据内容和趋势
3. 数据的时间范围或关键数值
4. 图表的视觉特征（颜色、布局等）
5. 这个图表在{section}章节中的分析价值和意义

要求：
- 描述准确、客观，适合用于研报或无障碍阅读
- 语言专业简洁，符合金融研报标准
- 重点突出数据洞察和分析价值，而非技术细节"""

        try:
            description = chat_no_tool(
                user_content=description_prompt,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,
                max_tokens=500
            )
            return description.strip() if description else f"基于{target_name}的{chart_title}图表"
        except Exception as e:
            print(f"   ⚠️  图片描述生成失败: {e}")
            return f"这是一个关于{target_name}的{chart_title}图表，展示了{chart_type}类型的数据可视化。{reason}"
    
    def _save_image_asset(
        self, 
        chart_html: str, 
        chart_png_path: str, 
        chart_html_path: str,
        image_description: str, 
        chart_title: str, 
        chart_type: str, 
        target_name: str, 
        data_ids: list, 
        section: str = "未分类", 
        report_value: str = "数据展示"
    ) -> str:
        """
        保存图片资产信息到JSON文件（已弃用，现在使用统一的资产文件）
        保留此方法仅为向后兼容
        """
        print(f"   ⚠️  _save_image_asset方法已弃用，现在使用统一的可视化资产文件")
        return ""
    
    def _save_unified_visualization_assets(
        self, 
        processed_suggestions: List[Dict[str, Any]], 
        target_name: str
    ) -> str:
        """
        保存统一的可视化资产文件，包含所有成功生成的图表信息
        
        Args:
            processed_suggestions: 所有处理过的可视化建议
            target_name: 目标名称
            
        Returns:
            保存的统一资产文件路径
        """
        try:
            # 获取资产输出目录的父目录（与其他JSON文件同级）
            assets_dir = self.get_assets_output_dir()
            parent_dir = os.path.dirname(assets_dir)
            
            # 筛选成功的建议
            successful_suggestions = [s for s in processed_suggestions if s.get("success", False)]
            
            # 构建统一的资产数据结构
            unified_assets = {
                "metadata": {
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "target_type": self.get_target_name_field().replace("_name", ""),  # company 或 industry
                    "target_name": target_name,
                    "total_charts": len(successful_suggestions),
                    "failed_charts": len(processed_suggestions) - len(successful_suggestions),
                    "asset_version": "1.0"
                },
                "charts": []
            }
            
            # 为每个成功的图表创建资产条目
            for suggestion in successful_suggestions:
                chart_asset = {
                    "asset_id": f"chart_{suggestion.get('timestamp', int(time.time() * 1000))}",
                    "chart_title": suggestion.get("chart_title", ""),
                    "chart_type": suggestion.get("visualization_type", ""),
                    "section": suggestion.get("section", "未分类"),
                    "report_value": suggestion.get("report_value", "数据展示"),
                    "priority": suggestion.get("priority", "medium"),
                    "reason": suggestion.get("reason", ""),
                    "image_description": suggestion.get("image_description", ""),
                    "png_path": suggestion.get("chart_png_path"),
                    "has_png": suggestion.get("has_png", False),
                    "data_source_ids": suggestion.get("data_ids", []),
                    "raw_data_count": suggestion.get("raw_data_count", 0),
                    "references": suggestion.get("references", []),
                    "created_at": suggestion.get("created_at", ""),
                    "processing_method": suggestion.get("processing_method", ""),
                    "file_size": 0
                }
                
                # 计算PNG文件大小
                if chart_asset["png_path"] and os.path.exists(chart_asset["png_path"]):
                    chart_asset["file_size"] = os.path.getsize(chart_asset["png_path"])
                
                unified_assets["charts"].append(chart_asset)
            
            # 按章节和优先级排序
            section_priority = {"核心财务数据": 1, "业务发展": 2, "市场表现": 3, "风险评估": 4, "未分类": 5}
            priority_order = {"high": 1, "medium": 2, "low": 3}
            
            unified_assets["charts"].sort(key=lambda x: (
                section_priority.get(x.get("section", "未分类"), 5),
                priority_order.get(x.get("priority", "medium"), 2),
                x.get("chart_title", "")
            ))
            
            # 保存统一资产文件
            asset_filename = f"visualization_assets.json"
            asset_path = os.path.join(parent_dir, asset_filename)
            
            with open(asset_path, "w", encoding="utf-8") as f:
                json.dump(unified_assets, f, ensure_ascii=False, indent=2)
            
            print(f"📄 统一可视化资产文件已保存: {asset_path}")
            print(f"   📊 包含 {len(successful_suggestions)} 个成功图表")
            print(f"   📁 资产文件大小: {os.path.getsize(asset_path)} 字节")
            
            # 统计各章节的图表数量
            section_stats = {}
            for chart in unified_assets["charts"]:
                section = chart.get("section", "未分类")
                section_stats[section] = section_stats.get(section, 0) + 1
            
            print(f"   📋 章节分布: {dict(section_stats)}")
            
            return asset_path
            
        except Exception as e:
            print(f"   ❌ 统一资产文件保存失败: {e}")
            return ""
    
    def _process_single_suggestion(
        self,
        suggestion: Dict[str, Any],
        all_data: List[Dict[str, Any]],
        target_name: str,
        max_context_tokens: int
    ) -> Dict[str, Any]:
        """
        同步版本：处理单个可视化建议，生成对应的图表
        为了向后兼容而保留，建议在异步环境中使用 _process_single_suggestion_async_impl
        
        Args:
            suggestion: 单个可视化建议
            all_data: 所有数据
            target_name: 目标名称
            max_context_tokens: 最大上下文token数
            
        Returns:
            处理结果，包含生成的图表HTML/PNG
        """
        chart_title = suggestion.get("chart_title", "Unknown")
        chart_type = suggestion.get("visualization_type", "unknown")
        data_ids = suggestion.get("data_ids", [])
        reason = suggestion.get("reason", "")
        priority = suggestion.get("priority", "medium")
        section = suggestion.get("section", "未分类")
        report_value = suggestion.get("report_value", "数据展示")
        
        if not data_ids:
            return {
                "success": False,
                "error": "no_data_ids",
                "original_suggestion": suggestion
            }
        
        print(f"   📋 收集图表数据，数据IDs: {data_ids}")
        
        # 获取原始数据  
        raw_data = self.get_data_by_ids(data_ids, all_data)
        if not raw_data:
            return {
                "success": False,
                "error": "no_raw_data_found",
                "original_suggestion": suggestion
            }
        
        print(f"   📊 获取到 {len(raw_data)} 个原始数据项")
        
        # 生成图表
        try:
            chart_html = self._generate_chart(
                chart_title=chart_title,
                chart_type=chart_type,
                reason=reason,
                raw_data=raw_data,
                target_name=target_name,
                max_context_tokens=max_context_tokens,
                section=section,
                report_value=report_value
            )
            
            if not chart_html:
                return {
                    "success": False,
                    "error": "chart_generation_failed",
                    "original_suggestion": suggestion
                }
            
            # 创建参考文献
            references = []
            id_to_ref_num = {}
            
            for i, item in enumerate(raw_data, 1):
                actual_title = item.get("title", "") or f"{item.get(self.get_target_name_field(), '')} 数据"
                ref_info = {
                    "ref_num": i,
                    "data_id": item["id"],
                    "title": actual_title,
                    "url": item.get("url", ""),
                    self.get_target_name_field(): item.get(self.get_target_name_field(), ""),
                    "company_code": item.get("company_code", "")
                }
                references.append(ref_info)
                id_to_ref_num[item["id"]] = i
            
            # PNG生成部分 - 同步版本不执行，避免事件循环冲突
            print(f"   ⚠️  同步版本跳过PNG生成，请使用异步版本以生成PNG")
            has_png = False
            png_path = None
            image_description = f"使用同步方法生成的{chart_title}图表（未生成PNG）"
            asset_json_path = ""
            
            return {
                "success": True,
                "chart_title": chart_title,
                "visualization_type": chart_type,
                "reason": reason,
                "priority": priority,
                "section": section,
                "report_value": report_value,
                "data_ids": data_ids,
                "chart_html": chart_html,
                "chart_png_path": png_path,
                "image_description": image_description,
                "has_png": has_png,
                "raw_data_count": len(raw_data),
                "references": references,
                "id_to_ref_num": id_to_ref_num,
                "processing_method": "text2infographic_sync",
                "original_suggestion": suggestion,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "timestamp": int(time.time() * 1000)
            }
            
        except Exception as e:
            print(f"   ❌ 图表生成失败: {e}")
            return {
                "success": False,
                "error": f"generation_exception: {str(e)}",
                "original_suggestion": suggestion
            }
