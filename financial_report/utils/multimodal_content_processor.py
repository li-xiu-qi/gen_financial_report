# -*- coding: utf-8 -*-
# @FileName: multimodal_content_processor.py
# @Author: Kiro
# @Time: 2025-01-23
# @Description: 完整的多模态内容处理流程，整合所有步骤

import os
import json
from typing import List, Dict, Any, Optional
from financial_report.llm_calls.visual_content_identifier import identify_visualizable_content
from financial_report.llm_calls.text2infographic_html import text2infographic_html, text_to_infographic_html_pompt
from financial_report.llm_calls.image_description_generator import generate_image_description
from financial_report.llm_calls.multimodal_content_assembler import assemble_multimodal_content
from financial_report.utils.html2png_snapshot import html_to_png_snapshot


class MultimodalContentProcessor:
    """多模态内容处理器，整合文本分析、可视化生成、图片描述和内容组装的完整流程"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        output_dir: str = "multimodal_outputs",
        max_tokens: int = 4000,
        temperature: float = 0.3
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.output_dir = output_dir
        self.max_tokens = max_tokens
        self.temperature = temperature
        
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def process_text_content(
        self, 
        text_content: str, 
        content_id: str = None
    ) -> Dict[str, Any]:
        """
        处理单段文本内容，完成完整的多模态处理流程
        
        Args:
            text_content: 待处理的文本内容
            content_id: 内容标识符，用于文件命名
            
        Returns:
            处理结果字典
        """
        if not content_id:
            content_id = f"content_{hash(text_content) % 10000}"
        
        print(f"开始处理内容: {content_id}")
        
        # 步骤1: 识别可视化内容
        print("  步骤1: 识别可视化内容...")
        visual_analysis = identify_visualizable_content(
            text_to_analyze=text_content,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
        
        result = {
            "content_id": content_id,
            "original_text": text_content,
            "visual_analysis": visual_analysis,
            "visualizations": [],
            "assembled_content": None
        }
        
        # 如果不适合可视化，直接返回原文本
        if not visual_analysis.get("is_visualizable", False):
            print(f"  内容不适合可视化: {visual_analysis.get('reason', '未知原因')}")
            result["assembled_content"] = {
                "assembled_text": text_content,
                "has_visualizations": False
            }
            return result
        
        # 步骤2: 生成HTML图表
        print("  步骤2: 生成HTML图表...")
        try:
            html_content = text2infographic_html(
                system_prompt=text_to_infographic_html_pompt,
                query=text_content,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if html_content:
                # 保存HTML文件
                html_path = os.path.join(self.output_dir, f"{content_id}.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                # 步骤3: 转换为PNG图片
                print("  步骤3: 转换为PNG图片...")
                try:
                    image_path = os.path.join(self.output_dir, f"{content_id}.png")
                    abs_image_path = html_to_png_snapshot(html_content, image_path)
                    
                    # 步骤4: 生成图片描述
                    print("  步骤4: 生成图片描述...")
                    image_description = generate_image_description(
                        original_text=text_content,
                        chart_type=visual_analysis.get("visualization_type", "unknown"),
                        chart_title=visual_analysis.get("chart_title", "数据图表"),
                        chart_data=visual_analysis.get("extracted_data", {}),
                        api_key=self.api_key,
                        base_url=self.base_url,
                        model=self.model,
                        max_tokens=1000,
                        temperature=self.temperature
                    )
                    
                    visualization_info = {
                        "html_path": html_path,
                        "image_path": abs_image_path,
                        "description": image_description,
                        "chart_type": visual_analysis.get("visualization_type"),
                        "chart_title": visual_analysis.get("chart_title")
                    }
                    
                    result["visualizations"].append(visualization_info)
                    
                except Exception as e:
                    print(f"  图片生成失败: {e}")
                    visualization_info = {
                        "html_path": html_path,
                        "image_path": None,
                        "description": f"基于{visual_analysis.get('chart_title', '数据')}的可视化图表",
                        "chart_type": visual_analysis.get("visualization_type"),
                        "chart_title": visual_analysis.get("chart_title"),
                        "error": str(e)
                    }
                    result["visualizations"].append(visualization_info)
            
        except Exception as e:
            print(f"  HTML生成失败: {e}")
            result["html_generation_error"] = str(e)
        
        # 步骤5: 组装多模态内容
        print("  步骤5: 组装多模态内容...")
        chart_descriptions = [viz.get("description", "") for viz in result["visualizations"]]
        image_paths = [viz.get("image_path") for viz in result["visualizations"] if viz.get("image_path")]
        
        assembled_result = assemble_multimodal_content(
            original_text=text_content,
            chart_descriptions=chart_descriptions,
            image_paths=image_paths,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=2000,
            temperature=self.temperature
        )
        
        result["assembled_content"] = assembled_result
        
        # 保存完整结果
        result_path = os.path.join(self.output_dir, f"{content_id}_result.json")
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"  处理完成: {content_id}")
        return result
    
    def process_multiple_contents(
        self, 
        text_contents: List[str], 
        content_ids: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        批量处理多段文本内容
        
        Args:
            text_contents: 文本内容列表
            content_ids: 内容标识符列表
            
        Returns:
            处理结果列表
        """
        if content_ids is None:
            content_ids = [f"content_{i}" for i in range(len(text_contents))]
        
        results = []
        for i, text_content in enumerate(text_contents):
            content_id = content_ids[i] if i < len(content_ids) else f"content_{i}"
            result = self.process_text_content(text_content, content_id)
            results.append(result)
        
        return results
    
    def get_summary_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成处理结果的汇总报告
        
        Args:
            results: 处理结果列表
            
        Returns:
            汇总报告
        """
        total_contents = len(results)
        visualizable_contents = sum(1 for r in results if r["visual_analysis"].get("is_visualizable", False))
        successful_visualizations = sum(1 for r in results if r["visualizations"])
        total_images = sum(len(r["visualizations"]) for r in results)
        
        summary = {
            "total_contents": total_contents,
            "visualizable_contents": visualizable_contents,
            "successful_visualizations": successful_visualizations,
            "total_images_generated": total_images,
            "visualization_rate": visualizable_contents / total_contents if total_contents > 0 else 0,
            "success_rate": successful_visualizations / visualizable_contents if visualizable_contents > 0 else 0,
            "details": []
        }
        
        for result in results:
            detail = {
                "content_id": result["content_id"],
                "is_visualizable": result["visual_analysis"].get("is_visualizable", False),
                "visualization_count": len(result["visualizations"]),
                "has_assembled_content": result["assembled_content"] is not None
            }
            summary["details"].append(detail)
        
        return summary