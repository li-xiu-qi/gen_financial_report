"""
公司研究报告生成器
基于unified_report_generator.py实现公司研报的生成
"""

import os
import json
import argparse
import traceback
from dotenv import load_dotenv
from unified_report_generator import UnifiedReportGenerator


def generate_company_report(
    company_name: str,
    data_directory: str,
    images_directory: str = None,
    output_file: str = None,
    enable_chart_enhancement: bool = True
):
    """
    生成公司研究报告
    
    Args:
        company_name: 公司名称
        data_directory: 数据目录路径
        images_directory: 图片目录路径
        output_file: 输出文件路径
        enable_chart_enhancement: 是否启用图表增强
    
    Returns:
        生成的报告内容和统计信息
    """
    
    try:
        print(f"🏢 开始生成 {company_name} 公司研究报告...")
        print(f"📂 数据目录: {data_directory}")
        if images_directory:
            print(f"🖼️  图片目录: {images_directory}")
        
        # 1. 创建公司报告生成器
        print("🔧 初始化公司报告生成器...")
        generator = UnifiedReportGenerator.from_env(report_type="company")
        
        # 2. 加载数据
        print("📊 加载公司数据文件...")
        data = generator.load_report_data(
            data_dir=data_directory,
            images_directory=images_directory
        )
        print("✅ 公司数据加载完成")
        
        # 3. 生成报告
        print(f"📝 开始生成 {company_name} 研究报告...")
        report = generator.generate_complete_report(
            subject_name=company_name,
            data=data,
            output_file=output_file,
            enable_chart_enhancement=enable_chart_enhancement
        )
        
        # 4. 显示统计信息
        print(f"\n📊 公司报告生成统计:")
        stats = report.get("generation_stats", {})
        print(f"   - 总章节数: {stats.get('total_sections', 0)}")
        print(f"   - 有数据支撑: {stats.get('sections_with_data', 0)}")
        print(f"   - 无数据支撑: {stats.get('sections_without_data', 0)}")
        print(f"   - 总图表数: {stats.get('total_charts', 0)}")
        
        if output_file:
            print(f"📁 报告已保存至: {output_file}")
        
        return report
        
    except Exception as e:
        print(f"❌ 公司报告生成失败: {e}")
        traceback.print_exc()
        return None


def main():
    """主程序入口"""
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="生成公司研究报告")
    parser.add_argument('--company_name', default='4Paradigm', help='公司名称')
    parser.add_argument('--company_code', help='公司代码 (可选)')
    parser.add_argument('--data_dir', default='test_company_datas', help='数据目录路径')
    parser.add_argument('--output', help='输出文件路径')
    
    args = parser.parse_args()
    
    # 加载环境变量
    load_dotenv()
    
    # 公司研报配置
    company_name = args.company_name
    data_directory = args.data_dir
    images_directory = os.path.join(data_directory, "images")
    output_file = args.output or os.path.join(data_directory, f"{company_name}_research_report.md")
    
    print("=" * 80)
    print("🏢 公司研究报告生成系统")
    print("=" * 80)
    
    try:
        # 检查数据目录是否存在
        if not os.path.exists(data_directory):
            print(f"❌ 数据目录不存在: {data_directory}")
            return
        
        # 检查必需的数据文件
        required_files = [
            "company_outline.json",
            "flattened_company_data.json", 
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
        report = generate_company_report(
            company_name=company_name,
            data_directory=data_directory,
            images_directory=images_directory,
            output_file=output_file,
            enable_chart_enhancement=True
        )
        
        if report:
            print(f"\n🎉 {company_name} 公司研究报告生成完成!")
            print("=" * 80)
        else:
            print(f"\n❌ {company_name} 公司研究报告生成失败!")
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
    except Exception as e:
        print(f"\n❌ 程序执行出错: {e}")
        traceback.print_exc()


def generate_custom_company_report(
    company_name: str,
    company_code: str = "",
    data_dir: str = "test_company_datas",
    output_dir: str = None
):
    """
    生成自定义公司报告的便捷函数
    
    Args:
        company_name: 公司名称
        company_code: 公司代码（可选）
        data_dir: 数据目录
        output_dir: 输出目录（默认使用数据目录）
    """
    
    if not output_dir:
        output_dir = data_dir
    
    # 构建文件路径
    images_directory = os.path.join(data_dir, "images")
    output_file = os.path.join(output_dir, f"{company_name}_research_report.md")
    
    # 生成报告
    return generate_company_report(
        company_name=company_name,
        data_directory=data_dir,
        images_directory=images_directory if os.path.exists(images_directory) else None,
        output_file=output_file,
        enable_chart_enhancement=True
    )


if __name__ == "__main__":
    main()
