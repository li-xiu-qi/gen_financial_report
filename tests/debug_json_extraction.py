#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script for JSON extraction issues
"""

import json
import sys
import os

# Add the financial_report utils to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'financial_report', 'utils'))

from extract_json_array import extract_json_array

# Test data from the user's example
test_text = '''AI回复: ```json
  ""人工智能+" 就业结构变化 (岗位替代率 OR 新增就业岗位) 分行业 site:mohrss.gov.cn filetype:pdf",
  ""人工智能+" 企业数量增长 (初创企业 OR 上市公司) 注册资金 2023..2025 site:amr.gov.cn",
  ""人工智能+" 风险投资 (金额 OR 轮次) 季度报告 2023..2025 site:csrc.gov.cn filetype:pdf",
  ""人工智能+" 数据安全 监管政策 (合规成本 OR 处罚案例) site:cac.gov.cn",
  ""人工智能+" 算力基础设施 (投资额 OR 利用率) 区域分布 site:miit.gov.cn",
  ""人工智能+" 国际竞争力指数 (全球排名 OR 细分领域) 2023..2025 site:caict.ac.cn",
  ""人工智能+" 行业应用深度 (医疗 OR 金融 OR 制造) 渗透率 site:gov.cn filetype:pdf",
  ""人工智能+" 中小企业 数字化转型 (补贴政策 OR 实施困难) site:miit.gov.cn",
  ""人工智能+" 能源消耗 (碳排放 OR 能效比) 环境影响评估 site:mee.gov.cn",
  ""人工智能+" 人才缺口 (高校培养 OR 海外引进) 统计 site:moe.gov.cn",
  ""人工智能+" 国际技术壁垒 (出口管制 OR 专利诉讼) 案例 site:mofcom.gov.cn filetype:pdf",
  ""人工智能+" 系统性风险 (技术依赖 OR 市场泡沫) 预警报告 site:pbc.gov.cn"
]
```'''

def debug_extraction():
    print("=== 调试 JSON 提取 ===")
    print(f"原始文本长度: {len(test_text)}")
    print(f"原始文本前100字符: {repr(test_text[:100])}")
    print()
    
    # 测试不同模式
    modes = ['auto', 'jsonblock', 'array', 'objects']
    
    for mode in modes:
        print(f"--- 模式: {mode} ---")
        try:
            result = extract_json_array(test_text, mode=mode)
            print(f"提取结果存在: {result is not None}")
            if result:
                print(f"结果长度: {len(result)}")
                print(f"结果前100字符: {repr(result[:100])}")
                
                # 尝试解析为JSON
                try:
                    parsed = json.loads(result)
                    print(f"✅ JSON解析成功! 数组长度: {len(parsed)}")
                    print(f"第一个元素: {repr(parsed[0][:50])}...")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    # 显示有问题的部分
                    if hasattr(e, 'pos'):
                        error_pos = e.pos
                        print(f"错误位置 {error_pos} 附近: {repr(result[max(0, error_pos-20):error_pos+20])}")
            else:
                print("❌ 没有提取到内容")
        except Exception as e:
            print(f"❌ 提取过程出错: {e}")
        print()

def manual_analysis():
    print("=== 手动分析 ===")
    
    # 手动找到 ```json 块
    import re
    match = re.search(r'```json\s*([\s\S]*?)\s*```', test_text)
    if match:
        content = match.group(1).strip()
        print(f"找到 JSON 块，内容长度: {len(content)}")
        print("JSON 块内容:")
        print(repr(content))
        print()
        
        # 检查是否看起来像数组
        content_stripped = content.strip()
        if content_stripped.startswith('[') and content_stripped.endswith(']'):
            print("✅ 看起来是数组格式")
        else:
            print("❌ 不是标准数组格式")
            print(f"开始字符: {repr(content_stripped[:10])}")
            print(f"结束字符: {repr(content_stripped[-10:])}")
        
        # 尝试修复并解析
        try:
            # 如果不是以 [ 开头，尝试添加
            if not content_stripped.startswith('['):
                fixed_content = '[' + content_stripped
            else:
                fixed_content = content_stripped
                
            # 如果不是以 ] 结尾，尝试添加  
            if not fixed_content.endswith(']'):
                fixed_content = fixed_content + ']'
                
            print(f"修复后内容: {repr(fixed_content[:100])}...")
            parsed = json.loads(fixed_content)
            print(f"✅ 修复后解析成功! 数组长度: {len(parsed)}")
            
        except json.JSONDecodeError as e:
            print(f"❌ 修复后仍然解析失败: {e}")
    else:
        print("❌ 没有找到 ```json 块")

if __name__ == "__main__":
    debug_extraction()
    manual_analysis()
