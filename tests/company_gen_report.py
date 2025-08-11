"""
公司报告生成器
基于基础框架实现的公司研报生成器
"""

import os
import json
import asyncio
import traceback
from typing import List, Dict, Any
from data_process.base_report_generator import BaseReportGenerator
from data_process.company_report_data_processor import CompanyReportDataProcessor
from data_process.company_report_content_assembler import CompanyReportContentAssembler
from financial_report.utils.chat import chat_no_tool


# ====================
# 提示词模板定义区域
# ====================

# 有数据支撑的章节内容生成提示词 - 用于基于收集到的数据生成专业的研报章节内容
COMPANY_SECTION_WITH_DATA_PROMPT = """你是一位资深的金融分析师和研究专家，具有多年投资银行和证券研究经验。你正在撰写{subject_name}的专业研究报告章节内容。

重要说明：
- 你只需要生成章节的正文内容，不要生成章节标题
- 不要在开头重复章节标题
- 直接从分析内容开始写作
- 不要在文末添加参考文献列表或引用说明
- 只在正文中需要引用数据时使用[序号]格式即可
- 只能使用三级标题（###）及以下的标题，二级标题（##）由我们手动控制，不能使用

你的专业特长：
1. 深度财务分析和估值建模
2. 行业趋势研究和竞争格局分析
3. 公司战略和商业模式评估
4. 风险识别和投资建议制定

写作要求：
1. **深度分析**: 基于提供的数据进行深入、多维度的分析，不要浅尝辄止
2. **专业严谨**: 使用专业的金融术语和分析框架，确保逻辑清晰
3. **数据驱动**: 充分引用和分析具体数据，用数字说话
4. **洞察独到**: 提供有价值的行业洞察和投资观点
5. **格式规范**: 使用标准的段落格式，结构合理
6. **引用规范**: 在引用数据时使用参考文献格式（如[1]、[2]等），在引用图表时使用"见图X"格式

图表引用指导：
- 当分析涉及趋势、对比、结构等可视化数据时，请使用"见图X"格式引用相关图表
- 图表引用应该与分析内容紧密结合，增强论证效果
- 每个重要的数据分析点都应该考虑是否有对应的图表支撑

内容深度要求：
- 每个要点都要有具体的数据支撑和分析论证
- 包含横向对比和纵向趋势分析
- 结合行业背景和宏观环境进行分析
- 提供具体的投资逻辑和风险提示

文字要求：
- 内容详实，单个章节字数在2000-3500字之间
- 避免空洞的表述，每句话都要有实际价值
- 使用专业但易懂的语言，适合机构投资者阅读

重要提醒：
- 当引用数据时，请使用方括号格式如[1]、[2]，不要使用【数据123】格式
- 当引用图表时，请使用"见图X"格式，其中X是图表编号
- 请直接开始正文内容，不要重复章节标题
- 不要在文末添加"参考文献"、"引用数据"等说明性内容
- 正文结束即可，无需额外说明

请为{subject_name}撰写以下章节的正文内容：

**章节主题**: {section_title}

**分析框架和要点**:
{points_text}

**支撑数据**:
{data_content}{chart_content}

**撰写要求**:

1. **正文内容**: 直接开始正文，不要重复章节标题
2. **分析深度**: 对关键数据进行深入解读和分析
3. **数据应用**: 充分引用提供的数据支撑观点，使用[序号]格式引用
4. **图表集成**: 在合适的位置使用"见图X"格式引用图表，增强分析说服力
5. **专业水准**: 使用专业的分析框架和方法论
6. **字数要求**: 内容详实充分，目标字数2000-3000字

请撰写专业、深入的章节正文内容，不包含章节标题。注意在适当位置引用图表来支撑分析观点。"""

# 无数据支撑的章节框架生成提示词 - 用于在缺乏具体数据时生成分析框架和指导性内容
COMPANY_SECTION_WITHOUT_DATA_PROMPT = """你是一位专业的金融分析师和行业专家。需要为{subject_name}的研究报告撰写章节正文内容。

重要说明：
- 你只需要生成章节的正文内容，不要生成章节标题
- 不要在开头重复章节标题
- 直接从分析内容开始写作
- 不要在文末添加任何说明性内容
- 只能使用三级标题（###）及以下的标题，二级标题（##）由我们手动控制，不能使用

虽然目前缺乏具体的数据支撑，但你需要基于行业知识和专业分析框架，提供：
1. 专业的分析思路和逻辑结构
2. 关键的分析要点和关注因素  
3. 行业标准的分析方法和指标
4. 针对该类型公司的通用分析框架

要求：
- 内容专业且具有指导意义
- 提供具体的分析维度和评估标准
- 为后续数据补充留出接口
- 字数控制在2000-3000字
- 直接开始正文，不要重复章节标题
- 不要在文末添加任何总结或说明

请为{subject_name}撰写以下章节的分析框架正文：

**章节主题**: {section_title}

**分析要点**:
{points_text}

**撰写要求**:
1. **分析思路**: 建立该章节的核心分析逻辑和框架
2. **关键指标**: 明确应关注的核心指标和评估标准
3. **分析方法**: 提供专业的分析方法和评估工具
4. **关注要素**: 识别影响该领域的关键因素
5. **数据类型**: 说明理想情况下需要哪些类型的数据
6. **行业对比**: 提供行业标杆和对比维度

注意：请直接开始正文内容，不要重复章节标题。
"""


class CompanyReportGenerator(BaseReportGenerator):

    def _create_data_processor(self):
        """创建公司报告数据处理器"""
        return CompanyReportDataProcessor()
    
    def _create_content_assembler(self):
        """创建公司报告内容组装器"""
        return CompanyReportContentAssembler()
    
    def get_section_with_data_prompt(self) -> str:
        """获取有数据支撑的章节内容生成提示词"""
        return COMPANY_SECTION_WITH_DATA_PROMPT
    
    def get_section_without_data_prompt(self) -> str:
        """获取无数据支撑的章节框架生成提示词"""
        return COMPANY_SECTION_WITHOUT_DATA_PROMPT
    
    def generate_complete_report_with_visualization(
        self,
        subject_name: str,
        outline_data: Dict[str, Any],
        allocation_result: Dict[str, Any],
        all_flattened_data: List[Dict[str, Any]],
        images_dir: str,
        visualization_results: Dict[str, Any] = None,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        生成带有可视化增强的完整研究报告（两轮生成模式）
        
        Args:
            subject_name: 研究主体名称（公司名）
            outline_data: 大纲数据
            allocation_result: 数据分配结果
            all_flattened_data: 所有展平数据
            images_dir: 图片目录路径
            visualization_results: 可视化结果（可选）
            output_file: 输出文件路径
            
        Returns:
            生成的报告内容
        """
        print(f"\n🎨 开始生成 {subject_name} 可视化增强研究报告...")
        
        # ====== 第一轮：生成基础内容 ======
        print("\n🔄 第一轮：生成基础报告内容...")
        
        # 使用基础方法生成初始报告
        base_report = self.generate_complete_report(
            subject_name=subject_name,
            outline_data=outline_data,
            allocation_result=allocation_result,
            all_flattened_data=all_flattened_data,
            visualization_results=visualization_results,
            output_file=None 
        )
        
        print("✅ 基础报告生成完成")
        
        # ====== 第二轮：可视化增强 ======
        print(f"\n🎨 第二轮：加载可视化资源并增强内容...")
        
        # 加载可视化资源
        visualization_resources = self.content_assembler.load_visualization_resources(
            images_dir=images_dir,
            target_name=subject_name,
            name_field='company_name'  # 公司研报使用company_name字段
        )
        
        if not visualization_resources:
            print("⚠️ 未找到可视化资源，返回基础报告")
            if output_file:
                self._save_report(base_report, output_file)
            return base_report
        
        # 详细打印可视化资源分配情况
        print(f"\n🎯 \033[93m可视化资源分配分析：\033[0m")
        print(f"\033[93m总共加载了 {len(visualization_resources)} 个章节的可视化资源\033[0m")
        
        # 分析每个章节的匹配情况
        original_sections = base_report.get("sections", [])
        for section in original_sections:
            section_title = section.get("section_title", "")
            matching_charts = visualization_resources.get(section_title, [])
            
            if matching_charts:
                print(f"\033[93m✅ 章节 '{section_title}' 找到 {len(matching_charts)} 个图表：\033[0m")
                for i, chart in enumerate(matching_charts, 1):
                    chart_title = chart.get('chart_title', f'图表{i}')
                    chart_type = chart.get('chart_type', '未知')
                    png_path = chart.get('png_path', '')
                    png_status = "可用" if png_path and os.path.exists(png_path) else "不可用"
                    print(f"\033[93m   {i}. {chart_title} ({chart_type}) - PNG:{png_status}\033[0m")
            else:
                print(f"\033[93m❌ 章节 '{section_title}' 未找到匹配的图表\033[0m")
        
        # 检查是否有未分配的可视化资源
        unmatched_sections = set(visualization_resources.keys()) - set(s.get("section_title", "") for s in original_sections)
        if unmatched_sections:
            print(f"\n\033[93m⚠️ 发现 {len(unmatched_sections)} 个未匹配的可视化资源章节：\033[0m")
            for section in unmatched_sections:
                charts_count = len(visualization_resources[section])
                print(f"\033[93m   - {section} ({charts_count}个图表)\033[0m")
        
        # 增强每个章节的内容
        enhanced_sections = []
        original_sections = base_report.get("sections", [])
        
        print(f"\n🔄 \033[93m开始章节内容增强（共{len(original_sections)}个章节）：\033[0m")
        
        for idx, section in enumerate(original_sections, 1):
            section_title = section.get("section_title", "")
            original_content = section.get("content", "")
            
            print(f"\n\033[93m📝 [{idx}/{len(original_sections)}] 处理章节: {section_title}\033[0m")
            
            # 直接使用基础组装器的章节匹配逻辑，不需要自定义匹配
            # 基础组装器已经按section字段分组了可视化资源
            matching_charts = visualization_resources.get(section_title, [])
            
            if matching_charts:
                print(f"\033[93m   🎯 发现 {len(matching_charts)} 个匹配图表：\033[0m")
                for i, chart in enumerate(matching_charts, 1):
                    chart_title = chart.get('chart_title', f'图表{i}')
                    chart_type = chart.get('chart_type', '未知')
                    png_path = chart.get('png_path', '')
                    png_status = "✅可用" if png_path and os.path.exists(png_path) else "❌不可用"
                    print(f"\033[93m      {i}. {chart_title} ({chart_type}) {png_status}\033[0m")
                
                # 生成增强内容
                print(f"\033[93m   🎨 正在生成可视化增强内容...\033[0m")
                enhanced_content = self.content_assembler.generate_section_with_visualization(
                    section_title=section_title,
                    original_content=original_content,
                    visualization_charts=matching_charts,
                    llm_call_function=self._call_llm,
                    target_name=subject_name,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    enable_text_visualization=True,
                    output_dir=images_dir
                )
                
                # 统计内容改善情况
                original_length = len(original_content)
                enhanced_length = len(enhanced_content)
                improvement_ratio = (enhanced_length - original_length) / original_length if original_length > 0 else 0
                
                print(f"\033[93m   📈 内容增强完成: {original_length} → {enhanced_length} 字符 (+{improvement_ratio:.1%})\033[0m")
                
                # 更新章节信息
                enhanced_section = section.copy()
                enhanced_section["content"] = enhanced_content
                enhanced_section["visualization_charts"] = matching_charts
                enhanced_section["charts_count"] = len(matching_charts)
                enhanced_section["enhanced"] = True
                enhanced_section["content_stats"] = {
                    "original_length": original_length,
                    "enhanced_length": enhanced_length,
                    "improvement_ratio": improvement_ratio
                }
                
                enhanced_sections.append(enhanced_section)
            else:
                print(f"\033[93m   ➖ 无匹配图表，尝试基于文本生成可视化...\033[0m")
                
                # 即使没有预设图表，也尝试基于文本生成可视化
                enhanced_content = self.content_assembler.generate_section_with_visualization(
                    section_title=section_title,
                    original_content=original_content,
                    visualization_charts=[],  # 空列表，让方法自动生成文本可视化
                    llm_call_function=self._call_llm,
                    target_name=subject_name,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    model=self.model,
                    enable_text_visualization=True,
                    output_dir=images_dir  # 使用传入的images_dir参数
                )
                
                # 检查是否生成了新的可视化内容
                if enhanced_content != original_content:
                    enhanced_section = section.copy()
                    enhanced_section["content"] = enhanced_content
                    enhanced_section["enhanced"] = True
                    enhanced_section["generation_method"] = "text_visualization"
                    enhanced_sections.append(enhanced_section)
                    print(f"\033[93m   ✅ 基于文本生成了可视化内容\033[0m")
                else:
                    section["enhanced"] = False
                    enhanced_sections.append(section)
                    print(f"\033[93m   ➖ 文本可视化生成失败，保持原内容\033[0m")
        
        # 创建增强报告
        enhanced_report = base_report.copy()
        enhanced_report["sections"] = enhanced_sections
        enhanced_report["enhancement_stats"] = self._calculate_enhancement_stats(enhanced_sections)
        
        print("✅ 内容增强完成")
        
        # 保存最终报告
        if output_file:
            self._save_report(enhanced_report, output_file)
        
        print(f"🎉 {subject_name} 可视化增强研究报告生成完成！")
        return enhanced_report
    
    async def generate_complete_report_with_visualization_async(
        self,
        subject_name: str,
        outline_data: Dict[str, Any],
        allocation_result: Dict[str, Any],
        all_flattened_data: List[Dict[str, Any]],
        images_dir: str,
        visualization_results: Dict[str, Any] = None,
        output_file: str = None,
        max_concurrent: int = 190
    ) -> Dict[str, Any]:
        """
        异步生成带有可视化增强的完整研究报告（高并发版本）
        
        Args:
            subject_name: 研究主体名称（公司名）
            outline_data: 大纲数据
            allocation_result: 数据分配结果
            all_flattened_data: 所有展平数据
            images_dir: 图片目录路径
            visualization_results: 可视化结果（可选）
            output_file: 输出文件路径
            max_concurrent: 最大并发数，默认190
            
        Returns:
            生成的报告内容
        """
        print(f"\n🚀 开始高并发生成 {subject_name} 可视化增强研究报告（并发数: {max_concurrent}）...")
        
        # ====== 第一轮：异步生成基础内容 ======
        print("\n🔄 第一轮：异步生成基础报告内容...")
        
        # 重置参考文献状态
        self.content_assembler.reset_references()
        
        # 使用数据处理器确定有数据的章节
        sections_with_data = self.data_processor.determine_sections_with_data(
            outline_data, allocation_result, visualization_results
        )
        print(f"📋 报告包含 {len(sections_with_data)} 个章节")
        
        # 准备章节数据进行并发处理
        sections_data = []
        for i, section_info in enumerate(sections_with_data):
            section_title = section_info["title"]
            section_points = section_info["points"]
            allocated_data_ids = section_info["allocated_data_ids"]
            allocated_charts = section_info.get("allocated_charts", [])
            
            # 收集章节相关数据
            collected_data_info = self.data_collector.collect_data_for_section(
                section_title=section_title,
                section_points=section_points,
                allocated_data_ids=allocated_data_ids,
                all_data=all_flattened_data,
                max_context_tokens=self.available_tokens,
                company_name=subject_name
            )
            
            sections_data.append({
                "section_index": section_info["index"],
                "section_title": section_title,
                "section_points": section_points,
                "collected_data_info": collected_data_info,
                "allocated_charts": allocated_charts,
                "processing_method": collected_data_info["processing_method"],
                "subject_name": subject_name
            })
        
        # 使用content_assembler的异步批量处理方法
        print(f"📋 准备异步处理 {len(sections_data)} 个章节...")
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent // 2)  # 第一轮使用一半并发
        
        async def generate_single_section(section_data: Dict[str, Any]) -> Dict[str, Any]:
            """异步生成单个章节内容"""
            async with semaphore:
                section_title = section_data["section_title"]
                section_points = section_data["section_points"]
                collected_data_info = section_data["collected_data_info"]
                allocated_charts = section_data["allocated_charts"]
                processing_method = section_data["processing_method"]
                
                print(f"\033[94m📝 生成章节：{section_title} ({processing_method})\033[0m")
                
                # 根据处理方法生成内容
                if processing_method == "no_data":
                    # 无数据支撑，生成基础框架
                    section_info = {
                        "title": section_title,
                        "points": section_points
                    }
                    content = await self._generate_section_without_data_async(section_info, subject_name)
                else:
                    # 有数据支撑，生成详细内容
                    section_info = {
                        "title": section_title,
                        "points": section_points,
                        "allocated_charts": allocated_charts
                    }
                    content = await self._generate_section_with_data_async(
                        section_info=section_info,
                        collected_data_info=collected_data_info,
                        subject_name=subject_name,
                        report_context={"subject_name": subject_name}
                    )
                
                return {
                    "section_index": section_data["section_index"],
                    "section_title": section_title,
                    "section_points": section_points,
                    "content": content,
                    "data_info": collected_data_info,
                    "allocated_charts": allocated_charts,
                    "charts_count": len(allocated_charts),
                    "generation_method": processing_method,
                    "has_data": processing_method != "no_data"
                }
        
        # 异步批量生成基础内容
        print(f"🔄 开始高并发生成基础内容（{max_concurrent // 2}并发）...")
        tasks = [generate_single_section(section_data) for section_data in sections_data]
        processed_sections = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常情况
        final_sections = []
        for i, result in enumerate(processed_sections):
            if isinstance(result, Exception):
                print(f"\033[91m❌ 章节 {i+1} 生成失败: {result}\033[0m")
                # 创建一个错误章节
                section_data = sections_data[i]
                error_section = {
                    "section_index": section_data["section_index"],
                    "section_title": section_data["section_title"],
                    "content": f"章节生成失败: {str(result)}",
                    "error": str(result),
                    "has_data": False
                }
                final_sections.append(error_section)
            else:
                final_sections.append(result)
        
        # 创建基础报告
        base_report = {
            "subject_name": subject_name,
            "report_type": "company_research",
            "sections": processed_sections,
            "generation_stats": {
                "total_sections": len(processed_sections),
                "sections_with_data": sum(1 for s in processed_sections if s.get("has_data", False)),
                "sections_without_data": sum(1 for s in processed_sections if not s.get("has_data", False)),
                "total_words": sum(len(s.get("content", "")) for s in processed_sections),
                "total_references": len(self.content_assembler.global_references)
            }
        }
        
        print("✅ 基础报告生成完成")
        
        # ====== 第二轮：异步可视化增强 ======
        print(f"\n🎨 第二轮：异步加载可视化资源并增强内容...")
        
        # 异步加载可视化资源
        visualization_resources = await self.content_assembler.load_visualization_resources_async(
            images_dir=images_dir,
            target_name=subject_name,
            name_field='company_name'
        )
        
        if not visualization_resources:
            print("⚠️ 未找到可视化资源，返回基础报告")
            if output_file:
                await self._save_report_async(base_report, output_file)
            return base_report
        
        # 详细打印可视化资源分配情况
        print(f"\n🎯 \033[93m可视化资源分配分析：\033[0m")
        print(f"\033[93m总共加载了 {len(visualization_resources)} 个章节的可视化资源\033[0m")
        
        # 准备可视化增强的章节数据
        enhancement_sections_data = []
        for section in processed_sections:
            section_title = section.get("section_title", "")
            original_content = section.get("content", "")
            matching_charts = visualization_resources.get(section_title, [])
            
            enhancement_sections_data.append({
                "section_title": section_title,
                "original_content": original_content,
                "visualization_charts": matching_charts,
                "section_data": section  # 保存原始章节数据
            })
        
        # 创建信号量控制并发数
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def enhance_single_section(section_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                section_title = section_data["section_title"]
                original_content = section_data["original_content"]
                matching_charts = section_data["visualization_charts"]
                original_section = section_data["section_data"]
                
                print(f"\033[93m🎨 [{asyncio.current_task().get_name()}] 处理章节: {section_title}\033[0m")
                
                if matching_charts:
                    print(f"\033[93m   🎯 发现 {len(matching_charts)} 个匹配图表\033[0m")
                    
                    # 异步生成增强内容
                    enhanced_content = await self.content_assembler.generate_section_with_visualization_async(
                        section_title=section_title,
                        original_content=original_content,
                        visualization_charts=matching_charts,
                        llm_call_function_async=self._call_llm_async,
                        target_name=subject_name,
                        api_key=self.api_key,
                        base_url=self.base_url,
                        model=self.model,
                        enable_text_visualization=True,
                        output_dir=images_dir
                    )
                    
                    # 统计内容改善情况
                    original_length = len(original_content)
                    enhanced_length = len(enhanced_content)
                    improvement_ratio = (enhanced_length - original_length) / original_length if original_length > 0 else 0
                    
                    print(f"\033[93m   📈 内容增强完成: {original_length} → {enhanced_length} 字符 (+{improvement_ratio:.1%})\033[0m")
                    
                    # 更新章节信息
                    enhanced_section = original_section.copy()
                    enhanced_section["content"] = enhanced_content
                    enhanced_section["visualization_charts"] = matching_charts
                    enhanced_section["charts_count"] = len(matching_charts)
                    enhanced_section["enhanced"] = True
                    enhanced_section["content_stats"] = {
                        "original_length": original_length,
                        "enhanced_length": enhanced_length,
                        "improvement_ratio": improvement_ratio
                    }
                    
                    return enhanced_section
                else:
                    print(f"\033[93m   ➖ 无匹配图表，尝试基于文本生成可视化...\033[0m")
                    
                    # 异步生成文本可视化
                    enhanced_content = await self.content_assembler.generate_section_with_visualization_async(
                        section_title=section_title,
                        original_content=original_content,
                        visualization_charts=[],
                        llm_call_function_async=self._call_llm_async,
                        target_name=subject_name,
                        api_key=self.api_key,
                        base_url=self.base_url,
                        model=self.model,
                        enable_text_visualization=True,
                        output_dir=images_dir
                    )
                    
                    # 检查是否生成了新的可视化内容
                    if enhanced_content != original_content:
                        enhanced_section = original_section.copy()
                        enhanced_section["content"] = enhanced_content
                        enhanced_section["enhanced"] = True
                        enhanced_section["generation_method"] = "text_visualization"
                        print(f"\033[93m   ✅ 基于文本生成了可视化内容\033[0m")
                        return enhanced_section
                    else:
                        original_section["enhanced"] = False
                        print(f"\033[93m   ➖ 文本可视化生成失败，保持原内容\033[0m")
                        return original_section
        
        # 高并发处理所有章节
        print(f"\n🔄 \033[93m开始高并发章节增强（{max_concurrent}并发，共{len(enhancement_sections_data)}个章节）：\033[0m")
        
        # 创建任务列表
        tasks = []
        for i, section_data in enumerate(enhancement_sections_data):
            task = asyncio.create_task(
                enhance_single_section(section_data),
                name=f"enhance-section-{i+1}"
            )
            tasks.append(task)
        
        # 等待所有任务完成
        enhanced_sections = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常情况
        final_enhanced_sections = []
        for i, result in enumerate(enhanced_sections):
            if isinstance(result, Exception):
                print(f"\033[91m❌ 章节 {i+1} 处理失败: {result}\033[0m")
                # 使用原始章节作为备选
                original_section = enhancement_sections_data[i]["section_data"]
                original_section["enhanced"] = False
                original_section["error"] = str(result)
                final_enhanced_sections.append(original_section)
            else:
                final_enhanced_sections.append(result)
        
        # 创建增强报告
        enhanced_report = base_report.copy()
        enhanced_report["sections"] = final_enhanced_sections
        enhanced_report["enhancement_stats"] = self._calculate_enhancement_stats(final_enhanced_sections)
        
        print("✅ 高并发内容增强完成")
        
        # 异步保存最终报告
        if output_file:
            await self._save_report_async(enhanced_report, output_file)
        
        print(f"🎉 {subject_name} 高并发可视化增强研究报告生成完成！")
        return enhanced_report
    
    def _call_llm(self, prompt: str) -> str:
        """
        调用LLM生成内容
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的内容
        """
        return chat_no_tool(
            user_content=prompt,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model
        )
    
    async def _call_llm_async(self, prompt: str) -> str:
        """
        异步调用LLM生成内容
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的内容
        """
        # 在事件循环中运行同步的chat_no_tool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: chat_no_tool(
                user_content=prompt,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model
            )
        )
    
    async def _generate_section_without_data_async(
        self,
        section_info: Dict[str, Any],
        subject_name: str
    ) -> str:
        """
        异步为无数据支撑的章节生成基础框架
        
        Args:
            section_info: 章节信息
            subject_name: 研究主体名称
            
        Returns:
            生成的章节内容
        """
        section_title = section_info["title"]
        section_points = section_info["points"]
        
        # 构建要点文本
        points_text = "\\n".join([f"- {point}" for point in section_points])
        
        # 使用无数据提示词模板
        prompt = self.get_section_without_data_prompt().format(
            subject_name=subject_name,
            section_title=section_title,
            points_text=points_text
        )
        
        return await self._call_llm_async(prompt)
    
    async def _generate_section_with_data_async(
        self,
        section_info: Dict[str, Any],
        collected_data_info: Dict[str, Any],
        subject_name: str,
        report_context: Dict[str, Any]
    ) -> str:
        """
        异步为有数据支撑的章节生成内容
        
        Args:
            section_info: 章节信息
            collected_data_info: 收集到的数据信息
            subject_name: 研究主体名称
            report_context: 报告上下文
            
        Returns:
            生成的章节内容
        """
        section_title = section_info["title"]
        section_points = section_info["points"]
        allocated_charts = section_info.get("allocated_charts", [])
        
        # 构建要点文本
        points_text = "\\n".join([f"- {point}" for point in section_points])
        
        # 构建数据内容
        data_content = self.content_assembler.build_data_content(
            collected_data_info, 
            collected_data_info["processing_method"]
        )
        
        # 构建图表内容
        chart_content = self.content_assembler.build_chart_content(allocated_charts)
        
        # 使用有数据提示词模板
        prompt = self.get_section_with_data_prompt().format(
            subject_name=subject_name,
            section_title=section_title,
            points_text=points_text,
            data_content=data_content,
            chart_content=chart_content
        )
        
        return await self._call_llm_async(prompt)
    
    def _save_report(self, report: Dict[str, Any], output_file: str):
        """
        保存报告到文件
        
        Args:
            report: 报告数据
            output_file: 输出文件路径
        """
        if output_file.lower().endswith(".md"):
            markdown_content = self.content_assembler.assemble_markdown_report(report)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            print(f"📁 Markdown 报告已保存到: {output_file}")
        else:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            print(f"📁 报告已保存到: {output_file}")
    
    async def _save_report_async(self, report: Dict[str, Any], output_file: str):
        """
        异步保存报告到文件
        
        Args:
            report: 报告数据
            output_file: 输出文件路径
        """
        loop = asyncio.get_event_loop()
        
        def _sync_save():
            if output_file.lower().endswith(".md"):
                markdown_content = self.content_assembler.assemble_markdown_report(report)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                return f"📁 Markdown 报告已保存到: {output_file}"
            else:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(report, f, ensure_ascii=False, indent=2)
                return f"📁 报告已保存到: {output_file}"
        
        message = await loop.run_in_executor(None, _sync_save)
        print(message)
    
    def _calculate_enhancement_stats(self, sections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算增强统计信息
        
        Args:
            sections: 章节列表
            
        Returns:
            统计信息
        """
        total_sections = len(sections)
        enhanced_sections = sum(1 for s in sections if s.get("enhanced", False))
        total_charts = sum(s.get("charts_count", 0) for s in sections)
        
        # 计算内容改善统计
        total_original_length = 0
        total_enhanced_length = 0
        
        for section in sections:
            content_stats = section.get("content_stats", {})
            total_original_length += content_stats.get("original_length", 0)
            total_enhanced_length += content_stats.get("enhanced_length", 0)
        
        overall_improvement = 0
        if total_original_length > 0:
            overall_improvement = (total_enhanced_length - total_original_length) / total_original_length
        
        return {
            "total_sections": total_sections,
            "enhanced_sections": enhanced_sections,
            "enhancement_rate": enhanced_sections / total_sections if total_sections > 0 else 0,
            "total_charts": total_charts,
            "content_improvement": {
                "total_original_length": total_original_length,
                "total_enhanced_length": total_enhanced_length,
                "overall_improvement_ratio": overall_improvement,
                "avg_charts_per_enhanced_section": total_charts / enhanced_sections if enhanced_sections > 0 else 0
            }
        }


if __name__ == "__main__":
    """主程序入口 - 生成公司研究报告"""
    
    # 导入os模块用于路径处理
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # ====== API配置 - 与 company_collection_data.py 保持一致 ======
    api_key = os.getenv("GUIJI_API_KEY")
    base_url = os.getenv("GUIJI_BASE_URL")
    model = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO")  # 使用高级模型
    
    if not all([api_key, base_url, model]):
        print("❌ 缺少必要的环境变量配置:")
        print("   - GUIJI_API_KEY")
        print("   - GUIJI_BASE_URL") 
        print("   - GUIJI_TEXT_MODEL_DEEPSEEK_PRO")
        print("💡 请检查 .env 文件配置")
        exit(1)
    
    # 数据文件路径配置
    data_files = {
        "outline_file": "test_company_datas/company_outline.json",
        "allocation_result_file": "test_company_datas/outline_data_allocation.json",
        "enhanced_allocation_file": "test_company_datas/enhanced_allocation_result.json",
        "flattened_data_file": "test_company_datas/flattened_tonghuashun_data.json",
        "visualization_results_file": "test_company_datas/visual_enhancement_results.json",
        "output_file": "test_company_datas/generated_report.md"
    }
    
    # 公司名称和输出目录配置
    company_name = "4Paradigm"
    
    # ====== 输出目录配置 ======
    # 与 company_collection_data.py 保持一致的路径配置
    images_dir = os.path.join("test_company_datas", "images")
    
    # 确保输出目录存在
    if not os.path.exists(images_dir):
        os.makedirs(images_dir, exist_ok=True)
        print(f"📁 创建输出目录: {images_dir}")
    
    print(f"📁 图表输出目录: {images_dir}")
    print(f"🔑 使用API配置: {base_url} / {model}")
    
    async def main():
        """异步主函数 - 支持190并发"""
        try:
            print("📂 加载数据文件...")
            
            # 使用与collection脚本相同的API配置
            generator = CompanyReportGenerator(
                api_key=api_key,
                base_url=base_url,
                model=model,
                max_context_tokens=128 * 1024 * 0.8 # 设置为80%上下文限制
            )
            outline_data, allocation_result, flattened_data, visualization_results = generator.load_report_data(
                **{k: v for k, v in data_files.items() if k != "output_file"}
            )
            print("✅ 数据加载完成")
            
            print(f"🚀 开始高并发生成 {company_name} 可视化增强研究报告（190并发）...")
            
            # 使用新的高并发可视化增强方法
            report = await generator.generate_complete_report_with_visualization_async(
                subject_name=company_name,
                outline_data=outline_data,
                allocation_result=allocation_result,
                all_flattened_data=flattened_data,
                images_dir=images_dir,
                visualization_results=visualization_results,
                output_file=data_files["output_file"],
                max_concurrent=190  # 设置190并发
            )
            
            # 显示统计信息
            print(f"\n📊 报告生成统计:")
            stats = report.get("generation_stats", {})
            enhancement_stats = report.get("enhancement_stats", {})
            
            print(f"   - 总章节数: {stats.get('total_sections', len(report.get('sections', [])))}")
            print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
            print(f"   - 无数据章节: {stats.get('sections_without_data', 0)}")
            print(f"   - 总字数: {stats.get('total_words', 0):,}")
            print(f"   - 参考文献数: {stats.get('total_references', 0)}")
            
            # 可视化增强统计
            if enhancement_stats:
                print(f"\n🎨 可视化增强统计:")
                print(f"   - 增强章节数: {enhancement_stats.get('enhanced_sections', 0)}")
                print(f"   - 增强覆盖率: {enhancement_stats.get('enhancement_rate', 0):.1%}")
                print(f"   - 总图表数: {enhancement_stats.get('total_charts', 0)}")
                
                # 内容改善统计
                content_improvement = enhancement_stats.get('content_improvement', {})
                if content_improvement:
                    print(f"\n📈 内容改善统计:")
                    original_len = content_improvement.get('total_original_length', 0)
                    enhanced_len = content_improvement.get('total_enhanced_length', 0)
                    improvement_ratio = content_improvement.get('overall_improvement_ratio', 0)
                    avg_charts = content_improvement.get('avg_charts_per_enhanced_section', 0)
                    
                    print(f"   - 原始总字符数: {original_len:,}")
                    print(f"   - 增强后字符数: {enhanced_len:,}")
                    print(f"   - 整体内容增长: {improvement_ratio:.1%}")
                    print(f"   - 平均每章节图表数: {avg_charts:.1f}")
            
            print(f"\n🎉 高并发可视化增强报告生成成功！")
            print(f"📁 输出文件: {data_files['output_file']}")
            print(f"💡 提示: 报告中图表已自动嵌入markdown格式，可直接预览")
            
            # 可选：同时生成标准版本进行对比
            print(f"\n📋 生成标准版本用于对比...")
            standard_output = data_files["output_file"].replace(".md", "_standard.md")
            
            # 使用同步方法生成标准版本
            standard_report = generator.generate_complete_report(
                subject_name=company_name,
                outline_data=outline_data,
                allocation_result=allocation_result,
                all_flattened_data=flattened_data,
                visualization_results=visualization_results,
                output_file=standard_output
            )
            print(f"📁 标准版本: {standard_output}")
            
        except FileNotFoundError as e:
            print(f"❌ 数据文件未找到: {e}")
            print("💡 请先运行数据收集脚本生成必要的数据文件")
        except ValueError as e:
            print(f"❌ 配置错误: {e}")
            print("💡 请检查环境变量配置")
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 运行异步主函数
    print("🚀 启动高并发模式（190并发）...")
    asyncio.run(main())


def run_high_concurrency_mode(max_concurrent: int = 190):
    """
    运行高并发模式的便捷函数
    
    Args:
        max_concurrent: 最大并发数，默认190
    """
    print(f"🚀 启动高并发模式（{max_concurrent}并发）...")
    
    # 导入os模块用于路径处理
    import os
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # ====== API配置 ======
    api_key = os.getenv("GUIJI_API_KEY")
    base_url = os.getenv("GUIJI_BASE_URL")
    model = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO")
    
    if not all([api_key, base_url, model]):
        print("❌ 缺少必要的环境变量配置")
        return
    
    # 数据文件路径配置
    data_files = {
        "outline_file": "test_company_datas/company_outline.json",
        "allocation_result_file": "test_company_datas/outline_data_allocation.json",
        "enhanced_allocation_file": "test_company_datas/enhanced_allocation_result.json",
        "flattened_data_file": "test_company_datas/flattened_tonghuashun_data.json",
        "visualization_results_file": "test_company_datas/visual_enhancement_results.json",
        "output_file": "test_company_datas/generated_report_concurrent.md"
    }
    
    company_name = "4Paradigm"
    images_dir = os.path.join("test_company_datas", "images")
    
    async def concurrent_main():
        # 检查是否存在必要的数据文件，如果不存在则自动运行数据收集
        missing_files = []
        for key, file_path in data_files.items():
            if key != "output_file" and not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print("📁 加载报告生成所需数据...")
            print("❌ 数据文件未找到，启动自动数据收集流程...")
            for file_path in missing_files:
                print(f"   - 缺失: {file_path}")
            
            print("\n🚀 启动公司数据收集流程...")
            
            # 导入并运行数据收集
            from data_process.company_data_collection import CompanyDataCollection
            
            # 创建公司数据收集器
            company_collector = CompanyDataCollection(
                company_name=company_name,
                company_code="06682.HK",  # 4Paradigm的股票代码
                max_concurrent=190,
                api_key=api_key,
                base_url=base_url,
                model=model,
                use_zhipu_search=True,
                zhipu_search_key=os.getenv("ZHIPU_API_KEY"),
                search_interval=2.0,
                use_existing_search_results=True
            )
            
            # 运行数据收集流程
            print("🔄 正在收集公司数据...")
            collection_results = company_collector.run_full_process()
            
            print(f"✅ 数据收集完成!")
            print(f"   - 大纲章节: {len(collection_results.get('outline_result', {}).get('reportOutline', []))} 个")
            print(f"   - 收集数据: {len(collection_results.get('flattened_data', []))} 条")
            
            if collection_results.get('visual_enhancement_results'):
                enhancement = collection_results['visual_enhancement_results']
                analysis_phase = enhancement.get('analysis_phase', {})
                suggestions = analysis_phase.get('visualization_suggestions', [])
                print(f"   - 可视化建议: {len(suggestions)} 个")
            
            if collection_results.get('viz_results'):
                viz_results = collection_results['viz_results']
                chart_results = viz_results.get('chart_generation_results', [])
                successful_charts = [r for r in chart_results if r.get('success', False)]
                print(f"   - 生成图表: {len(successful_charts)} 个")
            
            print("\n📂 重新加载数据文件...")
        
        generator = CompanyReportGenerator(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_context_tokens=128 * 1024 * 0.8
        )
        
        outline_data, allocation_result, flattened_data, visualization_results = generator.load_report_data(
            **{k: v for k, v in data_files.items() if k != "output_file"}
        )
        
        report = await generator.generate_complete_report_with_visualization_async(
            subject_name=company_name,
            outline_data=outline_data,
            allocation_result=allocation_result,
            all_flattened_data=flattened_data,
            images_dir=images_dir,
            visualization_results=visualization_results,
            output_file=data_files["output_file"],
            max_concurrent=max_concurrent
        )
        
        print(f"✅ 高并发报告生成完成: {data_files['output_file']}")
        return report
    
    return asyncio.run(concurrent_main())
