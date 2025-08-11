"""
公司可视化数据增强器（重构版）
基于 BaseVisualDataEnhancer，专门处理公司研报的可视化需求
"""

import json
from typing import List, Dict, Any, Optional
from .base_visual_data_enhancer import BaseVisualDataEnhancer


class CompanyVisualDataEnhancer(BaseVisualDataEnhancer):
    """公司可视化数据增强器"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        outline_data: Optional[Dict[str, Any]] = None
    ):
        super().__init__(api_key, base_url, model)
        self.outline_data = outline_data
        
    def set_outline_data(self, outline_data: Dict[str, Any]) -> None:
        """设置大纲数据"""
        self.outline_data = outline_data
        
    def get_outline_chapters(self) -> List[str]:
        """获取大纲章节标题列表"""
        if not self.outline_data:
            # 默认章节（兜底方案）
            return [
                "一、投资摘要与核心观点",
                "二、公司基本面与行业地位分析",  
                "三、三大会计报表与财务比率分析",
                "四、估值与预测模型",
                "五、公司治理结构与发展战略",
                "六、投资建议与风险提醒"
            ]
        
        # 从大纲数据中提取章节标题
        chapters = []
        report_outline = self.outline_data.get("reportOutline", [])
        for section in report_outline:
            title = section.get("title", "")
            if title:
                chapters.append(title)
        
        return chapters if chapters else self.get_outline_chapters()  # 递归调用默认方案
    
    def get_target_name_field(self) -> str:
        """获取目标名称字段"""
        return "company_name"
    
    def get_analysis_system_prompt(self) -> str:
        """获取公司可视化分析的系统提示词"""
        return """你是一名专业的卖方研究分析师，擅长数据可视化。你的任务是从数据中识别适合在卖方研究报告中展示的可视化内容。

**重要提醒**: 用户会指定一个目标公司，你必须确保所有的可视化建议都以该公司为分析中心，突出该公司的特色和表现。

**研报章节与可视化重点**：

**重要说明**: 用户会在具体的用户提示词中提供实际的章节标题。请严格按照用户提供的实际章节标题输出section字段，不要使用下面的示例章节名称。

**典型可视化内容**：
- 投资摘要章节: 目标公司历史股价与估值走势图、主要财务指标预测图表、盈利预测对比图、投资评级分布统计图
- 基本面分析章节: 公司在行业中的市场份额饼图、与主要竞争对手财务指标对比柱状图、业务收入构成及变化趋势图、股权结构饼图、核心竞争力雷达图
- 财务分析章节: 收入与利润增长趋势图、毛利率/净利率历史趋势对比图、各项财务指标历史趋势图、与同业财务指标对比图、ROE分解分析图、现金流构成分析图、债务结构分析图
- 估值分析章节: 与可比公司估值散点图、历史估值区间分布图、敏感性分析热力图、不同估值方法结果对比图、目标价区间测算图
- 风险分析章节: 风险因素重要性评估雷达图、面临的行业风险趋势图、财务风险指标变化图

**输出要求**：
请以JSON数组格式输出，每个建议包含：
- visualization_type: 可视化类型 (line/bar/pie/donut/scatter/heatmap/radar)
- chart_title: 符合研报专业性的图表标题（必须包含目标公司名称）
- data_ids: 相关的数据ID列表（**重要：必须使用上述数据摘要中实际存在的ID，不得虚构**）
- reason: 选择这些数据的理由及其在研报框架中的重要性（必须明确提及目标公司）
- priority: 优先级 (high/medium/low)
- section: 建议放在研报哪个章节（**重要：必须使用用户提示词中提供的实际章节标题**）
- report_value: 这个图表对研报的价值（投资逻辑支撑/竞争分析/基本面展示/财务证据/估值依据/风险提示）

**关键约束**：
1. data_ids 字段中的所有ID必须来自上述提供的数据摘要，不得创造或虚构任何ID
2. 如果某个可视化概念缺乏对应的实际数据，请不要强行生成该建议
3. 优先选择数据质量高、内容丰富的数据项进行可视化建议
4. **section字段必须严格使用用户提示词中提供的实际章节标题，不得自行创造章节名称**"""
    
    def get_analysis_user_prompt(
        self, 
        target_name: str, 
        batch_index: int, 
        total_batches: int, 
        data_summaries: List[Dict[str, Any]]
    ) -> str:
        """获取公司可视化分析的用户提示词"""
        
        # 获取实际的章节标题
        chapters = self.get_outline_chapters()
        chapter_list = "\n".join([f"- {chapter}" for chapter in chapters])
        
        return f"""请分析以下数据摘要，识别适合进行可视化的数据组合。
        
**重要提醒**: 本次分析的目标公司是 **{target_name}**，请确保所有可视化建议都以该公司为中心进行分析和比较。

**目标公司**: {target_name}
**批次**: {batch_index}/{total_batches}

**数据摘要列表**：
{json.dumps(data_summaries, ensure_ascii=False, indent=2)}

**重要约束**：
1. 在输出可视化建议时，data_ids 字段中的每一个ID都必须是上述数据摘要列表中实际存在的ID
2. 请仔细检查每个数据项的ID（在数据摘要的"id"字段中），确保引用的ID准确无误
3. 不得创造、虚构或猜测任何数据ID，即使是为了完善可视化建议
4. 如果缺乏某类数据，请根据现有数据调整可视化建议，而不是虚构数据ID

请仔细分析这批数据，识别适合在卖方研报各章节中展示的可视化内容。
        
**核心要求**: 所有分析必须以 **{target_name}** 为中心，重点突出该公司在各个维度的表现和特征。

**可用的研报章节** (请在section字段中使用以下确切的章节标题):
{chapter_list}

**重要提醒**: 在section字段中，请严格使用上述列出的章节标题，确保与实际报告大纲一致。

重点关注以下内容：
- 投资摘要相关: {target_name}的盈利预测与业绩趋势数据、估值水平与目标价相关数据、投资评级变化历史
- 基本面分析相关: {target_name}在行业中的市场份额和排名数据、与主要竞争对手的多维度对比数据、业务结构和收入构成数据、公司治理和股权结构相关数据
- 财务分析相关: {target_name}详细的财务指标历史数据、与同业财务指标对比数据、现金流和运营效率相关数据、盈利能力和财务质量数据
- 估值分析相关: {target_name}与可比公司估值数据、不同估值方法的测算数据、敏感性分析相关数据、目标价测算相关数据
- 治理战略相关: {target_name}的研发投入与技术实力相关数据、核心竞争优势量化数据、管理层背景和治理结构数据
- 风险分析相关: {target_name}面临的各类风险因素的量化评估数据、风险指标的历史变化数据

请针对性输出JSON格式的可视化建议，确保每个建议都能为研报相应章节增加实质性的分析价值，并且明确体现{target_name}的特色和表现："""
    
    def get_incremental_enhancement_system_prompt(self) -> str:
        """获取增量增强的系统提示词"""
        return """你是一个专业的公司分析专家，负责对公司研报的可视化建议进行增量增强。

重要说明：
- 你将收到一个可视化建议和当前数据块的完整内容
- 当前提供的数据只是整个分析中的一部分（第X/Y个）
- 你需要基于这些数据对建议进行增量增强，而不是完全重新生成
- 如果这是第一个数据块，请开始初步分析；如果是后续块，请在之前分析基础上进行增强

增量增强要求：
1. 保持公司分析的专业性和投资价值
2. 基于实际数据内容提取关键财务指标、业务数据和竞争信息
3. 识别数据中的投资亮点、风险因素和业绩趋势
4. 整合新数据与之前分析的结果
5. 提供丰富的细节信息，包括具体数值、同比增长、行业对比等
6. 保留所有重要的财务数据和业务洞察

输出要求：
- 返回增强后的完整数据分析内容
- 包含具体的财务数据、业务指标、竞争优势分析
- 保持投资研究的专业深度和准确性
- 如果是多段处理，要体现数据的累积分析效果"""
    
    def get_incremental_enhancement_user_prompt(
        self,
        suggestion: Dict[str, Any],
        data_content: str,
        current_index: int,
        total_count: int
    ) -> str:
        """获取增量增强的用户提示词"""
        
        # 构建建议信息
        suggestion_info = f"""可视化建议:
标题: {suggestion.get('chart_title', 'N/A')}
类型: {suggestion.get('chart_type', 'N/A')}
目的: {suggestion.get('reason', 'N/A')}
章节: {suggestion.get('section', 'N/A')}
研报价值: {suggestion.get('report_value', 'N/A')}"""

        if current_index == 1:
            # 第一段数据的处理
            return f"""请对以下公司数据进行初步分析，为投资研报图表生成做准备。

**{suggestion_info}**

**数据处理进度:** 第{current_index}/{total_count}个数据块

**数据内容:**
{data_content}

请进行初步的公司数据分析，提取关键财务指标、业务数据和投资要点。这是多段数据处理的第一段，请为后续数据整合做好基础。

要求：
1. 提取所有相关的财务数据和业务指标
2. 识别公司业绩趋势、竞争优势、风险因素
3. 分析数据的投资价值和研报意义
4. 为后续数据整合准备分析框架"""
        
        else:
            # 后续段数据的增量处理 - 需要之前的分析结果
            return f"""请基于之前的分析结果，整合当前数据段进行增量增强。

**{suggestion_info}**

**数据处理进度:** 第{current_index}/{total_count}个数据块

**当前数据段内容:**
{data_content}

请在之前分析基础上进行增量增强：
1. 整合新数据与已有分析结果
2. 更新和补充财务指标、业务数据
3. 保持分析的连贯性和投资逻辑
4. 丰富投资亮点和风险分析
5. 如果是最后一段，请提供完整的综合分析结果

返回增强后的完整分析内容。"""
