"""
基础数据收集类
提供通用的数据收集流程，包括大纲生成、搜索查询、数据收集、摘要、分配和可视化等功能
"""
import os
import json
import time
import traceback
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from financial_report.search_tools.search_tools import bing_search_with_cache, zhipu_search_with_cache
from data_process.content_summarizer import generate_summaries_for_collected_data
from data_process.outline_data_allocator import allocate_data_to_outline_sync
from data_process.search_data_processor import SearchDataProcessor


class BaseDataCollection(ABC):
    """基础数据收集类"""
    
    def __init__(self, target_name: str, data_type: str, max_concurrent: int = 190, 
                 api_key: Optional[str] = None, base_url: Optional[str] = None, 
                 model: Optional[str] = None, use_zhipu_search: bool = False, zhipu_search_key: str = None,
                 search_url: Optional[str] = None, search_interval: float = 1.0, 
                 use_existing_search_results: bool = True):
        """
        初始化基础数据收集器
        
        Args:
            target_name: 目标名称（行业名、宏观主题等）
            data_type: 数据类型（industry、macro等）
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
        self.target_name = target_name
        self.data_type = data_type
        self.max_concurrent = max_concurrent
        self.use_zhipu_search = use_zhipu_search
        self.search_interval = search_interval
        self.use_existing_search_results = use_existing_search_results
        
        # 加载环境变量
        load_dotenv()
        self._setup_api_config(api_key, base_url, model, zhipu_search_key=zhipu_search_key, search_url=search_url)
        self._setup_paths()
        
    def _setup_api_config(self, api_key: Optional[str] = None, base_url: Optional[str] = None, 
                         model: Optional[str] = None, zhipu_search_key: Optional[str] = None,
                         search_url: Optional[str] = None):
        """设置API配置"""
        # Chat 部分统一使用通用的API配置（硅基流动等）
        self.api_key = api_key or os.getenv("GUIJI_API_KEY")
        self.base_url = base_url or os.getenv("GUIJI_BASE_URL")
        self.model = model or os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO")
        self.max_chat_tokens = int(128 * 1024 * 0.8)
        self.search_url = search_url or os.getenv("SEARCH_URL")
        
        # 搜索部分专门的智谱配置
        if self.use_zhipu_search and not zhipu_search_key:
            raise ValueError("zhipu API key is required for using Zhipu search.")

        self.zhipu_api_key = zhipu_search_key
        self.zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
        self.zhipu_model = os.getenv("ZHIPU_FREE_TEXT_MODEL") 
        self.zhipu_max_chat_tokens = int(128 * 1024 * 0.8)
        
    def _setup_paths(self):
        """设置文件路径"""
        # 创建数据目录
        self.data_dir = f"test_{self.data_type}_datas"
        if not os.path.exists(self.data_dir):
            os.mkdir(self.data_dir)
            
        # 定义文件路径
        self.outline_file = os.path.join(self.data_dir, f"{self.data_type}_outline.json")
        self.flattened_data_file = os.path.join(self.data_dir, f"flattened_{self.data_type}_data.json")
        self.allocation_result_file = os.path.join(self.data_dir, "outline_data_allocation.json")
        self.viz_results_file = os.path.join(self.data_dir, "visualization_data_results.json")
        
        # 可视化路径配置
        self.visualization_html_output_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
        self.visualization_assets_output_dir = os.path.join(self.data_dir, "images")
        
        if not os.path.exists(self.visualization_assets_output_dir):
            os.makedirs(self.visualization_assets_output_dir, exist_ok=True)
    
    @abstractmethod
    def generate_outline(self) -> Dict[str, Any]:
        """生成大纲 - 子类必须实现"""
        pass
    
    @abstractmethod
    def generate_search_queries(self, outline_result: Dict[str, Any]) -> List[Any]:
        """生成搜索查询 - 子类必须实现"""
        pass
    
    @abstractmethod
    def create_visual_enhancer(self):
        """创建可视化数据增强器 - 子类必须实现"""
        pass
    
    @abstractmethod
    def create_visualization_processor(self):
        """创建可视化数据处理器 - 子类必须实现"""
        pass
    
    def print_start_banner(self):
        """打印开始横幅"""
        search_type = "智谱搜索" if self.use_zhipu_search else "Bing搜索"
        existing_results_info = "使用已有结果" if self.use_existing_search_results else "重新搜索"
        print("=" * 60)
        print(f"🚀 启动{self.data_type}研究报告数据收集流程")
        print(f"🎯 目标{self.data_type}: {self.target_name}")
        print(f"🔍 搜索方式: {search_type}")
        print(f"📁 搜索策略: {existing_results_info}")
        print(f"⏱️ 搜索间隔: {self.search_interval}秒")
        print("=" * 60)
    
    def step1_generate_outline(self) -> Dict[str, Any]:
        """步骤1: 生成大纲"""
        print(f"\n步骤 1：生成{self.data_type}大纲")
        print("="*50)
        
        try:
            outline_result = self.generate_outline()
            
            if outline_result:
                # 确保有标准格式 - 统一使用公司格式
                if "reportOutline" not in outline_result:
                    outline_result = {
                        "reportOutline": outline_result.get("outline", []),
                        f"{self.data_type}Name": outline_result.get(f"{self.data_type}Name", self.target_name)
                    }
                    
                    # 为不同类型添加特定字段
                    if self.data_type == "company":
                        outline_result["companyCode"] = outline_result.get("companyCode", "")
                    elif self.data_type == "industry":
                        # 行业类型不需要代码字段
                        pass
                    elif self.data_type == "macro":
                        # 宏观类型不需要代码字段  
                        pass
            else:
                outline_result = {"reportOutline": []}
            
            with open(self.outline_file, "w", encoding="utf-8") as f:
                json.dump(outline_result, f, ensure_ascii=False, indent=2)
            
            print(f"✅ {self.data_type}大纲生成完成，共 {len(outline_result.get('reportOutline', []))} 个章节")
            return outline_result
            
        except Exception as e:
            print(f"❌ {self.data_type}大纲生成失败: {e}")
            return {"outline": []}
    
    def step2_collect_data(self, outline_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """步骤2: 生成搜索查询并收集数据"""
        print(f"\n步骤 2：生成搜索查询并收集数据")
        print("="*50)
        
        # 检查是否使用已有搜索结果
        if self.use_existing_search_results and os.path.exists(self.flattened_data_file):
            try:
                with open(self.flattened_data_file, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
                
                if existing_data and len(existing_data) > 0:
                    print(f"📁 发现已有搜索结果文件: {self.flattened_data_file}")
                    print(f"📊 已有数据项数量: {len(existing_data)}")
                    print(f"💰 使用已有搜索结果，节省搜索成本")
                    print(f"✅ 跳过搜索步骤，直接使用已有的 {len(existing_data)} 条数据")
                    return existing_data
                else:
                    print(f"📁 搜索结果文件存在但为空，将重新搜索")
            except Exception as e:
                print(f"⚠️ 读取已有搜索结果失败: {e}")
                print(f"🔄 将重新执行搜索")
        elif self.use_existing_search_results:
            print(f"📁 搜索结果文件不存在: {self.flattened_data_file}")
            print(f"🔄 将执行新的搜索")
        else:
            print(f"🔄 配置为重新搜索，忽略已有结果文件")
        
        try:
            # 生成搜索查询
            queries_list = self.generate_search_queries(outline_result)
            print(f"✅ 生成 {len(queries_list)} 个搜索查询")
            
            # 创建搜索数据处理器
            search_processor = SearchDataProcessor(
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                summary_api_key=self.api_key,
                summary_base_url=self.base_url,
                summary_model=self.model
            )
            
            # 第一阶段：批量收集所有搜索数据
            print("\n🔍 第一阶段：批量收集搜索数据...")
            search_start_time = time.time()
            all_raw_search_results = []
            current_id = 1
            
            for i, query_info in enumerate(queries_list, 1):
                query = query_info.get("query", query_info) if isinstance(query_info, dict) else query_info
                section = query_info.get("section_title", f"{self.data_type}研究") if isinstance(query_info, dict) else f"{self.data_type}研究"
                
                print(f"📊 [{i}/{len(queries_list)}] 搜索: {query[:60]}...")
                
                # 添加搜索间隔控制，防止请求过于频繁
                if i > 1:  # 第一个请求不需要等待
                    print(f"⏳ 等待 {self.search_interval} 秒，防止请求过于频繁...")
                    time.sleep(self.search_interval)
                
                try:
                    # 根据配置选择搜索方式
                    if self.use_zhipu_search:
                        print(f"🔍 使用智谱搜索...")
                        search_results = zhipu_search_with_cache(
                            query=query,
                            count=50,
                            force_refresh=False,
                            zhipu_api_key=self.zhipu_api_key,
                            timeout=30,
                            rate_limit_delay=0.5
                        )
                    else:
                        print(f"🔍 使用Bing搜索...")
                        search_results = bing_search_with_cache(
                            query=query, 
                            search_api_url=self.search_url,
                            total=10,
                            rate_limit_delay=0.5
                        )
                    
                    if search_results:
                        # 格式化搜索结果
                        formatted_results = search_processor.format_search_results_to_flattened_data(
                            search_results=search_results,
                            company_name=self.target_name,
                            search_query=query,
                            start_id=current_id
                        )
                        
                        if formatted_results:
                            # 添加章节信息
                            for result in formatted_results:
                                result["section_title"] = section
                            
                            all_raw_search_results.extend(formatted_results)
                            current_id = max([int(item["id"]) for item in formatted_results]) + 1
                            print(f"   ✅ 获得 {len(formatted_results)} 个原始数据项")
                    else:
                        print(f"   ⚠️ 搜索未返回结果")
                
                except Exception as e:
                    print(f"   ❌ 搜索失败: {e}")
                    # 搜索失败时也要等待，避免连续失败请求
                    if i < len(queries_list):
                        print(f"⏳ 搜索失败，等待 {self.search_interval * 2} 秒后继续...")
                        time.sleep(self.search_interval * 2)
                    continue
            
            search_end_time = time.time()
            search_duration = search_end_time - search_start_time
            print(f"✅ 第一阶段完成，共收集 {len(all_raw_search_results)} 个原始数据项")
            print(f"⏱️ 搜索阶段耗时: {search_duration:.2f}秒")
            
            # 第二阶段：批量并发处理大模型任务
            print(f"\n🤖 第二阶段：批量并发处理大模型任务（并发数: {self.max_concurrent}）...")
            llm_start_time = time.time()
            all_flattened_data = []
            
            if all_raw_search_results:
                try:
                    # 批量质量评估
                    print(f"🔍 开始批量质量评估 {len(all_raw_search_results)} 个数据项...")
                    high_quality_results = search_processor.assess_search_results_quality(
                        search_results=[{
                            "url": item["url"],
                            "title": item["title"], 
                            "md": item["content"],
                            "data_source_type": item["data_source_type"]
                        } for item in all_raw_search_results],
                        company_name=self.target_name,
                        section_title=f"{self.data_type}研究",
                        max_concurrent=self.max_concurrent
                    )
                    
                    if high_quality_results:
                        print(f"✅ 质量评估完成，筛选出 {len(high_quality_results)} 个高质量数据项")
                        
                        # 将质量评估结果映射回原始数据
                        high_quality_urls = {item["url"] for item in high_quality_results}
                        filtered_raw_results = []
                        
                        for raw_item in all_raw_search_results:
                            if raw_item["url"] in high_quality_urls:
                                # 找到对应的质量评估结果，添加质量评估信息
                                for hq_item in high_quality_results:
                                    if hq_item["url"] == raw_item["url"]:
                                        raw_item["quality_assessment"] = hq_item.get("quality_assessment", {})
                                        break
                                filtered_raw_results.append(raw_item)
                        
                        # 批量生成摘要
                        print(f"📝 开始批量生成摘要...")
                        summarized_results = generate_summaries_for_collected_data(
                            data_items=filtered_raw_results,
                            api_key=self.api_key,
                            base_url=self.base_url,
                            model=self.model,
                            max_summary_length=500,
                            max_concurrent=self.max_concurrent,
                            chat_max_token_length=self.max_chat_tokens
                        )
                        
                        if summarized_results:
                            all_flattened_data = summarized_results
                            print(f"✅ 摘要生成完成，最终获得 {len(all_flattened_data)} 个高质量数据项")
                        else:
                            all_flattened_data = filtered_raw_results
                            print(f"⚠️ 摘要生成失败，使用原始数据: {len(all_flattened_data)} 个数据项")
                    else:
                        print("⚠️ 质量评估未筛选出高质量数据，使用所有原始数据")
                        all_flattened_data = all_raw_search_results
                        
                except Exception as e:
                    print(f"❌ 大模型批量处理失败: {e}")
                    print("📋 将使用原始搜索数据...")
                    all_flattened_data = all_raw_search_results
            else:
                print("⚠️ 没有收集到搜索数据")
            
            llm_end_time = time.time()
            llm_duration = llm_end_time - llm_start_time
            total_duration = llm_end_time - search_start_time
            
            print(f"⏱️ 大模型处理耗时: {llm_duration:.2f}秒")
            print(f"⏱️ 总耗时: {total_duration:.2f}秒")
            print(f"📊 性能统计: 搜索{search_duration:.1f}s + 大模型{llm_duration:.1f}s = 总计{total_duration:.1f}s")
            
            # 保存展平数据
            with open(self.flattened_data_file, "w", encoding="utf-8") as f:
                json.dump(all_flattened_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 数据收集完成，共获得 {len(all_flattened_data)} 条高质量数据")
            return all_flattened_data
            
        except Exception as e:
            print(f"❌ 数据收集失败: {e}")
            traceback.print_exc()
            return []
    
    def step3_allocate_data(self, outline_result: Dict[str, Any], flattened_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """步骤3: 数据分配到大纲"""
        print(f"\n步骤 3：数据分配到大纲")
        print("="*50)
        
        try:
            allocation_result = allocate_data_to_outline_sync(
                outline_data=outline_result,
                flattened_data=flattened_data,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                max_concurrent=self.max_concurrent
            )
            
            with open(self.allocation_result_file, "w", encoding="utf-8") as f:
                json.dump(allocation_result, f, ensure_ascii=False, indent=2)
            
            stats = allocation_result.get("allocation_stats", {})
            print(f"✅ 数据分配完成")
            print(f"   - 匹配成功: {stats.get('matched_count', 0)}")
            print(f"   - 匹配率: {stats.get('match_rate', 0):.1f}%")
            
            return allocation_result
            
        except Exception as e:
            print(f"❌ 数据分配失败: {e}")
            return {}
    
    def step4_visual_enhancement(self, flattened_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """步骤4: 可视化数据增强"""
        print(f"\n步骤 4：可视化数据增强")
        print("="*50)
        
        try:
            if flattened_data:
                # 创建可视化数据增强器
                visual_enhancer = self.create_visual_enhancer()
                
                # 设置大纲数据（确保可视化建议与大纲章节匹配）
                if hasattr(visual_enhancer, 'set_outline_data') and os.path.exists(self.outline_file):
                    try:
                        with open(self.outline_file, "r", encoding="utf-8") as f:
                            outline_data = json.load(f)
                        visual_enhancer.set_outline_data(outline_data)
                        print(f"   📋 已设置大纲数据，确保章节匹配")
                    except Exception as e:
                        print(f"   ⚠️  设置大纲数据失败: {e}")
                
                # 运行可视化数据增强
                visual_enhancement_results = visual_enhancer.run_full_enhancement_process(
                    flattened_data=flattened_data,
                    target_name=self.target_name,
                    max_concurrent=self.max_concurrent
                )
                
                analysis_phase = visual_enhancement_results.get("analysis_phase", {})
                suggestions = analysis_phase.get("visualization_suggestions", [])
                print(f"✅ 可视化数据增强完成，生成 {len(suggestions)} 个可视化建议")
                
                return visual_enhancement_results
                
            else:
                print("⚠️ 没有可用数据，跳过可视化增强")
                return None
                
        except Exception as e:
            print(f"❌ 可视化数据增强失败: {e}")
            traceback.print_exc()
            return None
    
    def step5_visualization_processing(self, visual_enhancement_results: Optional[Dict[str, Any]], 
                                     flattened_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """步骤5: 可视化数据处理"""
        print(f"\n步骤 5：可视化数据处理")
        print("="*50)
        
        try:
            if visual_enhancement_results and flattened_data:
                # 创建可视化数据处理器
                viz_processor = self.create_visualization_processor()
                
                # 直接处理可视化数据并生成图表（不依赖文件）
                viz_results = viz_processor.process_visualization_data(
                    enhancement_results=visual_enhancement_results,
                    all_flattened_data=flattened_data,
                    target_name=self.target_name,
                    max_context_tokens=self.max_chat_tokens,
                    max_concurrent=self.max_concurrent
                )
                
                # 保存处理结果
                with open(self.viz_results_file, "w", encoding="utf-8") as f:
                    json.dump(viz_results, f, ensure_ascii=False, indent=2)
                
                processing_summary = viz_results.get("processing_summary", {})
                successful_count = processing_summary.get("successful_count", 0)
                print(f"✅ 可视化数据处理完成，成功生成 {successful_count} 个图表")
                
                return viz_results
                
            else:
                print("⚠️ 没有可视化增强结果，跳过数据处理")
                return None
                
        except Exception as e:
            print(f"❌ 可视化数据处理失败: {e}")
            traceback.print_exc()
            return None
    
    def print_summary(self):
        """打印流程总结"""
        print(f"\n🎉 {self.data_type}数据收集流程完成！")
        print("📁 生成的文件:")
        print(f"   - {self.data_type}大纲: {self.outline_file}")
        print(f"   - 展平数据: {self.flattened_data_file}")
        print(f"   - 数据分配: {self.allocation_result_file}")
        
        if os.path.exists(self.viz_results_file):
            print(f"   - 可视化处理: {self.viz_results_file}")
        
        # 检查图表资产
        if os.path.exists(self.visualization_assets_output_dir):
            png_files = [f for f in os.listdir(self.visualization_assets_output_dir) if f.endswith('.png')]
            if png_files:
                print(f"   - 图表资产: {len(png_files)} 个PNG文件")
    
    def run_full_process(self):
        """运行完整流程"""
        self.print_start_banner()
        
        # 步骤1: 生成大纲
        outline_result = self.step1_generate_outline()
        
        # 步骤2: 收集数据
        flattened_data = self.step2_collect_data(outline_result)
        
        # 步骤3: 数据分配
        allocation_result = self.step3_allocate_data(outline_result, flattened_data)
        
        # 步骤4: 可视化增强
        visual_enhancement_results = self.step4_visual_enhancement(flattened_data)
        
        # 步骤5: 可视化处理
        viz_results = self.step5_visualization_processing(visual_enhancement_results, flattened_data)
        
        # 打印总结
        self.print_summary()
        
        return {
            "outline_result": outline_result,
            "flattened_data": flattened_data,
            "allocation_result": allocation_result,
            "visual_enhancement_results": visual_enhancement_results,
            "viz_results": viz_results
        }
