#!/usr/bin/env python3
"""
修复 DOCX 转换问题的临时脚本
专门处理包含中文字符的文件路径转换问题
"""

import os
import sys
import shutil
import tempfile
import subprocess
from pathlib import Path


def safe_convert_to_docx(md_file: str, docx_file: str = None) -> bool:
    """
    安全地将 Markdown 文件转换为 DOCX 格式
    通过使用临时英文文件名来避免编码问题

    Args:
        md_file: Markdown 文件路径
        docx_file: DOCX 输出文件路径

    Returns:
        bool: 转换是否成功
    """
    try:
        if not os.path.exists(md_file):
            print(f"❌ Markdown 文件不存在: {md_file}")
            return False

        if docx_file is None:
            docx_file = "./Fixed_Report.docx"

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
                with open(temp_md, "r", encoding="utf-8") as f:
                    content = f.read()
                print("✅ 文件编码检查通过 (UTF-8)")
            except UnicodeDecodeError:
                try:
                    with open(temp_md, "r", encoding="gbk") as f:
                        content = f.read()
                    with open(temp_md, "w", encoding="utf-8") as f:
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
            print(f"   命令: {' '.join(pandoc_cmd)}")

            # 执行转换
            result = subprocess.run(
                pandoc_cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="ignore",
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
    import argparse

    parser = argparse.ArgumentParser(description="修复 DOCX 转换问题")
    parser.add_argument("md_file", help="Markdown 文件路径")
    parser.add_argument("--output", "-o", help="输出 DOCX 文件路径")

    args = parser.parse_args()

    success = safe_convert_to_docx(args.md_file, args.output)

    if success:
        print("🎉 转换完成!")
        return 0
    else:
        print("💥 转换失败!")
        return 1


if __name__ == "__main__":
    exit(main())
