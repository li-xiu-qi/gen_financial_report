"""
工具类和辅助函数
"""

import os
import re
from typing import Dict, Any, Tuple


class PathUtils:
    """路径处理工具类"""
    
    @staticmethod
    def normalize_path(path: str) -> str:
        """规范化路径分隔符"""
        if not path:
            return ""
        return path.replace('\\', '/')
    
    @staticmethod
    def is_valid_png_path(path: str) -> bool:
        """检查PNG路径是否有效"""
        return bool(path and os.path.exists(path))


class ChartValidator:
    """图表验证器"""
    
    @staticmethod
    def get_chart_status(chart: Dict[str, Any]) -> Tuple[str, str, str]:
        """
        获取图表状态信息
        
        Args:
            chart: 图表字典
            
        Returns:
            (status, path_info, usage_instruction) 元组
        """
        png_path = chart.get('png_path', '')
        absolute_png_path = PathUtils.normalize_path(png_path)
        has_valid_png = PathUtils.is_valid_png_path(absolute_png_path)
        
        if has_valid_png:
            status = "✅ 可用（有效PNG图片路径）"
            path_info = f"- **PNG图片绝对路径**：{absolute_png_path}"
            chart_title = chart.get('chart_title', '图表')
            usage_instruction = f"""- **🚨 必须使用的Markdown嵌入语法**：`![{chart_title}]({absolute_png_path})`
- **⚠️ 重要提醒**：必须原样复制上述Markdown语法到正文中，在分析中自然嵌入
- **使用要求**：此图表必须在内容中引用，并提供2-3段深入的数据解读"""
        else:
            status = "❌ 不可用（PNG图片路径无效或为空）"
            path_info = f"- **PNG图片路径**：{absolute_png_path or '路径为空'}"
            usage_instruction = f"""- **🚫 禁止使用**：此图表PNG路径无效，不可在内容中引用图片
- **替代方案**：可以基于HTML代码和图表描述进行文字分析，但不要尝试嵌入图片
- **严格禁止**：绝不可编造或虚构此图表的图片路径"""
        
        return status, path_info, usage_instruction


class HtmlContentReader:
    """HTML内容读取器"""
    
    @staticmethod
    def read_html_content(html_path: str, chart_data: Dict[str, Any] = None) -> str:
        """
        读取HTML内容
        
        Args:
            html_path: HTML文件路径
            chart_data: 图表数据（可选，可能已包含html_content）
            
        Returns:
            HTML内容字符串
        """
        # 先尝试从chart_data中获取
        if chart_data:
            html_content = chart_data.get('html_content', '')
            if html_content:
                return html_content
        
        # 从文件读取
        if html_path and os.path.exists(html_path):
            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                print(f"⚠️ 读取HTML文件失败 {html_path}: {e}")
                return "HTML内容读取失败"
        
        return ""


class TitleValidator:
    """标题验证器"""
    
    @staticmethod
    def has_chinese_number(title: str) -> bool:
        """
        检查标题是否已经包含序号（中文数字或阿拉伯数字）
        
        Args:
            title: 标题文本
            
        Returns:
            如果包含序号则返回True
        """
        # 检查中文数字序号
        chinese_numbers = ['一、', '二、', '三、', '四、', '五、', '六、', '七、', '八、', '九、', '十、']
        if any(num in title for num in chinese_numbers):
            return True
        
        # 检查阿拉伯数字序号（如 "1."、"2."等）
        if re.match(r'^\d+\.', title.strip()):
            return True
            
        return False
