import re

def clean_markdown_links(text: str) -> str:
    """
    从Markdown或HTML混合文本中，清理各种链接、图片及Base64数据。
    
    处理顺序:
    1. 优先移除各类图片标签（HTML和Markdown）及Base64数据。
    2. 移除各类链接标签（HTML和Markdown）。
    3. 移除独立的URL。
    4. 标准化文本格式（空格等）。

    :param text: 包含链接的原始字符串。
    :return: 清理后的纯净文本字符串。
    """
    if not isinstance(text, str):
        return ""

    cleaned_text = text

    # --- 第一步：移除所有图片和Base64数据 ---
    # Markdown图片: ![alt](data:...) or ![alt](http://...)
    cleaned_text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', cleaned_text)
    # HTML图片: <img src="data:..."> or <img src="http://...">
    cleaned_text = re.sub(r'<img[^>]+>', '', cleaned_text, flags=re.IGNORECASE)
    
    # --- 第二步：移除所有链接 ---
    # 新增：处理HTML链接 <a href="...">text</a> -> text
    # re.DOTALL 确保可以匹配换行的链接内容
    cleaned_text = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', cleaned_text, flags=re.IGNORECASE | re.DOTALL)
    # Markdown链接: [text](url) -> text
    cleaned_text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', cleaned_text)
    # 数据链接: [file.pdf](data:...) -> file.pdf
    cleaned_text = re.sub(r'\[([^\]]*)\]\(\s*data:[^)]*\)', r'\1', cleaned_text)

    # --- 第三步：移除独立的URL ---
    # (?i) 表示忽略大小写, (?:https?://|www\.) 表示匹配 http://, https://, 或 www.
    cleaned_text = re.sub(r'(?i)\b(?:https?://|www\.)[^\s<>"]+', '', cleaned_text)

    # --- 第四步：格式化收尾 ---
    cleaned_text = re.sub(r'<\s*>', '', cleaned_text)   # 残余的空HTML标签 <>
    cleaned_text = re.sub(r'\s{2,}', ' ', cleaned_text) # 规范化空格
    # 移除特殊的 /* 前缀
    cleaned_text = cleaned_text.replace('/* ', '')
    
    return cleaned_text.strip()
