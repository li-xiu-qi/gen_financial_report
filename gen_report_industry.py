"""
行业研究报告生成器
基于unified_report_generator.py实现行业研报的生成
"""

import os
import json
import traceback
from dotenv import load_dotenv
from unified_report_generator import UnifiedReportGenerator


def generate_industry_report(
    industry_name: str,
    data_directory: str,
    images_directory: str = None,
    output_file: str = None,
    enable_chart_enhancement: bool = True
):
    """
    生成行业研究报告
    
    Args:
        industry_name: 行业名称
        data_directory: 数据目录路径
        images_directory: 图片目录路径
        output_file: 输出文件路径
        enable_chart_enhancement: 是否启用图表增强
    
    Returns:
        生成的报告内容和统计信息
    """
    
    try:
        print(f"🏭 开始生成 {industry_name} 行业研究报告...")
        print(f"📂 数据目录: {data_directory}")
        if images_directory:
            print(f"🖼️  图片目录: {images_directory}")
        
        # 1. 创建行业报告生成器
        print("🔧 初始化行业报告生成器...")
        generator = UnifiedReportGenerator.from_env(report_type="industry")
        
        # 2. 加载数据
        print("📊 加载行业数据文件...")
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=images_directory
        )
        print("✅ 行业数据加载完成")
        
        # 3. 生成报告
        print(f"📝 开始生成 {industry_name} 研究报告...")
        report = generator.generate_complete_report(
            subject_name=industry_name,
            data=data,
            output_file=output_file,
            enable_chart_enhancement=enable_chart_enhancement
        )
        
        # 4. 显示统计信息
        print(f"\n📊 行业报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")
        
        if output_file:
            print(f"📁 报告已保存至: {output_file}")
        
        return report
        
    except Exception as e:
        print(f"❌ 行业报告生成失败: {e}")
        traceback.print_exc()
        return None


def main():
    """主程序入口"""
    
    # 加载环境变量
    load_dotenv()
    
    # 行业研报配置
    industry_name = "中国智能服务机器人产业"
    data_directory = os.path.join("test_industry_datas")
    images_directory = os.path.join(data_directory, "images")
    output_file = os.path.join(data_directory, f"{industry_name}_research_report.md")
    
    print("=" * 80)
    print("🏭 行业研究报告生成系统")
    print("=" * 80)
    
    try:
        # 检查数据目录是否存在
        if not os.path.exists(data_directory):
            print(f"❌ 数据目录不存在: {data_directory}")
            return
        
        # 检查必需的数据文件
        required_files = [
            "industry_outline.json",
            "flattened_industry_data.json", 
            "outline_data_allocation.json"
        ]
        
        missing_files = []
        for file in required_files:
            file_path = os.path.join(data_directory, file)
            if not os.path.exists(file_path):
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ 缺少必需的数据文件: {missing_files}")
            return
        
        # 检查图片目录
        if images_directory and not os.path.exists(images_directory):
            print(f"⚠️ 图片目录不存在: {images_directory}，将跳过图表功能")
            images_directory = None
        
        # 生成报告
        report = generate_industry_report(
            industry_name=industry_name,
            data_directory=data_directory,
            images_directory=images_directory,
            output_file=output_file,
            enable_chart_enhancement=True
        )
        
        if report:
            print(f"\n🎉 {industry_name} 行业研究报告生成完成!")
            print("=" * 80)
        else:
            print(f"\n❌ {industry_name} 行业研究报告生成失败!")
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        traceback.print_exc()


def generate_custom_industry_report(
    industry_name: str,
    industry_code: str = "",
    data_dir: str = "test_industry_datas",
    output_dir: str = None
):
    """
    生成自定义行业报告的便捷函数
    
    Args:
        industry_name: 行业名称
        industry_code: 行业代码（可选）
        data_dir: 数据目录
        output_dir: 输出目录（默认使用数据目录）
    """
    
    if not output_dir:
        output_dir = data_dir
    
    # 构建文件路径
    images_directory = os.path.join(data_dir, "images")
    output_file = os.path.join(output_dir, f"{industry_name}_research_report.md")
    
    # 生成报告
    return generate_industry_report(
        industry_name=industry_name,
        data_directory=data_dir,
        images_directory=images_directory if os.path.exists(images_directory) else None,
        output_file=output_file,
        enable_chart_enhancement=True
    )


def generate_industry_report_batch(
    industries: list,
    base_data_dir: str = "industry_data",
    base_output_dir: str = "industry_reports"
):
    """
    批量生成多个行业报告
    
    Args:
        industries: 行业列表，每个元素包含行业名称等信息
        base_data_dir: 基础数据目录
        base_output_dir: 基础输出目录
    """
    
    results = []
    
    for industry_info in industries:
        try:
            if isinstance(industry_info, str):
                industry_name = industry_info
            else:
                industry_name = industry_info.get("name", "")
            
            if not industry_name:
                print(f"⚠️ 跳过无效的行业信息: {industry_info}")
                continue
            
            # 构建目录路径
            industry_data_dir = os.path.join(base_data_dir, industry_name)
            industry_output_dir = os.path.join(base_output_dir, industry_name)
            
            # 确保输出目录存在
            os.makedirs(industry_output_dir, exist_ok=True)
            
            print(f"\n🏭 处理行业: {industry_name}")
            
            # 生成报告
            report = generate_custom_industry_report(
                industry_name=industry_name,
                data_dir=industry_data_dir,
                output_dir=industry_output_dir
            )
            
            results.append({
                "industry_name": industry_name,
                "success": report is not None,
                "report": report
            })
            
        except Exception as e:
            print(f"❌ 处理行业 {industry_name} 时出错: {e}")
            results.append({
                "industry_name": industry_name,
                "success": False,
                "error": str(e)
            })
    
    # 汇总结果
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    print(f"\n📊 批量生成结果汇总:")
    print(f"   - 成功: {len(successful)} 个")
    print(f"   - 失败: {len(failed)} 个")
    
    if failed:
        print(f"\n❌ 失败的行业:")
        for result in failed:
            print(f"   - {result['industry_name']}: {result.get('error', '未知错误')}")
    
    return results


if __name__ == "__main__":
    main()
