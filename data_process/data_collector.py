"""
数据收集助手
用于根据大纲章节需求智能收集和提取相关数据，支持大token量的分段处理
"""

import json
from typing import List, Dict, Any, Optional, Tuple
from financial_report.utils.calculate_tokens import OpenAITokenCalculator
from financial_report.utils.chat import chat_no_tool


class DataCollector:
    """数据收集助手，负责为报告章节收集相关数据"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        token_calculator: Optional[OpenAITokenCalculator] = None,
        max_output_tokens: int = 16384  # 增加默认输出token以支持更详细的信息收集
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.token_calculator = token_calculator or OpenAITokenCalculator()
        self.max_output_tokens = max_output_tokens
    
    def get_data_by_ids(
        self, 
        data_ids: List[str], 
        all_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        根据ID列表获取对应的数据项
        
        Args:
            data_ids: 数据ID列表
            all_data: 所有数据的列表
            
        Returns:
            匹配的数据项列表
        """
        id_to_data = {str(item["id"]): item for item in all_data}
        return [id_to_data[data_id] for data_id in data_ids if data_id in id_to_data]
    
    def calculate_content_tokens(self, data_items: List[Dict[str, Any]]) -> int:
        """
        计算数据项内容的总token数
        
        Args:
            data_items: 数据项列表
            
        Returns:
            总token数
        """
        total_content = ""
        for item in data_items:
            content = item.get("summary", "") or item.get("content", "") or item.get("md", "")
            total_content += f"\\n\\n【数据{item['id']}】{item.get('title', '')}\\n{content}"
        
        return self.token_calculator.count_tokens(total_content)
    
    def collect_data_for_section(
        self,
        section_title: str,
        section_points: List[str],
        allocated_data_ids: List[str],
        all_data: List[Dict[str, Any]],
        max_context_tokens: int,
        company_name: str = "",
        max_output_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        为特定章节收集数据
        
        Args:
            section_title: 章节标题
            section_points: 章节要点
            allocated_data_ids: 分配给该章节的数据ID列表
            all_data: 所有可用数据
            max_context_tokens: 最大上下文token数（已扣除prompt空间）
            company_name: 公司名称
            max_output_tokens: 最大输出token数，如果为None则使用实例默认值
            
        Returns:
            包含收集数据和处理信息的字典
        """
        # 确定使用的最大输出token数
        output_tokens = max_output_tokens if max_output_tokens is not None else self.max_output_tokens
        print(f"📊 为章节 '{section_title}' 收集数据...")
        print(f"   📋 分配的数据ID数量: {len(allocated_data_ids)}")
        print(f"   🔧 最大输出token配置: {output_tokens:,}")
        
        # 1. 获取分配的数据
        relevant_data = self.get_data_by_ids(allocated_data_ids, all_data)
        print(f"   ✅ 成功获取 {len(relevant_data)} 个数据项")
        
        if not relevant_data:
            return {
                "section_title": section_title,
                "collected_data": [],
                "processing_method": "no_data",
                "total_tokens": 0,
                "summary": f"章节 '{section_title}' 暂无相关数据",
                "references": []  # 添加空的参考文献列表
            }
        
        # 2. 创建参考文献映射
        references = []
        id_to_ref_num = {}
        
        for i, item in enumerate(relevant_data, 1):
            # 优先使用实际的标题和URL
            actual_title = item.get("title", "")
            actual_url = item.get("url", "")
            
            # 如果没有标题，使用公司名称 + 数据源类型
            if not actual_title:
                company_name = item.get("company_name", "")
                data_source_type = item.get("data_source_type", "数据")
                actual_title = f"{company_name} {data_source_type}"
            
            ref_info = {
                "ref_num": i,
                "data_id": item["id"], 
                "title": actual_title,
                "url": actual_url,
                "source": item.get("data_source", "unknown"),
                "company_name": item.get("company_name", ""),
                "company_code": item.get("company_code", ""),
                "market": item.get("market", "")
            }
            references.append(ref_info)
            id_to_ref_num[item["id"]] = i
            
        print(f"   📚 创建参考文献映射: {len(references)} 个")
        
        # 3. 计算token使用量
        total_tokens = self.calculate_content_tokens(relevant_data)
        print(f"   📈 数据总token数: {total_tokens:,}")
        print(f"   📏 可用上下文token: {max_context_tokens:,}")
        
        # 4. 根据token量决定处理方式
        if total_tokens <= max_context_tokens:
            # 数据量适中，直接返回
            print(f"   ✅ 数据量适中，直接使用全部数据")
            return {
                "section_title": section_title,
                "section_points": section_points,
                "collected_data": relevant_data,
                "processing_method": "direct",
                "total_tokens": total_tokens,
                "company_name": company_name,
                "references": references,
                "id_to_ref_num": id_to_ref_num
            }
        else:
            # 数据量过大，需要分批处理和提取
            print(f"   ⚠️  数据量过大，启用分批提取模式")
            result = self._extract_data_in_batches(
                section_title=section_title,
                section_points=section_points,
                relevant_data=relevant_data,
                max_context_tokens=max_context_tokens,
                company_name=company_name,
                max_output_tokens=output_tokens
            )
            # 添加参考文献信息
            result["references"] = references
            result["id_to_ref_num"] = id_to_ref_num
            return result
    
    def _extract_data_in_batches(
        self,
        section_title: str,
        section_points: List[str],
        relevant_data: List[Dict[str, Any]],
        max_context_tokens: int,
        company_name: str,
        max_output_tokens: int
    ) -> Dict[str, Any]:
        """
        分批提取数据的关键信息
        
        Args:
            section_title: 章节标题
            section_points: 章节要点
            relevant_data: 相关数据列表
            max_context_tokens: 最大上下文token数
            company_name: 公司名称
            max_output_tokens: 最大输出token数
            
        Returns:
            提取后的数据摘要
        """
        print(f"   🔄 开始分批数据提取...")
        
        # 将数据分批，每批不超过token限制
        batches = self._create_data_batches(relevant_data, max_context_tokens)
        print(f"   📦 数据分为 {len(batches)} 个批次处理")
        
        # 对每个批次进行信息提取
        extracted_summaries = []
        for i, batch in enumerate(batches):
            print(f"   🔄 处理第 {i+1}/{len(batches)} 批次 ({len(batch)} 个数据项)...")
            
            try:
                batch_summary = self._extract_batch_information(
                    section_title=section_title,
                    section_points=section_points,
                    data_batch=batch,
                    company_name=company_name,
                    batch_index=i+1,
                    total_batches=len(batches),
                    max_output_tokens=max_output_tokens
                )
                extracted_summaries.append(batch_summary)
                print(f"   ✅ 第 {i+1} 批次提取完成")
            except Exception as e:
                print(f"   ❌ 第 {i+1} 批次提取失败: {e}")
                # 失败时使用原始数据的简要信息
                fallback_summary = self._create_fallback_summary(batch)
                extracted_summaries.append(fallback_summary)
        
        # 合并所有提取的信息
        final_summary = self._merge_extracted_summaries(
            section_title, extracted_summaries, len(relevant_data)
        )
        
        return {
            "section_title": section_title,
            "section_points": section_points,
            "collected_data": [{"summary": final_summary, "source_count": len(relevant_data)}],
            "processing_method": "batch_extraction",
            "total_tokens": self.token_calculator.count_tokens(final_summary),
            "original_data_count": len(relevant_data),
            "batch_count": len(batches),
            "company_name": company_name
        }
    
    def _create_data_batches(
        self, 
        data_items: List[Dict[str, Any]], 
        max_tokens_per_batch: int
    ) -> List[List[Dict[str, Any]]]:
        """
        将数据分批，确保每批token数不超过限制
        
        Args:
            data_items: 数据项列表
            max_tokens_per_batch: 每批最大token数
            
        Returns:
            分批后的数据列表
        """
        batches = []
        current_batch = []
        current_tokens = 0
        
        for item in data_items:
            content = item.get("summary", "") or item.get("content", "") or item.get("md", "")
            item_tokens = self.token_calculator.count_tokens(content)
            
            # 如果单个项目就超过限制，单独成批
            if item_tokens > max_tokens_per_batch:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
                batches.append([item])
                continue
            
            # 检查添加当前项目是否会超过限制
            if current_tokens + item_tokens > max_tokens_per_batch and current_batch:
                batches.append(current_batch)
                current_batch = [item]
                current_tokens = item_tokens
            else:
                current_batch.append(item)
                current_tokens += item_tokens
        
        # 添加最后一批
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def _extract_batch_information(
        self,
        section_title: str,
        section_points: List[str],
        data_batch: List[Dict[str, Any]],
        company_name: str,
        batch_index: int,
        total_batches: int,
        max_output_tokens: int
    ) -> str:
        """
        从一批数据中提取关键信息
        
        Args:
            section_title: 章节标题
            section_points: 章节要点
            data_batch: 数据批次
            company_name: 公司名称
            batch_index: 当前批次索引
            total_batches: 总批次数
            max_output_tokens: 最大输出token数
            
        Returns:
            提取的关键信息摘要
        """
        # 构建数据内容
        data_content = ""
        for item in data_batch:
            content = item.get("summary", "") or item.get("content", "") or item.get("md", "")
            data_content += f"\\n\\n【数据{item['id']}】{item.get('title', '')}\\n{content}"
        
        # 构建提取提示
        points_text = "\\n".join([f"- {point}" for point in section_points])
        
        system_prompt = f"""你是一个专业的金融数据收集和分析助手。你的任务是从提供的数据中全面收集与特定章节相关的所有有价值信息，包括具体数据、细节和深度分析内容。

**收集目标章节**: {section_title}
**章节要点**:
{points_text}

**信息收集要求**:
1. **全面性收集**: 不仅要提取关键信息摘要，更要收集具体的数据、数字、比例、趋势等细节信息
2. **数据完整性**: 保留所有相关的财务数据、业务指标、时间序列数据、对比数据等
3. **细节保留**: 包含具体的公司名称、产品名称、技术细节、合作伙伴、监管要求等
4. **分析观点**: 收集专家观点、分析师评价、市场预期、风险评估等深度分析内容
5. **时间信息**: 保留具体的时间节点、发展历程、预期时间表等时序信息
6. **引用来源**: 在收集信息时保持数据来源的标识（如【数据X】格式）

**重点收集内容类型**:
- 具体的财务数字和比例数据
- 业务运营的详细指标和KPI
- 技术参数、产品规格、性能数据
- 市场份额、竞争格局的具体数据
- 监管政策的具体条款和影响
- 合作协议的具体内容和条件
- 风险因素的具体描述和量化数据
- 未来规划的具体目标和时间表

**输出格式要求**:
1. 按照信息类型分段组织，但保持流畅的段落形式
2. 每个重要数据点都要包含具体数值和单位
3. 保留原文中的专业术语和技术细节
4. 对于复杂的分析，保留完整的逻辑链条
5. 确保信息的完整性，避免过度简化

**输出长度**: 尽可能详细和完整，不要为了简洁而省略重要细节。目标是为后续报告写作提供充分的素材支撑。"""

        user_prompt = f"""请从以下数据中全面收集与"{section_title}"相关的所有有价值信息：

**收集要求**: 
- 提取所有相关的具体数据、数字、细节信息
- 不要只做高层次总结，要保留具体的业务细节
- 包含所有相关的分析观点和专家评价
- 保持信息的完整性和准确性

**公司**: {company_name}
**处理进度**: 第{batch_index}/{total_batches}批次数据

**数据内容**:
{data_content}

请进行全面的信息收集（注意：要收集具体信息和数据细节，不是简单摘要）："""

        try:
            response = chat_no_tool(
                user_content=user_prompt,
                system_content=system_prompt,
                api_key=self.api_key,
                base_url=self.base_url,
                model=self.model,
                temperature=0.3,
                max_tokens=max_output_tokens
            )
            return response.strip()
        except Exception as e:
            print(f"     ❌ 批次提取失败: {e}")
            raise e
    
    def _create_fallback_summary(self, data_batch: List[Dict[str, Any]]) -> str:
        """
        创建备用摘要（当AI提取失败时使用）
        
        Args:
            data_batch: 数据批次
            
        Returns:
            备用摘要文本
        """
        summaries = []
        for item in data_batch:
            title = item.get("title", "")
            summary = item.get("summary", "") or item.get("content", "")[:200] + "..."
            summaries.append(f"{title}: {summary}")
        
        return "\\n\\n".join(summaries)
    
    def _merge_extracted_summaries(
        self, 
        section_title: str, 
        summaries: List[str], 
        original_count: int
    ) -> str:
        """
        合并多个批次提取的摘要
        
        Args:
            section_title: 章节标题
            summaries: 提取的摘要列表
            original_count: 原始数据数量
            
        Returns:
            合并后的最终摘要
        """
        if not summaries:
            return f"未能从 {original_count} 个数据源中提取到与 '{section_title}' 相关的信息。"
        
        if len(summaries) == 1:
            return summaries[0]
        
        # 多个摘要需要合并
        merged_content = f"基于 {original_count} 个数据源的综合分析：\\n\\n"
        for i, summary in enumerate(summaries, 1):
            merged_content += f"**数据批次 {i}**: {summary}\\n\\n"
        
        return merged_content.strip()


def create_data_id_lookup_function(all_data: List[Dict[str, Any]]) -> callable:
    """
    创建一个通过ID查找数据的函数，供大模型使用
    
    Args:
        all_data: 所有数据的列表
        
    Returns:
        查找函数
    """
    id_to_data = {str(item["id"]): item for item in all_data}
    
    def get_data_by_id(data_id: str) -> Dict[str, Any]:
        """
        根据ID获取数据项
        
        Args:
            data_id: 数据ID
            
        Returns:
            数据项字典，如果找不到则返回空字典
        """
        return id_to_data.get(str(data_id), {})
    
    return get_data_by_id


def extract_data_references_from_text(text: str) -> List[str]:
    """
    从文本中提取数据引用ID
    
    Args:
        text: 包含数据引用的文本
        
    Returns:
        提取的数据ID列表
    """
    import re
    
    # 匹配模式：【数据123】或[数据123]或(数据123)
    patterns = [
        r'【数据(\d+)】',
        r'\\[数据(\d+)\\]',
        r'\\(数据(\d+)\\)',
        r'数据ID[：:](\d+)',
        r'引用数据(\d+)'
    ]
    
    data_ids = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        data_ids.extend(matches)
    
    return list(set(data_ids))  # 去重
