"""
行业可视化数据增强器
基于 BaseVisualDataEnhancer，专门分析行业数据并识别适合可视化的数据组合
"""

import json
from typing import List, Dict, Any, Optional
from .base_visual_data_enhancer import BaseVisualDataEnhancer


class IndustryVisualDataEnhancer(BaseVisualDataEnhancer):
    """行业可视化数据增强器"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str
    ):
        super().__init__(api_key, base_url, model)
    
    def get_target_name_field(self) -> str:
        """获取目标名称字段"""
        return "industry_name"
    
    def get_outline_chapters(self) -> List[str]:
        """获取大纲章节标题列表"""
        if not self.outline_data:
            # 默认行业章节（兜底方案）
            return [
                "一、行业概述与发展现状",
                "二、市场规模与增长趋势",
                "三、竞争格局与重点企业分析",
                "四、产业链分析与上下游关系",
                "五、政策环境与技术发展",
                "六、投资机会与风险提示"
            ]
        
        # 从大纲数据中提取章节标题
        chapters = []
        report_outline = self.outline_data.get("reportOutline", [])
        for section in report_outline:
            title = section.get("title", "")
            if title:
                chapters.append(title)
        
        return chapters if chapters else self.get_outline_chapters()  # 递归调用默认方案
    
    def get_analysis_system_prompt(self) -> str:
        """获取行业可视化分析的系统提示词"""
        return """你是一名专业的行业研究分析师，擅长数据可视化。你的任务是从行业数据中识别适合在行业研究报告中展示的可视化内容。

**重要提醒**: 用户会指定一个目标行业，你必须确保所有的可视化建议都以该行业为分析中心，突出该行业的特征和投资价值。

**行业研报章节框架与可视化重点**：

1. **一、行业概况与发展趋势**
   - 目标行业规模历史变化趋势图（产值、产量、市场规模等）
   - 目标行业生命周期阶段判断图
   - 目标行业增长率与GDP增长率对比图
   - 目标行业细分市场结构占比变化图
   - 目标行业景气度指数变化图

2. **二、竞争格局与集中度分析**
   - 目标行业集中度变化趋势图（CR4、CR8、HHI指数等）
   - 目标行业头部企业市场份额对比饼图/柱状图
   - 目标行业企业梯队分布图
   - 目标行业进入退出企业数量变化图
   - 目标行业不同规模企业数量分布图

3. **三、产业链与价值链分析**
   - 目标行业产业链全景图
   - 目标行业上下游议价能力对比图
   - 目标行业价值链各环节利润分布图
   - 目标行业关键原材料价格影响分析图
   - 目标行业产业链各环节集中度对比图

4. **四、政策环境与技术演进**
   - 影响目标行业的相关政策时间轴与影响度分析图
   - 目标行业技术演进路径图
   - 目标行业研发投入强度对比图
   - 目标行业专利申请趋势图
   - 目标行业政策支持力度量化分析图

5. **五、情景分析与敏感性测试**
   - 目标行业不同情景下规模预测图
   - 目标行业关键变量敏感性分析热力图
   - 目标行业乐观/中性/悲观情景对比图
   - 目标行业关键风险因素影响度分析图
   - 目标行业外部冲击模拟结果图

6. **六、投资策略与风险评估**
   - 目标行业投资价值评估雷达图
   - 目标行业进入时机与退出策略分析图
   - 目标行业风险收益散点图
   - 目标行业投资回报期分析图
   - 目标行业关键成功因素权重分析图

**输出要求**：
请以JSON数组格式输出，每个建议包含：
- visualization_type: 可视化类型 (line/bar/pie/donut/scatter/heatmap/radar/area/combo)
- chart_title: 符合行业研报专业性的图表标题（必须包含目标行业名称）
- data_ids: 相关的数据ID列表
- reason: 选择这些数据的理由及其在行业研报框架中的重要性（必须明确提及目标行业）
- priority: 优先级 (high/medium/low)
- section: 建议放在研报哪个章节（一、二、三、四、五、六）
- report_value: 这个图表对行业研报的价值（发展趋势分析/竞争格局洞察/产业链分析/政策技术影响/情景预测/投资决策支持）
- analysis_dimension: 分析维度（时间趋势/结构对比/关系分析/敏感性测试/综合评估）"""
    
    def get_analysis_user_prompt(
        self, 
        target_name: str, 
        batch_index: int, 
        total_batches: int, 
        data_summaries: List[Dict[str, Any]]
    ) -> str:
        """获取行业可视化分析的用户提示词"""
        
        # 获取实际的章节标题
        chapters = self.get_outline_chapters()
        chapter_list = "\n".join([f"- {chapter}" for chapter in chapters])
        
        return f"""请分析以下数据摘要，识别适合进行可视化的行业数据组合。

**重要提醒**: 本次分析的目标行业是 **{target_name}**，请确保所有可视化建议都以该行业为中心进行分析。

**目标行业**: {target_name}
**批次**: {batch_index}/{total_batches}

**数据摘要列表**：
{json.dumps(data_summaries, ensure_ascii=False, indent=2)}

**重要约束**：
1. 在输出可视化建议时，data_ids 字段中的每一个ID都必须是上述数据摘要列表中实际存在的ID
2. 请仔细检查每个数据项的ID（在数据摘要的"id"字段中），确保引用的ID准确无误
3. 不得创造、虚构或猜测任何数据ID，即使是为了完善可视化建议
4. 如果缺乏某类数据，请根据现有数据调整可视化建议，而不是虚构数据ID

请仔细分析这批数据，识别适合在行业研报各章节中展示的可视化内容。
        
**核心要求**: 所有分析必须以 **{target_name}** 为中心，重点突出该行业的发展趋势和投资价值。

**可用的研报章节** (请在section字段中使用以下确切的章节标题):
{chapter_list}

**重要提醒**: 在section字段中，请严格使用上述列出的章节标题，确保与实际报告大纲一致。

重点关注以下内容：
- 市场规模与增长: {target_name}的市场规模历史数据、增长趋势预测数据、细分市场结构数据
- 竞争格局分析: {target_name}主要参与企业的市场份额数据、财务指标对比数据、竞争地位变化数据
- 产业链分析: {target_name}上下游关系数据、成本结构分析数据、供应链风险评估数据
- 政策技术环境: 相关政策影响评估数据、技术发展趋势数据、创新投入数据
- 投资机会评估: {target_name}投资价值评估数据、风险因素量化数据、未来机会预测数据

请针对性输出JSON格式的可视化建议，确保每个建议都能为行业研报相应章节增加实质性的分析价值，并且明确体现{target_name}的行业特色和发展前景："""
    
    def get_incremental_enhancement_system_prompt(self) -> str:
        """获取增量增强的系统提示词"""
        return """你是一个专业的行业分析专家，负责对行业研报的可视化建议进行增量增强。

重要说明：
- 你将收到一个可视化建议和当前数据块的完整内容
- 当前提供的数据只是整个分析中的一部分（第X/Y个）
- 你需要基于这些数据对建议进行增量增强，而不是完全重新生成
- 如果这是第一个数据块，请开始初步分析；如果是后续块，请在之前分析基础上进行增强

增量增强要求：
1. 保持行业分析的宏观视角和系统性
2. 基于实际数据内容提取关键行业指标、市场数据和发展趋势
3. 识别数据中的行业驱动因素、竞争态势和发展机遇
4. 整合新数据与之前分析的结果
5. 提供丰富的细节信息，包括市场规模、增长率、份额分布等
6. 保留所有重要的行业数据和洞察

输出要求：
- 返回增强后的完整数据分析内容
- 包含具体的行业数据、市场指标、竞争格局分析
- 保持行业研究的专业深度和准确性
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
            return f"""请对以下行业数据进行初步分析，为行业研报图表生成做准备。

**{suggestion_info}**

**数据处理进度:** 第{current_index}/{total_count}个数据块

**数据内容:**
{data_content}

请进行初步的行业数据分析，提取关键市场指标、竞争数据和发展趋势。这是多段数据处理的第一段，请为后续数据整合做好基础。

要求：
1. 提取所有相关的行业数据和市场指标
2. 识别行业发展趋势、竞争格局、政策影响
3. 分析数据的行业价值和研报意义
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
2. 更新和补充行业指标、市场数据
3. 保持分析的连贯性和行业逻辑
4. 丰富行业洞察和竞争分析
5. 如果是最后一段，请提供完整的综合分析结果

返回增强后的完整分析内容。"""
