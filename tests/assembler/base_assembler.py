"""
基础报告内容组装器类
"""

import re
import json
import os
import time
import uuid
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor

from financial_report.llm_calls.text2infographic_html import text2infographic_html
from financial_report.utils.html2png import html2png

from .templates import (
    VISUALIZATION_ENHANCEMENT_PROMPT_TEMPLATE,
    CHART_RESOURCE_TEMPLATE,
    CHART_USAGE_REQUIREMENTS,
    TEXT_VISUALIZATION_QUERY_TEMPLATE
)
from .utils import PathUtils, ChartValidator, HtmlContentReader, TitleValidator


class BaseReportContentAssembler(ABC):
    """基础报告内容组装器 - 提供通用的内容组装接口"""
    
    def __init__(self):
        """初始化内容组装器"""
        # 全局参考文献管理
        self.global_references = []  # 存储所有参考文献
        self.global_id_to_ref = {}   # 数据ID到参考文献序号的映射
    
    def get_default_section_mapping(self) -> Dict[str, str]:
        """
        获取默认的章节映射关系 - 可被子类重写
        
        Returns:
            章节映射字典
        """
        return {
            "一": "一、投资摘要与核心观点",
            "二": "二、竞争格局与对比分析", 
            "三": "三、基本面分析",
            "四": "四、财务状况分析",
            "五": "五、估值分析与投资建议"
        }
    
    async def process_sections_batch_async(
        self,
        sections_data: List[Dict[str, Any]],
        llm_call_function_async,
        visualization_resources: Dict[str, List[Dict[str, Any]]] = None,
        target_name: str = None,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        enable_text_visualization: bool = True,
        output_dir: str = None,
        max_concurrent: int = 3
    ) -> List[Dict[str, Any]]:
        """
        异步批量处理章节，支持并发生成
        
        Args:
            sections_data: 章节数据列表，每个包含 section_title, content, allocated_charts 等
            llm_call_function_async: 异步LLM调用函数
            visualization_resources: 可视化资源字典
            target_name: 目标名称
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            enable_text_visualization: 是否启用文本可视化
            output_dir: 输出目录
            max_concurrent: 最大并发数
            
        Returns:
            处理后的章节列表
        """
        print(f"🚀 开始异步批量处理 {len(sections_data)} 个章节，最大并发数：{max_concurrent}")
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_section(section_data: Dict[str, Any]) -> Dict[str, Any]:
            """处理单个章节"""
            async with semaphore:
                section_title = section_data.get('section_title', '')
                original_content = section_data.get('content', '')
                allocated_charts = section_data.get('allocated_charts', [])
                
                # 如果有可视化资源，获取该章节的图表
                section_charts = allocated_charts.copy()
                if visualization_resources and section_title in visualization_resources:
                    section_charts.extend(visualization_resources[section_title])
                
                print(f"\033[94m📝 开始处理章节：{section_title}\033[0m")
                
                # 异步生成带可视化的章节内容
                enhanced_content = await self.generate_section_with_visualization_async(
                    section_title=section_title,
                    original_content=original_content,
                    visualization_charts=section_charts,
                    llm_call_function_async=llm_call_function_async,
                    target_name=target_name,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    enable_text_visualization=enable_text_visualization,
                    output_dir=output_dir
                )
                
                print(f"\033[94m✅ 完成章节：{section_title}\033[0m")
                
                # 更新章节数据
                result_section = section_data.copy()
                result_section['content'] = enhanced_content
                result_section['allocated_charts'] = section_charts
                
                return result_section
        
        # 并发处理所有章节
        tasks = [process_single_section(section_data) for section_data in sections_data]
        processed_sections = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常情况
        final_sections = []
        for i, result in enumerate(processed_sections):
            if isinstance(result, Exception):
                print(f"⚠️ 章节 {sections_data[i].get('section_title', f'章节{i+1}')} 处理失败: {result}")
                # 使用原始数据
                final_sections.append(sections_data[i])
            else:
                final_sections.append(result)
        
        print(f"🎉 批量处理完成，成功处理 {len([r for r in processed_sections if not isinstance(r, Exception)])} 个章节")
        return final_sections
    
    async def generate_multiple_visualizations_async(
        self,
        sections_data: List[Dict[str, Any]],
        target_name: str,
        api_key: str,
        base_url: str,
        model: str,
        output_dir: str = None,
        max_concurrent: int = 2
    ) -> List[Dict[str, Any]]:
        """
        异步并发生成多个章节的文本可视化
        
        Args:
            sections_data: 章节数据列表
            target_name: 目标名称
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            output_dir: 输出目录
            max_concurrent: 最大并发数（图表生成比较消耗资源，建议设小一些）
            
        Returns:
            生成的图表信息列表
        """
        print(f"🎨 开始异步批量生成可视化，最大并发数：{max_concurrent}")
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_single_visualization(section_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """为单个章节生成可视化"""
            async with semaphore:
                section_title = section_data.get('section_title', '')
                section_content = section_data.get('content', '')
                
                return await self.generate_text_based_visualization_async(
                    section_title=section_title,
                    section_content=section_content,
                    target_name=target_name,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    output_dir=output_dir
                )
        
        # 并发生成所有可视化
        tasks = [generate_single_visualization(section_data) for section_data in sections_data]
        visualizations = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 过滤有效的可视化结果
        valid_visualizations = []
        for i, result in enumerate(visualizations):
            if isinstance(result, Exception):
                print(f"⚠️ 章节 {sections_data[i].get('section_title', f'章节{i+1}')} 可视化生成失败: {result}")
            elif result is not None:
                valid_visualizations.append(result)
        
        print(f"🎉 可视化生成完成，成功生成 {len(valid_visualizations)} 个图表")
        return valid_visualizations
    
    def load_visualization_resources(self, images_dir: str, target_name: str, name_field: str = 'company_name') -> Dict[str, List[Dict[str, Any]]]:
        """
        加载可视化资源（JSON文件）并按章节分组
        
        Args:
            images_dir: 图片目录路径
            target_name: 目标名称（公司名/行业名等），用于筛选相关文件
            name_field: 名称字段名，默认为'company_name'，行业可用'industry_name'等
            
        Returns:
            按章节分组的可视化资源字典
        """
        print(f"📊 加载可视化资源：{images_dir}")
        
        visualization_resources = {}
        
        if not os.path.exists(images_dir):
            print(f"⚠️ 图片目录不存在：{images_dir}")
            return visualization_resources
        
        # 扫描JSON文件
        json_files = [f for f in os.listdir(images_dir) if f.endswith('.json')]
        print(f"🔍 发现 {len(json_files)} 个可视化描述文件")
        
        for json_file in json_files:
            try:
                json_path = os.path.join(images_dir, json_file)
                with open(json_path, 'r', encoding='utf-8') as f:
                    chart_data = json.load(f)
                
                # 检查是否为目标对象的图表
                if chart_data.get(name_field) == target_name:
                    section = self._normalize_section_name(chart_data.get("section", "其他"))
                    
                    if section not in visualization_resources:
                        visualization_resources[section] = []
                        
                    visualization_resources[section].append(chart_data)
                    
            except Exception as e:
                print(f"⚠️ 加载可视化文件失败 {json_file}: {e}")
        
        self._print_visualization_summary(visualization_resources)
        return visualization_resources
    
    async def load_visualization_resources_async(self, images_dir: str, target_name: str, name_field: str = 'company_name') -> Dict[str, List[Dict[str, Any]]]:
        """
        异步加载可视化资源（JSON文件）并按章节分组
        
        Args:
            images_dir: 图片目录路径
            target_name: 目标名称（公司名/行业名等），用于筛选相关文件
            name_field: 名称字段名，默认为'company_name'，行业可用'industry_name'等
            
        Returns:
            按章节分组的可视化资源字典
        """
        print(f"📊 异步加载可视化资源：{images_dir}")
        
        visualization_resources = {}
        
        if not os.path.exists(images_dir):
            print(f"⚠️ 图片目录不存在：{images_dir}")
            return visualization_resources
        
        # 扫描JSON文件
        json_files = [f for f in os.listdir(images_dir) if f.endswith('.json')]
        print(f"🔍 发现 {len(json_files)} 个可视化描述文件")
        
        async def load_single_json(json_file: str) -> Optional[Dict[str, Any]]:
            """异步加载单个JSON文件"""
            try:
                json_path = os.path.join(images_dir, json_file)
                # 使用线程池执行IO操作
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    def read_json():
                        with open(json_path, 'r', encoding='utf-8') as f:
                            return json.load(f)
                    chart_data = await loop.run_in_executor(executor, read_json)
                
                # 检查是否为目标对象的图表
                if chart_data.get(name_field) == target_name:
                    return chart_data
                return None
            except Exception as e:
                print(f"⚠️ 加载可视化文件失败 {json_file}: {e}")
                return None
        
        # 并行加载所有JSON文件
        tasks = [load_single_json(json_file) for json_file in json_files]
        chart_data_list = await asyncio.gather(*tasks)
        
        # 按章节分组
        for chart_data in chart_data_list:
            if chart_data is not None:
                section = self._normalize_section_name(chart_data.get("section", "其他"))
                if section not in visualization_resources:
                    visualization_resources[section] = []
                visualization_resources[section].append(chart_data)
        
        self._print_visualization_summary(visualization_resources)
        return visualization_resources
    
    def _normalize_section_name(self, section: str) -> str:
        """
        规范化章节名称，统一格式便于匹配
        
        Args:
            section: 原始章节名称
            
        Returns:
            规范化后的章节名称
        """
        # 移除多余的空格和符号
        section = section.strip()
        
        # 获取章节映射（子类可以重写）
        section_mapping = self.get_default_section_mapping()
        
        # 尝试匹配中文数字
        for key, standard_name in section_mapping.items():
            if section.startswith(key):
                return standard_name
        
        return section
    
    def _print_visualization_summary(self, visualization_resources: Dict[str, List[Dict[str, Any]]]):
        """打印可视化资源摘要"""
        total_charts = sum(len(charts) for charts in visualization_resources.values())
        print(f"✅ 成功加载 {total_charts} 个可视化资源，覆盖 {len(visualization_resources)} 个章节")
        
        # 详细打印每个章节的可视化资源
        if visualization_resources:
            print(f"\n🎨 \033[93m可视化资源详情：\033[0m")
            for section_name, charts in visualization_resources.items():
                print(f"\033[93m📊 章节：{section_name} ({len(charts)}个图表)\033[0m")
                for i, chart in enumerate(charts, 1):
                    chart_title = chart.get('chart_title', f'图表{i}')
                    chart_type = chart.get('chart_type', '未知类型')
                    png_path = chart.get('png_path', '')
                    report_value = chart.get('report_value', '')
                    
                    # 检查PNG路径是否有效
                    png_status = "✅" if PathUtils.is_valid_png_path(png_path) else "❌"
                    
                    print(f"\033[93m   {i}. {chart_title}\033[0m")
                    print(f"      类型: {chart_type} | 价值: {report_value} | PNG: {png_status}")
                    if png_path:
                        print(f"      路径: {png_path}")
                    else:
                        print(f"      路径: 无PNG文件")
        else:
            print(f"\n⚠️ \033[93m未找到任何可视化资源\033[0m")
    
    def build_visualization_enhanced_prompt(
        self,
        section_title: str,
        original_content: str,
        visualization_charts: List[Dict[str, Any]]
    ) -> str:
        """
        构建可视化增强提示词，用于第二轮内容生成
        
        Args:
            section_title: 章节标题
            original_content: 第一轮生成的原始内容
            visualization_charts: 该章节的可视化图表列表
            
        Returns:
            增强提示词
        """
        if not visualization_charts:
            return original_content
        
        # 构建图表资源部分
        chart_resources = self._build_chart_resources(visualization_charts)
        
        # 使用模板构建完整提示词
        prompt = VISUALIZATION_ENHANCEMENT_PROMPT_TEMPLATE.format(
            original_content=original_content,
            chart_resources=chart_resources
        )
        
        return prompt
    
    def _build_chart_resources(self, visualization_charts: List[Dict[str, Any]]) -> str:
        """构建图表资源字符串"""
        chart_resources = ""
        valid_charts_count = 0
        
        for i, chart in enumerate(visualization_charts, 1):
            chart_title = chart.get('chart_title', f'图表{i}')
            chart_type = chart.get('chart_type', '未知类型')
            image_description = chart.get('image_description', '')
            png_path = chart.get('png_path', '')
            html_path = chart.get('html_path', '')
            report_value = chart.get('report_value', '')
            
            # 使用绝对路径，确保图片可以正确引用
            absolute_png_path = PathUtils.normalize_path(png_path)
            absolute_html_path = PathUtils.normalize_path(html_path)
            
            # 获取图表状态
            path_status, path_info, chart_usage_instruction = ChartValidator.get_chart_status(chart)
            
            # 统计有效图表
            if PathUtils.is_valid_png_path(absolute_png_path):
                valid_charts_count += 1
            
            # 读取HTML内容
            html_content = HtmlContentReader.read_html_content(html_path, chart)
            
            chart_resources += CHART_RESOURCE_TEMPLATE.format(
                chart_number=i,
                chart_title=chart_title,
                chart_type=chart_type,
                report_value=report_value,
                path_status=path_status,
                path_info=path_info,
                absolute_html_path=absolute_html_path,
                chart_usage_instruction=chart_usage_instruction,
                html_content=html_content,
                image_description=image_description
            ) + "\n"
        
        # 添加有效图表统计信息到图表资源顶部
        valid_charts_summary = f"""
## 📊 图表资源状态总览
- **总图表数量**：{len(visualization_charts)}个
- **可用图表数量**：{valid_charts_count}个（有有效PNG路径）
- **不可用图表数量**：{len(visualization_charts) - valid_charts_count}个（PNG路径无效或为空）

⚠️ **重要提醒**：只能引用标记为"✅ 可用"的图表，禁止引用标记为"❌ 不可用"的图表！

"""
        return valid_charts_summary + chart_resources
    
    def generate_section_with_visualization(
        self,
        section_title: str,
        original_content: str,
        visualization_charts: List[Dict[str, Any]],
        llm_call_function,
        target_name: str = None,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        enable_text_visualization: bool = True,
        output_dir: str = None
    ) -> str:
        """
        生成带有可视化增强的章节内容
        
        Args:
            section_title: 章节标题
            original_content: 原始内容
            visualization_charts: 可视化图表列表
            llm_call_function: LLM调用函数
            target_name: 目标名称（用于生成文本可视化）
            api_key: API密钥（用于生成文本可视化）
            base_url: API基础URL（用于生成文本可视化）
            model: 模型名称（用于生成文本可视化）
            enable_text_visualization: 是否启用基于文本的可视化生成
            output_dir: 图表输出目录
            
        Returns:
            增强后的章节内容
        """
        # 如果没有预设图表，且启用了文本可视化，尝试生成基于文本的图表
        if (not visualization_charts and enable_text_visualization and 
            target_name and api_key and base_url and model):
            
            print(f"\033[93m📝 {section_title} 无预设图表，尝试基于文本内容生成可视化...\033[0m")
            
            # 生成基于文本的可视化
            text_chart = self.generate_text_based_visualization(
                section_title=section_title,
                section_content=original_content,
                target_name=target_name,
                api_key=api_key,
                base_url=base_url,
                model=model,
                output_dir=output_dir
            )
            
            if text_chart:
                visualization_charts = [text_chart]
                print(f"\033[93m   ✅ 成功生成文本可视化图表\033[0m")
            else:
                print(f"\033[93m   ⚠️ 文本可视化生成失败，保持原内容\033[0m")
        
        if not visualization_charts:
            print(f"\033[93m📝 {section_title} 无可视化资源，保持原内容\033[0m")
            return original_content
        
        print(f"\033[93m🎨 为 {section_title} 生成可视化增强内容（{len(visualization_charts)}个图表）\033[0m")
        
        # 构建增强提示词
        enhanced_prompt = self.build_visualization_enhanced_prompt(
            section_title, original_content, visualization_charts
        )
        
        try:
            # 调用LLM生成增强内容
            enhanced_content = llm_call_function(enhanced_prompt)
            
            # 在内容末尾添加图表路径信息（用于后续处理）
            enhanced_content += self._append_chart_paths(visualization_charts)
            
            return enhanced_content
            
        except Exception as e:
            print(f"⚠️ 生成增强内容失败: {e}")
            return original_content
    
    async def generate_section_with_visualization_async(
        self,
        section_title: str,
        original_content: str,
        visualization_charts: List[Dict[str, Any]],
        llm_call_function_async,
        target_name: str = None,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        enable_text_visualization: bool = True,
        output_dir: str = None
    ) -> str:
        """
        异步生成带有可视化增强的章节内容
        
        Args:
            section_title: 章节标题
            original_content: 原始内容
            visualization_charts: 可视化图表列表
            llm_call_function_async: 异步LLM调用函数
            target_name: 目标名称（用于生成文本可视化）
            api_key: API密钥（用于生成文本可视化）
            base_url: API基础URL（用于生成文本可视化）
            model: 模型名称（用于生成文本可视化）
            enable_text_visualization: 是否启用基于文本的可视化生成
            output_dir: 图表输出目录
            
        Returns:
            增强后的章节内容
        """
        # 如果没有预设图表，且启用了文本可视化，尝试生成基于文本的图表
        if (not visualization_charts and enable_text_visualization and 
            target_name and api_key and base_url and model):
            
            print(f"\033[93m📝 {section_title} 无预设图表，尝试基于文本内容生成可视化...\033[0m")
            
            # 异步生成基于文本的可视化
            text_chart = await self.generate_text_based_visualization_async(
                section_title=section_title,
                section_content=original_content,
                target_name=target_name,
                api_key=api_key,
                base_url=base_url,
                model=model,
                output_dir=output_dir
            )
            
            if text_chart:
                visualization_charts = [text_chart]
                print(f"\033[93m   ✅ 成功生成文本可视化图表\033[0m")
            else:
                print(f"\033[93m   ⚠️ 文本可视化生成失败，保持原内容\033[0m")
        
        if not visualization_charts:
            print(f"\033[93m📝 {section_title} 无可视化资源，保持原内容\033[0m")
            return original_content
        
        print(f"\033[93m🎨 为 {section_title} 生成可视化增强内容（{len(visualization_charts)}个图表）\033[0m")
        
        # 构建增强提示词
        enhanced_prompt = self.build_visualization_enhanced_prompt(
            section_title, original_content, visualization_charts
        )
        
        try:
            # 异步调用LLM生成增强内容
            enhanced_content = await llm_call_function_async(enhanced_prompt)
            
            # 在内容末尾添加图表路径信息（用于后续处理）
            enhanced_content += self._append_chart_paths(visualization_charts)
            
            return enhanced_content
            
        except Exception as e:
            print(f"⚠️ 生成增强内容失败: {e}")
            return original_content
    
    def _append_chart_paths(self, charts: List[Dict[str, Any]]) -> str:
        """
        在内容末尾添加图表路径信息（隐藏格式，用于后续处理）
        
        Args:
            charts: 图表列表
            
        Returns:
            格式化的图表路径信息
        """
        if not charts:
            return ""
        
        paths_info = "\n\n<!-- CHART_PATHS\n"
        for i, chart in enumerate(charts, 1):
            # 使用绝对路径
            png_path = chart.get('png_path', '')
            html_path = chart.get('html_path', '')
            chart_title = chart.get('chart_title', f'图表{i}')
            
            if png_path:
                # 规范化路径分隔符
                absolute_png_path = PathUtils.normalize_path(png_path)
                absolute_html_path = PathUtils.normalize_path(html_path)
                
                paths_info += f"图{i}: {chart_title}\n"
                paths_info += f"  - PNG: {absolute_png_path}\n"
                if absolute_html_path:
                    paths_info += f"  - HTML: {absolute_html_path}\n"
        paths_info += "-->\n"
        
        return paths_info
    
    def extract_chart_references(self, content: str) -> Dict[str, str]:
        """
        从内容中提取图表引用关系
        
        Args:
            content: 包含图表引用的内容
            
        Returns:
            图表编号到路径的映射字典
        """
        chart_refs = {}
        
        # 提取隐藏的图表路径信息
        pattern = r'<!-- CHART_PATHS\n(.*?)\n-->'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            paths_text = match.group(1)
            for line in paths_text.split('\n'):
                if ':' in line:
                    chart_num, path = line.split(':', 1)
                    chart_refs[chart_num.strip()] = path.strip()
        
        return chart_refs
    
    def update_global_references(self, collected_data_info: Dict[str, Any]) -> None:
        """
        更新全局参考文献列表
        
        Args:
            collected_data_info: 收集的数据信息
        """
        section_references = collected_data_info.get("references", [])
        
        for i, ref_info in enumerate(section_references, 1):
            data_id = ref_info["data_id"]
            if data_id not in self.global_id_to_ref:
                # 分配新的全局参考文献序号
                new_ref_num = len(self.global_references) + 1
                
                self.global_references.append({
                    "ref_num": new_ref_num,
                    "data_id": data_id,
                    "title": ref_info["title"],
                    "url": ref_info["url"],
                    "source": ref_info["source"],
                    "company_name": ref_info.get("company_name", ""),
                    "company_code": ref_info.get("company_code", ""),
                    "market": ref_info.get("market", "")
                })
                self.global_id_to_ref[data_id] = new_ref_num
    
    def convert_data_ids_to_references(self, content: str) -> str:
        """
        将内容中的数据ID引用转换为参考文献序号
        
        Args:
            content: 包含数据ID引用的内容
            
        Returns:
            转换后的内容
        """
        # 匹配【数据123】格式
        def replace_data_ref(match):
            data_id = match.group(1)
            ref_num = self.global_id_to_ref.get(data_id, data_id)
            return f"[{ref_num}]"
        
        # 替换各种格式的数据引用
        patterns = [
            r'【数据(\d+)】',
            r'\\[数据(\d+)\\]',
            r'\\(数据(\d+)\\)',
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, replace_data_ref, content)
        
        return content
    
    def build_chart_content(self, allocated_charts: List[Dict[str, Any]]) -> str:
        """
        构建图表内容描述，包含详细的图表信息以供AI分析引用
        
        Args:
            allocated_charts: 分配的图表列表
            
        Returns:
            格式化的图表内容字符串，包含图表描述和引用信息
        """
        if not allocated_charts:
            return ""
            
        chart_content = "\n\n**可用图表资源：**\n"
        chart_content += "⚠️ 重要：请务必在撰写内容时使用Markdown语法 `![图表标题](绝对路径)` 嵌入以下图表！不能只写图表标题！\n"
        chart_content += "🚨 严禁虚构：严禁创造、编造或虚构任何图片路径！只能使用下方明确提供的图表！\n"
        
        for i, chart in enumerate(allocated_charts, 1):
            chart_title = chart.get("chart_title", f"图表{i}")
            chart_description = chart.get("image_description", "")
            png_path = chart.get("png_path", "")
            html_path = chart.get("html_path", "")
            chart_type = chart.get("chart_type", "")
            match_score = chart.get("match_score", 0)
            
            chart_content += f"\n**图表{i}：{chart_title}**\n"
            
            if chart_type:
                chart_content += f"- 图表类型：{chart_type}\n"
                
            if chart_description:
                chart_content += f"- 详细描述：{chart_description}\n"
                
            if match_score > 0:
                chart_content += f"- 相关度：{match_score:.2f}\n"
                
            if png_path:
                # 规范化路径分隔符并使用绝对路径
                absolute_png_path = PathUtils.normalize_path(png_path)
                chart_content += f"- PNG图片绝对路径：{absolute_png_path}\n"
                chart_content += f"- **必须使用的Markdown嵌入语法**：`![{chart_title}]({absolute_png_path})`\n"
                chart_content += f"- ⚠️ 注意：必须原样复制上述Markdown语法到内容中，确保图片正确显示\n"
                chart_content += f"- 🚫 严禁修改：绝对不允许修改上述路径或创造其他图片路径\n"
                
            if html_path:
                absolute_html_path = PathUtils.normalize_path(html_path)
                chart_content += f"- HTML文件绝对路径：{absolute_html_path}\n"
                
                # 读取并添加HTML内容
                html_content = HtmlContentReader.read_html_content(html_path, chart)
                
                if html_content:
                    chart_content += f"- HTML图表代码：\n```html\n{html_content}\n```\n"
                
            chart_content += f"- ⚠️ 强制要求：必须使用上述Markdown语法嵌入图表，不可仅写图表标题\n"
        
        chart_content += CHART_USAGE_REQUIREMENTS
        
        return chart_content
    
    def build_data_content(
        self, 
        collected_data_info: Dict[str, Any], 
        processing_method: str
    ) -> str:
        """
        构建数据内容（带参考文献序号）
        
        Args:
            collected_data_info: 收集的数据信息
            processing_method: 处理方法
            
        Returns:
            格式化的数据内容字符串
        """
        collected_data = collected_data_info.get("collected_data", [])
        data_content = ""
        
        if processing_method == "direct":
            # 直接使用原始数据
            for i, item in enumerate(collected_data, 1):
                content = item.get("summary", "") or item.get("content", "") or item.get("md", "")
                title = item.get("title", "")
                ref_num = self.global_id_to_ref.get(item['id'], item['id'])
                # 添加文献标记
                data_content += f"\n\n【第{i}篇开始】\n当前文献的id是：{item['id']}\n**来源[{ref_num}]：{title}**\n{content}\n【第{i}篇结束】"
        else:
            # 使用提取的摘要
            for i, item in enumerate(collected_data, 1):
                content = item.get('summary', '')
                # 从摘要中提取可能的数据ID引用，并转换为参考文献序号
                content = self.convert_data_ids_to_references(content)
                # 添加文献标记
                data_content += f"\n\n【第{i}篇开始】\n当前文献的id是：{item.get('id', 'unknown')}\n{content}\n【第{i}篇结束】"
        
        return data_content
    
    @abstractmethod
    def get_report_title(self, subject_name: str) -> str:
        """获取报告标题 - 子类需要实现"""
        pass
    
    def assemble_final_report(
        self,
        subject_name: str,
        report_plan: Dict[str, Any],
        generated_sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        组装最终报告
        
        Args:
            subject_name: 研究主体名称
            report_plan: 报告规划
            generated_sections: 生成的章节列表
            
        Returns:
            完整的报告
        """
        print(f"📋 组装最终报告...")
        
        # 生成报告标题
        report_title = self.get_report_title(subject_name)
        
        # 开始组装报告内容
        full_content = f"# {report_title}\n\n"
        
        # 添加目录
        full_content += "## 目录\n\n"
        for i, section in enumerate(generated_sections, 1):
            section_title = section['section_title']
            # 检查标题是否已经包含中文序号，如果有就不添加数字序号
            if TitleValidator.has_chinese_number(section_title):
                full_content += f"{section_title}\n"
            else:
                full_content += f"{i}. {section_title}\n"
        full_content += "\n"
        
        # 添加各章节内容
        for i, section in enumerate(generated_sections, 1):
            section_title = section['section_title']
            # 检查标题是否已经包含中文序号，如果有就不添加数字序号
            if TitleValidator.has_chinese_number(section_title):
                full_content += f"## {section_title}\n\n"
            else:
                full_content += f"## {i}. {section_title}\n\n"
            # 直接添加生成的内容，不再处理标题
            full_content += section['content'].strip()
            
            # 添加该章节的图表
            allocated_charts = section.get('allocated_charts', [])
            if allocated_charts:
                full_content += "\n\n### 相关图表\n\n"
                for chart_idx, chart in enumerate(allocated_charts, 1):
                    chart_title = chart.get("chart_title", f"图表{chart_idx}")
                    chart_description = chart.get("image_description", "")
                    png_path = chart.get("png_path", "")
                    
                    full_content += f"**图{chart_idx}：{chart_title}**\n\n"
                    
                    # 如果有图片路径，添加图片引用
                    if png_path:
                        # 使用Markdown格式嵌入图片
                        full_content += f"![{chart_title}]({png_path})\n\n"
                        
                    # 添加图表描述
                    if chart_description:
                        full_content += f"{chart_description}\n\n"
            
            full_content += "\n\n"
        
        # 添加参考文献
        if self.global_references:
            full_content += "## 参考文献\n\n"
            for ref in self.global_references:
                # 使用简单的 [序号] 标题 URL 格式
                ref_line = f"[{ref['ref_num']}] {ref['title']}"
                if ref['url']:
                    ref_line += f"\n    {ref['url']}"
                full_content += ref_line + "\n\n"
        
        return {
            "report_title": report_title,
            "subject_name": subject_name,
            "full_content": full_content,
            "markdown": full_content,  # 添加markdown字段，与full_content相同
            "sections": generated_sections,
            "report_plan": report_plan,
            "references": self.global_references,
            "generation_stats": {
                "total_sections": len(generated_sections),
                "sections_with_data": sum(1 for s in generated_sections if s['generation_method'] != 'no_data'),
                "sections_without_data": sum(1 for s in generated_sections if s['generation_method'] == 'no_data'),
                "total_words": len(full_content),
                "total_references": len(self.global_references),
                "total_charts": sum(len(s.get('allocated_charts', [])) for s in generated_sections)
            }
        }
    
    async def assemble_final_report_async(
        self,
        subject_name: str,
        report_plan: Dict[str, Any],
        generated_sections: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        异步组装最终报告
        
        Args:
            subject_name: 研究主体名称
            report_plan: 报告规划
            generated_sections: 生成的章节列表
            
        Returns:
            完整的报告
        """
        print(f"📋 异步组装最终报告...")
        
        # 生成报告标题
        report_title = self.get_report_title(subject_name)
        
        # 开始组装报告内容
        full_content = f"# {report_title}\n\n"
        
        # 添加目录
        full_content += "## 目录\n\n"
        for i, section in enumerate(generated_sections, 1):
            section_title = section['section_title']
            # 检查标题是否已经包含中文序号，如果有就不添加数字序号
            if TitleValidator.has_chinese_number(section_title):
                full_content += f"{section_title}\n"
            else:
                full_content += f"{i}. {section_title}\n"
        full_content += "\n"
        
        # 使用线程池异步处理内容组装
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            def build_section_content():
                content = ""
                # 添加各章节内容
                for i, section in enumerate(generated_sections, 1):
                    section_title = section['section_title']
                    # 检查标题是否已经包含中文序号，如果有就不添加数字序号
                    if TitleValidator.has_chinese_number(section_title):
                        content += f"## {section_title}\n\n"
                    else:
                        content += f"## {i}. {section_title}\n\n"
                    # 直接添加生成的内容，不再处理标题
                    content += section['content'].strip()
                    
                    # 添加该章节的图表
                    allocated_charts = section.get('allocated_charts', [])
                    if allocated_charts:
                        content += "\n\n### 相关图表\n\n"
                        for chart_idx, chart in enumerate(allocated_charts, 1):
                            chart_title = chart.get("chart_title", f"图表{chart_idx}")
                            chart_description = chart.get("image_description", "")
                            png_path = chart.get("png_path", "")
                            
                            content += f"**图{chart_idx}：{chart_title}**\n\n"
                            
                            # 如果有图片路径，添加图片引用
                            if png_path:
                                # 使用Markdown格式嵌入图片
                                content += f"![{chart_title}]({png_path})\n\n"
                                
                            # 添加图表描述
                            if chart_description:
                                content += f"{chart_description}\n\n"
                    
                    content += "\n\n"
                return content
            
            sections_content = await loop.run_in_executor(executor, build_section_content)
            full_content += sections_content
        
        # 添加参考文献
        if self.global_references:
            full_content += "## 参考文献\n\n"
            for ref in self.global_references:
                # 使用简单的 [序号] 标题 URL 格式
                ref_line = f"[{ref['ref_num']}] {ref['title']}"
                if ref['url']:
                    ref_line += f"\n    {ref['url']}"
                full_content += ref_line + "\n\n"
        
        return {
            "report_title": report_title,
            "subject_name": subject_name,
            "full_content": full_content,
            "markdown": full_content,  # 添加markdown字段，与full_content相同
            "sections": generated_sections,
            "report_plan": report_plan,
            "references": self.global_references,
            "generation_stats": {
                "total_sections": len(generated_sections),
                "sections_with_data": sum(1 for s in generated_sections if s['generation_method'] != 'no_data'),
                "sections_without_data": sum(1 for s in generated_sections if s['generation_method'] == 'no_data'),
                "total_words": len(full_content),
                "total_references": len(self.global_references),
                "total_charts": sum(len(s.get('allocated_charts', [])) for s in generated_sections)
            }
        }
    
    def generate_text_based_visualization(
        self,
        section_title: str,
        section_content: str,
        target_name: str,
        api_key: str,
        base_url: str,
        model: str,
        output_dir: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        基于章节文本内容生成可视化图表
        
        Args:
            section_title: 章节标题
            section_content: 章节内容
            target_name: 目标名称（公司名等）
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            output_dir: 输出目录，默认为images目录
            
        Returns:
            图表信息字典，包含路径和描述等
        """
        if not section_content or len(section_content.strip()) < 50:
            print(f"\033[93m⚠️ {section_title} 内容太短，跳过图表生成\033[0m")
            return None
        
        print(f"\033[93m🎨 为 {section_title} 基于文本内容生成可视化图表...\033[0m")
        
        # 确定输出目录
        if not output_dir:
            # 默认使用与 company_collection_data.py 一致的输出目录
            project_root = os.path.dirname(os.path.dirname(__file__))
            output_dir = os.path.join(project_root, "test_company_datas", "images")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # HTML临时文件需要放在项目根目录下（与js目录同级），以便正确引用echarts
        html_temp_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 构建可视化查询
        visualization_query = TEXT_VISUALIZATION_QUERY_TEMPLATE.format(
            target_name=target_name,
            section_title=section_title,
            section_content=section_content
        )
        
        try:
            # 生成HTML图表
            chart_html = text2infographic_html(
                query=visualization_query,
                api_key=api_key,
                base_url=base_url,
                model=model,
                temperature=0.3,
                max_tokens=3000
            )
            
            if not chart_html:
                print(f"\033[93m⚠️ HTML图表生成失败\033[0m")
                return None
            
            # 生成唯一文件名
            timestamp = int(time.time())
            chart_id = str(uuid.uuid4())[:8]
            base_filename = f"text_chart_{target_name}_{timestamp}_{chart_id}"
            
            # 保存HTML文件到项目根目录（与js目录同级）
            html_path = os.path.join(html_temp_dir, f"{base_filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(chart_html)
            
            # 转换为PNG图片（保存到images目录）
            png_path = os.path.join(output_dir, f"{base_filename}.png")
            try:
                html2png(html_path, png_path)
                print(f"\033[93m✅ 成功生成图表：{png_path}\033[0m")
                
                # 删除临时HTML文件
                try:
                    os.remove(html_path)
                    print(f"\033[93m🗑️ 已删除临时HTML文件：{html_path}\033[0m")
                except Exception as cleanup_e:
                    print(f"\033[93m⚠️ 删除临时HTML文件失败: {cleanup_e}\033[0m")
                    
            except Exception as e:
                print(f"\033[93m⚠️ PNG转换失败: {e}\033[0m")
                # 转换失败时也删除临时HTML文件
                try:
                    os.remove(html_path)
                    print(f"\033[93m🗑️ 已删除临时HTML文件：{html_path}\033[0m")
                except Exception as cleanup_e:
                    print(f"\033[93m⚠️ 删除临时HTML文件失败: {cleanup_e}\033[0m")
                return None
            
            # 构建图表信息
            chart_info = {
                "chart_title": f"{target_name} - {section_title}分析图表",
                "chart_type": "基于文本生成的分析图表",
                "png_path": png_path,
                "html_path": None,  # HTML文件已删除，不再提供路径
                "html_content": chart_html,
                "image_description": f"基于{section_title}内容自动生成的可视化图表，用于支撑该章节的分析观点",
                "report_value": "中等",
                "section": section_title,
                "company_name": target_name if "公司" in str(target_name) else None,
                "industry_name": target_name if "行业" in str(target_name) else None
            }
            
            return chart_info
            
        except Exception as e:
            print(f"\033[93m⚠️ 文本可视化生成失败: {e}\033[0m")
            return None
    
    async def generate_text_based_visualization_async(
        self,
        section_title: str,
        section_content: str,
        target_name: str,
        api_key: str,
        base_url: str,
        model: str,
        output_dir: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        异步基于章节文本内容生成可视化图表
        
        Args:
            section_title: 章节标题
            section_content: 章节内容
            target_name: 目标名称（公司名等）
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            output_dir: 输出目录，默认为images目录
            
        Returns:
            图表信息字典，包含路径和描述等
        """
        if not section_content or len(section_content.strip()) < 50:
            print(f"\033[93m⚠️ {section_title} 内容太短，跳过图表生成\033[0m")
            return None
        
        print(f"\033[93m🎨 为 {section_title} 基于文本内容异步生成可视化图表...\033[0m")
        
        # 确定输出目录
        if not output_dir:
            # 默认使用与 company_collection_data.py 一致的输出目录
            project_root = os.path.dirname(os.path.dirname(__file__))
            output_dir = os.path.join(project_root, "test_company_datas", "images")
        
        # 确保输出目录存在
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, os.makedirs, output_dir, True)
        
        # HTML临时文件需要放在项目根目录下（与js目录同级），以便正确引用echarts
        html_temp_dir = os.path.dirname(os.path.dirname(__file__))
        
        # 构建可视化查询
        visualization_query = TEXT_VISUALIZATION_QUERY_TEMPLATE.format(
            target_name=target_name,
            section_title=section_title,
            section_content=section_content
        )
        
        try:
            # 异步生成HTML图表
            def generate_chart():
                return text2infographic_html(
                    query=visualization_query,
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    temperature=0.3,
                    max_tokens=3000
                )
            
            chart_html = await loop.run_in_executor(executor, generate_chart)
            
            if not chart_html:
                print(f"\033[93m⚠️ HTML图表生成失败\033[0m")
                return None
            
            # 生成唯一文件名
            timestamp = int(time.time())
            chart_id = str(uuid.uuid4())[:8]
            base_filename = f"text_chart_{target_name}_{timestamp}_{chart_id}"
            
            # 异步保存HTML文件到项目根目录（与js目录同级）
            html_path = os.path.join(html_temp_dir, f"{base_filename}.html")
            
            def write_html():
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(chart_html)
            
            await loop.run_in_executor(executor, write_html)
            
            # 异步转换为PNG图片（保存到images目录）
            png_path = os.path.join(output_dir, f"{base_filename}.png")
            
            try:
                def convert_to_png():
                    html2png(html_path, png_path)
                
                await loop.run_in_executor(executor, convert_to_png)
                print(f"\033[93m✅ 成功生成图表：{png_path}\033[0m")
                
                # 异步删除临时HTML文件
                try:
                    await loop.run_in_executor(executor, os.remove, html_path)
                    print(f"\033[93m🗑️ 已删除临时HTML文件：{html_path}\033[0m")
                except Exception as cleanup_e:
                    print(f"\033[93m⚠️ 删除临时HTML文件失败: {cleanup_e}\033[0m")
                    
            except Exception as e:
                print(f"\033[93m⚠️ PNG转换失败: {e}\033[0m")
                # 转换失败时也异步删除临时HTML文件
                try:
                    await loop.run_in_executor(executor, os.remove, html_path)
                    print(f"\033[93m🗑️ 已删除临时HTML文件：{html_path}\033[0m")
                except Exception as cleanup_e:
                    print(f"\033[93m⚠️ 删除临时HTML文件失败: {cleanup_e}\033[0m")
                return None
            
            # 构建图表信息
            chart_info = {
                "chart_title": f"{target_name} - {section_title}分析图表",
                "chart_type": "基于文本生成的分析图表",
                "png_path": png_path,
                "html_path": None,  # HTML文件已删除，不再提供路径
                "html_content": chart_html,
                "image_description": f"基于{section_title}内容自动生成的可视化图表，用于支撑该章节的分析观点",
                "report_value": "中等",
                "section": section_title,
                "company_name": target_name if "公司" in str(target_name) else None,
                "industry_name": target_name if "行业" in str(target_name) else None
            }
            
            return chart_info
            
        except Exception as e:
            print(f"\033[93m⚠️ 文本可视化生成失败: {e}\033[0m")
            return None
    
    def reset_references(self):
        """重置参考文献状态（用于生成新报告时）"""
        self.global_references = []
        self.global_id_to_ref = {}
    
    def assemble_markdown_report(self, final_report: dict) -> str:
        """
        将最终报告内容转换为 Markdown 格式
        
        Args:
            final_report: 由 assemble_final_report 生成的报告字典
            
        Returns:
            Markdown 格式字符串
        """
        lines = []
        subject_name = final_report.get("subject_name", "研究主体")
        report_plan = final_report.get("report_plan", {})
        plan_content = report_plan.get("plan_content", "") if report_plan else ""
        sections = final_report.get("sections", [])
        
        # 报告标题
        report_title = self.get_report_title(subject_name)
        lines.append(f"# {report_title}\n")
        
        # 目录
        lines.append("## 目录\n")
        for i, section in enumerate(sections, 1):
            title = section.get("section_title", f"章节{i}")
            # 检查标题是否已经包含中文序号，如果有就不添加数字序号
            if TitleValidator.has_chinese_number(title):
                lines.append(f"{title}")
            else:
                lines.append(f"{i}. {title}")
        lines.append("")
        
        # 章节内容
        for i, section in enumerate(sections, 1):
            title = section.get("section_title", f"章节{i}")
            content = section.get("content", "")
            allocated_charts = section.get("allocated_charts", [])
            
            # 检查标题是否已经包含中文序号，如果有就不添加数字序号
            if TitleValidator.has_chinese_number(title):
                lines.append(f"## {title}\n")
            else:
                lines.append(f"## {i}. {title}\n")
            lines.append(f"{content}\n")
            
            # 添加图表（如果有的话）
            if allocated_charts:
                lines.append("### 相关图表\n")
                for chart_idx, chart in enumerate(allocated_charts, 1):
                    chart_title = chart.get("chart_title", f"图表{chart_idx}")
                    chart_description = chart.get("image_description", "")
                    png_path = chart.get("png_path", "")
                    
                    lines.append(f"**图{chart_idx}：{chart_title}**\n")
                    
                    # 如果有图片路径，添加图片引用
                    if png_path:
                        lines.append(f"![{chart_title}]({png_path})\n")
                    
                    # 添加图表描述
                    if chart_description:
                        lines.append(f"{chart_description}\n")
                
                lines.append("")
        
        # 参考文献
        references = final_report.get("references", [])
        if references:
            lines.append("---\n")
            lines.append("## 参考文献\n")
            for ref in references:
                ref_num = ref.get("ref_num", "")
                title = ref.get("title", "")
                url = ref.get("url", "")
                
                ref_line = f"[{ref_num}] {title}"
                if url:
                    ref_line += f"\n    {url}"
                lines.append(ref_line)
            lines.append("")
        
        return "\n".join(lines)
    
    async def complete_report_generation_async(
        self,
        subject_name: str,
        report_plan: Dict[str, Any],
        sections_data: List[Dict[str, Any]],
        llm_call_function_async,
        images_dir: str = None,
        name_field: str = 'company_name',
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        enable_text_visualization: bool = True,
        output_dir: str = None,
        max_concurrent_sections: int = 3,
        max_concurrent_charts: int = 2
    ) -> Dict[str, Any]:
        """
        完整的异步报告生成工作流
        
        Args:
            subject_name: 研究主体名称
            report_plan: 报告规划
            sections_data: 章节数据列表
            llm_call_function_async: 异步LLM调用函数
            images_dir: 图片目录
            name_field: 名称字段
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            enable_text_visualization: 是否启用文本可视化
            output_dir: 输出目录
            max_concurrent_sections: 章节处理最大并发数
            max_concurrent_charts: 图表生成最大并发数
            
        Returns:
            完整的报告
        """
        print(f"🚀 开始异步报告生成工作流...")
        start_time = time.time()
        
        # 步骤1: 异步加载可视化资源
        visualization_resources = {}
        if images_dir:
            print(f"📊 步骤1: 异步加载可视化资源...")
            visualization_resources = await self.load_visualization_resources_async(
                images_dir=images_dir,
                target_name=subject_name,
                name_field=name_field
            )
            print(f"✅ 可视化资源加载完成")
        
        # 步骤2: 异步批量处理章节
        print(f"📝 步骤2: 异步批量处理章节...")
        processed_sections = await self.process_sections_batch_async(
            sections_data=sections_data,
            llm_call_function_async=llm_call_function_async,
            visualization_resources=visualization_resources,
            target_name=subject_name,
            api_key=api_key,
            base_url=base_url,
            model=model,
            enable_text_visualization=enable_text_visualization,
            output_dir=output_dir,
            max_concurrent=max_concurrent_sections
        )
        print(f"✅ 章节处理完成")
        
        # 步骤3: 异步组装最终报告
        print(f"📋 步骤3: 异步组装最终报告...")
        final_report = await self.assemble_final_report_async(
            subject_name=subject_name,
            report_plan=report_plan,
            generated_sections=processed_sections
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # 添加性能统计
        final_report['processing_stats'] = {
            'total_processing_time': processing_time,
            'sections_processed': len(processed_sections),
            'visualization_resources_loaded': sum(len(charts) for charts in visualization_resources.values()),
            'max_concurrent_sections': max_concurrent_sections,
            'max_concurrent_charts': max_concurrent_charts
        }
        
        print(f"🎉 异步报告生成完成！总耗时：{processing_time:.2f}秒")
        print(f"📊 处理了 {len(processed_sections)} 个章节")
        print(f"🎨 加载了 {sum(len(charts) for charts in visualization_resources.values())} 个可视化资源")
        
        return final_report
