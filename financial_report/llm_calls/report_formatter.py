"""
报告格式化器 - 负责统一处理标题、内容格式和最终报告组装
"""

import json
from typing import List, Dict, Any, Optional


class ReportFormatter:
    """报告格式化器，统一处理标题和内容格式"""
    
    def __init__(self, title_style: str = "markdown"):
        """
        初始化格式化器
        
        Args:
            title_style: 标题样式 ("markdown", "plain", "numbered")
        """
        self.title_style = title_style
    
    def format_section_title(self, title: str, level: int = 1, index: Optional[int] = None) -> str:
        """
        格式化章节标题
        
        Args:
            title: 原始标题
            level: 标题级别 (1-6)
            index: 章节序号
            
        Returns:
            格式化后的标题
        """
        if self.title_style == "markdown":
            prefix = "#" * level
            if index:
                return f"{prefix} {index}. {title}"
            else:
                return f"{prefix} {title}"
                
        elif self.title_style == "numbered":
            if index:
                return f"{index}. {title}"
            else:
                return title
                
        else:  # plain
            return title
    
    def format_section_content(
        self, 
        title: str, 
        content: str, 
        index: Optional[int] = None,
        include_title: bool = True,
        title_level: int = 2
    ) -> str:
        """
        格式化章节内容（包含标题）
        
        Args:
            title: 章节标题
            content: 章节内容
            index: 章节序号
            include_title: 是否包含标题
            title_level: 标题级别
            
        Returns:
            格式化后的完整章节
        """
        if include_title:
            formatted_title = self.format_section_title(title, title_level, index)
            return f"{formatted_title}\n\n{content}"
        else:
            return content
    
    def assemble_complete_report(
        self,
        report_data: Dict[str, Any],
        include_toc: bool = True,
        include_summary: bool = True
    ) -> str:
        """
        组装完整报告
        
        Args:
            report_data: 报告数据
            include_toc: 是否包含目录
            include_summary: 是否包含摘要
            
        Returns:
            完整的格式化报告
        """
        report_parts = []
        
        # 1. 报告标题
        main_title = report_data.get("report_title", "投资研究报告")
        report_parts.append(self.format_section_title(main_title, level=1))
        report_parts.append("")
        
        # 2. 基本信息
        company_name = report_data.get("company_name", "")
        company_code = report_data.get("company_code", "")
        timestamp = report_data.get("generation_timestamp", "")
        
        if company_name or company_code:
            info_section = f"**公司名称**: {company_name}\n"
            if company_code:
                info_section += f"**股票代码**: {company_code}\n"
            if timestamp:
                info_section += f"**报告生成时间**: {timestamp}\n"
            report_parts.append(info_section)
            report_parts.append("")
        
        # 3. 执行摘要
        if include_summary and report_data.get("report_summary"):
            summary_title = self.format_section_title("执行摘要", level=2)
            report_parts.append(summary_title)
            report_parts.append("")
            report_parts.append(report_data["report_summary"])
            report_parts.append("")
        
        # 4. 目录
        if include_toc:
            toc_title = self.format_section_title("目录", level=2)
            report_parts.append(toc_title)
            report_parts.append("")
            
            sections = report_data.get("enhanced_sections", report_data.get("sections", []))
            for idx, section in enumerate(sections, 1):
                section_title = section.get("section_title", section.get("title", ""))
                if self.title_style == "markdown":
                    report_parts.append(f"- [{idx}. {section_title}](#{idx}-{section_title.replace(' ', '-').lower()})")
                else:
                    report_parts.append(f"{idx}. {section_title}")
            
            report_parts.append("")
        
        # 5. 各章节内容
        sections = report_data.get("enhanced_sections", report_data.get("sections", []))
        for idx, section in enumerate(sections, 1):
            section_title = section.get("section_title", section.get("title", ""))
            
            # 优先使用增强内容，然后是普通内容
            content = (section.get("enhanced_content") or 
                      section.get("content") or 
                      section.get("integrated_report", ""))
            
            if content:
                formatted_section = self.format_section_content(
                    title=section_title,
                    content=content,
                    index=idx,
                    include_title=True,
                    title_level=2
                )
                report_parts.append(formatted_section)
                report_parts.append("")
        
        # 6. 附录信息
        if report_data.get("generation_stats"):
            stats = report_data["generation_stats"]
            appendix_title = self.format_section_title("附录：生成统计", level=2)
            report_parts.append(appendix_title)
            report_parts.append("")
            
            stats_content = f"""**报告生成统计信息**

- 总章节数：{stats.get('successful_sections', 0) + stats.get('failed_sections', 0)}
- 成功生成：{stats.get('successful_sections', 0)}
- 生成失败：{stats.get('failed_sections', 0)}
- 总生成长度：{stats.get('total_generated_length', 0):,} 字符
- 总迭代轮数：{stats.get('total_iterations', 0)}"""
            
            report_parts.append(stats_content)
            report_parts.append("")
        
        return "\n".join(report_parts)
    
    def export_to_markdown(self, report_data: Dict[str, Any], output_path: str) -> bool:
        """
        导出为Markdown文件
        
        Args:
            report_data: 报告数据
            output_path: 输出文件路径
            
        Returns:
            是否成功
        """
        try:
            # 临时设置为markdown样式
            original_style = self.title_style
            self.title_style = "markdown"
            
            markdown_content = self.assemble_complete_report(report_data)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)
            
            # 恢复原始样式
            self.title_style = original_style
            
            return True
        except Exception as e:
            print(f"导出Markdown失败: {e}")
            return False
    
    def get_content_without_titles(self, report_data: Dict[str, Any]) -> List[str]:
        """
        获取不包含标题的纯内容列表
        
        Args:
            report_data: 报告数据
            
        Returns:
            纯内容列表
        """
        contents = []
        sections = report_data.get("enhanced_sections", report_data.get("sections", []))
        
        for section in sections:
            content = (section.get("enhanced_content") or 
                      section.get("content") or 
                      section.get("integrated_report", ""))
            if content:
                contents.append(content)
        
        return contents
    
    def validate_report_structure(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证报告结构完整性
        
        Args:
            report_data: 报告数据
            
        Returns:
            验证结果
        """
        validation_result = {
            "is_valid": True,
            "issues": [],
            "statistics": {}
        }
        
        # 检查必要字段
        required_fields = ["company_name", "report_title"]
        for field in required_fields:
            if not report_data.get(field):
                validation_result["issues"].append(f"缺少必要字段: {field}")
                validation_result["is_valid"] = False
        
        # 检查章节
        sections = report_data.get("enhanced_sections", report_data.get("sections", []))
        if not sections:
            validation_result["issues"].append("报告没有章节内容")
            validation_result["is_valid"] = False
        else:
            empty_sections = 0
            total_length = 0
            
            for idx, section in enumerate(sections, 1):
                section_title = section.get("section_title", section.get("title", ""))
                content = (section.get("enhanced_content") or 
                          section.get("content") or 
                          section.get("integrated_report", ""))
                
                if not section_title:
                    validation_result["issues"].append(f"第{idx}章节缺少标题")
                
                if not content or len(content.strip()) < 100:
                    empty_sections += 1
                    validation_result["issues"].append(f"第{idx}章节内容过短或为空: {section_title}")
                else:
                    total_length += len(content)
            
            validation_result["statistics"] = {
                "total_sections": len(sections),
                "empty_sections": empty_sections,
                "total_content_length": total_length,
                "average_section_length": total_length // (len(sections) - empty_sections) if len(sections) > empty_sections else 0
            }
        
        return validation_result