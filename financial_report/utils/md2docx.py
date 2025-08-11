import subprocess
from os import path, remove, rename
from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def md2docx(
    md_path: str, doc_path: str, reference_doc: str = None, pandoc_path: str = "pandoc"
):
    """
    将 Markdown 文件转换为 docx，并优化表格宽度。
    :param md_path: 输入的 markdown 文件路径
    :param doc_path: 输出的 docx 文件路径
    :param reference_doc: 参考样式 docx 路径，可选
    :param pandoc_path: pandoc 可执行文件路径，默认已加入环境变量
    """
    pandoc_cmd = [
        pandoc_path,
        md_path,
        "-o",
        doc_path,
        "--resource-path=images",
        "--extract-media=images",
        "--standalone",
    ]
    if reference_doc:
        pandoc_cmd.append(f'--reference-doc={reference_doc}')  # 去掉引号
    cwd_dir = path.dirname(md_path) or None
    subprocess.run(
        pandoc_cmd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd_dir,
    )

    doc = Document(doc_path)
    section = doc.sections[0]
    page_width = section.page_width
    usable_width = page_width - section.left_margin - section.right_margin

    for table in doc.tables:
        table.autofit = False
        tbl = table._tbl
        tblPr = tbl.tblPr
        tblW = tblPr.find(qn("w:tblW"))
        if tblW is None:
            tblW = OxmlElement("w:tblW")
            tblPr.append(tblW)
        tblW.set(qn("w:type"), "dxa")
        tblW.set(qn("w:w"), str(usable_width))
        num_cols = len(table.columns)
        cell_width = usable_width // num_cols
        for row in table.rows:
            for cell in row.cells:
                cell.width = cell_width

    tmp_file = doc_path + ".tmp"
    doc.save(tmp_file)
    remove(doc_path)
    rename(tmp_file, doc_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="将 Markdown 转为 docx 并优化表格宽度")
    parser.add_argument("md_path", help="输入的 markdown 文件路径")
    parser.add_argument("doc_path", help="输出的 docx 文件路径")
    parser.add_argument("--pandoc", default="pandoc", help="pandoc 可执行文件路径")
    parser.add_argument("--ref", default=None, help="参考样式 docx 路径")
    args = parser.parse_args()
    md2docx(args.md_path, args.doc_path, args.pandoc, args.ref)
