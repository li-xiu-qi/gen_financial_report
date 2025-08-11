"""
提取JSON对象的工具函数
专门用于从文本中提取单个JSON对象
"""

import json
import re


def extract_json_object(text: str) -> str:
    """
    从字符串中提取第一个JSON对象。
    
    优先级：
    1. ```json 代码块中的内容
    2. 第一个独立的 {} JSON对象
    
    Args:
        text: 包含JSON对象的文本
        
    Returns:
        str: 提取的JSON字符串，如果没找到则返回None
    """
    
    def find_json_block():
        """提取 ```json 代码块中的内容"""
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            content = match.group(1).strip()
            try:
                # 验证提取的是否是合法的JSON
                json.loads(content)
                return content
            except json.JSONDecodeError:
                return None
        return None
    
    def find_first_object():
        """查找第一个合法的 {} JSON对象"""
        start_index = text.find('{')
        
        while start_index != -1:
            stack = 0
            in_string = False
            
            # 从找到的起始字符开始遍历
            for i in range(start_index, len(text)):
                char = text[i]
                
                # 处理字符串状态，忽略字符串中的特殊字符
                if char == '"' and (i == 0 or text[i-1] != '\\'):
                    in_string = not in_string
                
                # 只在非字符串状态下处理括号
                if not in_string:
                    if char == '{':
                        stack += 1
                    elif char == '}':
                        stack -= 1
                        
                        # 找到匹配的闭括号
                        if stack == 0:
                            obj_str = text[start_index:i+1]
                            try:
                                # 验证是否为合法JSON对象
                                json.loads(obj_str)
                                return obj_str
                            except json.JSONDecodeError:
                                # 不是合法的JSON，继续查找下一个
                                break
            
            # 查找下一个可能的起始位置
            start_index = text.find('{', start_index + 1)
        
        return None
    
    # 按优先级尝试提取
    # 1. 首先尝试代码块
    result = find_json_block()
    if result is not None:
        return result
    
    # 2. 然后尝试独立的JSON对象
    result = find_first_object()
    if result is not None:
        return result
    
    return None


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        # 测试代码块
        """这是一些文本
        ```json
        {
            "is_visualizable": true,
            "reason": "包含数值数据"
        }
        ```
        后续文本""",
        
        # 测试普通JSON对象
        '文本开头 {"is_visualizable": false, "reason": "无数值数据"} 文本结尾',
        
        # 测试多个对象（应该只返回第一个）
        '{"a": 1} {"b": 2}',
        
        # 测试无效JSON
        'text {invalid json} more text',
        
        # 测试嵌套对象
        '{"outer": {"inner": {"value": 123}}, "other": "data"}',
        
        # 测试字符串中包含花括号
        '{"message": "包含{花括号}的字符串", "valid": true}',
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"测试 {i}:")
        print(f"输入: {test_text[:50]}...")
        result = extract_json_object(test_text)
        print(f"结果: {result}")
        if result:
            try:
                parsed = json.loads(result)
                print(f"验证: 成功解析为JSON对象")
            except:
                print(f"验证: 解析失败")
        print("-" * 50)
