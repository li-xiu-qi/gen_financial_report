"""
统一配置管理
整合所有 API 密钥、URL 和配置项
"""

import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """统一配置管理类"""
    
    def __init__(self):
        """初始化配置"""
        self._load_config()
    
    def _load_config(self):
        """从环境变量加载配置"""
        
        # ========== API 服务商配置 ==========
        
        # 火山引擎配置
        self.VOLCANO_API_KEY = os.getenv("OPENAI_API_KEY")
        self.VOLCANO_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
        self.VOLCANO_MODEL = os.getenv("OPENAI_MODEL", "deepseek-v3-250324")
        
        # 硅基流动配置  
        self.GUIJI_API_KEY = os.getenv("GUIJI_API_KEY")
        self.GUIJI_BASE_URL = os.getenv("GUIJI_BASE_URL", "https://api.siliconflow.cn/v1")
        self.GUIJI_TEXT_MODEL = os.getenv("GUIJI_TEXT_MODEL", "moonshotai/Kimi-K2-Instruct")
        self.GUIJI_TEXT_MODEL_DEEPSEEK = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK", "deepseek-ai/DeepSeek-V3")
        self.GUIJI_TEXT_MODEL_DEEPSEEK_PRO = os.getenv("GUIJI_TEXT_MODEL_DEEPSEEK_PRO", "Pro/deepseek-ai/DeepSeek-V3")
        self.GUIJI_FREE_TEXT_MODEL = os.getenv("GUIJI_FREE_TEXT_MODEL", "THUDM/GLM-Z1-9B-0414")
        
        # 智谱配置
        self.ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
        self.ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/")
        self.ZHIPU_FREE_TEXT_MODEL = os.getenv("ZHIPU_FREE_TEXT_MODEL", "glm-4-flash")
        
        # 本地API配置
        self.LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "anything")
        self.LOCAL_BASE_URL = os.getenv("LOCAL_BASE_URL", "http://xia.xshare.fun:10002/v1")
        self.LOCAL_TEXT_MODEL = os.getenv("LOCAL_TEXT_MODEL", "qwen3")
        self.LOCAL_EMBEDDING_MODEL = os.getenv("LOCAL_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")
        self.LOCAL_RERANK_MODEL = os.getenv("LOCAL_RERANK_MODEL", "Qwen3-Reranker-0.6B")
        
        # ========== 服务配置 ==========
        
        # 基于mineru封装成的PDF解析服务，基于微服务架构，内置缓存加速
        self.PDF_BASE_URL = os.getenv("PDF_BASE_URL", "http://localhost:10001")
        
        # 本地的搜索服务，基于playwright实现的本地搜索引擎逆向服务，search server提供，基于微服务架构，内置缓存加速
        self.SEARCH_URL = os.getenv("SEARCH_URL")
        
        # 缓存配置
        self.CACHE_PATH = os.getenv("CACHE_PATH", ".cache")
        self.CACHE_ENABLED = os.getenv("CACHE", "true").lower() == "true"
        
        # ========== 数据收集配置 ==========
        
        # 并发配置
        self.MAX_CONCURRENT_COMPANY = int(os.getenv("MAX_CONCURRENT_COMPANY", "2000"))
        self.MAX_CONCURRENT_INDUSTRY = int(os.getenv("MAX_CONCURRENT_INDUSTRY", "2000")) 
        self.MAX_CONCURRENT_MACRO = int(os.getenv("MAX_CONCURRENT_MACRO", "2000"))
        
        # 搜索配置
        self.USE_ZHIPU_SEARCH = os.getenv("USE_ZHIPU_SEARCH", "false").lower() == "true"
        self.SEARCH_INTERVAL_COMPANY = float(os.getenv("SEARCH_INTERVAL_COMPANY", "1.0"))
        self.SEARCH_INTERVAL_INDUSTRY = float(os.getenv("SEARCH_INTERVAL_INDUSTRY", "1.0"))
        self.SEARCH_INTERVAL_MACRO = float(os.getenv("SEARCH_INTERVAL_MACRO", "1.0"))
        
        # 其他配置
        self.USE_EXISTING_SEARCH_RESULTS = os.getenv("USE_EXISTING_SEARCH_RESULTS", "true").lower() == "true"
        
        # ========== 报告生成配置 ==========
        
        # Token配置
        self.MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", str(128 * 1024)))
        self.CONTEXT_USAGE_RATIO = float(os.getenv("CONTEXT_USAGE_RATIO", "0.8"))
        
        # 生成配置
        self.ENABLE_CHART_ENHANCEMENT = os.getenv("ENABLE_CHART_ENHANCEMENT", "true").lower() == "true"
        self.DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.5"))
        self.DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "8192"))
    
    def get_data_collection_config(self, collection_type: str) -> Dict[str, Any]:
        """
        获取数据收集配置
        
        Args:
            collection_type: 收集类型 ('company', 'industry', 'macro')
        
        Returns:
            配置字典
        """
        base_config = {
            "api_key": self.GUIJI_API_KEY,
            "base_url": self.GUIJI_BASE_URL,
            "model": self.GUIJI_TEXT_MODEL_DEEPSEEK_PRO,
            "use_zhipu_search": self.USE_ZHIPU_SEARCH,
            "zhipu_search_key": self.ZHIPU_API_KEY,
            "search_url": self.SEARCH_URL,
            "use_existing_search_results": self.USE_EXISTING_SEARCH_RESULTS
        }
        
        if collection_type == "company":
            base_config.update({
                "max_concurrent": self.MAX_CONCURRENT_COMPANY,
                "search_interval": self.SEARCH_INTERVAL_COMPANY
            })
        elif collection_type == "industry":
            base_config.update({
                "max_concurrent": self.MAX_CONCURRENT_INDUSTRY,
                "search_interval": self.SEARCH_INTERVAL_INDUSTRY
            })
        elif collection_type == "macro":
            base_config.update({
                "max_concurrent": self.MAX_CONCURRENT_MACRO,
                "search_interval": self.SEARCH_INTERVAL_MACRO
            })
        
        return base_config
    
    def get_report_generation_config(self, report_type: str) -> Dict[str, Any]:
        """
        获取报告生成配置
        
        Args:
            report_type: 报告类型 ('company', 'industry', 'macro')
        
        Returns:
            配置字典
        """
        return {
            "api_key": self.GUIJI_API_KEY,
            "base_url": self.GUIJI_BASE_URL,
            "model": self.GUIJI_TEXT_MODEL_DEEPSEEK_PRO,
            "report_type": report_type,
            "max_context_tokens": self.MAX_CONTEXT_TOKENS,
            "context_usage_ratio": self.CONTEXT_USAGE_RATIO,
            "enable_chart_enhancement": self.ENABLE_CHART_ENHANCEMENT,
            "temperature": self.DEFAULT_TEMPERATURE,
            "max_tokens": self.DEFAULT_MAX_TOKENS
        }
    
    def get_api_config(self, provider: str) -> Dict[str, Any]:
        """
        获取指定服务商的API配置
        
        Args:
            provider: 服务商 ('volcano', 'guiji', 'zhipu', 'local')
        
        Returns:
            API配置字典
        """
        configs = {
            "volcano": {
                "api_key": self.VOLCANO_API_KEY,
                "base_url": self.VOLCANO_BASE_URL,
                "model": self.VOLCANO_MODEL
            },
            "guiji": {
                "api_key": self.GUIJI_API_KEY,
                "base_url": self.GUIJI_BASE_URL,
                "model": self.GUIJI_TEXT_MODEL,
                "deepseek_model": self.GUIJI_TEXT_MODEL_DEEPSEEK,
                "deepseek_pro_model": self.GUIJI_TEXT_MODEL_DEEPSEEK_PRO,
                "free_model": self.GUIJI_FREE_TEXT_MODEL
            },
            "zhipu": {
                "api_key": self.ZHIPU_API_KEY,
                "base_url": self.ZHIPU_BASE_URL,
                "model": self.ZHIPU_FREE_TEXT_MODEL
            },
            "local": {
                "api_key": self.LOCAL_API_KEY,
                "base_url": self.LOCAL_BASE_URL,
                "model": self.LOCAL_TEXT_MODEL,
                "embedding_model": self.LOCAL_EMBEDDING_MODEL,
                "rerank_model": self.LOCAL_RERANK_MODEL
            }
        }
        
        return configs.get(provider, {})
    
    def validate_config(self) -> Dict[str, bool]:
        """
        验证配置完整性
        
        Returns:
            验证结果字典
        """
        results = {}
        
        # 验证必需的API密钥
        results["guiji_api_key"] = bool(self.GUIJI_API_KEY)
        results["zhipu_api_key"] = bool(self.ZHIPU_API_KEY)
        results["volcano_api_key"] = bool(self.VOLCANO_API_KEY)
        
        # 验证URL配置
        results["guiji_base_url"] = bool(self.GUIJI_BASE_URL)
        results["zhipu_base_url"] = bool(self.ZHIPU_BASE_URL)
        results["pdf_base_url"] = bool(self.PDF_BASE_URL)
        
        return results
    
    def print_config_status(self):
        """打印配置状态"""
        print("🔧 配置状态检查")
        print("=" * 50)
        
        validation = self.validate_config()
        
        for key, status in validation.items():
            status_icon = "✅" if status else "❌"
            print(f"{status_icon} {key}: {'已配置' if status else '未配置'}")
        
        print("\n📊 服务配置:")
        print(f"   - PDF解析服务: {self.PDF_BASE_URL}")
        print(f"   - 搜索服务: {self.SEARCH_URL or '未配置'}")
        print(f"   - 缓存路径: {self.CACHE_PATH}")
        print(f"   - 缓存启用: {'是' if self.CACHE_ENABLED else '否'}")
        
        print("\n⚙️ 数据收集配置:")
        print(f"   - 公司并发数: {self.MAX_CONCURRENT_COMPANY}")
        print(f"   - 行业并发数: {self.MAX_CONCURRENT_INDUSTRY}")
        print(f"   - 宏观并发数: {self.MAX_CONCURRENT_MACRO}")
        print(f"   - 智谱搜索: {'启用' if self.USE_ZHIPU_SEARCH else '禁用'}")


# 创建全局配置实例
config = Config()


# 便捷函数
def get_config() -> Config:
    """获取全局配置实例"""
    return config


def get_data_collection_config(collection_type: str) -> Dict[str, Any]:
    """获取数据收集配置的便捷函数"""
    return config.get_data_collection_config(collection_type)


def get_report_generation_config(report_type: str) -> Dict[str, Any]:
    """获取报告生成配置的便捷函数"""
    return config.get_report_generation_config(report_type)


def get_api_config(provider: str) -> Dict[str, Any]:
    """获取API配置的便捷函数"""
    return config.get_api_config(provider)


if __name__ == "__main__":
    # 运行配置检查
    config.print_config_status()
