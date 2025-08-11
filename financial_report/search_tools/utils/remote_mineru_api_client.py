#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
【PDF转换API客户端】

本文件封装了一个名为 RemoteMineruAPIClient 的客户端类，旨在简化与 PDF转Markdown FastAPI 服务的交互。

核心功能:
- 连接到您的服务。
- 上传本地PDF文件进行转换。
- 获取转换后的Markdown内容。
- 管理服务器缓存。

快速使用示例:
    from remote_mineru_api_client import RemoteMineruAPIClient

    # 1. 初始化客户端，指向您的服务地址
    client = RemoteMineruAPIClient(server_url="http://127.0.0.1:10003")

    # 2. 调用转换方法
    results = client.convert_pdf_to_md(
        file_paths=["/home/user/docs/report.pdf"],
        md_output_path="/tmp/markdown_output"
    )

    # 3. 从返回结果中提取您需要的Markdown内容
    if results:
        markdown_content = results[0]['md_content']
        print(markdown_content)
"""

import requests
import os
import json
from typing import List, Dict, Any, Optional


class RemoteMineruAPIClient:
    """
    一个与 Remote Mineru FastAPI 服务交互的客户端。

    此类将所有HTTP请求的复杂性都封装起来，您只需要调用简单的方法，
    并直接处理返回的Python数据即可。

    使用方法:
        # 1. 创建实例
        client = RemoteMineruAPIClient(server_url="http://127.0.0.1:10003")
        # 2. 调用方法
        client.health_check()
        client.convert_pdf_to_md(...)
    """

    def __init__(self, server_url: str = "http://127.0.0.1:10003"):
        """
        初始化 API 客户端。

        参数:
            server_url (str): 【必须】您的 FastAPI 服务的根 URL。
                              例如: "http://127.0.0.1:10003"
        """
        # 确保 URL 格式正确，末尾不带斜杠
        if server_url.endswith('/'):
            self.base_url = server_url[:-1]
        else:
            self.base_url = server_url
        
        # 使用 Session 对象可以复用TCP连接，提高与同一主机通信的性能
        self.session = requests.Session()
        print(f"客户端已初始化，目标服务器: {self.base_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Any]:
        """
        (内部方法) 统一发送请求并处理通用错误。
        """
        url = f"{self.base_url}/{endpoint}"
        try:
            # 为所有请求设置一个默认的超时时间 (300秒 = 5分钟)
            kwargs.setdefault('timeout', 300)
            response = self.session.request(method, url, **kwargs)
            # 如果服务器返回错误状态码 (如 404, 500), 则主动抛出异常
            response.raise_for_status()

            # 某些请求 (如清理缓存) 可能成功但没有返回体，正常处理
            if not response.content:
                return {"status": "success", "message": "操作成功，无内容返回"}
            
            # 将服务器返回的JSON字符串解析为Python字典或列表
            return response.json()

        except requests.exceptions.ConnectionError:
            print(f"【错误】: 无法连接到服务 {self.base_url}。请确认服务正在运行且地址/端口正确。")
            raise
        except requests.exceptions.HTTPError as e:
            print(f"【错误】: 服务器返回HTTP错误 {e.response.status_code}。响应内容: {e.response.text}")
            raise
        except json.JSONDecodeError:
            print(f"【错误】: 无法解析服务器返回的JSON。可能是服务器内部错误。响应内容: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
            print(f"【错误】: 发生请求相关的未知错误: {e}")
            raise

    def health_check(self) -> Optional[Dict[str, str]]:
        """
        检查服务是否健康在线。

        返回:
            一个字典，包含服务的状态信息。如果请求失败则返回 None。

        返回结果示例:
            {'status': 'ok', 'message': 'PDF to Markdown service is running'}
        
        使用示例:
            if client.health_check():
                print("服务正常！")
        """
        print("\n--- 1. 正在进行健康检查 ---")
        try:
            result = self._make_request('get', 'health')
            print(f"健康检查成功: {result}")
            return result
        except Exception:
            print("健康检查失败。")
            return None


    def convert_pdf_to_md(
        self,
        file_paths: List[str],
        md_output_path: Optional[str] = None,
        return_content: bool = True,
        backend: str = 'pipeline',
        method: str = 'auto',
        lang: str = 'ch',
        use_cache: bool = True
    ) -> Optional[List[Dict[str, Any]]]:
        """
        【核心功能】上传一个或多个PDF文件，将其转换为Markdown，并获取内容。

        此方法会处理与服务器的所有交互细节，您只需要提供文件路径和输出位置即可。

        参数:
            file_paths (List[str]): 【必须】您本地电脑上PDF文件的路径列表。
                例如: ["/path/to/doc1.pdf", "/path/to/doc2.pdf"]
            md_output_path (Optional[str]): 【可选】告知【服务器】将转换后的.md文件保存在哪个绝对路径下。
                未传递时，服务器自动使用默认目录。
            return_content (bool): 【重点】是否在返回结果中包含完整的Markdown文本。
                默认为 True，强烈建议保持为 True，这样才能直接获取内容。
            backend (str): 使用的解析后端。
            method (str): 使用的解析方法。
            lang (str): 文档语言。
            use_cache (bool): 是否使用服务器缓存。

        返回:
            一个列表(List)，其中每个元素都是一个字典(Dict)，对应一个文件的处理结果。
            如果请求失败或在客户端发生错误，则返回 None。

        返回结果示例 (当上传一个文件时):
            [
                {
                    "file_path": "/tmp/tmp_xyz/doc1.pdf",
                    "md_path": "/tmp/my_markdowns/auto/doc1/doc1.md",
                    "md_content": "# 这是转换后的Markdown第一行\\n\\n这是第二行..."
                }
            ]

        使用示例 (如何拿到您要的Markdown内容):
            results = client.convert_pdf_to_md(...)
            if results:
                # 获取第一个文件的结果字典
                first_file_result = results[0]
                # 【直接获取Markdown内容】
                markdown_text = first_file_result['md_content']
                print(markdown_text)
        """
        print(f"\n--- 2. 准备上传 {len(file_paths)} 个PDF文件进行转换 ---")
        
        # 准备API的查询参数 (query parameters)
        params = {
            'return_content': return_content,
            'backend': backend,
            'method': method,
            'lang': lang,
            'use_cache': use_cache,
        }
        if md_output_path is not None:
            params['md_output_path'] = md_output_path
        
        # 准备要上传的文件列表 (multipart/form-data)
        files_to_upload = []
        opened_files = [] # 记录所有打开的文件句柄，以便后续关闭

        try:
            # 遍历本地文件路径，检查文件是否存在并打开
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    # 如果任何一个文件不存在，这是一个致命错误，直接抛出异常
                    raise FileNotFoundError(f"客户端错误: 本地文件未找到 -> {file_path}")
                
                # 以二进制读取模式('rb')打开文件
                file_obj = open(file_path, 'rb')
                opened_files.append(file_obj)
                
                # 按照 requests 库的要求准备文件元组
                # 'files' 这个字段名必须和服务端 @File(..., alias="files") 的别名一致
                files_to_upload.append(
                    ('files', (os.path.basename(file_path), file_obj, 'application/pdf'))
                )
            
            # 发送请求
            print("文件准备就绪，正在发送到服务器...")
            results = self._make_request(
                'post',
                'convert_pdf_to_md',
                params=params,
                files=files_to_upload
            )
            print("服务器处理完毕，已收到结果。")
            return results

        except Exception as e:
            # 捕获包括文件未找到在内的所有错误
            print(f"【错误】: 在PDF转换请求准备或执行过程中发生错误: {e}")
            return None
        finally:
            # 【重要】无论成功还是失败，都确保关闭所有已打开的文件，防止资源泄露
            for f in opened_files:
                f.close()

    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """
        获取服务器上缓存的统计信息。

        返回:
            一个字典，包含缓存的详细信息。如果请求失败则返回 None。

        返回结果示例:
            {
                "cache_size": 5, 
                "cache_directory": "/home/user/.cache/remote_pdf_parse_serve", 
                "disk_usage": 131072
            }
        """
        print("\n--- 3. 正在获取缓存统计信息 ---")
        try:
            stats = self._make_request('get', 'cache_stats')
            print(f"当前缓存统计: {stats}")
            return stats
        except Exception:
            print("获取缓存统计失败。")
            return None

    def clear_cache(self) -> Optional[Dict[str, str]]:
        """
        清理服务器上的所有解析缓存。

        返回:
            一个字典，指示操作结果。如果请求失败则返回 None。
        
        返回结果示例:
            {'message': '缓存已成功清理'}
        """
        print("\n--- 4. 正在请求清理缓存 ---")
        try:
            result = self._make_request('get', 'clear_cache')
            print(f"缓存清理成功: {result.get('message', result)}")
            return result
        except Exception:
            print("清理缓存失败。")
            return None