#!/usr/bin/env python3
"""
统一报告生成脚本
支持公司、行业、宏观三种报告类型的命令行生成
包含自动数据收集功能
"""

import argparse
import os
import sys
import traceback
import subprocess
from pathlib import Path
from dotenv import load_dotenv

from unified_report_generator import UnifiedReportGenerator
from config import get_data_collection_config, get_config


def run_data_collection(collection_type: str, **kwargs) -> bool:
    """
    运行数据收集程序

    Args:
        collection_type: 收集类型 ('company', 'industry', 'macro')
        **kwargs: 传递给数据收集的参数

    Returns:
        True if successful, False otherwise
    """
    try:
        # 获取统一配置
        config = get_data_collection_config(collection_type)

        if collection_type == "company":
            from data_process.company_data_collection import CompanyDataCollection

            company_name = kwargs.get("company_name")
            company_code = kwargs.get("company_code", "")

            print(f"🔄 开始收集 {company_name} 公司数据...")

            collector = CompanyDataCollection(
                company_name=company_name,
                company_code=company_code,
                max_concurrent=config["max_concurrent"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                use_zhipu_search=config["use_zhipu_search"],
                zhipu_search_key=config["zhipu_search_key"],
                search_interval=config["search_interval"],
                use_existing_search_results=config["use_existing_search_results"],
            )

            results = collector.run_full_process()

            if results:
                print(f"✅ {company_name} 公司数据收集完成!")
                return True
            else:
                print(f"❌ {company_name} 公司数据收集失败!")
                return False

        elif collection_type == "industry":
            from data_process.industry_data_collection import IndustryDataCollection

            industry_name = kwargs.get("industry_name")

            print(f"🔄 开始收集 {industry_name} 行业数据...")

            collector = IndustryDataCollection(
                industry_name=industry_name,
                max_concurrent=config["max_concurrent"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                use_zhipu_search=config["use_zhipu_search"],
                zhipu_search_key=config["zhipu_search_key"],
                search_interval=config["search_interval"],
            )

            results = collector.run_full_process()

            if results:
                print(f"✅ {industry_name} 行业数据收集完成!")
                return True
            else:
                print(f"❌ {industry_name} 行业数据收集失败!")
                return False

        elif collection_type == "macro":
            from data_process.macro_data_collection import MacroDataCollection

            macro_name = kwargs.get("macro_name")
            time_period = kwargs.get("time", "2023-2025")
            macro_theme = f"{macro_name} ({time_period})"

            print(f"🔄 开始收集 {macro_theme} 宏观数据...")

            collector = MacroDataCollection(
                macro_theme=macro_theme,
                max_concurrent=config["max_concurrent"],
                api_key=config["api_key"],
                base_url=config["base_url"],
                model=config["model"],
                use_zhipu_search=config["use_zhipu_search"],
                zhipu_search_key=config["zhipu_search_key"],
                search_interval=config["search_interval"],
            )

            results = collector.run_full_process()

            if results:
                print(f"✅ {macro_theme} 宏观数据收集完成!")
                return True
            else:
                print(f"❌ {macro_theme} 宏观数据收集失败!")
                return False

        else:
            print(f"❌ 未知的收集类型: {collection_type}")
            return False

    except Exception as e:
        print(f"❌ 数据收集过程出错: {e}")
        traceback.print_exc()
        return False


def check_data_directory(data_directory: str, report_type: str) -> bool:
    """
    检查数据目录是否存在且包含必需的文件

    Args:
        data_directory: 数据目录路径
        report_type: 报告类型 ('company', 'industry', 'macro')

    Returns:
        True if data is complete, False otherwise
    """
    if not os.path.exists(data_directory):
        return False

    # 根据报告类型检查必需的文件
    if report_type == "company":
        required_files = [
            "company_outline.json",
            "flattened_company_data.json",
            "outline_data_allocation.json",
        ]
    elif report_type == "industry":
        required_files = [
            "industry_outline.json",
            "flattened_industry_data.json",
            "outline_data_allocation.json",
        ]
    elif report_type == "macro":
        required_files = [
            "macro_outline.json",
            "flattened_macro_data.json",
            "outline_data_allocation.json",
        ]
    else:
        return False

    # 检查所有必需文件是否存在
    for file in required_files:
        file_path = os.path.join(data_directory, file)
        if not os.path.exists(file_path):
            return False

    return True


def generate_company_report(args):
    """生成公司研究报告"""
    company_name = args.company_name
    company_code = getattr(args, "company_code", "")

    # 构建数据目录路径
    if hasattr(args, "data_dir") and args.data_dir:
        data_directory = args.data_dir
    else:
        # 首先检查通用的 test_company_datas 目录
        generic_data_dir = "test_company_datas"
        if os.path.exists(generic_data_dir) and check_data_directory(generic_data_dir, "company"):
            data_directory = generic_data_dir
        else:
            # 如果通用目录不存在或不完整，使用特定命名规则
            safe_name = company_name.replace(" ", "_").replace("/", "_")
            data_directory = f"test_company_datas_{safe_name}"

    images_directory = os.path.join(data_directory, "images")

    # 构建输出文件路径
    if hasattr(args, "output") and args.output:
        output_file = args.output
    else:
        output_file = os.path.join(data_directory, f"{company_name}_research_report.md")

    print("=" * 80)
    print("🏢 公司研究报告生成系统")
    print("=" * 80)
    print(f"📊 公司名称: {company_name}")
    if company_code:
        print(f"📈 公司代码: {company_code}")
    print(f"📂 数据目录: {data_directory}")

    try:
        # 检查数据目录，如果不存在或不完整则先收集数据
        if not check_data_directory(data_directory, "company"):
            print(f"📂 数据目录不存在或不完整: {data_directory}")
            print("🔄 开始自动收集公司数据...")

            success = run_data_collection(
                "company", company_name=company_name, company_code=company_code
            )

            if not success:
                print("❌ 数据收集失败，无法生成报告")
                return 1

            # 重新检查数据目录
            if not check_data_directory(data_directory, "company"):
                print("❌ 数据收集完成但数据文件仍不完整")
                return 1

        print("✅ 数据目录检查通过")

        # 创建报告生成器
        generator = UnifiedReportGenerator.from_env(report_type="company")

        # 加载数据
        print("📁 加载公司数据文件...")
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=(
                images_directory if os.path.exists(images_directory) else None
            ),
        )
        print("✅ 公司数据加载完成")

        # 生成报告
        print(f"📝 开始生成 {company_name} 研究报告...")
        report = generator.generate_complete_report(
            subject_name=company_name,
            data=data,
            output_file=output_file,
            enable_chart_enhancement=True,
        )

        # 显示统计信息
        print(f"\n📊 公司报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")

        print(f"\n🎉 {company_name} 公司研究报告生成完成!")
        print(f"📁 报告文件: {output_file}")

        return 0

    except Exception as e:
        print(f"❌ 公司报告生成失败: {e}")
        traceback.print_exc()
        return 1


def generate_industry_report(args):
    """生成行业研究报告"""
    industry_name = args.industry_name

    # 构建数据目录路径
    if hasattr(args, "data_dir") and args.data_dir:
        data_directory = args.data_dir
    else:
        # 首先检查通用的 test_industry_datas 目录
        generic_data_dir = "test_industry_datas"
        if os.path.exists(generic_data_dir) and check_data_directory(generic_data_dir, "industry"):
            data_directory = generic_data_dir
        else:
            # 如果通用目录不存在或不完整，使用特定命名规则
            safe_name = (
                industry_name.replace(" ", "_").replace("/", "_").replace("&", "and")
            )
            data_directory = f"test_industry_datas_{safe_name}"

    images_directory = os.path.join(data_directory, "images")

    # 构建输出文件路径
    if hasattr(args, "output") and args.output:
        output_file = args.output
    else:
        output_file = os.path.join(
            data_directory, f"{industry_name}_research_report.md"
        )

    print("=" * 80)
    print("🏭 行业研究报告生成系统")
    print("=" * 80)
    print(f"📊 行业名称: {industry_name}")
    print(f"📂 数据目录: {data_directory}")

    try:
        # 检查数据目录，如果不存在或不完整则先收集数据
        if not check_data_directory(data_directory, "industry"):
            print(f"📂 数据目录不存在或不完整: {data_directory}")
            print("🔄 开始自动收集行业数据...")

            success = run_data_collection("industry", industry_name=industry_name)

            if not success:
                print("❌ 数据收集失败，无法生成报告")
                return 1

            # 重新检查数据目录
            if not check_data_directory(data_directory, "industry"):
                print("❌ 数据收集完成但数据文件仍不完整")
                return 1

        print("✅ 数据目录检查通过")

        # 创建报告生成器
        generator = UnifiedReportGenerator.from_env(report_type="industry")

        # 加载数据
        print("📁 加载行业数据文件...")
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=(
                images_directory if os.path.exists(images_directory) else None
            ),
        )
        print("✅ 行业数据加载完成")

        # 生成报告
        print(f"📝 开始生成 {industry_name} 研究报告...")
        report = generator.generate_complete_report(
            subject_name=industry_name,
            data=data,
            output_file=output_file,
            enable_chart_enhancement=True,
        )

        # 显示统计信息
        print(f"\n📊 行业报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")

        print(f"\n🎉 {industry_name} 行业研究报告生成完成!")
        print(f"📁 报告文件: {output_file}")

        return 0

    except Exception as e:
        print(f"❌ 行业报告生成失败: {e}")
        traceback.print_exc()
        return 1


def generate_macro_report(args):
    """生成宏观研究报告"""
    macro_name = args.macro_name
    time_period = getattr(args, "time", "2023-2025")

    # 构建完整的宏观主题名称
    macro_theme = f"{macro_name} ({time_period})"

    # 构建数据目录路径
    if hasattr(args, "data_dir") and args.data_dir:
        data_directory = args.data_dir
    else:
        # 首先检查通用的 test_macro_datas 目录
        generic_data_dir = "test_macro_datas"
        if os.path.exists(generic_data_dir) and check_data_directory(
            generic_data_dir, "macro"
        ):
            data_directory = generic_data_dir
        else:
            # 如果通用目录不存在或不完整，使用特定命名规则
            safe_name = (
                macro_name.replace(" ", "_").replace("/", "_").replace("&", "and")
            )
            data_directory = f"test_macro_datas_{safe_name}"

    images_directory = os.path.join(data_directory, "images")

    # 构建输出文件路径
    if hasattr(args, "output") and args.output:
        output_file = args.output
    else:
        output_file = os.path.join(
            data_directory, f"{macro_name}_{time_period}_research_report.md"
        )

    print("=" * 80)
    print("🌏 宏观研究报告生成系统")
    print("=" * 80)
    print(f"📊 宏观主题: {macro_name}")
    print(f"📅 时间范围: {time_period}")
    print(f"📂 数据目录: {data_directory}")

    try:
        # 检查数据目录，如果不存在或不完整则先收集数据
        if not check_data_directory(data_directory, "macro"):
            print(f"📂 数据目录不存在或不完整: {data_directory}")
            print("🔄 开始自动收集宏观数据...")

            success = run_data_collection(
                "macro", macro_name=macro_name, time=time_period
            )

            if not success:
                print("❌ 数据收集失败，无法生成报告")
                return 1

            # 重新检查数据目录
            if not check_data_directory(data_directory, "macro"):
                print("❌ 数据收集完成但数据文件仍不完整")
                return 1

        print("✅ 数据目录检查通过")

        # 创建报告生成器
        generator = UnifiedReportGenerator.from_env(report_type="macro")

        # 加载数据
        print("📁 加载宏观数据文件...")
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=(
                images_directory if os.path.exists(images_directory) else None
            ),
        )
        print("✅ 宏观数据加载完成")

        # 生成报告
        print(f"📝 开始生成 {macro_theme} 研究报告...")
        report = generator.generate_complete_report(
            subject_name=macro_theme,
            data=data,
            output_file=output_file,
            enable_chart_enhancement=True,
        )

        # 显示统计信息
        print(f"\n📊 宏观报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")

        print(f"\n🎉 {macro_theme} 宏观研究报告生成完成!")
        print(f"📁 报告文件: {output_file}")

        return 0

    except Exception as e:
        print(f"❌ 宏观报告生成失败: {e}")
        traceback.print_exc()
        return 1


def main():
    """主程序入口"""

    # 加载环境变量
    load_dotenv()

    # 显示配置状态
    print("🔧 检查配置状态...")
    config = get_config()
    validation = config.validate_config()

    missing_configs = [k for k, v in validation.items() if not v]
    if missing_configs:
        print(f"⚠️ 缺少配置: {missing_configs}")
        print("💡 请检查 .env 文件配置")
    else:
        print("✅ 配置检查通过")

    # 创建主解析器
    parser = argparse.ArgumentParser(
        description="统一研究报告生成工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:

公司报告:
  python generate_report.py company --company_name "商汤科技" --company_code "00020.HK"
  python generate_report.py company --company_name "4Paradigm"

行业报告:
  python generate_report.py industry --industry_name "智能风控&大数据征信服务"
  python generate_report.py industry --industry_name "中国智能服务机器人产业"

宏观报告:
  python generate_report.py macro --macro_name "生成式AI基建与算力投资趋势" --time "2023-2026"
  python generate_report.py macro --macro_name "人工智能+政策效果评估" --time "2023-2025"
        """,
    )

    # 添加子命令
    subparsers = parser.add_subparsers(dest="command", help="报告类型")

    # 公司报告子命令
    company_parser = subparsers.add_parser("company", help="生成公司研究报告")
    company_parser.add_argument("--company_name", required=True, help="公司名称")
    company_parser.add_argument("--company_code", help="公司代码 (可选)")
    company_parser.add_argument("--data_dir", help="自定义数据目录路径")
    company_parser.add_argument("--output", help="输出文件路径")

    # 行业报告子命令
    industry_parser = subparsers.add_parser("industry", help="生成行业研究报告")
    industry_parser.add_argument("--industry_name", required=True, help="行业名称")
    industry_parser.add_argument("--data_dir", help="自定义数据目录路径")
    industry_parser.add_argument("--output", help="输出文件路径")

    # 宏观报告子命令
    macro_parser = subparsers.add_parser("macro", help="生成宏观研究报告")
    macro_parser.add_argument("--macro_name", required=True, help="宏观主题名称")
    macro_parser.add_argument(
        "--time", default="2023-2025", help="时间范围 (默认: 2023-2025)"
    )
    macro_parser.add_argument("--data_dir", help="自定义数据目录路径")
    macro_parser.add_argument("--output", help="输出文件路径")

    # 解析参数
    args = parser.parse_args()

    # 检查是否提供了子命令
    if not args.command:
        parser.print_help()
        return 1

    # 根据命令类型调用相应的处理函数
    try:
        if args.command == "company":
            return generate_company_report(args)
        elif args.command == "industry":
            return generate_industry_report(args)
        elif args.command == "macro":
            return generate_macro_report(args)
        else:
            print(f"❌ 未知的命令类型: {args.command}")
            return 1

    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
        return 1
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
