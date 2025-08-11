#!/usr/bin/env python3
"""
行业研究报告生成器 - 便捷调用脚本
自动集成数据收集和报告生成，支持自动转换为 DOCX 格式
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path


def ensure_reports_directory():
    """确保 reports 目录存在"""
    reports_dir = "reports"
    if not os.path.exists(reports_dir):
        os.makedirs(reports_dir)
        print(f"✅ 创建输出目录: {reports_dir}")
    return reports_dir


def safe_convert_to_docx(md_file: str, docx_file: str = None) -> bool:
    """
    安全地将 Markdown 文件转换为 DOCX 格式
    通过使用临时英文文件名来避免编码问题
    
    Args:
        md_file: Markdown 文件路径
        docx_file: DOCX 输出文件路径，如果为空则自动生成
    
    Returns:
        bool: 转换是否成功
    """
    import tempfile
    import shutil
    
    try:
        if not os.path.exists(md_file):
            print(f"❌ Markdown 文件不存在: {md_file}")
            return False
        
        if docx_file is None:
            # 确保 reports 目录存在并设置默认输出路径
            reports_dir = ensure_reports_directory()
            docx_file = os.path.join(reports_dir, "Industry_Research_Report.docx")
        
        print(f"🔧 开始安全转换 Markdown 到 DOCX...")
        print(f"   源文件: {md_file}")
        print(f"   目标文件: {docx_file}")
        
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用英文临时文件名
            temp_md = os.path.join(temp_dir, "temp_report.md")
            temp_docx = os.path.join(temp_dir, "temp_report.docx")
            
            # 复制 Markdown 文件到临时位置
            shutil.copy2(md_file, temp_md)
            print("✅ 文件已复制到临时目录")
            
            # 检查并修复文件编码
            try:
                with open(temp_md, 'r', encoding='utf-8') as f:
                    content = f.read()
                print("✅ 文件编码检查通过 (UTF-8)")
            except UnicodeDecodeError:
                try:
                    with open(temp_md, 'r', encoding='gbk') as f:
                        content = f.read()
                    with open(temp_md, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print("✅ 文件已转换为 UTF-8 编码")
                except Exception as e:
                    print(f"⚠️ 编码转换失败: {e}")
            
            # 复制图片目录（如果存在）
            original_dir = os.path.dirname(md_file)
            images_dir = os.path.join(original_dir, "images")
            if os.path.exists(images_dir):
                temp_images = os.path.join(temp_dir, "images")
                shutil.copytree(images_dir, temp_images)
                print("✅ 图片目录已复制")
            
            # 获取参考文档路径
            refs_doc = os.path.join(os.path.dirname(__file__), "md2docx", "refs.docx")
            if not os.path.exists(refs_doc):
                refs_doc = None
            
            # 构建 pandoc 命令
            pandoc_cmd = [
                "pandoc",
                temp_md,
                "-o",
                temp_docx,
                "--resource-path=images",
                "--extract-media=images",
                "--standalone",
            ]
            
            if refs_doc:
                pandoc_cmd.append(f"--reference-doc={refs_doc}")
            
            print("🔄 执行 Pandoc 转换...")
            
            # 执行转换
            result = subprocess.run(
                pandoc_cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode != 0:
                print(f"❌ Pandoc 执行失败:")
                print(f"   返回码: {result.returncode}")
                print(f"   错误输出: {result.stderr}")
                return False
            
            # 检查临时 DOCX 文件是否生成
            if not os.path.exists(temp_docx):
                print("❌ 临时 DOCX 文件未生成")
                return False
            
            # 复制结果文件到目标位置
            shutil.copy2(temp_docx, docx_file)
            print(f"✅ DOCX 文件生成成功: {docx_file}")
            
            return True
            
    except Exception as e:
        print(f"❌ 转换过程出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主程序入口"""
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="生成行业研究报告",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python run_industry_research_report.py --industry_name "智能风控&大数据征信服务"
  python run_industry_research_report.py --industry_name "中国智能服务机器人产业"
  python run_industry_research_report.py --industry_name "中国智能服务机器人产业" --to_docx
  python run_industry_research_report.py --industry_name "中国智能服务机器人产业" --to_docx --docx_output "reports/robot_industry.docx"
  uv run run_industry_research_report.py --industry_name "中国智能服务机器人产业"
        """)
    
    parser.add_argument('--industry_name', required=True, help='行业名称')
    parser.add_argument('--data_dir', help='自定义数据目录路径')
    parser.add_argument('--output', help='输出文件路径')
    parser.add_argument('--to_docx', action='store_true', help='自动转换为 DOCX 格式')
    parser.add_argument('--docx_output', help='自定义 DOCX 输出文件路径')
    
    args = parser.parse_args()
    
    # 构建调用参数
    cmd = [
        sys.executable, 'generate_report.py', 'industry',
        '--industry_name', args.industry_name
    ]
    
    if args.data_dir:
        cmd.extend(['--data_dir', args.data_dir])
    
    if args.output:
        cmd.extend(['--output', args.output])
    

    
    # 调用主程序
    try:
        result = subprocess.run(cmd, check=True)
        
        # 如果生成成功且需要转换为 DOCX
        if result.returncode == 0 and args.to_docx:
            # 确定 Markdown 文件路径
            if args.output:
                md_file = args.output
            else:
                # 默认输出路径逻辑
                if args.data_dir:
                    data_directory = args.data_dir
                else:
                    # 首先检查通用的 test_industry_datas 目录
                    generic_data_dir = "test_industry_datas"
                    if os.path.exists(generic_data_dir):
                        data_directory = generic_data_dir
                    else:
                        # 如果通用目录不存在，使用特定命名规则
                        safe_name = args.industry_name.replace(' ', '_').replace('/', '_').replace('&', 'and')
                        data_directory = f"test_industry_datas_{safe_name}"
                md_file = os.path.join(data_directory, f"{args.industry_name}_research_report.md")
            
            # 转换为 DOCX - 如果没有指定输出路径，则输出到 reports 目录
            if args.docx_output:
                docx_output = args.docx_output
            else:
                docx_output = None  # 让 safe_convert_to_docx 函数处理默认路径
            
            docx_success = safe_convert_to_docx(md_file, docx_output)
            if not docx_success:
                print("⚠️ 报告生成成功，但 DOCX 转换失败")
        
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode
    except KeyboardInterrupt:
        print("\n🛑 用户中断操作")
        return 1


if __name__ == "__main__":
    exit(main())
