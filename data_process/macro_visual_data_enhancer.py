"""
宏观可视化数据增强器
基于 BaseVisualDataEnhancer，专门处理宏观经济/策略报告的可视化需求
"""

import json
from typing import List, Dict, Any, Optional
from .base_visual_data_enhancer import BaseVisualDataEnhancer


class MacroVisualDataEnhancer(BaseVisualDataEnhancer):
    """宏观可视化数据增强器"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str
    ):
        super().__init__(api_key, base_url, model)
    
    def get_target_name_field(self) -> str:
        """获取目标名称字段"""
        return "macro_theme"
    
    def get_outline_chapters(self) -> List[str]:
        """获取大纲章节标题列表"""
        if not self.outline_data:
            # 默认宏观章节（兜底方案）
            return [
                "一、宏观经济环境分析",
                "二、政策环境与监管动态",
                "三、市场趋势与机会识别",
                "四、风险评估与情景分析",
                "五、投资策略与配置建议",
                "六、总结与展望"
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
        """获取宏观可视化分析的系统提示词"""
        return """你是一名专业的宏观经济分析师，擅长数据可视化。你的任务是从宏观经济数据中识别适合在宏观经济/策略报告中展示的可视化内容。

**重要提醒**: 用户会指定一个宏观主题，你必须确保所有的可视化建议都以该主题为分析中心，突出宏观经济变量间的关系和政策效果。

**宏观经济/策略报告章节框架与可视化重点**：

1. **一、宏观经济核心指标分析**
   - 目标主题相关的GDP增长趋势图（总量与结构）
   - 目标主题影响下的CPI/PPI变化趋势对比图
   - 相关利率变化趋势图（央行政策利率、市场利率）
   - 汇率波动与目标主题关联分析图
   - 货币供应量M0/M1/M2增速变化图
   - 就业与失业率相关指标趋势图

2. **二、政策措施与效果解读**
   - 目标主题相关政策发布时间轴与影响度分析图
   - 政策实施前后关键指标对比图
   - 不同政策工具效果评估对比图
   - 政策传导机制可视化图表
   - 政策预期与实际效果偏差分析图
   - 多部门政策协调效果评估图

3. **三、区域对比与政策联动分析**
   - 不同地区目标主题相关指标对比图
   - 区域间政策联动效应分析图
   - 重点城市/省份相关数据热力图
   - 区域发展不平衡指数变化图
   - 政策扩散效应地理分布图
   - 区域间协调发展指标对比图

4. **四、全球视野与国际比较**
   - 中国与主要经济体相关指标对比图
   - 全球经济周期与中国经济关联分析图
   - 国际政策外溢效应分析图（如美联储政策影响）
   - 全球供应链与贸易数据可视化图
   - 国际资本流动与汇率联动分析图
   - 中国在全球经济中地位变化图

5. **五、风险预警与敏感性分析**
   - 宏观经济风险指标监测仪表盘
   - 关键变量敏感性分析热力图
   - "灰犀牛"事件风险评估雷达图
   - 系统性风险传导路径图
   - 压力测试情景分析结果图
   - 风险预警信号灯系统图

6. **六、政策模拟与情景分析**
   - 不同政策情景下关键指标预测图
   - 政策工具组合效果模拟对比图
   - 外部冲击情景模拟结果图
   - 政策边际效应递减分析图
   - 最优政策路径选择分析图
   - 长期结构性改革效果预测图

**输出要求**：
请以JSON数组格式输出，每个建议包含：
- visualization_type: 可视化类型 (line/bar/pie/donut/scatter/heatmap/radar/area/combo/gauge)
- chart_title: 符合宏观报告专业性的图表标题（必须包含目标主题关键词）
- data_ids: 相关的数据ID列表（**重要：必须使用上述数据摘要中实际存在的ID，不得虚构**）
- reason: 选择这些数据的理由及其在宏观报告框架中的重要性（必须明确提及目标主题）
- priority: 优先级 (high/medium/low)
- section: 建议放在报告哪个章节（一、二、三、四、五、六）
- report_value: 这个图表对宏观报告的价值（核心指标追踪/政策效果评估/区域联动分析/国际比较/风险预警/情景模拟）
- analysis_dimension: 分析维度（时间趋势/结构对比/关系分析/区域分布/敏感性测试/政策传导）

**关键约束**：
1. data_ids 字段中的所有ID必须来自上述提供的数据摘要，不得创造或虚构任何ID
2. 如果某个可视化概念缺乏对应的实际数据，请不要强行生成该建议
3. 优先选择数据质量高、内容丰富的数据项进行可视化建议
4. 重点关注宏观变量间的相互关系和政策传导机制"""
    
    def get_analysis_user_prompt(
        self, 
        target_name: str, 
        batch_index: int, 
        total_batches: int, 
        data_summaries: List[Dict[str, Any]]
    ) -> str:
        """获取宏观可视化分析的用户提示词"""
        return f"""请分析以下数据摘要，识别适合进行可视化的宏观经济数据组合。
        
**重要提醒**: 本次分析的宏观主题是 **{target_name}**，请确保所有可视化建议都以该主题为中心进行分析。

**宏观主题**: {target_name}
**批次**: {batch_index}/{total_batches}

**数据摘要列表**：
{json.dumps(data_summaries, ensure_ascii=False, indent=2)}

**重要约束**：
1. 在输出可视化建议时，data_ids 字段中的每一个ID都必须是上述数据摘要列表中实际存在的ID
2. 请仔细检查每个数据项的ID（在数据摘要的"id"字段中），确保引用的ID准确无误
3. 不得创造、虚构或猜测任何数据ID，即使是为了完善可视化建议
4. 如果缺乏某类数据，请根据现有数据调整可视化建议，而不是虚构数据ID

请仔细分析这批数据，识别适合在宏观经济/策略报告各章节中展示的可视化内容。
        
**核心要求**: 所有分析必须以 **{target_name}** 为中心，重点突出宏观经济变量间的关系、政策效果和风险预警。

重点关注：

**一、宏观经济核心指标分析**
   - 与{target_name}相关的GDP、CPI、利率、汇率等核心指标数据
   - {target_name}对货币供应量、就业等指标的影响数据
   - 宏观经济周期与{target_name}的关联数据

**二、政策措施与效果解读**
   - {target_name}相关的政策发布时间、内容和影响数据
   - 政策实施前后关键指标变化的对比数据
   - 不同政策工具在{target_name}领域的效果评估数据
   - 政策传导机制和预期效果的量化数据

**三、区域对比与政策联动分析**
   - 不同地区{target_name}相关指标的对比数据
   - 区域间政策联动和扩散效应数据
   - 重点城市/省份{target_name}发展数据
   - 区域发展不平衡的量化指标

**四、全球视野与国际比较**
   - 中国与其他国家{target_name}相关指标对比数据
   - 国际政策对中国{target_name}的外溢效应数据
   - 全球供应链、贸易与{target_name}的关联数据
   - 国际资本流动对{target_name}的影响数据

**五、风险预警与敏感性分析**
   - {target_name}相关的风险指标和预警信号数据
   - 关键变量对{target_name}的敏感性分析数据
   - 潜在"灰犀牛"事件的识别和评估数据
   - 系统性风险传导路径相关数据

**六、政策模拟与情景分析**
   - {target_name}不同政策情景的模拟数据
   - 外部冲击对{target_name}影响的测算数据
   - 政策边际效应和最优路径相关数据
   - 长期结构性改革效果预测数据

请针对性输出JSON格式的可视化建议，确保每个建议都能为宏观报告相应章节增加实质性的分析价值，并且明确体现{target_name}的宏观经济影响和政策意义："""
    
    def get_incremental_enhancement_system_prompt(self) -> str:
        """获取增量增强的系统提示词"""
        return """你是一个专业的宏观经济分析专家，负责对宏观经济/策略报告的可视化建议进行增量增强。

重要说明：
- 你将收到一个可视化建议和当前数据块的完整内容
- 当前提供的数据只是整个分析中的一部分（第X/Y个）
- 你需要基于这些数据对建议进行增量增强，而不是完全重新生成
- 如果这是第一个数据块，请开始初步分析；如果是后续块，请在之前分析基础上进行增强

增量增强要求：
1. 保持宏观分析的系统性和前瞻性
2. 基于实际数据内容提取关键经济指标、政策数据和市场信号
3. 识别数据中的经济规律、政策效果和风险因素
4. 整合新数据与之前分析的结果
5. 提供丰富的细节信息，包括具体数值、政策时间点、影响幅度等
6. 保留所有重要的宏观数据和政策洞察

输出要求：
- 返回增强后的完整数据分析内容
- 包含具体的宏观数据、政策效果、风险评估分析
- 保持宏观研究的专业深度和准确性
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
            return f"""请对以下宏观经济数据进行初步分析，为宏观策略报告图表生成做准备。

**{suggestion_info}**

**数据处理进度:** 第{current_index}/{total_count}个数据块

**数据内容:**
{data_content}

请进行初步的宏观数据分析，提取关键经济指标、政策信息和市场信号。这是多段数据处理的第一段，请为后续数据整合做好基础。

要求：
1. 提取所有相关的宏观经济数据和政策信息
2. 识别经济周期、政策效果、市场风险信号
3. 分析数据的宏观价值和策略意义
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
2. 更新和补充宏观指标、政策效果
3. 保持分析的连贯性和宏观逻辑
4. 丰富经济洞察和政策分析
5. 如果是最后一段，请提供完整的综合分析结果

返回增强后的完整分析内容。"""
