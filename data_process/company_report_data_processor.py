"""
公司研报数据处理器
负责处理所有报告生成前的数据准备和解析工作
"""

import json
import os
from typing import List, Dict, Any, Optional, Tuple
from data_process.base_report_data_processor import BaseReportDataProcessor


class CompanyReportDataProcessor(BaseReportDataProcessor):
    """公司研报数据处理器 - 负责数据加载、解析和预处理"""
    
    def __init__(self):
        """初始化数据处理器"""
        pass
    
    def load_report_data(
        self,
        company_outline_file: str,
        allocation_result_file: str,
        flattened_data_file: str,
        enhanced_allocation_file: str = None,
        visualization_results_file: str = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        加载报告生成所需的数据文件
        
        Args:
            company_outline_file: 公司大纲文件路径
            allocation_result_file: 数据分配结果文件路径
            flattened_data_file: 展平数据文件路径
            enhanced_allocation_file: 增强分配结果文件路径（可选）
            visualization_results_file: 可视化结果文件路径（可选）
            
        Returns:
            (outline_data, allocation_result, flattened_data, visualization_results) 元组
        """
        print("📁 加载报告生成所需数据...")
        
        # 加载大纲数据
        with open(company_outline_file, "r", encoding="utf-8") as f:
            outline_data = json.load(f)
        print(f"✅ 大纲数据加载完成: {len(outline_data.get('reportOutline', []))} 个章节")
        
        # 优先使用可视化结果，其次是增强分配结果
        if visualization_results_file and os.path.exists(visualization_results_file):
            with open(visualization_results_file, "r", encoding="utf-8") as f:
                visualization_results = json.load(f)
            
            # 加载基础分配结果
            allocation_file = enhanced_allocation_file if enhanced_allocation_file and os.path.exists(enhanced_allocation_file) else allocation_result_file
            with open(allocation_file, "r", encoding="utf-8") as f:
                allocation_result = json.load(f)
            
            summary = visualization_results.get("summary", {})
            print(f"✅ 可视化结果加载完成: {summary.get('successful_visualizations', 0)} 个可视化建议")
        else:
            visualization_results = None
            # 使用普通的数据分配结果
            allocation_file = enhanced_allocation_file if enhanced_allocation_file and os.path.exists(enhanced_allocation_file) else allocation_result_file
            with open(allocation_file, "r", encoding="utf-8") as f:
                allocation_result = json.load(f)
            
            allocation_type = "增强" if allocation_file == enhanced_allocation_file else "原始"
            stats = allocation_result.get("allocation_stats", {})
            print(f"✅ {allocation_type}分配结果加载完成: 匹配率 {stats.get('match_rate', 0):.1f}%")
        
        # 加载展平数据
        with open(flattened_data_file, "r", encoding="utf-8") as f:
            flattened_data = json.load(f)
        print(f"✅ 展平数据加载完成: {len(flattened_data)} 条数据")
        
        return outline_data, allocation_result, flattened_data, visualization_results
    
    def parse_outline_and_allocation(
        self, 
        outline_data: Dict[str, Any], 
        allocation_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        解析大纲和数据分配结果
        
        Args:
            outline_data: 原始大纲数据
            allocation_result: 数据分配结果
            
        Returns:
            包含数据分配信息的章节列表
        """
        sections_with_data = []
        
        outline_sections = outline_data.get("reportOutline", [])
        allocated_sections = allocation_result.get("outline_with_allocations", {}).get("reportOutline", [])
        
        for i, outline_section in enumerate(outline_sections):
            # 找到对应的分配数据
            allocated_data_ids = []
            if i < len(allocated_sections):
                allocated_data_ids = allocated_sections[i].get("allocated_data_ids", [])
            
            section_info = {
                "index": i,
                "title": outline_section.get("title", f"章节{i+1}"),
                "points": outline_section.get("points", []),
                "allocated_data_ids": allocated_data_ids,
                "allocated_charts": [],  # 无可视化数据时为空列表
                "data_count": len(allocated_data_ids)
            }
            
            sections_with_data.append(section_info)
        
        return sections_with_data
    
    def parse_outline_with_visualization(
        self, 
        outline_data: Dict[str, Any], 
        allocation_result: Dict[str, Any],
        visualization_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        解析大纲、数据分配和可视化结果
        
        Args:
            outline_data: 原始大纲数据
            allocation_result: 数据分配结果
            visualization_results: 可视化结果
            
        Returns:
            包含数据分配和可视化信息的章节列表
        """
        sections_with_data = []
        
        outline_sections = outline_data.get("reportOutline", [])
        allocated_sections = allocation_result.get("outline_with_allocations", {}).get("reportOutline", [])
        
        # 按章节组织可视化建议
        visualization_suggestions = visualization_results.get("analysis_phase", {}).get("visualization_suggestions", [])
        charts_by_section = {}
        for suggestion in visualization_suggestions:
            section = suggestion.get("section", "未分类")
            if section not in charts_by_section:
                charts_by_section[section] = []
            charts_by_section[section].append(suggestion)
        
        for i, outline_section in enumerate(outline_sections):
            # 获取基础信息
            section_title = outline_section.get("title", f"第{i+1}章")
            
            # 查找对应的分配数据
            allocated_data_ids = []
            if i < len(allocated_sections):
                allocated_data_ids = allocated_sections[i].get("allocated_data_ids", [])
            
            # 查找对应的可视化建议
            section_charts = []
            for section_key, charts in charts_by_section.items():
                if section_key in section_title or any(keyword in section_title for keyword in ["一、", "二、", "三、", "四、", "五、", "六、"]):
                    section_charts.extend(charts)
            
            section_info = {
                "index": i,
                "title": section_title,
                "points": outline_section.get("points", []),
                "allocated_data_ids": allocated_data_ids,
                "allocated_charts": section_charts,
                "data_count": len(allocated_data_ids),
                "charts_count": len(section_charts)
            }
            sections_with_data.append(section_info)
        
        return sections_with_data
    
    def determine_sections_with_data(
        self,
        outline_data: Dict[str, Any],
        allocation_result: Dict[str, Any],
        visualization_results: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        根据可用数据决定使用哪种解析方式
        
        Args:
            outline_data: 大纲数据
            allocation_result: 数据分配结果
            visualization_results: 可视化结果（可选）
            
        Returns:
            处理后的章节数据列表
        """
        if visualization_results and "analysis_phase" in visualization_results:
            print("🎨 使用可视化结果解析章节数据")
            return self.parse_outline_with_visualization(
                outline_data, allocation_result, visualization_results
            )
        else:
            print("📊 使用基础数据分配解析章节数据")
            return self.parse_outline_and_allocation(
                outline_data, allocation_result
            )
