import hashlib
import json
import re
from os import getenv, makedirs, path
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from pyquery import PyQuery as pq

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
except ImportError:
    ua = None

from .utils.html2md import html2md
from .utils.clean_links import clean_markdown_links
from .utils.save_pdf_http import save_pdf
from .utils.remote_mineru_api_client import RemoteMineruAPIClient

load_dotenv()


def _ensure_cache_dir() -> str:
    """
    确保缓存目录存在，如果不存在则创建，并返回其路径。
    默认路径为当前文件所在目录下的 'cache' 文件夹。

    :return: 缓存目录的绝对路径。
    :rtype: str
    """
    cache_path = path.join(path.dirname(__file__), "cache")
    if not path.exists(cache_path):
        makedirs(cache_path)
    return cache_path


def md5_hash(text: str) -> str:
    """
    对输入文本进行 MD5 哈希，返回哈希值字符串。

    :param text: 需要进行哈希的文本。
    :type text: str

    :return: 计算得到的 MD5 哈希值。
    :rtype: str
    """
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_page_with_cache(
    url: str,
    cache_prefix: str,
    force_refresh: bool = False,
    cache_dir: str = None,
    search_api_url: str = None,
    pdf_base_url: str = None,
    timeout: int = 30,
) -> dict | None:
    """
    加载指定 URL 的页面内容，支持缓存和强制刷新。若为 PDF 则调用 PDF 处理接口，否则将 HTML 转为 Markdown。返回处理后的数据字典。

    :param url: 需要加载的页面 URL。
    :type url: str
    :param cache_prefix: 缓存文件名前缀。
    :type cache_prefix: str
    :param force_refresh: 是否强制刷新缓存，默认 False。
    :type force_refresh: bool, optional
    :param cache_dir: 缓存目录路径。如果为 None，则使用默认路径 './cache'。
    :type cache_dir: str, optional

    :param search_api_url: 搜索API的URL。
    :type search_api_url: str, optional
    :param pdf_base_url: PDF上传和解析服务的URL，优先使用此参数。
    :type pdf_base_url: str, optional

    :return: 处理后的数据字典，或加载失败时返回 None。
    :rtype: dict | None
    """
    # 如果 cache_dir 未提供，则使用默认路径
    if cache_dir is None:
        cache_dir = _ensure_cache_dir()

    cache_file = path.join(cache_dir, f"{cache_prefix}.{md5_hash(url)}.json")
    
    print(f"\033[33mLoad page: {url}\033[0m")
    
    try:
        if force_refresh:
            raise FileNotFoundError
        with open(cache_file, "r", encoding="utf8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # 设置 User-Agent
        if ua:
            user_agent = ua.random
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        headers = {
            "User-Agent": user_agent
        }
        
        # 使用统一的超时时间
        cur_timeout = timeout
        
        # 首先尝试直接请求获取内容
        page_info = None
        try:
            print(f"直接请求: {url}")
            direct_resp = requests.get(url, headers=headers, timeout=cur_timeout)
            if direct_resp.status_code == 200:
                page_info = {
                    "url": url,
                    "html": direct_resp.text
                }
                print(f"直接请求成功: {url}")
        except Exception as e:
            print(f"直接请求失败: {url}, {e}")
        
        # 如果直接请求失败，则使用后端接口
        if not page_info:
            search_api_url = search_api_url or getenv("SEARCH_URL")
            try:
                page_text = requests.get(
                    f"{search_api_url}/goto?query={quote(url)}", timeout=cur_timeout
                ).text
            except requests.Timeout:
                print(f"请求超时: {url} (timeout={cur_timeout}s)")
                return None
            except Exception as e:
                print(f"请求异常: {url}, {e}")
                return None
            if not page_text:
                return None
            page_info = json.loads(page_text)
        name, ext = path.splitext(page_info["url"])
        ext = re.sub(r"[^0-9a-zA-Z.]+", "", ext, flags=re.IGNORECASE)[0:10] or ".html"

        result_data = None
        # 过滤掉表格、PPT、图片等文件
        # 只允许后缀为空、html、htm、pdf，其它全部过滤

        allowed_exts = ["", ".html", ".htm", ".pdf", ".docx"]
        # 常见需要过滤的文件类型（去掉 docx）
        filter_exts = [
            ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".asp", ".txt", ".doc", ".rtf", ".odt", ".log", ".json", ".xml", ".js", ".css", ".zip", ".rar", ".7z", ".tar", ".gz", ".exe", ".apk", ".bin", ".dll", ".iso", ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".mkv", ".wav", ".wps"
        ]
        if ext.lower() in filter_exts:
            return None
        if ext == ".pdf":
            pdf_path = path.join(cache_dir, f'bing.{md5_hash(page_info["url"])}.pdf')
            save_pdf(page_info["url"], pdf_path)
            # 优先使用参数传递的 pdf_base_url，其次环境变量
            pdf_service_url = pdf_base_url or getenv("PDF_BASE_URL")
            pdf_client = RemoteMineruAPIClient(server_url=pdf_service_url)
            health = pdf_client.health_check()
            if health and health.get("status") == "ok":
                results = pdf_client.convert_pdf_to_md(file_paths=[pdf_path])
                if results and results[0].get("md_content"):
                    cleaned_md = clean_markdown_links(results[0]["md_content"])
                    print(f"PDF内容长度: {len(cleaned_md) // 1024} KB")
                    result_data = dict(
                        url=url,
                        data_source_type="pdf",
                        md=cleaned_md,
                    )
        elif ext == ".docx":
            # 先下载 docx 文件
            docx_path = path.join(cache_dir, f'bing.{md5_hash(page_info["url"])}.docx')
            try:
                import requests
                with requests.get(page_info["url"], stream=True, timeout=cur_timeout) as r:
                    r.raise_for_status()
                    with open(docx_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                print(f"下载 docx 失败: {page_info['url']}, {e}")
                return None
            # 读取 docx 内容
            try:
                from docx import Document
                doc = Document(docx_path)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
                docx_md = '\n\n'.join(paragraphs)
                cleaned_md = clean_markdown_links(docx_md)
                result_data = dict(
                    url=url,
                    data_source_type="docx",
                    md=cleaned_md,
                )
            except Exception as e:
                print(f"读取 docx 失败: {docx_path}, {e}")
                return None
        else:
            raw_md = html2md(page_info["html"])
            cleaned_md = clean_markdown_links(raw_md)
            result_data = dict(url=url, data_source_type="html", md=cleaned_md)

        # 确保在写入前，result_data 是有值的
        if result_data:
            with open(cache_file, "w", encoding="utf8") as f:
                json.dump(result_data, f, ensure_ascii=False, indent=4)
        return result_data


def bing_search_with_cache(
    query: str,
    search_api_url: str,
    total: int = 10,
    cn: int = None,
    force_refresh: bool = False,
    cache_dir: str = None,
    searched_urls: set = None,
    pdf_base_url: str = None,
    timeout: int = 30,
) -> list:
    """
    使用 Bing 搜索接口获取查询结果，并对每个结果页面进行处理。返回包含标题和内容的结果列表。

    :param query: 搜索关键词。
    :type query: str
    :param total: 返回结果数量，默认 10。
    :type total: int, optional
    :param cn: 是否使用中文搜索，默认 None。
    :type cn: int, optional
    :param force_refresh: 是否强制刷新缓存，默认 False。
    :type force_refresh: bool, optional
    :param cache_dir: 缓存目录路径。如果为 None，则使用默认路径 './cache'。
    :type cache_dir: str, optional
    :param search_api_url: 搜索 API 地址，默认 None。
    :type search_api_url: str, optional

    :return: 搜索结果列表，每项为包含标题、url、数据源类型和 Markdown 内容的字典。
    :rtype: list[dict]
    """
    # 如果 cache_dir 未提供，则使用默认路径
    if cache_dir is None:
        cache_dir = _ensure_cache_dir()

    search_api_url = search_api_url or getenv("SEARCH_URL")
    search_url = f"{search_api_url}/bing?query={quote(query)}&total={total or 10}"
    if cn:
        search_url += "&cn=1"
    else:
        search_url += "&cn=0"
    search_results = requests.get(search_url).json()

    results = []
    if searched_urls is None:
        searched_urls = set()

    # 超时统计
    timeout_count = 0

    for i, item in enumerate(search_results):
        url = item["url"]
        if url in searched_urls:
            print(f"跳过已抓取: {url}")
            continue

        res = load_page_with_cache(
            url,
            cache_prefix="bing",
            force_refresh=force_refresh,
            cache_dir=cache_dir,
            search_api_url=search_api_url,
            pdf_base_url=pdf_base_url,
            timeout=timeout,
        )
        if not res:
            # 统计超时
            timeout_count += 1
            print(f"请求超时: {url} (timeout={timeout}s)")
            continue
        results.append(
            dict(
                title=item["title"],
                **res,
            )
        )
        searched_urls.add(url)
    return results


def get_tonghuashun_data(
    tonghuashun_total_code: str,
    search_api_url: str,
    force_refresh: bool = False,
    cache_dir: str = None,
    pdf_base_url: str = None,
    timeout: int = 30,
) -> dict:
    """
    通过内部搜索接口获取并解析同花顺(10jqka)的公司导航栏目和新闻公告列表。

    该函数首先调用一个搜索API获取包含公司信息的原始数据列表，然后遍历这个列表。
    它将返回的数据分为两类：
    1.  导航信息 (navs): 如“公司资料”、“财务分析”等，直接将其HTML内容转为Markdown。
    2.  新闻列表 (news): 如“新闻”、“公告”等，会进一步解析HTML内容，提取出每条新闻的链接，
        并调用 `load_page_with_cache` 函数抓取新闻详情页的内容。

    :param code: 股票代码 (例如: '00700')。
    :type code: str
    :param market: 市场类型, 'HK' (港股) 或 'A' (A股)。
    :type market: str
    :param search_api_url: 用于查询同花顺数据的内部搜索API地址。如果为 None，则会尝试从环境变量 'SEARCH_URL' 中获取。
    :type search_api_url: str
    :param force_refresh: 是否强制刷新缓存的新闻内容，默认为 False。此开关仅对新闻详情页的抓取有效。
    :type force_refresh: bool, optional
    :param cache_dir: 用于存储新闻页面缓存的目录路径。如果为 None, 则使用默认路径 './cache'。
    :type cache_dir: str, optional

    :return: 一个字典，包含 'navs' 和 'news' 两个键。
             - 'navs' (list): 包含非新闻/公告类的导航栏目信息。每个元素是一个字典，
               其中'md'键包含了从HTML转换来的Markdown内容。
             - 'news' (list): 包含解析出的新闻条目。每个元素是一个字典，
               包含了新闻的标题(title)、原始链接(url)和抓取到的页面内容。
    :rtype: dict
    """
    # 如果未提供缓存目录，则使用并确保默认路径存在。
    if cache_dir is None:
        cache_dir = _ensure_cache_dir()

    # 优先使用函数传入的API地址，否则从环境变量中获取。
    search_api_url = search_api_url or getenv("SEARCH_URL")

    # 根据市场类型，对股票代码进行规范化处理，以匹配搜索API的要求。
    normalized_code = tonghuashun_total_code

    url = f"{search_api_url}/10jqka?query={normalized_code}"
    print(f"Fetching data for {normalized_code} from {url}")
    # 调用搜索API，获取同花顺相关的导航和数据区块。
    import time
    from http.client import IncompleteRead
    from requests.exceptions import ChunkedEncodingError, ConnectionError
    max_retries = 3
    company_data = None
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=timeout)
            company_data = resp.json()
            break
        except requests.Timeout:
            print(f"同花顺接口超时: {url} (timeout={timeout}s)，重试 {attempt+1}/{max_retries}")
            time.sleep(2)
        except (IncompleteRead, ChunkedEncodingError, ConnectionError) as e:
            print(f"同花顺接口连接异常: {url}, {e}，重试 {attempt+1}/{max_retries}")
            time.sleep(2)
        except Exception as e:
            print(f"同花顺接口其它异常: {url}, {e}")
            break
    else:
        print(f"同花顺接口多次重试后仍失败: {url}")
        return dict(navs=[], news=[])

    result = dict(navs=[], news=[])

    # 遍历从API获取的每个数据区块（如：公司资料、新闻、公告等）。
    for nav_item in company_data:
        html_content = nav_item.pop("html", "")
        if not html_content:
            continue

        # 判断数据区块的类型：如果标题不含“新闻”或“公告”，则视为普通导航栏目。
        if "新闻" not in nav_item["title"] and "公告" not in nav_item["title"]:
            # 对于普通导航，直接将HTML内容转换为Markdown并清洗。
            raw_md = html2md(html_content)
            cleaned_md = clean_markdown_links(raw_md)
            nav_item.update(
                dict(
                    md=cleaned_md,
                    data_source_type="html",
                )
            )
            result["navs"].append(nav_item)
        else:
            # 如果是新闻或公告区块，则需要进一步解析HTML以获取新闻列表。
            doc = pq(html_content)
            # 使用pyquery选择器，精确查找指向新闻或报告详情页的链接。
            for link_element in doc.find("dl dt a, td a[tag=reports]"):
                link = pq(link_element)
                url, title = link.attr("href"), link.attr("title")

                if not url or not title:
                    continue

                print(f"\033[34mFetching news: {title} ({url})\033[0m")

                # 抓取单条新闻的详情页，此过程会利用缓存机制避免重复下载。
                res = load_page_with_cache(
                    url,
                    cache_prefix="10jqka",
                    force_refresh=force_refresh,
                    cache_dir=cache_dir,
                    search_api_url=search_api_url,
                    pdf_base_url=pdf_base_url,
                    timeout=timeout,
                )

                if res:
                    # 对新闻内容进行清洗（md字段）
                    if "md" in res:
                        res["md"] = clean_markdown_links(res["md"])
                    # 将抓取到的内容与标题和URL整合后，存入结果列表。
                    res.update(
                        dict(
                            title=title,
                            url=url,
                        )
                    )
                    result["news"].append(res)

    return result
