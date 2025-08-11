"""
内容整合器 - 用于整合多个子分析结果
"""

import json
import requests
from typing import List, Dict, Any


def integrate_sub_analyses(
    company_name: str,
    company_code: str,
    section_title: str,
    sub_analyses: List[Dict[str, Any]],
    api_key: str,
    base_url: str,
    model: str,
    max_tokens: int = 3000,
    temperature: float = 0.3
) -> str:
    """
    整合多个子分析结果为一个连贯的章节内容
    
    Args:
        company_name: 公司名称
        company_code: 公司代码
        section_title: 章节标题
        sub_analyses: 子分析结果列表
        api_key: API密钥
        base_url: API基础URL
        model: 模型名称
        max_tokens: 最大token数
        temperature: 温度参数
        
    Returns:
        整合后的章节内容
    """
    
    # 构建子分析内容摘要
    sub_content_summary = []
    for idx, analysis in enumerate(sub_analyses, 1):
        point = analysis.get("point", "")
        answer = analysis.get("answer", "")
        sources_count = len(analysis.get("sources", []))
        
        sub_content_summary.append(
            f"**子分析{idx}: {point}**\n"
            f"分析结果: {answer[:500]}{'...' if len(answer) > 500 else ''}\n"
            f"引用来源: {sources_count}个\n"
        )
    
    sub_content_text = "\n".join(sub_content_summary)
    
    # 构建整合提示
    system_prompt = f"""你是一位专业的金融分析师，正在撰写关于{company_name}（{company_code}）的投资研究报告。

你的任务是将多个子分析结果整合成一个连贯、专业的章节内容。

整合要求：
1. 保持内容的逻辑性和连贯性
2. 避免重复，合并相似观点
3. 突出关键信息和核心观点
4. 使用专业的金融分析语言
5. 保持客观、准确的分析态度
6. 适当引用数据和事实支撑观点
7. 结构清晰，层次分明

当前章节：{section_title}"""

    user_prompt = f"""请将以下子分析结果整合成一个完整、专业的《{section_title}》章节：

{sub_content_text}

请生成整合后的章节内容，要求：
- 内容完整、逻辑清晰
- 专业术语准确
- 观点有据可依
- 结构层次分明
- 长度适中（建议2000-3000字符）

开始整合："""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False
    }
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        integrated_content = result["choices"][0]["message"]["content"]
        
        return integrated_content
        
    except Exception as e:
        print(f"内容整合失败: {e}")
        # 返回简单的拼接作为fallback
        fallback_content = f"# {section_title}\n\n"
        for analysis in sub_analyses:
            fallback_content += f"## {analysis.get('point', '')}\n\n"
            fallback_content += f"{analysis.get('answer', '')}\n\n"
        
        return fallback_content