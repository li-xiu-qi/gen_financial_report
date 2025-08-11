import json
import requests
import os
import warnings

from dotenv import load_dotenv
from financial_report.llm_calls import generate_company_outline, company_outline_search_queries
from financial_report.search_tools.search_tools import (
    bing_search_with_cache,
    get_tonghuashun_data,
)
from financial_report.llm_calls.content_assessor import assess_content_quality_hybrid
from data_process.find_competitors import find_competitors
from data_process.content_summarizer import generate_summaries_for_collected_data
from data_process.outline_data_allocator import allocate_data_to_outline_sync
from data_process.company_visual_data_enhancer import CompanyVisualDataEnhancer
from data_process.company_visualization_data_processor import CompanyVisualizationDataProcessor

# 我们的大模型生成的内容统一保存到test_datas目录下，我们先创建这个
if not os.path.exists("test_company_datas"):
    os.mkdir("test_company_datas")

# ====== 导入到 ReflectRAG ======
# 导入环境变量
load_dotenv()

# 获取本地embedding模型配置
local_api_key = os.getenv("LOCAL_API_KEY")
local_base_url = os.getenv("LOCAL_BASE_URL")
local_embedding_model = os.getenv("LOCAL_EMBEDDING_MODEL")

api_key = os.getenv("GUIJI_API_KEY")
base_url = os.getenv("GUIJI_BASE_URL")
model = os.getenv("GUIJI_FREE_TEXT_MODEL")
costly_model = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO")

max_output_tokens = int(8 * 1024)
# 导入search_url和pdf_base_url
search_url = os.getenv("SEARCH_URL")
pdf_base_url = os.getenv("PDF_BASE_URL")

zhipu_api_key = os.getenv("GUIJI_API_KEY")
zhipu_base_url = os.getenv("GUIJI_BASE_URL")
zhipu_model = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO")
zhipu_max_chat_tokens = int(128 * 1024 * 0.8)  # 128K * 0.8

# ====== 统一并发配置 ======
MAX_CONCURRENT = 190  # 统一的最大并发数

# 定义目标公司信息
company_name = "4Paradigm"
company_code = "06682.HK"
target_company = company_name


# 文件路径定义（全部json和分析结果统一到 test_company_datas，图片也统一到 test_company_datas/images）
competitors_file = os.path.join("test_company_datas", "competitors.json")
company_outline_file = os.path.join("test_company_datas", "company_outline.json")
competitors_tonghuashun_data_file = os.path.join("test_company_datas", "competitors_tonghuashun_data.json")
flattened_tonghuashun_file = os.path.join("test_company_datas", "flattened_tonghuashun_data.json")
allocation_result_file = os.path.join("test_company_datas", "outline_data_allocation.json")
search_results_file = os.path.join("test_company_datas", "search_results_data.json")
enhanced_allocation_file = os.path.join("test_company_datas", "enhanced_allocation_result.json")
visual_enhancement_file = os.path.join("test_company_datas", "visual_enhancement_results.json")

# 图片输出目录
image_output_dir = os.path.join("test_company_datas", "images")
if not os.path.exists(image_output_dir):
    os.makedirs(image_output_dir, exist_ok=True)

# ====== 路径配置 ======
# 可视化输出路径配置
VISUALIZATION_HTML_OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))  # 项目根目录，与js同级
VISUALIZATION_ASSETS_OUTPUT_DIR = image_output_dir  # PNG和JSON资产输出目录

print(f"📁 可视化路径配置:")
print(f"   HTML输出目录: {VISUALIZATION_HTML_OUTPUT_DIR}")
print(f"   资产输出目录: {VISUALIZATION_ASSETS_OUTPUT_DIR}")

print("=" * 60)
print("🚀 启动公司研究报告数据收集和分配流程")
print("=" * 60)

# 步骤1: 获取竞争对手
print("\n" + "="*50)
print("步骤 1：获取竞争对手")
print("="*50)

try:
    competitors_result = find_competitors(
        name=target_company,
        api_key=zhipu_api_key,
        base_url=zhipu_base_url,
        chat_model=zhipu_model,
        search_api_url=search_url
    )
    
    with open(competitors_file, "w", encoding="utf-8") as f:
        json.dump(competitors_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 竞争对手分析完成")
    print(f"📁 文件已保存到: {competitors_file}")
    
    if "competitors" in competitors_result:
        competitors_list = competitors_result["competitors"]
        print(f"🏢 找到竞争对手: {len(competitors_list)} 家")
        for i, comp in enumerate(competitors_list[:5], 1):
            print(f"   {i}. {comp.get('name', 'N/A')} - {comp.get('description', 'N/A')[:50]}...")
        if len(competitors_list) > 5:
            print(f"   ... 还有 {len(competitors_list) - 5} 家竞争对手")
    
except Exception as e:
    print(f"❌ 竞争对手获取失败: {e}")
    competitors_result = {"competitors": []}

# 步骤2: 生成公司大纲
print("\n" + "="*50)
print("步骤 2：生成公司大纲")
print("="*50)

try:
    company_outline_result = generate_company_outline(
        company=target_company,
        company_code=company_code,
        api_key=zhipu_api_key,
        base_url=zhipu_base_url,
        model=zhipu_model,
        max_tokens=max_output_tokens
    )
    
    with open(company_outline_file, "w", encoding="utf-8") as f:
        json.dump(company_outline_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 公司大纲生成完成")
    print(f"📁 文件已保存到: {company_outline_file}")
    
    if "outline" in company_outline_result:
        outline_sections = company_outline_result["outline"]
        print(f"📋 大纲章节: {len(outline_sections)} 个")
        for i, section in enumerate(outline_sections[:5], 1):
            print(f"   {i}. {section.get('title', 'N/A')}")
        if len(outline_sections) > 5:
            print(f"   ... 还有 {len(outline_sections) - 5} 个章节")
    
except Exception as e:
    print(f"❌ 公司大纲生成失败: {e}")
    company_outline_result = {"outline": []}

# 步骤3: 获取同花顺数据
print("\n" + "="*50)
print("步骤 3：获取同花顺数据")
print("="*50)

try:
    # 读取竞争对手数据 
    if os.path.exists(competitors_file):
        with open(competitors_file, "r", encoding="utf-8") as f:
            competitors_data = json.load(f)
            
        # 处理不同的数据格式
        if isinstance(competitors_data, dict) and "competitors" in competitors_data:
            competitors_list = competitors_data["competitors"]
        elif isinstance(competitors_data, list):
            competitors_list = competitors_data
        else:
            competitors_list = []
    else:
        competitors_list = []
    
    # 构建公司列表
    all_companies = [{"name": target_company, "code": company_code}]
    
    for comp in competitors_list:
        if isinstance(comp, dict):
            comp_name = comp.get("company_name") or comp.get("name")
            comp_code = comp.get("tonghuashun_total_code") or comp.get("stock_code") or comp.get("code")
            
            if comp_name and comp_code:
                all_companies.append({
                    "name": comp_name,
                    "code": comp_code
                })
    
    print(f"📊 开始获取 {len(all_companies)} 家公司的同花顺数据...")
    
    # 为每个公司获取同花顺数据
    competitors_tonghuashun_data = {}
    for company in all_companies:
        try:
            company_data = get_tonghuashun_data(
                tonghuashun_total_code=company["code"],
                search_api_url=search_url
            )
            competitors_tonghuashun_data[company["name"]] = company_data
            print(f"✅ 获取 {company['name']} 数据成功")
        except Exception as e:
            print(f"⚠️  获取 {company['name']} 数据失败: {e}")
            competitors_tonghuashun_data[company["name"]] = {"navs": [], "news": []}
    
    with open(competitors_tonghuashun_data_file, "w", encoding="utf-8") as f:
        json.dump(competitors_tonghuashun_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 同花顺数据获取完成")
    print(f"📁 文件已保存到: {competitors_tonghuashun_data_file}")
    
    # 统计数据点
    total_navs = sum(len(data.get("navs", [])) for data in competitors_tonghuashun_data.values())
    total_news = sum(len(data.get("news", [])) for data in competitors_tonghuashun_data.values())
    print(f"📈 获取数据点: 导航 {total_navs} 个，新闻 {total_news} 个")
    
except Exception as e:
    print(f"❌ 同花顺数据获取失败: {e}")
    competitors_tonghuashun_data = {}

# 步骤4: 展平同花顺数据
print("\n" + "="*50)
print("步骤 4：展平同花顺数据")
print("="*50)

def flatten_tonghuashun_data(tonghuashun_data_dict: dict) -> list:
    """
    将同花顺数据展平为统一格式的数据列表
    
    Args:
        tonghuashun_data_dict: 公司名到同花顺数据的映射
        
    Returns:
        展平后的数据列表
    """
    flattened_data = []
    current_id = 1
    
    for company_name, company_data in tonghuashun_data_dict.items():
        # 处理导航数据 (navs)
        navs = company_data.get("navs", [])
        for nav_item in navs:
            flattened_record = {
                "id": str(current_id),
                "company_name": company_name,
                "company_code": "",
                "market": "",
                "tonghuashun_total_code": "",
                "url": nav_item.get("url", ""),
                "title": nav_item.get("title", ""),
                "data_source_type": nav_item.get("data_source_type", "html"),
                "content": nav_item.get("md", ""),
                "search_query": "",
                "data_source": "tonghuashun_nav"
            }
            flattened_data.append(flattened_record)
            current_id += 1
        
        # 处理新闻数据 (news)
        news = company_data.get("news", [])
        for news_item in news:
            flattened_record = {
                "id": str(current_id),
                "company_name": company_name,
                "company_code": "",
                "market": "",
                "tonghuashun_total_code": "",
                "url": news_item.get("url", ""),
                "title": news_item.get("title", ""),
                "data_source_type": news_item.get("data_source_type", "html"),
                "content": news_item.get("md", ""),
                "search_query": "",
                "data_source": "tonghuashun_news"
            }
            flattened_data.append(flattened_record)
            current_id += 1
    
    return flattened_data

try:
    flattened_data = flatten_tonghuashun_data(competitors_tonghuashun_data)
    
    with open(flattened_tonghuashun_file, "w", encoding="utf-8") as f:
        json.dump(flattened_data, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据展平完成")
    print(f"📁 文件已保存到: {flattened_tonghuashun_file}")
    print(f"📊 展平后数据项: {len(flattened_data)} 条")
    
except Exception as e:
    print(f"❌ 数据展平失败: {e}")
    flattened_data = []

# 步骤5: 数据分配到大纲
print("\n" + "="*50)
print("步骤 5：数据分配到大纲")
print("="*50)

try:
    from data_process.outline_data_allocator import allocate_data_to_outline_sync
    
    allocation_result = allocate_data_to_outline_sync(
        outline_data=company_outline_result,
        flattened_data=flattened_data,
        api_key=zhipu_api_key,
        base_url=zhipu_base_url,
        model=zhipu_model,
        max_tokens_per_batch=zhipu_max_chat_tokens,
        max_concurrent=MAX_CONCURRENT
    )
    
    with open(allocation_result_file, "w", encoding="utf-8") as f:
        json.dump(allocation_result, f, ensure_ascii=False, indent=2)
    print(f"✅ 数据分配完成")
    print(f"📁 文件已保存到: {allocation_result_file}")
    
    stats = allocation_result.get("allocation_stats", {})
    print(f"📊 分配统计:")
    print(f"   - 匹配成功: {stats.get('matched_count', 0)}")
    print(f"   - 总章节数: {stats.get('total_sections', 0)}")
    print(f"   - 匹配率: {stats.get('match_rate', 0):.1f}%")
    
except Exception as e:
    print(f"❌ 数据分配失败: {e}")
    allocation_result = {"allocated_sections": [], "allocation_stats": {}}

# 步骤6: 检查数据覆盖率
print("\n" + "="*50)
print("步骤 6：分析数据覆盖情况")
print("="*50)

try:
    # 分析覆盖率 - 修复数据结构访问
    outline_with_allocations = allocation_result.get("outline_with_allocations", {})
    report_outline = outline_with_allocations.get("reportOutline", [])
    
    empty_sections = []
    filled_sections = []
    
    for section in report_outline:
        allocated_data_ids = section.get("allocated_data_ids", [])
        if allocated_data_ids and len(allocated_data_ids) > 0:
            filled_sections.append(section)
        else:
            empty_sections.append(section)
    
    coverage_analysis = {
        "empty_sections": empty_sections,
        "filled_sections": filled_sections,
        "total_sections": len(report_outline),
        "coverage_rate": len(filled_sections) / len(report_outline) * 100 if report_outline else 0
    }
    
    coverage_file = "test_company_datas/outline_coverage_analysis.json"
    with open(coverage_file, "w", encoding="utf-8") as f:
        json.dump(coverage_analysis, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 覆盖率分析完成")
    print(f"📁 分析结果已保存到: {coverage_file}")
    print(f"📊 数据覆盖情况:")
    print(f"   - 已填充章节: {len(filled_sections)}")
    print(f"   - 空白章节: {len(empty_sections)}")
    if report_outline:
        print(f"   - 总体覆盖率: {coverage_analysis['coverage_rate']:.1f}%")
    
    if empty_sections:
        print(f"\n⚠️ 需要补充数据的章节:")
        for i, section in enumerate(empty_sections[:5], 1):
            print(f"   {i}. {section.get('title', 'N/A')}")
        if len(empty_sections) > 5:
            print(f"   ... 还有 {len(empty_sections) - 5} 个空白章节")
    
except Exception as e:
    print(f"❌ 覆盖率分析失败: {e}")
    empty_sections = []
    import traceback
    traceback.print_exc()

# 步骤7: 智能搜索增强
print("\n" + "="*50)
print("步骤 7：智能搜索增强")
print("="*50)

if empty_sections and len(empty_sections) > 0:
    print(f"\n🔍 开始为 {len(empty_sections)} 个无数据章节进行智能搜索...")
    
    try:
        from data_process.search_data_processor import SearchDataProcessor
        
        # 创建搜索数据处理器
        search_processor = SearchDataProcessor(
            api_key=zhipu_api_key,
            base_url=zhipu_base_url,
            model=zhipu_model,
            summary_api_key=zhipu_api_key,
            summary_base_url=zhipu_base_url,
            summary_model=zhipu_model
        )
        
        # 执行智能搜索
        search_results = search_processor.smart_search_for_empty_sections(
            empty_sections=empty_sections,
            company_name=target_company,
            existing_flattened_data=flattened_data,
            search_api_url=search_url,
            chat_max_token_length=zhipu_max_chat_tokens,
            max_searches_per_section=3,
            max_results_per_search=10,
            max_concurrent_summary=MAX_CONCURRENT
        )
        
        # 保存搜索结果
        with open(search_results_file, "w", encoding="utf-8") as f:
            json.dump(search_results, f, ensure_ascii=False, indent=2)
        print(f"✅ 智能搜索完成")
        print(f"📁 搜索结果已保存到: {search_results_file}")
        
        # 合并搜索数据
        new_search_data = search_results.get("new_search_data", [])
        if new_search_data:
            print(f"🔗 合并搜索数据...")
            enhanced_flattened_data = search_processor.merge_search_data_with_existing(
                existing_flattened_data=flattened_data,
                new_search_data=new_search_data
            )
            
            # 保存增强后的展平数据
            enhanced_flattened_file = "test_company_datas/enhanced_flattened_data.json"
            with open(enhanced_flattened_file, "w", encoding="utf-8") as f:
                json.dump(enhanced_flattened_data, f, ensure_ascii=False, indent=2)
            print(f"📁 增强后数据已保存到: {enhanced_flattened_file}")
            
            # 重新分配数据
            print(f"🔄 重新分配增强后的数据...")
            enhanced_allocation = allocate_data_to_outline_sync(
                outline_data=company_outline_result,
                flattened_data=enhanced_flattened_data,
                api_key=zhipu_api_key,
                base_url=zhipu_base_url,
                model=zhipu_model,
                max_tokens_per_batch=zhipu_max_chat_tokens,
                max_concurrent=MAX_CONCURRENT
            )
            
            with open(enhanced_allocation_file, "w", encoding="utf-8") as f:
                json.dump(enhanced_allocation, f, ensure_ascii=False, indent=2)
            print(f"✅ 增强分配完成")
            print(f"📁 结果已保存到: {enhanced_allocation_file}")
            
            # 更新统计信息
            enhanced_stats = enhanced_allocation.get("allocation_stats", {})
            print(f"📊 增强分配统计:")
            print(f"   - 匹配成功: {enhanced_stats.get('matched_count', 0)}")
            print(f"   - 总章节数: {enhanced_stats.get('total_sections', 0)}")
            print(f"   - 匹配率: {enhanced_stats.get('match_rate', 0):.1f}%")
            
    except Exception as e:
        print(f"❌ 智能搜索失败: {e}")
        print("将继续后续流程...")
        import traceback
        traceback.print_exc()
else:
    print(f"\n🎉 所有章节都有数据分配，无需额外搜索！")

# 步骤8: 可视化数据增强
print("\n" + "="*50)
print("步骤 8：可视化数据增强")
print("="*50)
print(f"🏢 分析目标公司: {company_name}")

try:
    # 确定要使用的最终数据
    final_flattened_data = None
    if os.path.exists("test_company_datas/enhanced_flattened_data.json"):
        print(f"\n📊 使用增强后的展平数据进行可视化分析...")
        with open("test_company_datas/enhanced_flattened_data.json", "r", encoding="utf-8") as f:
            final_flattened_data = json.load(f)
    elif flattened_data:
        print(f"\n📊 使用原始展平数据进行可视化分析...")
        final_flattened_data = flattened_data
    else:
        print(f"\n⚠️  没有可用的展平数据，跳过可视化增强步骤")

    if final_flattened_data:
        # 确定要使用的分配结果
        final_allocation_result = allocation_result
        if os.path.exists(enhanced_allocation_file):
            print(f"📋 使用增强后的分配结果...")
            with open(enhanced_allocation_file, "r", encoding="utf-8") as f:
                final_allocation_result = json.load(f)
        else:
            print(f"📋 使用原始分配结果...")

        # 创建公司可视化数据增强器
        visual_enhancer = CompanyVisualDataEnhancer(
            api_key=zhipu_api_key,
            base_url=zhipu_base_url,
            model=zhipu_model,
            outline_data=company_outline_result  # 传入大纲数据
        )

        # 运行完整的可视化数据增强流程
        print(f"🎯 目标公司: {company_name}")
        visual_enhancement_results = visual_enhancer.run_full_enhancement_process(
            flattened_data=final_flattened_data,
            target_name=company_name,  # 明确传递目标公司名称
            max_concurrent=MAX_CONCURRENT
        )

        # 保存可视化增强结果
        with open(visual_enhancement_file, "w", encoding="utf-8") as f:
            json.dump(visual_enhancement_results, f, ensure_ascii=False, indent=2)

        print(f"✅ 可视化数据增强完成")
        print(f"📁 结果已保存到: {visual_enhancement_file}")

        # 显示可视化建议统计
        analysis_phase = visual_enhancement_results.get("analysis_phase", {})
        visualization_suggestions = analysis_phase.get("visualization_suggestions", [])
        print(f"🎨 为 {company_name} 生成可视化建议: {len(visualization_suggestions)} 条")

        if visualization_suggestions:
            print(f"📊 可视化类型分布:")
            chart_types = {}
            for suggestion in visualization_suggestions:
                chart_type = suggestion.get("visualization_type", "未知")
                chart_types[chart_type] = chart_types.get(chart_type, 0) + 1
            
            for chart_type, count in chart_types.items():
                print(f"   - {chart_type}: {count} 个")
            
            print(f"📋 章节分布:")
            sections = {}
            for suggestion in visualization_suggestions:
                section = suggestion.get("section", "未分类")
                sections[section] = sections.get(section, 0) + 1
            
            for section, count in sections.items():
                print(f"   - 第{section}章节: {count} 个")
    else:
        print(f"⚠️  跳过可视化数据增强步骤")
        visual_enhancement_results = None

except Exception as e:
    print(f"❌ 可视化数据增强失败: {e}")

# 步骤8.5: 可视化数据处理 
print("\n" + "="*50)
print("步骤 8.5：可视化数据处理")  
print("="*50)
print(f"🏢 处理目标公司: {company_name}")

try:
    # 检查是否有可视化增强结果
    if os.path.exists(visual_enhancement_file) and visual_enhancement_results:
        print(f"📊 开始可视化数据处理...")
        
        # 确定要使用的数据
        final_data_for_viz = None
        if os.path.exists("test_datas/enhanced_flattened_data.json"):
            with open("test_company_datas/enhanced_flattened_data.json", "r", encoding="utf-8") as f:
                final_data_for_viz = json.load(f)
        elif flattened_data:
            final_data_for_viz = flattened_data
        
        if final_data_for_viz:
            # 创建公司可视化数据处理器（使用重构后的类）
            viz_processor = CompanyVisualizationDataProcessor(
                api_key=zhipu_api_key,
                base_url=zhipu_base_url, 
                model=zhipu_model,
                visualization_output_dir=VISUALIZATION_HTML_OUTPUT_DIR,
                assets_output_dir=VISUALIZATION_ASSETS_OUTPUT_DIR
            )
            
            # 处理可视化数据并生成图表
            print(f"🎯 目标公司: {company_name}")
            viz_results = viz_processor.process_visualization_results(
                visual_enhancement_file=visual_enhancement_file,
                all_flattened_data=final_data_for_viz,
                target_name=company_name,  # 明确传递目标公司名称
                max_context_tokens=zhipu_max_chat_tokens,
                max_concurrent=MAX_CONCURRENT
            )
            
            # 保存处理结果
            viz_results_file = "test_company_datas/visualization_data_results.json"
            with open(viz_results_file, "w", encoding="utf-8") as f:
                json.dump(viz_results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 可视化数据处理完成")
            print(f"📁 结果已保存到: {viz_results_file}")
            
            # 统计生成的图表
            processing_summary = viz_results.get("processing_summary", {})
            successful_count = processing_summary.get("successful_count", 0)
            failed_count = processing_summary.get("failed_count", 0)
            
            print(f"📈 为 {company_name} 生成图表统计:")
            print(f"   - 成功生成: {successful_count} 个")
            print(f"   - 生成失败: {failed_count} 个")
            
            # 显示成功生成的图表详情
            processed_suggestions = viz_results.get("processed_suggestions", [])
            successful_charts = [s for s in processed_suggestions if s.get("success", False)]
            
            if successful_charts:
                print(f"🎨 为 {company_name} 成功生成的图表:")
                chart_types = {}
                sections = {}
                
                for chart in successful_charts:
                    chart_type = chart.get("visualization_type", "未知")
                    section = chart.get("section", "未分类")
                    chart_types[chart_type] = chart_types.get(chart_type, 0) + 1
                    sections[section] = sections.get(section, 0) + 1
                    
                    print(f"   - {chart.get('chart_title', 'Unknown')}")
                    print(f"     类型: {chart_type}, 章节: 第{section}章节")
                    print(f"     PNG: {'有' if chart.get('has_png', False) else '无'}")
                
                print(f"\n📊 图表类型分布:")
                for chart_type, count in chart_types.items():
                    print(f"   - {chart_type}: {count} 个")
                
                print(f"\n📋 章节分布:")
                for section, count in sections.items():
                    print(f"   - 第{section}章节: {count} 个")
                    
                # 检查图片输出目录
                if os.path.exists(image_output_dir):
                    image_files = [f for f in os.listdir(image_output_dir) if f.endswith('.png')]
                    json_files = [f for f in os.listdir(image_output_dir) if f.endswith('.json')]
                    print(f"\n📁 图表资产:")
                    print(f"   - 图片文件: {len(image_files)} 个")
                    print(f"   - 配置文件: {len(json_files)} 个")
        else:
            print(f"⚠️  没有可用数据进行可视化处理")
    else:
        print(f"⚠️  没有可视化增强结果，跳过数据处理步骤")
        
except Exception as e:
    print(f"❌ 可视化数据处理失败: {e}")

# 步骤9: 图表分配功能已集成到可视化数据增强步骤中
print("\n" + "="*50)
print("步骤 9：图表分配")
print("="*50)
print(f"✅ 图表分配功能已集成到可视化数据增强步骤中")

print(f"\n🎉 数据收集和分配流程完成！")
print("📁 生成的文件:")
print(f"   - 竞争对手: {competitors_file}")
print(f"   - 公司大纲: {company_outline_file}")
print(f"   - 同花顺数据: {competitors_tonghuashun_data_file}")
print(f"   - 展平数据: {flattened_tonghuashun_file}")
print(f"   - 分配结果: {allocation_result_file}")

# 显示可选的增强文件
if os.path.exists("test_company_datas/outline_coverage_analysis.json"):
    print(f"   - 覆盖分析: test_company_datas/outline_coverage_analysis.json")
if os.path.exists(search_results_file):
    print(f"   - 搜索结果: {search_results_file}")
if os.path.exists(enhanced_allocation_file):
    print(f"   - 增强分配: {enhanced_allocation_file}")
if os.path.exists(visual_enhancement_file):
    print(f"   - 可视化增强: {visual_enhancement_file}")
if os.path.exists("test_company_datas/visualization_data_results.json"):
    print(f"   - 可视化数据收集: test_company_datas/visualization_data_results.json")

print(f"\n💡 推荐使用的最终数据文件:")
if os.path.exists(enhanced_allocation_file):
    print(f"   📊 使用增强后的分配结果: {enhanced_allocation_file}")
else:
    print(f"   📊 使用原始分配结果: {allocation_result_file}")

if os.path.exists(visual_enhancement_file):
    print(f"   🎨 可视化增强结果: {visual_enhancement_file}")

if os.path.exists("test_company_datas/visualization_data_results.json"):
    print(f"   📊 可视化数据收集: test_company_datas/visualization_data_results.json")

# 显示图表资产信息
if os.path.exists(image_output_dir) and os.listdir(image_output_dir):
    png_files = [f for f in os.listdir(image_output_dir) if f.endswith('.png')]
    image_count = len(png_files)
    print(f"   📈 图表资产: {image_output_dir}/ ({image_count} 个PNG图表)")
else:
    print(f"   ⚠️  暂无图表资产")
