#!/usr/bin/env python3
"""
快速运行示例 - 基于真实的测试用例
"""

import os
import sys
import subprocess
from dotenv import load_dotenv


def main():
    """主程序"""

    # 加载环境变量
    load_dotenv()

    print("🚀 研究报告生成 - 快速运行示例")
    print("=" * 60)

    examples = [
        {
            "name": "基于现有公司数据生成报告",
            "command": 'python run_company_research_report.py --company_name "4Paradigm" --data_dir "test_company_datas" --to_docx',
        },
        {
            "name": "基于现有行业数据生成报告",
            "command": 'python run_industry_research_report.py --industry_name "中国智能服务机器人产业" --data_dir "test_industry_datas" --to_docx',
        },
        {
            "name": "基于现有宏观数据生成报告",
            "command": 'python run_macro_research_report.py --macro_name "国家级人工智能+政策效果评估" --time "2023-2025" --data_dir "test_macro_datas" --to_docx',
        },
    ]

    print("📋 可用的示例:")
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['name']}")

    print("\n请选择要运行的示例 (1-3)，或按 Enter 显示所有命令:")
    choice = input().strip()

    if choice == "":
        print("\n📝 所有示例命令:")
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. {example['name']}")
            print(f"   {example['command']}")
    elif choice.isdigit() and 1 <= int(choice) <= len(examples):
        selected = examples[int(choice) - 1]
        print(f"\n🎯 运行: {selected['name']}")
        print(f"📝 命令: {selected['command']}")

        confirm = input("\n确认运行? (y/N): ").strip().lower()
        if confirm == "y":
            print("\n🚀 开始执行...")
            try:
                # 使用 shell=True 来正确处理引号
                subprocess.run(selected["command"], shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"❌ 执行失败: {e}")
            except KeyboardInterrupt:
                print("\n🛑 用户中断")
        else:
            print("❌ 取消执行")
    else:
        print("❌ 无效选择")

    print("\n💡 提示:")
    print("- 确保 .env 文件配置了正确的 API 密钥")
    print("- 程序会自动处理数据收集和报告生成")
    print("- 生成的报告将保存在相应的数据目录中")
    print("- 同时会自动导出 DOCX 格式文件到数据目录:")
    print("  * Company_Research_Report.docx")
    print("  * Industry_Research_Report.docx")
    print("  * Macro_Research_Report.docx")


if __name__ == "__main__":
    main()
