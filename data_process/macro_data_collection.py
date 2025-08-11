"""
宏观数据收集类
基于BaseDataCollection的宏观特定实现
"""
from typing import Dict, List, Any, Optional
from financial_report.llm_calls.generate_macro_outline import generate_macro_outline
from financial_report.llm_calls.generate_macro_search_queries import generate_macro_search_queries
from data_process.macro_visual_data_enhancer import MacroVisualDataEnhancer
from data_process.macro_visualization_data_processor import MacroVisualizationDataProcessor
from data_process.base_data_collection import BaseDataCollection


class MacroDataCollection(BaseDataCollection):
    """宏观数据收集类"""
    
    def __init__(self, macro_theme: str, max_concurrent: int = 190,
                 api_key: Optional[str] = None, base_url: Optional[str] = None, 
                 model: Optional[str] = None, use_zhipu_search: bool = False,
                 zhipu_search_key: Optional[str] = None, search_url: Optional[str] = None,
                 search_interval: float = 1.0, use_existing_search_results: bool = True):
        """
        初始化宏观数据收集器
        
        Args:
            macro_theme: 宏观主题
            max_concurrent: 最大并发数
            api_key: API密钥，如果为None则从环境变量获取
            base_url: API基础URL，如果为None则从环境变量获取
            model: 模型名称，如果为None则从环境变量获取
            use_zhipu_search: 是否使用智谱搜索，默认False使用本地搜索服务
            zhipu_search_key: 智谱搜索API密钥
            search_url: 本地搜索服务URL，如果为None则从环境变量获取
            search_interval: 搜索间隔时间（秒），默认1.0秒，防止请求过于频繁
            use_existing_search_results: 是否使用已有搜索结果，默认True，节省搜索成本
        """
        super().__init__(target_name=macro_theme, data_type="macro", 
                        max_concurrent=max_concurrent, api_key=api_key, 
                        base_url=base_url, model=model, use_zhipu_search=use_zhipu_search,
                        zhipu_search_key=zhipu_search_key, search_url=search_url,
                        search_interval=search_interval, use_existing_search_results=use_existing_search_results)
        self.macro_theme = macro_theme
    
    def generate_outline(self) -> Dict[str, Any]:
        """生成宏观大纲"""
        outline_result = generate_macro_outline(
            macro_theme=self.macro_theme,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=8192
        )
        
        if outline_result:
            formatted_result = {
                "reportOutline": outline_result.get("reportOutline", []),
                "macroName": outline_result.get("macroName", self.macro_theme)
            }
            return formatted_result
        else:
            return {"reportOutline": []}
    
    def generate_search_queries(self, outline_result: Dict[str, Any]) -> List[Any]:
        """生成宏观搜索查询"""
        queries_list = generate_macro_search_queries(
            macro_theme=self.macro_theme,
            outline=outline_result,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_output_tokens=8192
        )
        return queries_list
    
    def create_visual_enhancer(self):
        """创建宏观可视化数据增强器"""
        return MacroVisualDataEnhancer(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model
        )
    
    def create_visualization_processor(self):
        """创建宏观可视化数据处理器"""
        return MacroVisualizationDataProcessor(
            api_key=self.api_key,
            base_url=self.base_url, 
            model=self.model,
            visualization_output_dir=self.visualization_html_output_dir,
            assets_output_dir=self.visualization_assets_output_dir
        )
