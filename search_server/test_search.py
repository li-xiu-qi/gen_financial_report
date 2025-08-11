#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试search.py服务的功能
"""

import requests
import time
import json
from urllib.parse import quote

def test_search_service(base_url="http://localhost:30002"):
    """测试搜索服务的各个接口"""
    
    print("开始测试搜索服务...")
    print(f"服务地址: {base_url}")
    print("=" * 50)
    
    # 测试帮助接口
    print("\n1. 测试帮助接口")
    try:
        response = requests.get(f"{base_url}/help", timeout=10)
        if response.status_code == 200:
            print("✓ 帮助接口正常")
            print(f"可用接口:\n{response.text}")
        else:
            print(f"✗ 帮助接口异常: {response.status_code}")
    except Exception as e:
        print(f"✗ 帮助接口错误: {e}")
    
    # 测试外汇牌价接口（不需要参数）
    print("\n2. 测试外汇牌价接口")
    try:
        response = requests.get(f"{base_url}/whpj", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 外汇牌价接口正常，获取到 {len(data)} 条数据")
            if data:
                print(f"示例数据: {json.dumps(data[0], ensure_ascii=False, indent=2)}")
        else:
            print(f"✗ 外汇牌价接口异常: {response.status_code}")
    except Exception as e:
        print(f"✗ 外汇牌价接口错误: {e}")
    
    # 测试必应搜索
    print("\n3. 测试必应搜索接口")
    try:
        query = quote("Python编程")
        response = requests.get(f"{base_url}/bing?query={query}&total=3&cn=true", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 必应搜索接口正常，获取到 {len(data)} 条结果")
            if data:
                for i, item in enumerate(data[:2], 1):
                    print(f"结果{i}: {item.get('title', '')[:50]}...")
        else:
            print(f"✗ 必应搜索接口异常: {response.status_code}")
    except Exception as e:
        print(f"✗ 必应搜索接口错误: {e}")
    
    # 测试问财网搜索
    print("\n4. 测试问财网搜索接口")
    try:
        query = quote("比亚迪")
        response = requests.get(f"{base_url}/iwencai?query={query}", timeout=60)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 问财网搜索接口正常，获取到 {len(data)} 条结果")
            if data:
                for i, item in enumerate(data[:2], 1):
                    print(f"结果{i}: {item.get('title', '')[:50]}...")
        else:
            print(f"✗ 问财网搜索接口异常: {response.status_code}")
    except Exception as e:
        print(f"✗ 问财网搜索接口错误: {e}")
    
    # 测试通用网页抓取
    print("\n5. 测试通用网页抓取接口")
    try:
        url = quote("https://www.baidu.com")
        response = requests.get(f"{base_url}/goto?query={url}", timeout=30)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 网页抓取接口正常")
            print(f"页面标题: {data.get('title', '')}")
            print(f"HTML长度: {len(data.get('html', ''))}")
        else:
            print(f"✗ 网页抓取接口异常: {response.status_code}")
    except Exception as e:
        print(f"✗ 网页抓取接口错误: {e}")
    
    print("\n" + "=" * 50)
    print("测试完成！")


def check_service_status(base_url="http://localhost:30002"):
    """检查服务是否运行"""
    try:
        response = requests.get(f"{base_url}/help", timeout=5)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='测试搜索服务')
    parser.add_argument('--url', default='http://localhost:30002', help='服务地址')
    parser.add_argument('--wait', action='store_true', help='等待服务启动')
    args = parser.parse_args()
    
    if args.wait:
        print("等待服务启动...")
        for i in range(30):  # 等待最多30秒
            if check_service_status(args.url):
                print(f"服务已启动！(等待了 {i} 秒)")
                break
            time.sleep(1)
            print(f"等待中... {i+1}/30")
        else:
            print("服务启动超时，请检查服务是否正常运行")
            sys.exit(1)
    
    if not check_service_status(args.url):
        print(f"无法连接到服务 {args.url}")
        print("请确保服务已启动: python search.py")
        sys.exit(1)
    
    test_search_service(args.url)
