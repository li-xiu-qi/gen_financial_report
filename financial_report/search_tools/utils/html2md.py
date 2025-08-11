import requests
import trafilatura
from markdownify import markdownify as md
import json
from dateutil.parser import parse
from datetime import timezone
from typing import Optional
import asyncio
from bs4 import BeautifulSoup
from markdownify import MarkdownConverter
import re
from typing import List, Dict, Any
from markdownify import MarkdownConverter, abstract_inline_conversion, chomp
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import asyncio
import os
from typing import Optional


class ImageDescMarkdownConverter(MarkdownConverter):
    """
    自定义Markdown转换器，继承自MarkdownConverter。
    提供了更灵活的HTML到Markdown转换选项，例如：
    - 转换链接为绝对路径。
    - 移除所有链接和图片。
    - 特殊处理包含colspan或rowspan的表格。
    """

    def __init__(self, **kwargs):
        """
        初始化自定义的Markdown转换器。

        :param current_url: 当前页面的URL，用于将相对链接和图片路径转换为绝对路径。
                            如果提供了此参数，图片和链接的URL将自动转换为绝对路径。
        :param kwargs: 其他传递给父类MarkdownConverter的参数。
                       例如：strip (需要移除的标签列表), convert (仅转换的标签列表), heading_style等。
        """
        super().__init__(**kwargs)
        self.current_url = kwargs.get("current_url", None)
        self.img_desc_map = kwargs.get("img_desc_map", {})

    def convert_img(self, el, text, parent_tags):
        """
        转换<img>标签为Markdown格式的图片。
        如果提供了current_url，则将图片src转换为绝对路径。
        仅做基础的Markdown图片语法转换，不再进行图片分析。

        :param el: BeautifulSoup的Tag对象，代表<img>元素。
        :param text: 图片的替代文本（通常为空，因为alt属性会被单独提取）。
        :param parent_tags: 父标签集合，用于判断上下文。
        :return: Markdown格式的图片字符串，或者在特定情况下返回alt文本或空字符串。
        """
        alt_text = el.attrs.get("alt", "") or ""
        src_url = el.attrs.get("src", "") or ""
        title_text = el.attrs.get("title", "") or ""

        if (
                "_inline" in parent_tags
                and el.parent.name not in self.options["keep_inline_images_in"]
        ):
            return alt_text

        if not src_url:
            return alt_text

        # 转换为绝对路径
        if self.current_url:
            src_url = urljoin(self.current_url, src_url)

        # 优先使用AI分析结果
        if self.img_desc_map and src_url in self.img_desc_map:
            desc_info = self.img_desc_map[src_url]
            ai_title = desc_info.get("title") or alt_text or "图片"
            ai_desc = desc_info.get("description", "")
            md = f"![{ai_title}]({src_url})"
            if ai_desc:
                md += "\n" + "\n".join(f"> {line}" for line in ai_desc.strip().splitlines())
            return md

        if title_text:
            escaped_title = title_text.replace('"', r"\"")
            title_part = f' "{escaped_title}"'
        else:
            title_part = ""
        return f"![{alt_text}]({src_url}{title_part})"

    def _process_table_element(self, element):
        """
        辅助方法：处理包含colspan或rowspan属性的表格元素（td, th）。
        此方法会解析传入的表格元素字符串，并移除除了'colspan'和'rowspan'之外的所有属性。
        目的是在保留表格结构的同时，简化HTML，以便后续可能由其他工具或手动进行更复杂的Markdown转换。

        :param element: BeautifulSoup的Tag对象，代表一个HTML表格元素（如<table>, <tr>, <td>, <th>）。
        :return: 处理后的HTML元素字符串，仅保留colspan和rowspan属性。
        """
        # 使用BeautifulSoup解析传入的元素字符串，确保操作的是一个独立的DOM结构
        soup = BeautifulSoup(str(element), "html.parser")
        # 遍历soup中的所有标签
        for tag in soup.find_all(True):
            # 定义需要保留的属性列表
            attrs_to_keep = ["colspan", "rowspan"]
            # 更新标签的属性字典，只保留在attrs_to_keep列表中的属性
            tag.attrs = {
                key: value for key, value in tag.attrs.items() if key in attrs_to_keep
            }
        # 返回处理后soup的字符串表示形式
        return str(soup)

    def convert_table(self, el, text, parent_tags):
        """
        转换<table>标签为Markdown格式。
        如果表格中的<td>或<th>标签包含colspan或rowspan属性，
        则调用_process_table_element方法返回处理过的HTML字符串（保留结构但简化属性），
        否则，调用父类的convert_table方法进行标准转换。

        :param el: BeautifulSoup的Tag对象，代表<table>元素。
        :param text: 表格的内部文本内容（通常由子元素的转换结果拼接而成）。
        :param parent_tags: 父标签集合，用于判断上下文。
        :return: Markdown格式的表格字符串，或者在包含合并单元格时返回处理后的HTML字符串。
        """
        # 使用BeautifulSoup解析传入的<table>元素字符串
        soup = BeautifulSoup(str(el), "html.parser")
        # 检查表格中是否存在任何带有colspan或rowspan属性的<td>或<th>标签
        has_colspan_or_rowspan = any(
            tag.has_attr("colspan") or tag.has_attr("rowspan")
            for tag in soup.find_all(["td", "th"])
        )
        if has_colspan_or_rowspan:
            # 如果存在合并单元格，则调用_process_table_element处理整个表格元素
            # 返回的是简化属性后的HTML字符串，而不是Markdown
            return self._process_table_element(el)
        else:
            # 如果没有合并单元格，则调用父类的convert_table方法进行标准Markdown转换
            return super().convert_table(el, text, parent_tags)

    def convert_a(self, el, text, parent_tags):
        """
        转换<a>标签（链接）为Markdown格式。
        如果提供了current_url，则将链接href转换为绝对路径。
        处理自动链接（autolinks）和默认标题（default_title）的选项。

        :param el: BeautifulSoup的Tag对象，代表<a>元素。
        :param text: 链接的显示文本。
        :param convert_as_inline: 布尔值，指示是否应将此链接作为内联元素处理。
        :return: Markdown格式的链接字符串，或者在特定情况下返回空字符串。
        """

        # 使用chomp函数处理链接文本，分离前导/尾随空格
        prefix, suffix, text = chomp(text)
        if not text:
            # 如果链接文本为空（例如空的<a></a>标签），则返回空字符串
            return ""

        # 获取链接的href和title属性
        href_url = el.get("href")
        title_text = el.get("title")

        if self.current_url and href_url:
            # 如果需要将链接href转换为绝对路径
            # 使用urljoin将href_url（可能是相对路径）与current_url合并为绝对路径
            href_url = urljoin(self.current_url, href_url)

        # 处理Markdownify的autolinks选项：如果链接文本和href相同，且无标题，则使用<href>格式
        if (
                self.options.get("autolinks", False)  # 检查autolinks选项是否存在且为True
                and text.replace(r"\_", "_")
                == href_url  # 文本（处理转义的下划线后）与href相同
                and not title_text  # 没有title属性
                and not self.options.get("default_title", False)
        ):  # default_title选项未开启
            return f"<{href_url}>"  # 返回自动链接格式

        # 处理Markdownify的default_title选项：如果没有title属性，但开启了default_title，则使用href作为title
        if self.options.get("default_title", False) and not title_text and href_url:
            title_text = href_url

        # 处理链接标题，如果存在，则进行转义并格式化
        if title_text:
            escaped_title = title_text.replace('"', r"\"")  # 转义双引号
            title_part = f' "{escaped_title}"'  # 格式化为 "title"
        else:
            title_part = ""  # 如果没有标题，则为空

        # 返回标准Markdown格式的链接：[text](href_url "title_text")
        # 如果href_url为空或None，则只返回处理过的文本（prefix + text + suffix）
        return (
            f"{prefix}[{text}]({href_url}{title_part}){suffix}"
            if href_url
            else f"{prefix}{text}{suffix}"
        )

    # 加粗标签<b>的转换，使用markdownify库提供的abstract_inline_conversion辅助函数
    # self.options['strong_em_symbol'] 通常是 '*' 或 '_'
    # lambda self: 2 * self.options['strong_em_symbol'] 表示使用两个符号包裹文本，例如 **text**
    convert_b = abstract_inline_conversion(
        lambda self: 2 * self.options.get("strong_em_symbol", "*")
    )

    # 强调标签<em>或<i>的转换，同样使用abstract_inline_conversion
    # lambda self: self.options['strong_em_symbol'] 表示使用一个符号包裹文本，例如 *text*
    convert_em = abstract_inline_conversion(
        lambda self: self.options.get("strong_em_symbol", "*")
    )
    convert_i = convert_em  # <i>标签通常与<em>行为一致

    # 删除线标签<del>或<s>的转换
    convert_del = abstract_inline_conversion(lambda self: "~~")
    convert_s = convert_del  # <s>标签通常与<del>行为一致


# 匹配Markdown图片语法的正则表达式
IMG_TAG_RE = re.compile(r'!\[.*?\]\((https?://[^\)]+)\)', re.IGNORECASE)


def convert_url_to_markdown(
        url: str,
        add_frontmatter: bool = True,
) -> Optional[str]:
    """
    获取网页主要内容，转换为带YAML Frontmatter的Markdown字符串。
    :param url: 文章URL
    :param add_frontmatter: 是否添加YAML frontmatter
    :return: Markdown字符串或None
    """
    print(f"🚀 正在处理 URL: {url}\n")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()

        # --- 步骤 1: 使用trafilatura提取内容 ---
        html_content = trafilatura.extract(
            resp.content,
            include_comments=False,
            include_tables=True,
            include_images=True,
            include_links=True,
        )
        json_output = trafilatura.extract(
            resp.content,
            output_format="json",
            include_comments=False,
            include_tables=True,
        )

        if not html_content and not json_output:
            print("❌ 提取内容失败，页面可能不兼容或无正文。")
            return None

        metadata = {
            "title": "Untitled",
            "author": None,
            "date": None,
            "source": url,
        }
        data = {}
        if json_output:
            try:
                data = json.loads(json_output)
                metadata.update(
                    {
                        "title": data.get("title", "Untitled"),
                        "author": data.get("author"),
                        "date": data.get("date"),
                        "source": data.get("source") or url,
                    }
                )
            except json.JSONDecodeError:
                print("❌ 解析提取的JSON数据失败，使用默认元数据。")

        # 使用HTML内容，如果没有则尝试从JSON获取文本
        main_content = html_content
        if not main_content and json_output:
            try:
                data = json.loads(json_output)
                main_content = (
                        data.get("text", "")
                        or data.get("raw_text", "")
                        or data.get("content", "")
                )
            except json.JSONDecodeError:
                pass

        if not main_content:
            print("❌ 未能提取到任何文本内容")
            return None

        print(f"📏 提取到的内容长度: {len(main_content)} 字符")
        if "<" in main_content and ">" in main_content:
            clean_html = main_content
        else:
            clean_html = f"<p>{main_content.replace(chr(10), '</p><p>')}</p>"

        # 先转换为基础Markdown
        converter = ImageDescMarkdownConverter(
            heading_style="ATX", wrap=True, wrap_width=80
        )
        markdown_body = converter.convert(clean_html)

        try:
            if metadata["date"]:
                parsed_date = parse(metadata["date"])
                # 转换为带时区的标准格式
                standard_date = parsed_date.astimezone(timezone.utc).strftime(
                    "%Y-%m-%d"
                )
                metadata["date"] = standard_date
            else:
                metadata["date"] = ""
        except (ValueError, TypeError):
            metadata["date"] = ""  # 解析失败则留空

        # --- 步骤 6: 组合 YAML Frontmatter 和 Markdown 正文 ---
        if add_frontmatter:
            yaml_frontmatter = "---\n"
            yaml_frontmatter += f"title: \"{metadata['title']}\"\n"
            if metadata["author"]:
                yaml_frontmatter += f"author: \"{metadata['author']}\"\n"
            if metadata["date"]:
                yaml_frontmatter += f"date: {metadata['date']}\n"
            yaml_frontmatter += f"source: <{metadata['source']}>\n"
            yaml_frontmatter += "---\n\n"
        else:
            yaml_frontmatter = ""

        final_content = yaml_frontmatter + markdown_body

        return final_content

    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        return None


def html2md(html: str, skip_images: bool = False) -> str:
    """
    将HTML内容转换为Markdown，支持跳过图片。
    Args:
        html: HTML字符串
        skip_images: 是否跳过图片标签
    Returns:
        Markdown字符串
    """
    converter = ImageDescMarkdownConverter()
    if skip_images:
        # 移除所有图片标签
        soup = BeautifulSoup(html, "html.parser")
        for img in soup.find_all("img"):
            img.decompose()
        html = str(soup)
    return converter.convert(html)


# --- 主程序执行区域 ---
if __name__ == "__main__":
    # 您可以替换成任何想要测试的文章链接
    # 示例1: 技术博客
    test_url = "https://www.ruanyifeng.com/blog/2024/05/weekly-issue-299.html"

    # 示例2: 新闻文章
    # test_url = "https://www.theverge.com/2024/5/13/24155243/openai-gpt-4o-announcements-google-io"

    # 从.env文件读取ZHIPU的API KEY和BASE_URL
    from dotenv import load_dotenv

    load_dotenv()
    import os

    zhipu_api_key = os.getenv("ZHIPU_API_KEY")
    zhipu_base_url = os.getenv("ZHIPU_BASE_URL")
    zhipu_model = os.getenv("ZHIPU_MODEL")

    # 调用函数并获取返回的Markdown字符串，传入key和base_url
    markdown_output = convert_url_to_markdown(
        test_url,
    )

    # 如果成功获取，则保存到文件并打印到控制台
    if markdown_output:
        # 保存到 test.md 文件
        output_file = "test.md"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(markdown_output)
            print(f"✅ 内容已成功保存到 {output_file}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")

        print("---------- MARKDOWN 输出开始 ----------\n")
        print(markdown_output)
        print("\n----------- MARKDOWN 输出结束 -----------")
