
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'md2docx'))
from md2docx.md2dox import md2docx

if __name__ == "__main__":
    # 示例：将 test.md 转为 test.docx
    md_file = "4Paradigm_research_report.md"
    docx_file = "test.docx"
    if not os.path.exists(md_file):
        with open(md_file, "w", encoding="utf-8") as f:
            f.write("# 测试文档\n\n这是一个测试。\n\n| 列1 | 列2 |\n|----|----|\n| a  | b  |\n")
    md2docx(md_file, docx_file)
    print(f"已生成 {docx_file}")
