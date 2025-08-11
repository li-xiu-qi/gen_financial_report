"""
行业数据收集类
基于BaseDataCollection的行业特定实现
"""
from typing import Dict, List, Any, Optional
from financial_report.llm_calls import generate_industry_outline, generate_industry_search_queries
from data_process.industry_visual_data_enhancer import IndustryVisualDataEnhancer
from data_process.industry_visualization_data_processor import IndustryVisualizationDataProcessor
from data_process.base_data_collection import BaseDataCollection


class IndustryDataCollection(BaseDataCollection):
    """行业数据收集类"""
    
    def __init__(self, industry_name: str, max_concurrent: int = 190,
                 api_key: Optional[str] = None, base_url: Optional[str] = None, 
                 model: Optional[str] = None, use_zhipu_search: bool = False,
                 zhipu_search_key: Optional[str] = None, search_url: Optional[str] = None,
                 search_interval: float = 1.0, use_existing_search_results: bool = True):
        """
        初始化行业数据收集器
        
        Args:
            industry_name: 行业名称
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
        super().__init__(target_name=industry_name, data_type="industry", 
                        max_concurrent=max_concurrent, api_key=api_key, 
                        base_url=base_url, model=model, use_zhipu_search=use_zhipu_search,
                        zhipu_search_key=zhipu_search_key, search_url=search_url,
                        search_interval=search_interval, use_existing_search_results=use_existing_search_results)
        self.industry_name = industry_name
    
    def generate_outline(self) -> Dict[str, Any]:
        """生成行业大纲"""
        outline_result = generate_industry_outline(
            industry=self.industry_name,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=8192
        )
        
        if outline_result:
            formatted_result = {
                "reportOutline": outline_result.get("reportOutline", []),
                "industryName": outline_result.get("industryName", self.industry_name)
            }
            return formatted_result
        else:
            return {"reportOutline": []}
    
    def generate_search_queries(self, outline_result: Dict[str, Any]) -> List[Any]:
        """生成行业搜索查询"""
        queries_list = generate_industry_search_queries(
            industry_name=self.industry_name,
            outline=outline_result,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=8192
        )
        return queries_list
    
    def create_visual_enhancer(self):
        """创建行业可视化数据增强器"""
        return IndustryVisualDataEnhancer(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model
        )
    
    def create_visualization_processor(self):
        """创建行业可视化数据处理器"""
        return IndustryVisualizationDataProcessor(
            api_key=self.api_key,
            base_url=self.base_url, 
            model=self.model,
            visualization_output_dir=self.visualization_html_output_dir,
            assets_output_dir=self.visualization_assets_output_dir
        )
