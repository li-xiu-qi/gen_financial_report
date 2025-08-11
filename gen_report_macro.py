"""
宏观研究报告生成器
基于unified_report_generator.py实现宏观研报的生成
"""

import os
import json
import traceback
from dotenv import load_dotenv
from unified_report_generator import UnifiedReportGenerator


def generate_macro_report(
    macro_theme: str,
    data_directory: str,
    images_directory: str = None,
    output_file: str = None,
    enable_chart_enhancement: bool = True
):
    """
    生成宏观研究报告
    
    Args:
        macro_theme: 宏观主题名称
        data_directory: 数据目录路径
        images_directory: 图片目录路径
        output_file: 输出文件路径
        enable_chart_enhancement: 是否启用图表增强
    
    Returns:
        生成的报告内容和统计信息
    """
    
    try:
        print(f"🌏 开始生成 {macro_theme} 宏观研究报告...")
        print(f"📂 数据目录: {data_directory}")
        if images_directory:
            print(f"🖼️  图片目录: {images_directory}")
        
        # 1. 创建宏观报告生成器
        print("🔧 初始化宏观报告生成器...")
        generator = UnifiedReportGenerator.from_env(report_type="macro")
        
        # 2. 加载数据
        print("📊 加载宏观数据文件...")
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=images_directory
        )
        print("✅ 宏观数据加载完成")
        
        # 3. 生成报告
        print(f"📝 开始生成 {macro_theme} 研究报告...")
        report = generator.generate_complete_report(
            subject_name=macro_theme,
            data=data,
            output_file=output_file,
            enable_chart_enhancement=enable_chart_enhancement
        )
        
        # 4. 显示统计信息
        print(f"\n📊 宏观报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")
        
        if output_file:
            print(f"📁 报告已保存至: {output_file}")
        
        return report
        
    except Exception as e:
        print(f"❌ 宏观报告生成失败: {e}")
        traceback.print_exc()
        return None


def main():
    """主程序入口"""
    
    # 加载环境变量
    load_dotenv()
    
    # 宏观研报配置
    macro_theme = "国家级'人工智能+'政策效果评估 (2023-2025)"
    data_directory = os.path.join("test_macro_datas")
    images_directory = os.path.join(data_directory, "images")
    output_file = os.path.join(data_directory, f"宏观政策效果评估_research_report.md")
    
    print("=" * 80)
    print("🌏 宏观研究报告生成系统")
    print("=" * 80)
    
    try:
        # 检查数据目录是否存在
        if not os.path.exists(data_directory):
            print(f"❌ 数据目录不存在: {data_directory}")
            return
        
        # 检查必需的数据文件
        required_files = [
            "macro_outline.json",
            "flattened_macro_data.json", 
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
        report = generate_macro_report(
            macro_theme=macro_theme,
            data_directory=data_directory,
            images_directory=images_directory,
            output_file=output_file,
            enable_chart_enhancement=True
        )
        
        if report:
            print(f"\n🎉 {macro_theme} 宏观研究报告生成完成!")
            print("=" * 80)
        else:
            print(f"\n❌ {macro_theme} 宏观研究报告生成失败!")
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        traceback.print_exc()


def generate_custom_macro_report(
    macro_theme: str,
    theme_code: str = "",
    data_dir: str = "test_macro_datas",
    output_dir: str = None
):
    """
    生成自定义宏观报告的便捷函数
    
    Args:
        macro_theme: 宏观主题名称
        theme_code: 主题代码（可选）
        data_dir: 数据目录
        output_dir: 输出目录（默认使用数据目录）
    """
    
    if not output_dir:
        output_dir = data_dir
    
    # 构建文件路径
    images_directory = os.path.join(data_dir, "images")
    output_file = os.path.join(output_dir, f"{macro_theme}_research_report.md")
    
    # 生成报告
    return generate_macro_report(
        macro_theme=macro_theme,
        data_directory=data_dir,
        images_directory=images_directory if os.path.exists(images_directory) else None,
        output_file=output_file,
        enable_chart_enhancement=True
    )


def generate_macro_report_batch(
    themes: list,
    base_data_dir: str = "macro_data",
    base_output_dir: str = "macro_reports"
):
    """
    批量生成多个宏观报告
    
    Args:
        themes: 宏观主题列表，每个元素包含主题名称等信息
        base_data_dir: 基础数据目录
        base_output_dir: 基础输出目录
    """
    
    results = []
    
    for theme_info in themes:
        try:
            if isinstance(theme_info, str):
                theme_name = theme_info
            else:
                theme_name = theme_info.get("name", "")
            
            if not theme_name:
                print(f"⚠️ 跳过无效的主题信息: {theme_info}")
                continue
            
            # 构建目录路径
            theme_data_dir = os.path.join(base_data_dir, theme_name)
            theme_output_dir = os.path.join(base_output_dir, theme_name)
            
            # 确保输出目录存在
            os.makedirs(theme_output_dir, exist_ok=True)
            
            print(f"\n🌏 处理宏观主题: {theme_name}")
            
            # 生成报告
            report = generate_custom_macro_report(
                macro_theme=theme_name,
                data_dir=theme_data_dir,
                output_dir=theme_output_dir
            )
            
            results.append({
                "theme_name": theme_name,
                "success": report is not None,
                "report": report
            })
            
        except Exception as e:
            print(f"❌ 处理宏观主题 {theme_name} 时出错: {e}")
            results.append({
                "theme_name": theme_name,
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
        print(f"\n❌ 失败的宏观主题:")
        for result in failed:
            print(f"   - {result['theme_name']}: {result.get('error', '未知错误')}")
    
    return results


def generate_policy_analysis_report(
    policy_name: str,
    analysis_period: str = "2023-2025",
    data_dir: str = "policy_data",
    output_dir: str = "policy_reports"
):
    """
    生成政策分析报告的便捷函数
    
    Args:
        policy_name: 政策名称
        analysis_period: 分析周期
        data_dir: 数据目录
        output_dir: 输出目录
    """
    
    theme_name = f"{policy_name}政策效果评估 ({analysis_period})"
    
    return generate_custom_macro_report(
        macro_theme=theme_name,
        data_dir=data_dir,
        output_dir=output_dir
    )


def generate_economic_trend_report(
    economic_indicator: str,
    forecast_period: str = "2024-2026",
    data_dir: str = "economic_data",
    output_dir: str = "economic_reports"
):
    """
    生成经济趋势报告的便捷函数
    
    Args:
        economic_indicator: 经济指标名称
        forecast_period: 预测周期
        data_dir: 数据目录
        output_dir: 输出目录
    """
    
    theme_name = f"{economic_indicator}发展趋势分析 ({forecast_period})"
    
    return generate_custom_macro_report(
        macro_theme=theme_name,
        data_dir=data_dir,
        output_dir=output_dir
    )


if __name__ == "__main__":
    main()
