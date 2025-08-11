from financial_report.search_tools.search_tools import zhipu_search_with_cache
from dotenv import load_dotenv
from typing import Optional, Dict, Any, List
load_dotenv()
import os
api_key = os.getenv("ZHIPU_API_KEY")


res = zhipu_search_with_cache(query="中国半导体行业研究报告 市场规模 发展趋势", zhipu_api_key=api_key)
print(res)