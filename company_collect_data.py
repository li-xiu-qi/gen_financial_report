"""
公司数据收集主流程
使用重构后的CompanyDataCollection类，不依赖同花顺数据
"""
from data_process.company_data_collection import CompanyDataCollection
from config import get_data_collection_config

# ====== 公司目标定义 ======
company_name = "4Paradigm"
company_code = "06682.HK"

if __name__ == "__main__":
    # 获取统一配置
    config = get_data_collection_config("company")
    
    # 创建公司数据收集器
    company_collector = CompanyDataCollection(
        company_name=company_name,
        company_code=company_code,
        max_concurrent=config['max_concurrent'],
        api_key=config['api_key'],
        base_url=config['base_url'],
        model=config['model'],
        use_zhipu_search=config['use_zhipu_search'],
        zhipu_search_key=config['zhipu_search_key'],
        search_url=config['search_url'],
        search_interval=config['search_interval'],
        use_existing_search_results=config['use_existing_search_results']
    )
    
    # 运行完整流程
    results = company_collector.run_full_process()
    
    print(f"\n🎯 {company_name} 数据收集完成!")
    print(f"📊 处理结果:")
    print(f"   - 大纲章节: {len(results.get('outline_result', {}).get('reportOutline', []))} 个")
    print(f"   - 收集数据: {len(results.get('flattened_data', []))} 条")
    
    if results.get('visual_enhancement_results'):
        enhancement = results['visual_enhancement_results']
        analysis_phase = enhancement.get('analysis_phase', {})
        suggestions = analysis_phase.get('visualization_suggestions', [])
        print(f"   - 可视化建议: {len(suggestions)} 个")
    
    if results.get('viz_results'):
        viz_results = results['viz_results']
        chart_results = viz_results.get('chart_generation_results', [])
        successful_charts = [r for r in chart_results if r.get('success', False)]
        print(f"   - 生成图表: {len(successful_charts)} 个")
