"""
连续生成器 - 用于生成长文档，避免token限制
支持分段生成和自动续写机制
"""

import json
import requests
import time
from typing import List, Dict, Any, Optional


class ContinuousGenerator:
    """连续生成器，支持分段生成长文档"""
    
    def __init__(self, api_key: str, base_url: str, model: str, max_tokens: int = 8192):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.max_tokens = max_tokens
        
    def _make_api_call(self, messages: List[Dict], temperature: float = 0.3) -> str:
        """调用API生成内容"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"API调用失败: {e}")
            return ""
    
    def generate_section_continuously(
        self, 
        section_title: str,
        section_content: str,
        company_name: str,
        company_code: str,
        target_length: int = 3000,
        max_iterations: int = 5,
        include_title_in_generation: bool = False
    ) -> Dict[str, Any]:
        """
        连续生成某个章节的详细内容
        
        Args:
            section_title: 章节标题
            section_content: 章节基础内容
            company_name: 公司名称
            company_code: 公司代码
            target_length: 目标长度（字符数）
            max_iterations: 最大迭代次数
        
        Returns:
            包含完整生成内容的字典
        """
        
        # 构建标题控制指令
        title_instruction = ""
        if include_title_in_generation:
            title_instruction = f"请在内容开头包含章节标题：{section_title}"
        else:
            title_instruction = f"请注意：不要在内容中包含章节标题（{section_title}），标题将由系统自动添加。直接开始正文内容。"

        # 初始化对话历史
        messages = [
            {
                "role": "system",
                "content": f"""你是一位专业的金融分析师，正在撰写关于{company_name}（{company_code}）的投资研究报告。

请按照以下要求生成内容：
1. 内容要专业、详实、有深度
2. 使用专业的金融术语和分析框架
3. 结构清晰，逻辑严密
4. 每次生成尽可能多的内容，充分利用token限制
5. 如果内容未完成，在结尾用"[继续]"标记
6. 保持内容的连贯性和一致性
7. {title_instruction}

当前章节：{section_title}"""
            },
            {
                "role": "user", 
                "content": f"""请基于以下基础内容，生成详细的《{section_title}》章节内容：

基础内容：
{section_content}

要求：
- 目标长度约{target_length}字符
- 内容专业、详实
- 逻辑清晰、结构合理
- {'包含章节标题' if include_title_in_generation else '不要包含章节标题，直接开始正文'}

请开始生成："""
            }
        ]
        
        generated_parts = []
        total_length = 0
        iteration = 0
        
        print(f"开始连续生成章节：{section_title}")
        
        while iteration < max_iterations and total_length < target_length:
            iteration += 1
            print(f"  第{iteration}轮生成...")
            
            # 生成内容
            content = self._make_api_call(messages, temperature=0.3)
            
            if not content:
                print(f"  第{iteration}轮生成失败，跳过")
                break
                
            generated_parts.append(content)
            total_length += len(content)
            
            print(f"  第{iteration}轮完成，生成{len(content)}字符，累计{total_length}字符")
            
            # 检查是否需要继续
            if "[继续]" not in content and total_length >= target_length * 0.8:
                print(f"  内容已完整，停止生成")
                break
                
            if "[继续]" in content:
                # 移除继续标记
                content = content.replace("[继续]", "").strip()
                generated_parts[-1] = content
                
                # 添加继续生成的消息
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user", 
                    "content": "请继续完成这个章节的内容，保持内容的连贯性："
                })
            else:
                # 内容看起来完整了
                break
        
        # 合并所有生成的内容
        full_content = "\n\n".join(generated_parts)
        
        result = {
            "section_title": section_title,
            "generated_content": full_content,
            "generation_stats": {
                "iterations": iteration,
                "total_length": len(full_content),
                "target_length": target_length,
                "completion_rate": min(len(full_content) / target_length, 1.0),
                "parts_count": len(generated_parts)
            }
        }
        
        print(f"章节生成完成：{section_title}")
        print(f"  总轮数：{iteration}")
        print(f"  总长度：{len(full_content)}字符")
        print(f"  完成度：{result['generation_stats']['completion_rate']:.1%}")
        
        return result
    
    def generate_complete_report_continuously(
        self,
        section_reports: List[Dict],
        company_name: str,
        company_code: str,
        target_section_length: int = 3000,
        include_title_in_generation: bool = False
    ) -> Dict[str, Any]:
        """
        连续生成完整报告的所有章节
        
        Args:
            section_reports: 章节报告列表
            company_name: 公司名称  
            company_code: 公司代码
            target_section_length: 每个章节的目标长度
            
        Returns:
            完整的报告生成结果
        """
        
        print(f"\n{'='*60}")
        print(f"开始连续生成完整报告：{company_name}（{company_code}）")
        print(f"{'='*60}")
        
        enhanced_sections = []
        total_stats = {
            "total_iterations": 0,
            "total_generated_length": 0,
            "successful_sections": 0,
            "failed_sections": 0
        }
        
        for idx, section_report in enumerate(section_reports, 1):
            print(f"\n【章节{idx}/{len(section_reports)}】{section_report['section_title']}")
            
            # 准备基础内容
            base_content = section_report.get('integrated_report', '')
            if section_report.get('multimodal_content', {}).get('assembled_content', {}).get('assembled_text'):
                base_content = section_report['multimodal_content']['assembled_content']['assembled_text']
            
            try:
                # 连续生成该章节
                generation_result = self.generate_section_continuously(
                    section_title=section_report['section_title'],
                    section_content=base_content,
                    company_name=company_name,
                    company_code=company_code,
                    target_length=target_section_length,
                    include_title_in_generation=include_title_in_generation
                )
                
                enhanced_section = {
                    **section_report,
                    "enhanced_content": generation_result["generated_content"],
                    "generation_stats": generation_result["generation_stats"]
                }
                
                enhanced_sections.append(enhanced_section)
                
                # 更新统计
                stats = generation_result["generation_stats"]
                total_stats["total_iterations"] += stats["iterations"]
                total_stats["total_generated_length"] += stats["total_length"]
                total_stats["successful_sections"] += 1
                
                print(f"✅ 章节{idx}生成成功")
                
            except Exception as e:
                print(f"❌ 章节{idx}生成失败: {e}")
                # 使用原始内容作为fallback
                enhanced_section = {
                    **section_report,
                    "enhanced_content": base_content,
                    "generation_stats": {
                        "iterations": 0,
                        "total_length": len(base_content),
                        "target_length": target_section_length,
                        "completion_rate": 0.0,
                        "parts_count": 1,
                        "error": str(e)
                    }
                }
                enhanced_sections.append(enhanced_section)
                total_stats["failed_sections"] += 1
        
        # 生成报告摘要
        print(f"\n{'='*60}")
        print("生成报告摘要...")
        print(f"{'='*60}")
        
        summary_content = self._generate_report_summary(
            enhanced_sections, company_name, company_code
        )
        
        # 构建最终结果
        final_result = {
            "company_name": company_name,
            "company_code": company_code,
            "report_title": f"{company_name}（{company_code}）投资研究报告",
            "generation_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "enhanced_sections": enhanced_sections,
            "report_summary": summary_content,
            "generation_stats": total_stats,
            "metadata": {
                "total_sections": len(enhanced_sections),
                "average_section_length": total_stats["total_generated_length"] // len(enhanced_sections) if enhanced_sections else 0,
                "success_rate": total_stats["successful_sections"] / len(section_reports) if section_reports else 0
            }
        }
        
        print(f"\n🎉 完整报告生成完成！")
        print(f"成功章节：{total_stats['successful_sections']}/{len(section_reports)}")
        print(f"总生成长度：{total_stats['total_generated_length']:,}字符")
        print(f"平均章节长度：{final_result['metadata']['average_section_length']:,}字符")
        
        return final_result
    
    def _generate_report_summary(
        self, 
        enhanced_sections: List[Dict], 
        company_name: str, 
        company_code: str
    ) -> str:
        """生成报告摘要"""
        
        # 提取各章节的关键信息
        section_summaries = []
        for section in enhanced_sections:
            title = section['section_title']
            content = section.get('enhanced_content', section.get('integrated_report', ''))
            # 取前200字符作为摘要
            summary = content[:200] + "..." if len(content) > 200 else content
            section_summaries.append(f"**{title}**: {summary}")
        
        sections_text = "\n\n".join(section_summaries)
        
        messages = [
            {
                "role": "system",
                "content": f"""你是一位专业的金融分析师，需要为{company_name}（{company_code}）的投资研究报告撰写执行摘要。

请基于各章节内容，生成一个简洁而全面的报告摘要，包括：
1. 公司基本情况
2. 主要投资亮点
3. 风险因素
4. 投资建议

摘要应该专业、客观、有条理。"""
            },
            {
                "role": "user",
                "content": f"""请基于以下各章节内容，为{company_name}（{company_code}）生成投资研究报告的执行摘要：

{sections_text}

请生成专业的执行摘要："""
            }
        ]
        
        summary = self._make_api_call(messages, temperature=0.2)
        return summary if summary else "报告摘要生成失败"