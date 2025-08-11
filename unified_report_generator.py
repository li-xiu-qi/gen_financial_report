"""
统一的报告生成器
合并了基础类和具体实现，简化项目结构
"""

import os
import json
import re
import asyncio
import traceback
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# 导入必要的工具和模块
from financial_report.utils.calculate_tokens import TransformerTokenCalculator
from financial_report.utils.chat import chat_no_tool
from financial_report.llm_calls.text2infographic_html import text2infographic_html
from financial_report.utils.html2png import html2png
from financial_report.search_tools.search_tools import bing_search_with_cache

# 导入提示词模板
from report_prompts import (
    COMPANY_SECTION_WITH_DATA_PROMPT,
    COMPANY_SECTION_WITHOUT_DATA_PROMPT,
    SECTION_CHART_ENHANCEMENT_PROMPT,
    INDUSTRY_SECTION_WITH_DATA_PROMPT, 
    INDUSTRY_SECTION_WITHOUT_DATA_PROMPT,
    MACRO_SECTION_WITH_DATA_PROMPT,
    MACRO_SECTION_WITHOUT_DATA_PROMPT
)


# ====================
# 基础数据处理器
# ====================

class ReportDataProcessor:
    """统一的报告数据处理器"""
    
    def __init__(self):
        self.token_calculator = TransformerTokenCalculator(model_name="deepseek-ai/DeepSeek-V3-0324")
    
    def load_report_data(self, data_dir: str, images_directory: str = None) -> Dict[str, Any]:
        """
        加载报告所需的所有数据
        
        Args:
            data_dir: 数据目录路径
            images_directory: 图片目录路径
            
        Returns:
            包含所有数据的字典
        """
        print("📂 开始加载报告数据文件...")
        data = {}
        
        # 核心数据文件映射 - 根据实际的数据文件
        core_files = {
            'outline': ['company_outline.json', 'industry_outline.json', 'macro_outline.json'],
            'allocation': ['outline_data_allocation.json'],
            'flattened_data': ['flattened_company_data.json', 'flattened_industry_data.json', 'flattened_macro_data.json'],
            'visualization_results': ['visualization_data_results.json']  # 可视化处理结果文件
        }
  
        # 加载核心文件
        for key, possible_files in core_files.items():
            loaded = False
            for filename in possible_files:
                file_path = os.path.join(data_dir, filename)
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                            data[key] = content
                            print(f"✓ 已加载核心文件: {filename}")
                            loaded = True
                            break
                    except Exception as e:
                        print(f"✗ 加载 {filename} 失败: {e}")
            
            # 对于可视化结果文件，可以是可选的
            if not loaded and key == 'visualization_results':
                print(f"ℹ 未找到可视化结果文件，报告将不包含图表")
                continue
            elif not loaded:
                raise FileNotFoundError(f"未找到 {key} 的任何可用文件: {possible_files}")
        
        # 处理可视化数据
        if 'visualization_results' in data:
            if images_directory:
                data['visualizations'] = self._process_visualization_results(data['visualization_results'], images_directory)
                print("✓ 已处理可视化结果文件")
            else:
                print("⚠ 未指定图片目录，可视化功能可能受限")
        else:
            print("ℹ 未找到可视化结果文件，报告将不包含图表")
        
        # 标准化数据结构
        data = self._standardize_data_structure(data)
        
        return data
    
    def _process_visualization_results(self, results_data: Dict[str, Any], images_directory: str) -> Dict[str, Any]:
        """
        处理可视化结果文件（新的数据结构）
        
        Args:
            results_data: 可视化处理结果数据
            images_directory: 图片目录路径
            
        Returns:
            处理后的可视化数据
        """
        print("🔄 处理可视化结果文件...")
        
        # 提取处理摘要和建议列表
        processing_summary = results_data.get("processing_summary", {})
        processed_suggestions = results_data.get("processed_suggestions", [])
        
        print(f"   📊 找到 {len(processed_suggestions)} 个可视化建议")
        print(f"   🎯 目标名称: {processing_summary.get('company_name', 'unknown')}")
        print(f"   ✅ 成功图表: {processing_summary.get('successful_count', 0)}")
        print(f"   ❌ 失败图表: {processing_summary.get('failed_count', 0)}")
        
        # 处理图表数据，只保留成功生成的图表
        final_suggestions = []
        
        for suggestion in processed_suggestions:
            # 只处理成功生成的图表
            if not suggestion.get("success", False):
                continue
                
            # 获取PNG路径 - 适配新的字段名
            png_path = (suggestion.get("chart_png_path", "") or 
                       suggestion.get("png_path", ""))
            
            if png_path and images_directory:
                # 检查是否需要修复路径
                if not os.path.exists(png_path):
                    # 尝试从images_directory中找到文件
                    filename = os.path.basename(png_path)
                    corrected_path = os.path.join(images_directory, filename)
                    if os.path.exists(corrected_path):
                        png_path = corrected_path
                        print(f"   🔧 修复PNG路径: {filename}")
            
            # 构建图表信息，保持与原格式的兼容性
            chart_info = {
                "success": suggestion.get("success", False),
                "chart_title": suggestion.get("chart_title", ""),
                "chart_type": suggestion.get("visualization_type", suggestion.get("chart_type", "")),
                "section": suggestion.get("section", "未分类"),
                "report_value": suggestion.get("report_value", "数据展示"),
                "priority": suggestion.get("priority", "medium"),
                "reason": suggestion.get("reason", ""),
                "image_description": suggestion.get("image_description", ""),
                "png_path": png_path,
                "has_png": suggestion.get("has_png", bool(png_path and os.path.exists(png_path))),
                "data_source_ids": suggestion.get("data_ids", suggestion.get("data_source_ids", [])),
                "raw_data_count": suggestion.get("raw_data_count", 0),
                "references": suggestion.get("references", []),
                "created_at": suggestion.get("created_at", ""),
                "processing_time": suggestion.get("processing_time", ""),
                "file_size": suggestion.get("file_size", 0),
                "timestamp": suggestion.get("timestamp", "")
            }
            
            final_suggestions.append(chart_info)
        
        # 构建最终的可视化数据结构
        visualization_data = {
            "processing_summary": processing_summary,
            "processed_suggestions": final_suggestions,
            "metadata": {
                "total_suggestions": len(processed_suggestions),
                "successful_charts": len(final_suggestions),
                "failed_charts": len(processed_suggestions) - len(final_suggestions),
                "target_name": processing_summary.get("company_name", processing_summary.get("target_name", "")),
                "processing_time": processing_summary.get("processing_time", "")
            }
        }
        
        print(f"   ✅ 可视化结果处理完成，最终可用图表: {len(final_suggestions)}")
        return visualization_data
    
    def _standardize_data_structure(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化数据结构，适配新的数据格式"""
        # 标准化大纲数据结构
        if 'outline' in data:
            outline_data = data['outline']
            # 适配新的数据格式：直接包含reportOutline的结构
            if "reportOutline" in outline_data:
                data['outline'] = {"outline": outline_data["reportOutline"]}
            elif isinstance(outline_data, list):
                data['outline'] = {"outline": outline_data}
            elif "outline" not in outline_data and isinstance(outline_data, dict):
                # 如果是直接的outline数据，包装一下
                if any(key in outline_data for key in ["companyName", "companyCode"]):
                    # 保持原有结构
                    pass
                else:
                    data['outline'] = {"outline": outline_data}
        
        # 标准化分配数据结构
        if 'allocation' in data:
            allocation_data = data['allocation']
            # 适配新格式：outline_with_allocations包含了完整的分配信息
            if "outline_with_allocations" in allocation_data:
                data['allocation'] = allocation_data["outline_with_allocations"]
            
        return data
    
    def _smart_section_match(self, chart_section: str, outline_sections: List[str]) -> str:
        """智能匹配图表section和大纲section"""
        import re
        
        # 处理输入的图表章节标识
        chart_section = str(chart_section).strip()
        
        # 1. 直接匹配：如果chart_section就是"一"、"二"等，直接匹配
        if chart_section in ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]:
            for outline_section in outline_sections:
                if outline_section.startswith(f"{chart_section}、"):
                    return outline_section
        
        # 2. 提取数字前缀进行匹配
        def extract_number(section_title):
            match = re.match(r'^([一二三四五六七八九十]+)、', section_title)
            if match:
                chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                return chinese_nums.get(match.group(1), 0)
            return 0
        
        # 如果chart_section是数字，转换为对应的中文数字
        try:
            if chart_section.isdigit():
                num = int(chart_section)
                num_to_chinese = {1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '七', 8: '八', 9: '九', 10: '十'}
                if num in num_to_chinese:
                    target_chinese = num_to_chinese[num]
                    for outline_section in outline_sections:
                        if outline_section.startswith(f"{target_chinese}、"):
                            return outline_section
        except:
            pass
        
        chart_num = extract_number(chart_section)
        
        # 3. 数字前缀精确匹配
        if chart_num > 0:
            for outline_section in outline_sections:
                if extract_number(outline_section) == chart_num:
                    return outline_section
        
        # 4. 关键词匹配
        chart_keywords = set(re.findall(r'[\u4e00-\u9fff]+', chart_section.replace('、', '')))
        
        best_match = None
        best_score = 0
        
        for outline_section in outline_sections:
            outline_keywords = set(re.findall(r'[\u4e00-\u9fff]+', outline_section.replace('、', '')))
            # 计算交集得分
            intersection = chart_keywords & outline_keywords
            if intersection:
                score = len(intersection) / max(len(chart_keywords), len(outline_keywords))
                if score > best_score:
                    best_score = score
                    best_match = outline_section
        
        # 5. 如果关键词匹配分数足够高（>0.2），返回最佳匹配
        if best_score > 0.2:
            return best_match
            
        return None
    
    def determine_sections_with_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        确定各章节的数据分配情况，包括图表分配
        适配新的数据结构
        """
        print("📋 解析章节数据分配情况...")
        
        # 从统一数据结构中提取信息
        outline_data = data.get('outline', {})
        allocation_result = data.get('allocation', {})
        visualization_results = data.get('visualizations', {})
        
        sections_with_data = []
        
        # 适配新的数据结构
        if "reportOutline" in outline_data:
            outline = outline_data["reportOutline"]
        elif "outline" in outline_data:
            outline = outline_data["outline"]
        else:
            outline = outline_data.get("reportOutline", outline_data.get("outline", []))
        
        # 处理分配结果 - 适配新的数据结构
        if "reportOutline" in allocation_result:
            # 新格式：分配信息直接嵌入在outline中
            allocated_outline = allocation_result["reportOutline"]
            allocated_sections = {}
            for section in allocated_outline:
                title = section.get("title", "")
                allocated_data_ids = section.get("allocated_data_ids", [])
                allocated_sections[title] = allocated_data_ids
        else:
            # 旧格式兼容
            allocated_sections = allocation_result.get("allocated_sections", {})
            
            if not allocated_sections and isinstance(allocation_result, list):
                # 如果allocation_result是列表格式，需要转换
                for item in allocation_result:
                    if isinstance(item, dict) and "title" in item:
                        title = item["title"]
                        allocated_data_ids = item.get("allocated_data_ids", [])
                        allocated_sections[title] = allocated_data_ids
        
        # 解析图表分配结果
        chart_allocation = {}
        if visualization_results and "processed_suggestions" in visualization_results:
            print("   📊 处理可视化图表分配...")
            processed_suggestions = visualization_results.get("processed_suggestions", [])
            
            # 建立智能匹配映射
            outline_sections = [section.get("title", "") for section in outline]
            
            for suggestion in processed_suggestions:
                if suggestion.get("success") and suggestion.get("has_png"):
                    section = suggestion.get("section", "")
                    if section:
                        # 智能匹配：找到最匹配的大纲section
                        matched_section = self._smart_section_match(section, outline_sections)
                        if matched_section:
                            if matched_section not in chart_allocation:
                                chart_allocation[matched_section] = []
                            
                            # 构建图表信息
                            chart_info = {
                                "chart_title": suggestion.get("chart_title", ""),
                                "chart_type": suggestion.get("chart_type", ""),
                                "image_description": suggestion.get("image_description", ""),
                                "png_path": suggestion.get("png_path", ""),
                                "section": section,
                                "priority": suggestion.get("priority", "medium"),
                                "reason": suggestion.get("reason", ""),
                                "asset_id": suggestion.get("asset_id", ""),
                                "file_size": suggestion.get("file_size", 0),
                                "status": "success",
                                "data_source_ids": suggestion.get("data_source_ids", []),
                                "timestamp": suggestion.get("timestamp", "")
                            }
                            chart_allocation[matched_section].append(chart_info)
        
        for i, section in enumerate(outline):
            section_title = section.get("title", "")
            section_points = section.get("points", [])
            
            # 获取分配的数据ID
            allocated_data_ids = allocated_sections.get(section_title, [])
            
            # 获取分配的图表
            allocated_charts = chart_allocation.get(section_title, [])
            
            section_info = {
                "index": i + 1,
                "title": section_title,
                "points": section_points,
                "allocated_data_ids": allocated_data_ids,
                "allocated_charts": allocated_charts,
                "has_data": len(allocated_data_ids) > 0,
                "has_charts": len(allocated_charts) > 0
            }
            
            sections_with_data.append(section_info)
            
            print(f"   📄 {section_title}: {len(allocated_data_ids)}数据 + {len(allocated_charts)}图表")
        
        total_data = sum(len(s["allocated_data_ids"]) for s in sections_with_data)
        total_charts = sum(len(s["allocated_charts"]) for s in sections_with_data)
        print(f"✅ 章节解析完成: 共{len(sections_with_data)}章节, {total_data}数据项, {total_charts}图表")
        
        return sections_with_data


# ====================
# 基础内容组装器
# ====================

class ReportContentAssembler:
    """统一的报告内容组装器"""
    
    def __init__(self):
        # 全局参考文献管理
        self.global_references = []  # 存储所有参考文献
        self.global_id_to_ref = {}   # 数据ID到参考文献序号的映射
    
    def reset_references(self):
        """重置参考文献状态（用于生成新报告时）"""
        self.global_references = []
        self.global_id_to_ref = {}
    
    def update_global_references(self, data_items: List[Dict[str, Any]]) -> None:
        """更新全局参考文献映射，适配新的数据结构"""
        for data_item in data_items:
            data_id = data_item.get("id")
            # 构建source_info，适配新的数据结构
            source_info = {
                "title": data_item.get("title", "无标题"),
                "url": data_item.get("url", ""),
                "data_source_type": data_item.get("data_source_type", ""),
                "search_query": data_item.get("search_query", "")
            }
            
            if data_id and data_id not in self.global_id_to_ref:
                self.global_references.append(source_info)
                self.global_id_to_ref[data_id] = len(self.global_references)
    
    def convert_data_ids_to_references(self, content: str) -> str:
        """将数据ID转换为参考文献序号"""
        for data_id, ref_num in self.global_id_to_ref.items():
            content = content.replace(f"[{data_id}]", f"[{ref_num}]")
        return content
    
    def build_chart_content(self, allocated_charts: List[Dict[str, Any]]) -> str:
        """构建图表内容字符串，包含完整的图表信息供LLM进行图表增强，并给出markdown绝对路径图片引用示例"""
        if not allocated_charts:
            return "本章节暂无可用图表。"
        
        chart_content = "### 可用图表资源:\n\n"
        for i, chart in enumerate(allocated_charts, 1):
            # 兼容新旧格式的字段映射
            title = (chart.get("chart_title", "") or 
                    chart.get("title", "") or 
                    f"图表{i}")
            
            description = (chart.get("image_description", "") or 
                          chart.get("description", "") or 
                          "无描述")
            
            chart_type = (chart.get("chart_type", "") or 
                         chart.get("visualization_type", "") or 
                         "未知类型")
            
            png_path = (chart.get("png_path", "") or 
                       chart.get("chart_png_path", "") or 
                       "")
            
            chart_html = chart.get("chart_html", "")
            priority = chart.get("priority", "")
            reason = chart.get("reason", "")
            asset_id = chart.get("asset_id", "")
            data_source = chart.get("data_source", "")
            
            chart_content += f"**图{i}: {title}**\n"
            chart_content += f"- 图表类型: {chart_type}\n"
            chart_content += f"- 图片绝对路径: {png_path}\n"
            chart_content += f"- **Markdown图片引用**: ![]({png_path})\n"
            
            if priority:
                chart_content += f"- 优先级: {priority}\n"
            if reason:
                chart_content += f"- 分析价值: {reason}\n"
            if asset_id:
                chart_content += f"- 资产ID: {asset_id}\n"
            if data_source:
                chart_content += f"- 数据来源: {data_source}\n"
            
            # 重要：添加详细的图表描述
            if description and description != "无描述":
                chart_content += f"- **详细描述**: {description}\n"
            
            # 如果有HTML代码，也提供给LLM参考
            if chart_html:
                chart_content += f"- **图表HTML代码**: \n```html\n{chart_html[:500]}{'...(代码过长已截断)' if len(chart_html) > 500 else ''}\n```\n"
                
            chart_content += "\n"
        
        chart_content += "**图表引用说明**: \n"
        chart_content += "1. 在分析中引用图表时，请使用markdown语法 ![](绝对路径) 插入图片，绝对路径见上方。\n"
        chart_content += "2. 请结合图表的详细描述进行深入分析，不要简单重复描述内容。\n"
        chart_content += "3. 重点解读图表中的数据趋势、对比结果和业务含义。\n"
        chart_content += "4. 将图表分析与章节主题紧密结合，提供有价值的洞察。\n\n"
        
        return chart_content
    
    def build_data_content(self, collected_data_info: Dict[str, Any], processing_method: str) -> str:
        """构建数据内容字符串"""
        data_content = ""
        
        if processing_method == "summarized":
            summary = collected_data_info.get("summary", "")
            data_content = f"### 数据摘要:\n\n{summary}\n\n"
        elif processing_method == "full_data":
            for data_item in collected_data_info.get("collected_data", []):
                content = data_item.get("content", "")
                data_id = data_item.get("id")
                
                if content and data_id:
                    ref_num = self.global_id_to_ref.get(data_id, data_id)
                    data_content += f"**数据来源[{ref_num}]**: {content}\n\n"
        elif processing_method == "selected_data":
            for data_item in collected_data_info.get("collected_data", []):
                content = data_item.get("content", "")
                data_id = data_item.get("id")
                
                if content and data_id:
                    ref_num = self.global_id_to_ref.get(data_id, data_id)
                    data_content += f"**关键数据[{ref_num}]**: {content}\n\n"
        
        if not data_content:
            data_content = "本章节暂无相关数据支撑。\n\n"
        
        return data_content
    
    def get_report_title(self, subject_name: str, report_type: str = "研究报告") -> str:
        """获取报告标题"""
        return f"{subject_name}{report_type}"
    
    def assemble_final_report(
        self,
        subject_name: str,
        report_plan: Dict[str, Any],
        generated_sections: List[Dict[str, Any]],
        report_type: str = "研究报告"
    ) -> Dict[str, Any]:
        """组装最终报告"""
        report_title = self.get_report_title(subject_name, report_type)
        
        # 统计信息
        total_sections = len(generated_sections)
        sections_with_data = len([s for s in generated_sections if s.get("generation_method") != "no_data"])
        total_charts = sum(len(s.get("allocated_charts", [])) for s in generated_sections)
        
        final_report = {
            "report_title": report_title,
            "subject_name": subject_name,
            "report_plan": report_plan,
            "sections": generated_sections,
            "references": self.global_references,
            "generation_stats": {
                "total_sections": total_sections,
                "sections_with_data": sections_with_data,
                "sections_without_data": total_sections - sections_with_data,
                "total_charts": total_charts
            }
        }
        
        # 生成markdown内容
        final_report["content"] = self.assemble_markdown_report(final_report)
        
        return final_report
    
    def assemble_markdown_report(self, final_report: dict) -> str:
        """将最终报告转换为Markdown格式"""
        lines = []
        subject_name = final_report.get("subject_name", "研究主体")
        report_title = final_report.get("report_title", f"{subject_name}研究报告")
        sections = final_report.get("sections", [])
        references = final_report.get("references", [])
        
        # 报告标题
        lines.append(f"# {report_title}\n")
        
        # 目录
        lines.append("## 目录\n")
        for i, section in enumerate(sections, 1):
            title = section.get("section_title", f"章节{i}")
            # 检查标题是否已经包含中文序号
            if any(num in title for num in ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']):
                lines.append(f"{title}")
            else:
                lines.append(f"{i}. {title}")
        lines.append("")
        
        # 章节内容
        for i, section in enumerate(sections, 1):
            title = section.get("section_title", f"章节{i}")
            content = section.get("content", "")
            
            # 检查标题是否已经包含中文序号
            if any(num in title for num in ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']):
                lines.append(f"## {title}\n")
            else:
                lines.append(f"## {i}. {title}\n")
            
            lines.append(content)
            lines.append("\n")
        
        # 参考文献
        if references:
            lines.append("## 参考文献\n")
            for i, ref in enumerate(references, 1):
                title = ref.get("title", "无标题")
                url = ref.get("url", "")
                if url:
                    lines.append(f"[{i}] {title} - {url}")
                else:
                    lines.append(f"[{i}] {title}")
            lines.append("")
        
        return "\n".join(lines)


# ====================
# 统一报告生成器
# ====================

class UnifiedReportGenerator:
    """统一的报告生成器，支持公司、行业、宏观报告"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        report_type: str = "company",  # company, industry, macro
        max_context_tokens: int = 128 * 1024,
        context_usage_ratio: float = 0.8
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.report_type = report_type
        self.max_context_tokens = max_context_tokens
        self.available_tokens = int(max_context_tokens * context_usage_ratio)
        
        # 初始化组件
        self._initialize_components()
        self._setup_prompts()
    
    def _initialize_components(self):
        """初始化各个组件"""
        self.token_calculator = TransformerTokenCalculator(model_name="deepseek-ai/DeepSeek-V3-0324")
        self.data_processor = ReportDataProcessor()
        self.content_assembler = ReportContentAssembler()
    
    def _setup_prompts(self):
        """根据报告类型设置提示词"""
        if self.report_type == "company":
            self.section_with_data_prompt = COMPANY_SECTION_WITH_DATA_PROMPT
            self.section_without_data_prompt = COMPANY_SECTION_WITHOUT_DATA_PROMPT
            self.chart_enhancement_prompt = SECTION_CHART_ENHANCEMENT_PROMPT
        elif self.report_type == "industry":
            self.section_with_data_prompt = INDUSTRY_SECTION_WITH_DATA_PROMPT
            self.section_without_data_prompt = INDUSTRY_SECTION_WITHOUT_DATA_PROMPT
            self.chart_enhancement_prompt = SECTION_CHART_ENHANCEMENT_PROMPT
        elif self.report_type == "macro":
            self.section_with_data_prompt = MACRO_SECTION_WITH_DATA_PROMPT
            self.section_without_data_prompt = MACRO_SECTION_WITHOUT_DATA_PROMPT
            self.chart_enhancement_prompt = SECTION_CHART_ENHANCEMENT_PROMPT
        else:
            raise ValueError(f"不支持的报告类型: {self.report_type}")
    
    @classmethod
    def from_env(cls, report_type: str = "company", context_usage_ratio: float = 0.8):
        """从环境变量创建报告生成器"""
        load_dotenv()
        
        # 使用通用API配置（硅基流动等），与base_data_collection保持一致
        api_key = os.getenv("GUIJI_API_KEY")
        base_url = os.getenv("GUIJI_BASE_URL") 
        model = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO")
        max_context_tokens = int(128 * 1024 * context_usage_ratio)
        
        if not all([api_key, base_url, model]):
            raise ValueError("缺少必要的环境变量: GUIJI_API_KEY, GUIJI_BASE_URL, GUIJI_TEXT_MODEL_DEEPSEEK_PRO")
        
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            report_type=report_type,
            max_context_tokens=max_context_tokens,
            context_usage_ratio=1.0
        )
    
    def load_report_data(self, **kwargs) -> Dict[str, Any]:
        """加载报告数据"""
        return self.data_processor.load_report_data(**kwargs)
    
    def generate_complete_report(
        self,
        subject_name: str,
        data: Dict[str, Any],
        output_file: str = None,
        enable_chart_enhancement: bool = True
    ) -> Dict[str, Any]:
        """生成完整的研究报告
        
        Args:
            subject_name: 研究主体名称
            data: 统一数据结构（包含所有必要数据）
            output_file: 输出文件路径
            enable_chart_enhancement: 是否启用图表增强（默认True）
        """
        print(f"\n📝 开始生成 {subject_name} {self.report_type} 研究报告...")
        
        # 重置参考文献状态
        self.content_assembler.reset_references()
        
        # 1. 解析大纲和数据分配
        sections_with_data = self.data_processor.determine_sections_with_data(data)
        print(f"📋 报告包含 {len(sections_with_data)} 个章节")
        
        # 2. 创建简单的报告上下文
        report_context = {
            "subject_name": subject_name,
            "total_sections": len(sections_with_data)
        }
        
        # 3. 提取扁平化数据
        all_flattened_data = data.get('flattened_data', [])
        visualization_results = data.get('visualizations', {})
        
        # 4. 生成章节内容（包含增量式数据处理和立即图表增强）
        print(f"\n🔄 生成章节内容（数据+图表增强）...")
        generated_sections = []
        for i, section_info in enumerate(sections_with_data):
            print(f"\n📝 生成第 {i+1}/{len(sections_with_data)} 章节: {section_info['title']}")
            
            section_content = self._generate_section_content_base(
                section_info=section_info,
                subject_name=subject_name,
                all_data=all_flattened_data,
                report_context=report_context,
                enable_chart_enhancement=enable_chart_enhancement
            )
            
            generated_sections.append(section_content)
            print(f"✅ 章节 '{section_info['title']}' 生成完成")
        
        # 5. 跳过第二轮增强（因为已经在第4步中完成了）
        print(f"\n✅ 所有章节已完成增量式生成和图表增强")
        
        # 6. 组装完整报告
        final_report = self.content_assembler.assemble_final_report(
            subject_name=subject_name,
            report_plan=report_context,
            generated_sections=generated_sections,
            report_type=f"{self.report_type}研究报告"
        )
        
        # 7. 保存报告
        if output_file:
            if output_file.lower().endswith(".md"):
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(final_report["content"])
                print(f"📁 Markdown 报告已保存到: {output_file}")
            else:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(final_report, f, ensure_ascii=False, indent=2)
                print(f"� JSON 报告已保存到: {output_file}")
        
        # 8. 生成统计信息
        stats = {
            "total_sections": len(generated_sections),
            "sections_with_data": sum(1 for s in sections_with_data if s["has_data"]),
            "sections_without_data": sum(1 for s in sections_with_data if not s["has_data"]), 
            "total_charts": sum(len(s.get("allocated_charts", [])) for s in sections_with_data)
        }
        
        print(f"🎉 {subject_name} {self.report_type} 研究报告生成完成！")
        return final_report
    
    def _generate_section_content_base(
        self,
        section_info: Dict[str, Any],
        subject_name: str,
        all_data: List[Dict[str, Any]],
        report_context: Dict[str, Any],
        enable_chart_enhancement: bool = True
    ) -> Dict[str, Any]:
        """生成章节内容：先基础内容，然后立即检查图表增强"""
        section_title = section_info["title"]
        section_points = section_info["points"]
        allocated_data_ids = section_info["allocated_data_ids"]
        allocated_charts = section_info.get("allocated_charts", [])
        
        print(f"   📊 准备章节数据...")
        
        # 1. 直接获取分配给此章节的数据
        allocated_data_info = self._get_allocated_data_direct(
            allocated_data_ids=allocated_data_ids,
            all_data=all_data
        )
        
        # 2. 生成基础内容（不包含图表）
        if not allocated_data_info["has_data"]:
            print(f"   ⚠️  无数据支撑，生成基础框架")
            base_content = self._generate_section_without_data(section_info, subject_name)
        else:
            print(f"   📝 基于分配数据生成内容 (数据条数: {len(allocated_data_info['data_items'])})")
            base_content = self._generate_section_with_data_incremental(
                section_info=section_info,
                allocated_data_info=allocated_data_info,
                subject_name=subject_name,
                report_context=report_context
            )
        
        # 3. 立即检查是否有图表，如果有则进行图表增强
        final_content = base_content
        has_chart_enhancement = False
        
        if enable_chart_enhancement and len(allocated_charts) > 0:
            print(f"   🎨 发现 {len(allocated_charts)} 个图表，立即进行图表增强...")
            
            # 构建图表内容
            chart_content = self.content_assembler.build_chart_content(allocated_charts)
            
            # 使用图表增强提示词
            enhancement_prompt = self.chart_enhancement_prompt.format(
                original_content=base_content,
                chart_content=chart_content
            )
            
            try:
                enhanced_content = chat_no_tool(
                    user_content=enhancement_prompt,
                    system_content="",
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    temperature=0.3,
                    max_tokens=8192
                )
                
                final_content = enhanced_content.strip()
                has_chart_enhancement = True
                print(f"     ✅ 图表增强完成")
                
            except Exception as e:
                print(f"     ⚠️ 图表增强失败，保留基础内容: {e}")
                has_chart_enhancement = False
        else:
            print(f"   ⏭️  无图表或禁用图表增强，跳过增强步骤")
        
        return {
            "section_index": section_info["index"],
            "section_title": section_title,
            "section_points": section_points,
            "content": final_content,
            "data_info": allocated_data_info,
            "allocated_charts": allocated_charts,
            "charts_count": len(allocated_charts),
            "generation_method": "incremental" if allocated_data_info["has_data"] else "no_data",
            "has_chart_enhancement": has_chart_enhancement  # 标记是否已进行图表增强
        }

    def _get_allocated_data_direct(
        self,
        allocated_data_ids: List[str],
        all_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """直接获取分配给章节的数据，不进行总结，适配新的数据结构"""
        if not allocated_data_ids:
            return {
                "has_data": False,
                "data_items": [],
                "total_data_count": 0
            }
        
        # 根据ID查找对应的数据，新数据结构中ID是字符串
        data_items = []
        for data_item in all_data:
            item_id = str(data_item.get("id", ""))
            if item_id in allocated_data_ids:
                data_items.append(data_item)
        
        return {
            "has_data": len(data_items) > 0,
            "data_items": data_items,
            "total_data_count": len(data_items)
        }
    
    def _generate_section_with_data_incremental(
        self,
        section_info: Dict[str, Any],
        allocated_data_info: Dict[str, Any],
        subject_name: str,
        report_context: Dict[str, Any]
    ) -> str:
        """基于分配的数据进行增量式内容生成，适配新的数据结构"""
        section_title = section_info["title"]
        points = section_info["points"]
        data_items = allocated_data_info["data_items"]
        
        # 构建基础提示词
        points_text = "\n".join([f"- {point}" for point in points])
        
        # 初始化内容
        current_content = ""
        used_token_count = 0
        
        # 计算基础提示词的token数
        base_prompt = self.section_with_data_prompt.format(
            subject_name=subject_name,
            section_title=section_title,
            points_text=points_text,
            data_content=""
        )
        base_tokens = self.token_calculator.count_tokens(base_prompt)
        
        # 为当前内容和输出预留token
        content_tokens = self.token_calculator.count_tokens(current_content) if current_content else 0
        output_tokens = 8192  # 预留输出token
        available_tokens = self.available_tokens - base_tokens - content_tokens - output_tokens
        
        print(f"      可用tokens: {available_tokens}, 数据项: {len(data_items)}")
        
        # 更新全局参考文献
        self.content_assembler.update_global_references(data_items)
        
        # 增量式添加数据并生成内容
        batch_data = []
        batch_tokens = 0
        
        for i, data_item in enumerate(data_items):
            content = data_item.get("content", "")
            data_id = str(data_item.get("id", ""))
            
            if not content:
                continue
            
            # 获取参考文献编号
            ref_num = self.content_assembler.global_id_to_ref.get(data_id, data_id)
            formatted_data = f"**数据来源[{ref_num}]**: {content}\n\n"
            data_tokens = self.token_calculator.count_tokens(formatted_data)
            
            # 检查是否可以添加到当前批次
            if batch_tokens + data_tokens <= available_tokens:
                batch_data.append(formatted_data)
                batch_tokens += data_tokens
            else:
                # 当前批次已满，生成内容
                if batch_data:
                    batch_content = self._generate_content_with_batch(
                        subject_name, section_title, points_text, 
                        "".join(batch_data), current_content
                    )
                    if batch_content:
                        current_content = batch_content
                        # 重新计算当前内容的token数
                        content_tokens = self.token_calculator.count_tokens(current_content)
                        available_tokens = self.available_tokens - base_tokens - content_tokens - output_tokens
                        print(f"      已生成内容，剩余tokens: {available_tokens}")
                
                # 开始新批次
                batch_data = [formatted_data]
                batch_tokens = data_tokens
            
            print(f"      处理数据 {i+1}/{len(data_items)}, 批次tokens: {batch_tokens}")
        
        # 处理最后一个批次
        if batch_data:
            batch_content = self._generate_content_with_batch(
                subject_name, section_title, points_text, 
                "".join(batch_data), current_content
            )
            if batch_content:
                current_content = batch_content
        
        return current_content if current_content else self._generate_section_without_data(section_info, subject_name)
    
    def _generate_content_with_batch(
        self,
        subject_name: str,
        section_title: str,
        points_text: str,
        batch_data: str,
        current_content: str
    ) -> str:
        """使用当前批次数据生成或增强内容"""
        
        if current_content:
            # 增量模式：基于已有内容继续扩展
            prompt = f"""你是一个专业的研究报告撰写专家。现在需要你基于已有的章节内容和新增的数据，继续完善和扩展这个章节。

**研究主体**: {subject_name}
**章节标题**: {section_title}
**章节要点**:
{points_text}

**已有内容**:
{current_content}

**新增数据**:
{batch_data}

**任务要求**:
1. 基于新增数据，继续完善和扩展已有内容
2. 确保新内容与已有内容逻辑连贯
3. 适当引用数据来源，使用[数字]格式标注
4. 保持专业的分析深度和客观性
5. 不要重复已有内容，只增加新的分析和见解

请输出完整的章节内容（包含已有内容的改进版本）:"""
        else:
            # 初始模式：基于数据生成全新内容
            prompt = self.section_with_data_prompt.format(
                subject_name=subject_name,
                section_title=section_title,
                points_text=points_text,
                data_content=batch_data
            )
        
        try:
            response = chat_no_tool(
                user_content=prompt,
                system_content="",
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.4,
                max_tokens=8192
            )
            return response.strip()
        except Exception as e:
            print(f"        ❌ 内容生成失败: {e}")
            return current_content  # 返回已有内容

    def _enhance_sections_with_charts(
        self,
        generated_sections: List[Dict[str, Any]],
        subject_name: str
    ) -> List[Dict[str, Any]]:
        """第二轮增强：对有图表的章节进行图表增强"""
        enhanced_sections = []
        
        for section in generated_sections:
            allocated_charts = section.get("allocated_charts", [])
            
            if len(allocated_charts) > 0:
                print(f"   🎨 增强章节 '{section['section_title']}' ({len(allocated_charts)}个图表)")
                
                # 构建图表内容
                chart_content = self.content_assembler.build_chart_content(allocated_charts)
                
                # 使用图表增强提示词
                enhancement_prompt = self.chart_enhancement_prompt.format(
                    original_content=section["content"],
                    chart_content=chart_content
                )
                
                try:
                    enhanced_content = chat_no_tool(
                        user_content=enhancement_prompt,
                        system_content="",
                        api_key=self.api_key,
                        base_url=self.base_url,
                        model=self.model,
                        temperature=0.3,
                        max_tokens=8192
                    )
                    
                    # 更新章节内容
                    section["content"] = enhanced_content.strip()
                    section["has_chart_enhancement"] = True
                    print(f"     ✅ 图表增强完成")
                    
                except Exception as e:
                    print(f"     ⚠️ 图表增强失败，保留原内容: {e}")
                    section["has_chart_enhancement"] = False
            else:
                print(f"   ⏭️  章节 '{section['section_title']}' 无图表，跳过增强")
                section["has_chart_enhancement"] = False
            
            enhanced_sections.append(section)
        
        return enhanced_sections
    
    def _generate_section_without_data(self, section_info: Dict[str, Any], subject_name: str) -> str:
        """为无数据支撑的章节生成基础框架"""
        section_title = section_info["title"]
        points = section_info["points"]
        
        points_text = "\n".join([f"- {point}" for point in points])
        
        prompt = self.section_without_data_prompt.format(
            subject_name=subject_name,
            section_title=section_title,
            points_text=points_text
        )

        try:
            response = chat_no_tool(
                user_content=prompt,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.5,
                max_tokens=1024
            )
            return response.strip()
        except Exception as e:
            print(f"     ❌ 章节框架生成失败: {e}")
            return f"""本章节旨在分析{subject_name}在{section_title}方面的表现。主要关注以下方面：

{points_text}

*注：本章节需要进一步收集相关数据以提供详细分析。*"""


# ====================
# 便捷创建函数
# ====================

def create_company_generator(**kwargs) -> UnifiedReportGenerator:
    """创建公司报告生成器"""
    return UnifiedReportGenerator(report_type="company", **kwargs)

def create_industry_generator(**kwargs) -> UnifiedReportGenerator:
    """创建行业报告生成器"""
    return UnifiedReportGenerator(report_type="industry", **kwargs)

def create_macro_generator(**kwargs) -> UnifiedReportGenerator:
    """创建宏观报告生成器"""
    return UnifiedReportGenerator(report_type="macro", **kwargs)


# ====================
# 主程序示例
# ====================

if __name__ == "__main__":
    """主程序入口 - 生成行业研究报告示例"""
    
    # 加载环境变量
    load_dotenv()
    
    # 行业报告配置
    industry_name = "中国智能服务机器人产业"
    data_directory = "test_industry_datas"
    images_directory = "test_industry_datas/images"
    output_file = "test_industry_datas/generated_industry_report_unified.md"
    
    try:
        print("📂 加载行业数据文件...")
        
        # 创建行业报告生成器
        generator = UnifiedReportGenerator.from_env(report_type="industry")
        
        # 加载数据 - 使用新的统一接口
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=images_directory
        )
        print("✅ 行业数据加载完成")
        
        print(f"🚀 开始生成 {industry_name} 行业研究报告...")
        
        # 生成报告 - 使用新的统一接口
        report = generator.generate_complete_report(
            subject_name=industry_name,
            data=data,
            output_file=output_file
        )
        
        # 显示统计信息
        print(f"\n📊 行业报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")
        
        print(f"\n🎉 {industry_name} 行业研究报告生成完成!")
        print(f"📁 报告文件: {output_file}")
        
    except Exception as e:
        print(f"❌ 行业报告生成失败: {e}")
        traceback.print_exc()
