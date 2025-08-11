"""
行业数据收集主流程
使用重构后的IndustryDataCollection类
"""
from data_process.industry_data_collection import IndustryDataCollection
from config import get_data_collection_config

# ====== 行业目标定义 ======
industry_name = "中国智能服务机器人产业"

if __name__ == "__main__":
    # 获取统一配置
    config = get_data_collection_config("industry")
    
    # 创建行业数据收集器
    industry_collector = IndustryDataCollection(
        industry_name=industry_name,
        max_concurrent=config['max_concurrent'],
        api_key=config['api_key'],
        base_url=config['base_url'],
        model=config['model'],
        use_zhipu_search=config['use_zhipu_search'],
        zhipu_search_key=config['zhipu_search_key'],
        search_url=config['search_url'],
        search_interval=config['search_interval']
    )
    
    # 运行完整流程
    results = industry_collector.run_full_process()
