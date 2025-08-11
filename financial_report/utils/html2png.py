import os
import asyncio
import urllib.parse
import urllib.request
from playwright.async_api import async_playwright
import time

def html2png(html_input: str, image_path: str="image.png", is_file_path: bool=None) -> str:
    """
    将 HTML 内容或HTML文件渲染为图片，返回图片的绝对路径。
    :param html_input: HTML字符串内容 或 HTML文件路径
    :param image_path: 生成图片的路径（支持绝对或相对路径）
    :param is_file_path: 是否为文件路径。None时自动判断，True表示是文件路径，False表示是HTML内容
    :return: 图片的绝对路径
    """
    try:
        # 检查是否已经在事件循环中
        loop = asyncio.get_running_loop()
        # 如果已经在事件循环中，抛出异常提示使用异步版本
        raise RuntimeError("html2png不能在异步环境中直接调用，请使用 html2png_async")
    except RuntimeError as e:
        if "no running event loop" in str(e):
            # 没有运行的事件循环，可以安全地使用 asyncio.run
            return asyncio.run(_html_to_png_async(html_input, image_path, is_file_path))
        else:
            # 已经在事件循环中
            raise e


async def html2png_async(html_input: str, image_path: str="image.png", is_file_path: bool=None) -> str:
    """
    异步版本：将 HTML 内容或HTML文件渲染为图片，返回图片的绝对路径。
    适用于在已有异步环境中调用。
    :param html_input: HTML字符串内容 或 HTML文件路径
    :param image_path: 生成图片的路径（支持绝对或相对路径）
    :param is_file_path: 是否为文件路径。None时自动判断，True表示是文件路径，False表示是HTML内容
    :return: 图片的绝对路径
    """
    return await _html_to_png_async(html_input, image_path, is_file_path)

def _detect_html_input_type(html_input: str) -> bool:
    """
    自动检测输入是HTML内容还是文件路径
    :param html_input: 输入字符串
    :return: True表示是文件路径，False表示是HTML内容
    """
    # 简单判断：如果包含HTML标签且不是文件路径，则认为是HTML内容
    if os.path.exists(html_input) and html_input.lower().endswith(('.html', '.htm')):
        return True
    elif '<html' in html_input.lower() or '<!doctype' in html_input.lower():
        return False
    elif len(html_input) < 500 and (html_input.endswith('.html') or html_input.endswith('.htm')):
        # 短字符串且以.html结尾，可能是文件路径
        return True
    else:
        # 默认认为是HTML内容
        return False

async def _html_to_png_async(html_input: str, image_path: str, is_file_path: bool=None) -> str:
    """
    异步版本的HTML转PNG功能
    """
    # 获取图片绝对路径
    abs_img_path = os.path.abspath(image_path)
    
    # 自动判断输入类型
    if is_file_path is None:
        is_file_path = _detect_html_input_type(html_input)
    
    # 处理HTML内容
    if is_file_path:
        # 输入是文件路径
        if not os.path.exists(html_input):
            raise FileNotFoundError(f"HTML文件不存在: {html_input}")
        
        html_file_path = os.path.abspath(html_input)
        print(f"使用HTML文件: {html_file_path}")
        
        # 读取HTML内容用于验证
        with open(html_file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        use_temp_file = False
        tmp_html = html_file_path
    else:
        # 输入是HTML内容
        html_content = html_input
        # 创建临时HTML文件
        tmp_html = abs_img_path + ".html"
        use_temp_file = True
        
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"创建临时HTML文件: {tmp_html}")
    
    try:
        print(f"开始渲染HTML文件: {tmp_html}")
        
        async with async_playwright() as p:
            # 启动浏览器
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            try:
                # 创建页面
                page = await browser.new_page(
                    viewport={'width': 1200, 'height': 800}
                )
                
                # 设置超时时间
                page.set_default_timeout(30000)  # 30秒
                
                # 加载HTML文件 - 修复Windows路径问题
                # 将Windows路径转换为正确的file URL格式
                import urllib.parse
                file_url = urllib.parse.urljoin('file:', urllib.request.pathname2url(tmp_html))
                print(f"访问URL: {file_url}")
                await page.goto(file_url)
                
                # 等待图表渲染完成
                try:
                    # 等待ECharts容器加载
                    await page.wait_for_selector('#container', timeout=10000)
                    # 额外等待确保图表完全渲染
                    await page.wait_for_timeout(3000)
                except:
                    print("警告: 图表可能未完全加载，继续截图...")
                
                # 截图
                await page.screenshot(
                    path=abs_img_path,
                    full_page=True,
                    type='png'
                )
                
                print(f"图片已保存到: {abs_img_path}")
                
            finally:
                await browser.close()
                
    except Exception as e:
        print(f"渲染过程中出现错误: {e}")
        raise
    finally:
        # 只删除临时创建的HTML文件
        if use_temp_file and os.path.exists(tmp_html):
            os.remove(tmp_html)
            print(f"已删除临时HTML文件: {tmp_html}")
            
    return abs_img_path
