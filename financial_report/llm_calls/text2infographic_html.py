from financial_report.utils.chat import chat_no_tool
from financial_report.utils.extract_json_array import extract_json_array
import re

text_to_infographic_html_pompt = """
你是一位数据可视化专家。将用户文本转换为**可直接截图**的静态HTML图表，严格遵守以下规则：

1. 图表类型  
   仅使用 **treemap、sunburst、sankey、bar、circular** 等**非力引导**布局，保证布局100%确定。

2. 信息完整  
   - 所有节点、边必须**默认可见**标签，禁止隐藏、悬浮提示。  
   - 关键数据**不得**藏在tooltip。

3. 品牌色  
   识别公司实体并自动应用官方主色（例：AWS橙、Azure蓝、特斯拉红）。

4. 视觉规范  
   - 背景：`#FFFFFF`（浅色）或`#282c34`（深色）。  
   - 文字与背景对比度必须极高。  
   - 字号：标题18-22px，标签12-14px。  
   - 折线宽≥2px，数据点≥8px。  
   - 全局 `animation: false`。

5. 防裁剪  
   - 直角坐标系：`grid:{containLabel:true}`。  
   - 其他：`left/right/top/bottom ≥15%`。

6. 单位智能  
   统一单位（万、百万、亿、K、M…），并在轴/标签标注。

7. 纯净输出  
   - **无动画、无数据来源、无注释**。  
   - 仅返回1个完整HTML文件，使用本地库 `<script src="./js/echarts.min.js"></script>`。

8. 输出格式  
   返回纯HTML代码块，前后无额外文字。
   
9.输出示例：
```html
<!DOCTYPE html>
<html lang="en">
<head>
      <meta charset="UTF-8">

<!DOCTYPE html>
<html lang="zh-cn">
<head>
    <meta charset="UTF-8">
    <title>示例柱状图</title>
    <script src="./js/echarts.min.js"></script>
    <style>
        body { background: #FFFFFF; color: #222; }
        h2 { font-size: 20px; }
    </style>
</head>
<body>
    <h2>公司营收对比（单位：亿元）</h2>
    <div id="main" style="width:600px;height:400px;"></div>
    <script>
      ……
    </script>
</body>
</html>

"""

def extract_html_block(text):
   """
   用正则提取第一个完整HTML片段（以```html、<!DOCTYPE html>或<html开头，以</html>结尾）。
   """
   # 优先匹配 ```html ... ``` 代码块
   match = re.search(r'```html\s*([\s\S]*?)```', text)
   if match:
      return match.group(1).strip()
   # 匹配 <!DOCTYPE html ... </html>
   match = re.search(r'<!DOCTYPE html[\s\S]*?</html>', text)
   if match:
      return match.group(0).strip()
   # 匹配 <html ... </html>
   match = re.search(r'<html[\s\S]*?</html>', text)
   if match:
      return match.group(0).strip()
   # 如果都没有，返回原始文本
   return text.strip()

def text2infographic_html(
    query,
    api_key: str = None,
    base_url: str = None,
    model: str = None,
    max_tokens: int = 4000,
    temperature: float = 0.5,
):
    """
    使用指定的提示词生成行业研报大纲。
    """


    try:
        html = chat_no_tool(
            user_content=text_to_infographic_html_pompt + query,
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens, 
        )
        # 用正则提取完整HTML片段
        html = extract_html_block(html)
        return html
    except Exception as e:
        print(f"Error generating industry outline: {e}")
        return None

