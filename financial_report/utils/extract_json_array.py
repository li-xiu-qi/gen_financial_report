import json
import re

def extract_json_array(text: str, mode: str = 'auto'):
    """
    从字符串中提取第一个 JSON 数组或由多个对象组成的数组。

    mode:
      - 'auto': 优先提取 ```json 代码块，其次是独立的 [] 数组，最后是由多个 {} 对象拼接的数组。
      - 'jsonblock': 只提取 ```json 代码块中的内容。
      - 'array': 只提取第一个独立的 [] JSON 数组。
      - 'objects': 提取所有顶层的 {} JSON 对象并组成一个数组。
    """

    def find_json_block():
        """使用正则表达式安全地提取 json 代码块"""
        # 使用非贪婪模式 (.*?) 来匹配最近的 ```
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

    def find_array():
        """查找第一个合法的 [] 数组"""
        # 使用栈平衡来查找完整且合法的JSON数组
        start_char, end_char = '[', ']'
        
        # 从头开始查找第一个起始字符
        try:
            start_index = text.find(start_char)
        except ValueError:
            start_index = -1
            
        while start_index != -1:
            stack = 0
            in_string = False
            
            # 从找到的起始字符开始遍历
            for i in range(start_index, len(text)):
                char = text[i]

                # 切换字符串状态，忽略字符串中的特殊字符
                if char == '"' and (i == 0 or text[i-1] != '\\'):
                    in_string = not in_string
                
                if in_string:
                    continue

                if char == start_char:
                    stack += 1
                elif char == end_char:
                    stack -= 1
                
                if stack == 0:
                    # 找到了一个完整的、闭合的结构
                    potential_json = text[start_index : i + 1]
                    try:
                        # 验证提取的是否是合法的JSON
                        json.loads(potential_json)
                        return potential_json
                    except json.JSONDecodeError:
                        # 如果不是合法的JSON，跳出内层循环
                        # 从当前闭合结构的下一个位置继续寻找新的起始点
                        break
            
            # 从当前 start_index 的后一个位置继续查找新的起始字符
            try:
                start_index = text.find(start_char, start_index + 1)
            except ValueError:
                start_index = -1

        return None


    def find_objects():
        """查找所有顶层对象并拼接成数组"""
        objs = []
        i = 0
        in_string = False
        
        while i < len(text):
            # 忽略字符串中的 '{'
            char = text[i]
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                in_string = not in_string

            if text[i] == '{' and not in_string:
                start_idx = i
                stack = 1
                obj_in_string = False
                j = i + 1
                while j < len(text):
                    char_j = text[j]
                    if char_j == '"' and (j == 0 or text[j-1] != '\\'):
                        obj_in_string = not obj_in_string

                    if not obj_in_string:
                        if char_j == '{':
                            stack += 1
                        elif char_j == '}':
                            stack -= 1
                    
                    if stack == 0:
                        obj_str = text[start_idx:j+1]
                        try:
                            # 验证是否为合法JSON对象
                            json.loads(obj_str)
                            objs.append(obj_str)
                        except json.JSONDecodeError:
                            pass # 不是合法的，忽略
                        i = j # 从当前对象后继续搜索
                        break
                    j += 1
            i += 1
            
        if objs: # 只要找到至少一个对象
            return f"[{','.join(objs)}]"
        return None

    # --- 主逻辑 ---
    if mode == 'jsonblock':
        return find_json_block()
    if mode == 'array':
        return find_array()
    if mode == 'objects':
        return find_objects()
    
    # 'auto' 模式逻辑
    # 按优先级尝试
    result = find_json_block()
    if result is not None:
        return result
        
    result = find_array()
    if result is not None:
        return result
        
    result = find_objects()
    if result is not None:
        return result

    return None

if __name__ == "__main__":
    # --- 原有测试 ---
    print("--- 原有测试 ---")
    text1 = "请看这个列表[这不是JSON], 然后这里是代码块 ```json[{\"id\": 1, \"value\": \"]\"}]```"
    text2 = "这里只有一个对象 {\"name\": \"apple\"} 还有一个 {\"name\": \"banana\"}"
    text3 = "这是一个标准的JSON数组 [1, 2, 3]"
    text4 = "无效[1,2"

    print(f"Test 1 (auto): {extract_json_array(text1, mode='auto')}")
    print(f"Test 2 (auto): {extract_json_array(text2, mode='auto')}")
    print(f"Test 2 (objects): {extract_json_array(text2, mode='objects')}")
    print(f"Test 3 (auto): {extract_json_array(text3, mode='auto')}")
    print(f"Test 4 (auto): {extract_json_array(text4, mode='auto')}") # 无效JSON，应为None
    print("-" * 20)

    # --- 新增测试用例 ---
    print("\n--- 新增测试用例 ---")

    # Test 5: 完全没有JSON
    text5 = "这是一段不包含任何JSON的普通文本。"
    print(f"Test 5 (No JSON): {extract_json_array(text5, mode='auto')}")

    # Test 6: 'auto' 模式优先级测试
    text6a = "对象{\"id\":0}, 数组[1,2], 代码块 ```json[{\"id\":99}]```"
    text6b = "对象{\"id\":0}, 数组[1,2]"
    print(f"Test 6a (auto priority): {extract_json_array(text6a, mode='auto')}") # 应优先选择代码块
    print(f"Test 6b (auto priority): {extract_json_array(text6b, mode='auto')}") # 无代码块，应选择数组

    # Test 7: 复杂嵌套JSON
    text7 = '前文... [{"id": 1, "data": {"type": "A", "values": [10, 20, 30]}}, {"id": 2}] ...后文'
    print(f"Test 7 (Complex JSON): {extract_json_array(text7, mode='auto')}")

    # Test 8: 字符串内包含特殊字符
    text8 = '[{"key": "值包含[括号]和{花括号}"}]'
    print(f"Test 8 (Special chars in string): {extract_json_array(text8, mode='auto')}")

    # Test 9: 多个独立目标
    text9a = "第一个数组 [1, 2], 第二个数组 [3, 4]."
    text9b = '第一个对象 {"a": 1}，第二个对象 {"b": 2}'
    print(f"Test 9a (Multiple arrays): {extract_json_array(text9a, mode='array')}") # 应只提取第一个数组
    print(f"Test 9b (Multiple objects): {extract_json_array(text9b, mode='objects')}") # 应提取所有对象

    # Test 10: 包含大量空白字符
    text10 = """
        一些文字
        ```json
        [
            {
                "name": "格式混乱",
                "val": "  ok  "
            }
        ]
        ```
    """
    print(f"Test 10 (Formatted JSON): {extract_json_array(text10, mode='auto')}")

    # Test 11: 语法错误的JSON (例如，末尾有逗号)
    text11a = "这是一个错误的数组 [1, 2,]"
    text11b = "这是一个错误的对象 {\"a\":1,}"
    text11c = "代码块中也是错误的 ```json[{\"a\":1,}]```"
    print(f"Test 11a (Invalid array): {extract_json_array(text11a, mode='auto')}") # 应为 None
    print(f"Test 11b (Invalid object): {extract_json_array(text11b, mode='auto')}") # 应为 None
    print(f"Test 11c (Invalid in block): {extract_json_array(text11c, mode='auto')}") # 应为 None

    # Test 12: 对象之间没有空格
    text12 = '{"a":1}{"b":2,"c":{"d":3}}'
    print(f"Test 12 (Objects without space): {extract_json_array(text12, mode='objects')}")

    # Test 13: 混合了有效和无效的JSON
    text13 = "无效结构: [1, 2,]. 这是一个有效的: {\"status\": \"ok\"}"
    print(f"Test 13 (Mixed valid/invalid): {extract_json_array(text13, mode='auto')}") # 应跳过无效的，找到有效的