"""
公司数据收集类
基于BaseDataCollection的公司特定实现
"""
from typing import Dict, List, Any, Optional
from financial_report.llm_calls import generate_company_outline
from financial_report.llm_calls.generate_company_search_queries import generate_company_search_queries
from data_process.company_visual_data_enhancer import CompanyVisualDataEnhancer
from data_process.company_visualization_data_processor import CompanyVisualizationDataProcessor
from data_process.base_data_collection import BaseDataCollection


class CompanyDataCollection(BaseDataCollection):
    """公司数据收集类"""
    
    def __init__(self, company_name: str, company_code: str = "", max_concurrent: int = 190,
                 api_key: Optional[str] = None, base_url: Optional[str] = None, 
                 model: Optional[str] = None, use_zhipu_search: bool = False,
                 zhipu_search_key: Optional[str] = None, search_url: Optional[str] = None,
                 search_interval: float = 1.0, use_existing_search_results: bool = True):
        """
        初始化公司数据收集器
        
        Args:
            company_name: 公司名称
            company_code: 公司代码（股票代码等）
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
        super().__init__(target_name=company_name, data_type="company", 
                        max_concurrent=max_concurrent, api_key=api_key, 
                        base_url=base_url, model=model, use_zhipu_search=use_zhipu_search,
                        zhipu_search_key=zhipu_search_key, search_url=search_url,
                        search_interval=search_interval, use_existing_search_results=use_existing_search_results)
        self.company_name = company_name
        self.company_code = company_code
    
    def generate_outline(self) -> Dict[str, Any]:
        """生成公司大纲"""
        outline_result = generate_company_outline(
            company=self.company_name,
            company_code=self.company_code,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=8192
        )
        
        if outline_result:
            # 确保有标准格式
            if "reportOutline" not in outline_result:
                # 如果返回的是 {"outline": [...]} 格式，转换为标准格式
                if "outline" in outline_result:
                    formatted_result = {
                        "reportOutline": outline_result["outline"],
                        "companyName": outline_result.get("companyName", self.company_name),
                        "companyCode": outline_result.get("companyCode", self.company_code)
                    }
                    return formatted_result
            else:
                # 已经是标准格式，直接返回
                return outline_result
        
        return {"reportOutline": []}
    
    def generate_search_queries(self, outline_result: Dict[str, Any]) -> List[Any]:
        """生成公司搜索查询"""
        # 直接使用公司搜索查询生成函数
        queries_list = generate_company_search_queries(
            company_name=self.company_name,
            stock_code=self.company_code,
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model,
            max_tokens=8192
        )
        
        return queries_list
    
    def create_visual_enhancer(self):
        """创建公司可视化数据增强器"""
        return CompanyVisualDataEnhancer(
            api_key=self.api_key,
            base_url=self.base_url,
            model=self.model
        )
    
    def create_visualization_processor(self):
        """创建公司可视化数据处理器"""
        return CompanyVisualizationDataProcessor(
            api_key=self.api_key,
            base_url=self.base_url, 
            model=self.model,
            visualization_output_dir=self.visualization_html_output_dir,
            assets_output_dir=self.visualization_assets_output_dir
        )
