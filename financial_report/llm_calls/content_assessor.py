import re
import json
import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# diskcache 缓存支持
from diskcache import Cache
import hashlib

from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array

# 初始化缓存目录，并设置最大缓存大小为 10GB
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(_CACHE_DIR, exist_ok=True)
_cache = Cache(_CACHE_DIR, size_limit=10 * 1024 ** 3)  # 10GB

def _make_cache_key(*args):
    key_str = "|".join([str(a) for a in args])
    return hashlib.md5(key_str.encode("utf-8")).hexdigest()


def assess_cleaned_content_by_rules(cleaned_text: str, url: str) -> dict:
    """
    基于规则的内容质量评估，带缓存。
    """
    cache_key = _make_cache_key("rule", cleaned_text, url)
    if cache_key in _cache:
        return _cache[cache_key]
    
    # Rule 0: Check for extremely long content (likely data corruption or extraction errors)
    char_count = len(cleaned_text)
    MAX_CHARS_THRESHOLD = 250000  # 25万字符阈值
    if char_count > MAX_CHARS_THRESHOLD:
        result = {
            "is_high_quality": False,
            "reason": f"文档过长 ({char_count:,} 字符，超过 {MAX_CHARS_THRESHOLD:,} 字符阈值)，可能存在数据提取错误或重复内容。",
            "source": "rule"
        }
        _cache[cache_key] = result
        print(f"⚠️  过滤超长文档: {url[:50]}... ({char_count:,} 字符)")
        return result
    
    # Rule 1: Check for page load errors.
    error_patterns = ["This site can’t be reached", "took too long to respond", "ERR_CONNECTION_TIMED_OUT", "404 Not Found"]
    if any(p in cleaned_text for p in error_patterns):
        result = {
            "is_high_quality": False,
            "reason": "页面无法访问或返回错误。",
            "source": "rule"
        }
        _cache[cache_key] = result
        return result

    # Rule 2: Chinese content fast-pass.
    total_chars = len(cleaned_text)
    if total_chars > 50:
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', cleaned_text)
        num_chinese_chars = len(chinese_chars)
        chinese_ratio = num_chinese_chars / total_chars
        if chinese_ratio > 0.6 or num_chinese_chars > 150:
            result = {
                "is_high_quality": True,
                "reason": "高中文占比，内容充实。",
                "source": "rule"
            }
            _cache[cache_key] = result
            return result

    # Rule 3: Check for minimum content length.
    word_count = len(re.findall(r'\b\w+\b', cleaned_text))
    if word_count < 100:
        result = {
            "is_high_quality": False,
            "reason": f"文本内容过短 (仅 {word_count} 个词)。",
            "source": "rule"
        }
        _cache[cache_key] = result
        return result

    # Rule 4: Check for generic URL paths.
    try:
        path = urlparse(url).path
        generic_paths = ['/', '/about', '/about/', '/contact', '/contact/', '/events', '/events/', '/research']
        if path in generic_paths:
            result = {
                "is_high_quality": False,
                "reason": f"URL ({path}) 指向通用页面。",
                "source": "rule"
            }
            _cache[cache_key] = result
            return result
    except Exception:
        pass
    result = {
        "is_high_quality": True,
        "reason": "内容充实，未命中低质量规则。",
        "source": "rule"
    }
    _cache[cache_key] = result
    return result


def assess_quality_by_llm(text_snippet: str, url: str, query_objective: str, chat_model: str, api_key: str, base_url: str) -> dict:
    """
    使用大模型进行内容质量评估，带缓存。
    """
    cache_key = _make_cache_key("llm", text_snippet, url, query_objective, chat_model)
    if cache_key in _cache:
        return _cache[cache_key]
    print(f"Info: Routing to LLM for assessment (URL: {url[:70]}...)")
    system_content = "你是一个严谨的内容质量评估助手。你的任务是根据文档开头的片段，推断完整文档的质量。请严格识别并过滤掉导航页、错误页、或无意义的营销口号。你的回答必须是一个JSON对象。"
    user_content = f"""请根据用户的搜索目标，通过以下**文档开头的文本片段**，推断并评估**整个文档**的质量和相关性。

**用户搜索目标:** \"{query_objective}\"
**URL:** \"{url}\"

**文档开头片段:**
---
{text_snippet}
---

请判断这是否像一篇高质量、与目标相关的文章或报告的开头？
返回一个JSON对象，包含两个字段：
1. "is_high_quality": 布尔值 (true/false)
2. "reason": 字符串，用中文简要说明你的推断理由。

**JSON格式示例:**
```json
{{
  "is_high_quality": true,
  "reason": "从片段的标题和摘要来看，这很可能是一篇关于商汤盈利预测的深度报告，与目标高度相关。"
}}```"""

    try:
        messages = [{"role": "user", "content": user_content}]
        llm_response_str = chat_no_tool(
            model=chat_model,
            messages=messages,
            api_key=api_key,
            base_url=base_url,
            system_content=system_content,
            temperature=0.0,
            max_tokens=512,
        )
        json_text = extract_json_array(llm_response_str, mode='auto')
        if json_text:
            result_json = json.loads(json_text)
            is_high_quality = result_json.get("is_high_quality", False)
            reason = result_json.get("reason", "No reason provided.")
            result = {
                "is_high_quality": is_high_quality,
                "reason": reason,
                "source": "llm"
            }
            _cache[cache_key] = result
            return result
        result = {
            "is_high_quality": False,
            "reason": f"Failed to parse JSON from LLM response: {llm_response_str}",
            "source": "llm"
        }
        _cache[cache_key] = result
        return result
    except Exception as e:
        result = {
            "is_high_quality": False,
            "reason": f"LLM call failed - {e}",
            "source": "llm"
        }
        _cache[cache_key] = result
        return result


def assess_content_quality_hybrid(cleaned_text: str, url: str, query_objective: str, chat_model: str, api_key: str, base_url: str) -> dict:
    """
    混合策略进行内容质量评估，带缓存。
    """
    cache_key = _make_cache_key("hybrid", cleaned_text, url, query_objective, chat_model)
    if cache_key in _cache:
        return _cache[cache_key]
    if not cleaned_text or cleaned_text.isspace():
        result = {
            "is_high_quality": False,
            "reason": "清理后内容为空。",
            "source": "hybrid"
        }
        _cache[cache_key] = result
        return result
    char_count = len(cleaned_text)
    if char_count < 500:
        print(f"Info: Content length {char_count} < 500. Routing to LLM.")
        result = assess_quality_by_llm(cleaned_text, url, query_objective, chat_model, api_key, base_url)
        _cache[cache_key] = result
        return result
    else:
        print(f"Info: Content length {char_count} >= 500. Using rule-based assessment.")
        rule_assessment = assess_cleaned_content_by_rules(cleaned_text, url)
        if rule_assessment.get("is_high_quality", False):
            rule_assessment["source"] = "hybrid-rule"
            _cache[cache_key] = rule_assessment
            return rule_assessment
        else:
            print(f"Info: Rule-based check failed: '{rule_assessment}'. Fallback to LLM.")
            result = assess_quality_by_llm(cleaned_text[:1000], url, query_objective, chat_model, api_key, base_url)
            _cache[cache_key] = result
            return result


