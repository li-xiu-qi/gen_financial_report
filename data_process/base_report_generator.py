"""
基础报告生成器
为公司、行业、宏观研报提供统一的生成框架
"""

import json
import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from financial_report.utils.calculate_tokens import OpenAITokenCalculator
from financial_report.utils.chat import chat_no_tool
from data_process.data_collector import DataCollector
from data_process.base_report_data_processor import BaseReportDataProcessor
from data_process.base_report_content_assembler import BaseReportContentAssembler


class BaseReportGenerator(ABC):
    """基础报告生成器 - 提供通用的报告生成框架"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_context_tokens: int = 128 * 1024,  # 默认128K上下文
        context_usage_ratio: float = 0.8   # 使用80%的上下文空间
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_context_tokens = max_context_tokens
        self.available_tokens = int(max_context_tokens * context_usage_ratio)
        
        # 初始化组件
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化各个组件"""
        self.token_calculator = OpenAITokenCalculator()
        self.data_collector = DataCollector(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            token_calculator=self.token_calculator
        )
        self.data_processor = self._create_data_processor()
        self.content_assembler = self._create_content_assembler()
    
    @abstractmethod
    def _create_data_processor(self) -> BaseReportDataProcessor:
        """创建数据处理器 - 子类需要实现"""
        pass
    
    @abstractmethod
    def _create_content_assembler(self) -> BaseReportContentAssembler:
        """创建内容组装器 - 子类需要实现"""
        pass
    
    @abstractmethod
    def get_section_with_data_prompt(self) -> str:
        """获取有数据支撑的章节内容生成提示词 - 子类需要实现"""
        pass
    
    @abstractmethod
    def get_section_without_data_prompt(self) -> str:
        """获取无数据支撑的章节框架生成提示词 - 子类需要实现"""
        pass
    
    @classmethod
    def from_env(cls, context_usage_ratio: float = 0.8):
        """
        从环境变量创建报告生成器
        
        Args:
            context_usage_ratio: 上下文使用比例
            
        Returns:
            BaseReportGenerator实例
        """
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv("ZHIPU_API_KEY")
        base_url = os.getenv("ZHIPU_BASE_URL")
        model = os.getenv("ZHIPU_FREE_TEXT_MODEL")
        max_context_tokens = int(128 * 1024 * context_usage_ratio)
        
        if not all([api_key, base_url, model]):
            raise ValueError("缺少必要的环境变量: ZHIPU_API_KEY, ZHIPU_BASE_URL, ZHIPU_FREE_TEXT_MODEL")
        
        return cls(
            api_key=api_key,
            base_url=base_url,
            model=model,
            max_context_tokens=max_context_tokens,
            context_usage_ratio=1.0  # 已经在max_context_tokens中计算过了
        )
    
    @staticmethod
    def load_report_data(
        outline_file: str,
        allocation_result_file: str,
        flattened_data_file: str,
        enhanced_allocation_file: str = None,
        visualization_results_file: str = None
    ) -> tuple:
        """
        加载报告生成所需的数据文件
        
        Args:
            outline_file: 大纲文件路径
            allocation_result_file: 数据分配结果文件路径
            flattened_data_file: 展平数据文件路径
            enhanced_allocation_file: 增强分配结果文件路径（可选）
            visualization_results_file: 可视化结果文件路径（可选）
            
        Returns:
            (outline_data, allocation_result, flattened_data, visualization_results) 元组
        """
        processor = BaseReportDataProcessor()
        return processor.load_report_data(
            outline_file=outline_file,
            allocation_result_file=allocation_result_file,
            flattened_data_file=flattened_data_file,
            enhanced_allocation_file=enhanced_allocation_file,
            visualization_results_file=visualization_results_file
        )
    
    def generate_complete_report(
        self,
        subject_name: str,
        outline_data: Dict[str, Any],
        allocation_result: Dict[str, Any],
        all_flattened_data: List[Dict[str, Any]],
        visualization_results: Dict[str, Any] = None,
        output_file: str = None
    ) -> Dict[str, Any]:
        """
        生成完整的研究报告
        
        Args:
            subject_name: 研究主体名称（公司名/行业名/宏观主题等）
            outline_data: 大纲数据
            allocation_result: 数据分配结果
            all_flattened_data: 所有展平数据
            visualization_results: 可视化结果（包含章节分配信息）
            output_file: 输出文件路径
            
        Returns:
            生成的报告内容
        """
        print(f"\\n📝 开始生成 {subject_name} 研究报告...")
        
        # 重置参考文献状态
        self.content_assembler.reset_references()
        
        # 1. 解析大纲和数据分配
        sections_with_data = self.data_processor.determine_sections_with_data(
            outline_data, allocation_result, visualization_results
        )
        print(f"📋 报告包含 {len(sections_with_data)} 个章节")
        
        # 2. 创建简单的报告上下文（不生成详细规划）
        report_context = {
            "subject_name": subject_name,
            "total_sections": len(sections_with_data)
        }
        
        # 3. 逐章节生成内容
        generated_sections = []
        for i, section_info in enumerate(sections_with_data):
            print(f"\\n📝 生成第 {i+1}/{len(sections_with_data)} 章节: {section_info['title']}")
            
            section_content = self._generate_section_content(
                section_info=section_info,
                subject_name=subject_name,
                all_data=all_flattened_data,
                report_context=report_context
            )
            
            generated_sections.append(section_content)
            print(f"✅ 章节 '{section_info['title']}' 生成完成")
        
        # 4. 组装完整报告
        final_report = self.content_assembler.assemble_final_report(
            subject_name=subject_name,
            report_plan=report_context,
            generated_sections=generated_sections
        )
        
        # 5. 保存报告
        if output_file:
            if output_file.lower().endswith(".md"):
                markdown_content = self.content_assembler.assemble_markdown_report(final_report)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                print(f"📁 Markdown 报告已保存到: {output_file}")
            else:
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(final_report, f, ensure_ascii=False, indent=2)
                print(f"📁 报告已保存到: {output_file}")
        
        print(f"🎉 {subject_name} 研究报告生成完成！")
        return final_report
    
    # 以下方法已废弃，保留仅为兼容性
    def _create_report_plan(
        self, 
        subject_name: str, 
        sections_with_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        创建报告整体规划（已废弃，不再使用）
        
        Args:
            subject_name: 研究主体名称
            sections_with_data: 包含数据的章节信息
            
        Returns:
            报告规划信息
        """
        # 简化的报告上下文，不再生成详细规划
        return {
            "subject_name": subject_name,
            "total_sections": len(sections_with_data),
            "plan_content": ""  # 空内容，不再生成规划文本
        }
    
    def _generate_section_content(
        self,
        section_info: Dict[str, Any],
        subject_name: str,
        all_data: List[Dict[str, Any]],
        report_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成单个章节的内容
        
        Args:
            section_info: 章节信息
            subject_name: 研究主体名称
            all_data: 所有数据
            report_context: 报告上下文
            
        Returns:
            生成的章节内容
        """
        section_title = section_info["title"]
        section_points = section_info["points"]
        allocated_data_ids = section_info["allocated_data_ids"]
        allocated_charts = section_info.get("allocated_charts", [])
        
        print(f"   📊 收集章节数据...")
        if allocated_charts:
            print(f"   🎨 包含 {len(allocated_charts)} 个图表")
        
        # 1. 收集章节相关数据
        collected_data_info = self.data_collector.collect_data_for_section(
            section_title=section_title,
            section_points=section_points,
            allocated_data_ids=allocated_data_ids,
            all_data=all_data,
            max_context_tokens=self.available_tokens,
            company_name=subject_name  # 这里传入研究主体名称
        )
        
        # 2. 生成章节内容
        if collected_data_info["processing_method"] == "no_data":
            print(f"   ⚠️  无数据支撑，生成基础框架")
            content = self._generate_section_without_data(section_info, subject_name)
        else:
            print(f"   📝 基于数据生成内容 ({collected_data_info['processing_method']})")
            content = self._generate_section_with_data(
                section_info=section_info,
                collected_data_info=collected_data_info,
                subject_name=subject_name,
                report_context=report_context
            )
        
        return {
            "section_index": section_info["index"],
            "section_title": section_title,
            "section_points": section_points,
            "content": content,
            "data_info": collected_data_info,
            "allocated_charts": allocated_charts,
            "charts_count": len(allocated_charts),
            "generation_method": collected_data_info["processing_method"]
        }
    
    def _generate_section_without_data(
        self,
        section_info: Dict[str, Any],
        subject_name: str
    ) -> str:
        """
        为无数据支撑的章节生成基础框架
        
        Args:
            section_info: 章节信息
            subject_name: 研究主体名称
            
        Returns:
            生成的内容
        """
        section_title = section_info["title"]
        points = section_info["points"]
        
        points_text = "\n".join([f"- {point}" for point in points])
        
        prompt = self.get_section_without_data_prompt().format(
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
    
    def _generate_section_with_data(
        self,
        section_info: Dict[str, Any],
        collected_data_info: Dict[str, Any],
        subject_name: str,
        report_context: Dict[str, Any]
    ) -> str:
        """
        基于收集的数据生成章节内容
        
        Args:
            section_info: 章节信息
            collected_data_info: 收集的数据信息
            subject_name: 研究主体名称
            report_context: 报告上下文
            
        Returns:
            生成的章节内容
        """
        section_title = section_info["title"]
        points = section_info["points"]
        allocated_charts = section_info.get("allocated_charts", [])
        
        # 处理参考文献映射
        self.content_assembler.update_global_references(collected_data_info)
        
        # 构建图表内容
        chart_content = self.content_assembler.build_chart_content(allocated_charts)
        
        # 构建数据内容（带参考文献序号）
        data_content = self.content_assembler.build_data_content(
            collected_data_info, 
            collected_data_info["processing_method"]
        )
        
        # 构建提示词
        points_text = "\n".join([f"- {point}" for point in points])
        
        prompt = self.get_section_with_data_prompt().format(
            subject_name=subject_name,
            section_title=section_title,
            points_text=points_text,
            data_content=data_content,
            chart_content=chart_content
        )

        try:
            response = chat_no_tool(
                user_content=prompt,
                system_content="",  # 空字符串，因为提示词已合并
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.4,
                max_tokens=8192  # 增加输出token限制以支持更长内容
            )
            return response.strip()
        except Exception as e:
            print(f"     ❌ 章节内容生成失败: {e}")
            # 失败时返回基础框架
            return self._generate_section_without_data(section_info, subject_name)
