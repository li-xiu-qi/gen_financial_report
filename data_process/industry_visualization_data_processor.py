"""
行业可视化数据处理器
基于 BaseVisualizationProcessor，专门处理行业研报的可视化需求
"""

import os
from typing import Optional, Dict, Any
from .base_visualization_processor import BaseVisualizationProcessor


class IndustryVisualizationDataProcessor(BaseVisualizationProcessor):
    """行业可视化数据处理器，将可视化建议与实际数据结合，生成高质量的行业分析图表"""
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        visualization_output_dir: Optional[str] = None,
        assets_output_dir: Optional[str] = None
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            visualization_output_dir=visualization_output_dir,
            assets_output_dir=assets_output_dir
        )
        
        # 获取项目根目录作为默认基础路径
        project_root = os.path.dirname(os.path.dirname(__file__))
        
        # 配置可视化输出目录（HTML文件）- 优先使用传入参数，否则使用默认值
        self._visualization_output_dir = (
            visualization_output_dir or 
            self._base_visualization_output_dir or 
            project_root
        )
        
        # 配置资产输出目录（PNG和JSON文件）- 优先使用传入参数，否则使用默认值
        self._assets_output_dir = (
            assets_output_dir or 
            self._base_assets_output_dir or 
            os.path.join(project_root, "test_industry_datas", "images")
        )
    
    def get_target_name_field(self) -> str:
        """获取目标名称字段"""
        return "industry_name"
    
    def get_visualization_output_dir(self) -> str:
        """获取可视化输出目录 - 返回配置的HTML输出目录，与js文件夹同级"""
        return self._visualization_output_dir
    
    def get_assets_output_dir(self) -> str:
        """获取资产文件（PNG和JSON）输出目录 - 返回配置的资产输出目录"""
        return self._assets_output_dir
    
    def set_visualization_output_dir(self, output_dir: str) -> None:
        """动态设置可视化输出目录"""
        self._visualization_output_dir = output_dir
    
    def set_assets_output_dir(self, assets_dir: str) -> None:
        """动态设置资产输出目录"""
        self._assets_output_dir = assets_dir
    
    def get_chart_query_context(
        self,
        chart_title: str,
        chart_type: str,
        reason: str,
        target_name: str,
        section: str,
        report_value: str,
        data_content: str
    ) -> str:
        """构建行业图表生成的查询上下文"""
        
        # 根据章节调整生成要求
        section_requirements = {
            "一": "重点展示行业整体发展趋势、规模变化、生命周期阶段判断",
            "二": "突出行业集中度分析、竞争格局变化、头部企业市场份额对比",
            "三": "强调产业链上下游关系、价值链分析、关键环节识别",
            "四": "聚焦政策影响分析、技术演进趋势、外部环境变化",
            "五": "提供情景模拟结果、敏感性分析、关键变量影响测算",
            "六": "展示进入退出壁垒分析、投资策略建议、风险收益评估"
        }
        
        section_focus = section_requirements.get(section, "展示行业相关数据分析")
        
        if "由于数据量较大" in data_content:
            # 分块处理的情况
            chart_query = f"""目标: 为行业研究报告第{section}章节生成{chart_type}图表，展示"{chart_title}"。

行业研报章节: {section}
分析价值: {report_value}
分析目标: {reason}
目标行业: {target_name}
章节重点: {section_focus}

注意：由于数据量较大，以下是关键数据块的概述。请仔细提取其中的数字信息、时间序列数据和行业指标生成准确的专业图表：

{data_content}

重要提示：
1. 优先关注行业规模数据、集中度指标、产业链数据、政策影响指标
2. 确保图表数据的准确性和逻辑性，体现行业发展规律
3. 生成符合行业研报标准的静态图表，适合3年以上情景分析
4. 配色专业，突出行业特征，服务于{report_value}的分析目的
5. 标签完整可见，支持敏感性分析和变量影响展示
6. 重点体现行业生命周期、竞争格局、外部变量等核心分析要素"""
        else:
            # 完整数据处理的情况
            chart_query = f"""目标: 为行业研究报告第{section}章节生成{chart_type}图表，展示"{chart_title}"。

行业研报章节: {section}
分析价值: {report_value}
分析目标: {reason}
目标行业: {target_name}
章节重点: {section_focus}

数据内容:
{data_content}

请生成一个符合行业研报标准的专业图表。要求：
1. 数据真实、准确，体现行业发展特征和规律
2. 图表静态化，适合截图、打印和情景分析展示
3. 配色专业，符合行业研报标准，突出行业特色
4. 重点突出，服务于{report_value}的分析目的
5. 无需鼠标悬浮即可阅读所有信息
6. 支持多时间维度分析，体现行业生命周期和趋势变化
7. 适合敏感性分析和关键变量影响展示"""
        
        return chart_query
    
    def get_incremental_enhancement_system_prompt(self) -> str:
        """获取增量增强的系统提示词"""
        return """你是一个专业的行业分析专家，负责对行业研报图表数据进行增量增强。

重要说明：
- 你将收到一个图表建议和当前数据块的完整内容
- 当前提供的数据只是整个分析中的一部分（第X/Y段）
- 你需要基于这些数据对之前的分析进行增量增强，而不是完全重新生成
- 如果这是第一段数据，请开始初步分析；如果是后续段，请在之前分析基础上进行增强

增量增强要求：
1. 保持行业分析的宏观视角和系统性思维
2. 基于实际数据内容提取关键行业指标、市场数据和发展规律
3. 识别数据中的行业驱动因素、发展趋势和竞争态势
4. 整合新数据与之前分析的结果
5. 提供丰富的细节信息，包括市场规模、集中度、产业链数据等
6. 保留所有重要的定量和定性信息

输出要求：
- 返回增强后的完整数据分析内容
- 包含具体的行业数据、市场指标、竞争格局分析
- 保持行业研究的专业深度和准确性
- 如果是多段处理，要体现数据的累积分析效果"""
    
    def get_incremental_enhancement_user_prompt(
        self,
        suggestion: Dict[str, Any],
        data_content: str,
        current_segment: int,
        total_segments: int,
        previous_enhancement: Optional[str] = None
    ) -> str:
        """获取增量增强的用户提示词"""
        
        # 构建图表信息
        chart_info = f"""图表信息:
标题: {suggestion.get('chart_title', 'N/A')}
类型: {suggestion.get('chart_type', 'N/A')}
目的: {suggestion.get('reason', 'N/A')}
章节: {suggestion.get('section', 'N/A')}
研报价值: {suggestion.get('report_value', 'N/A')}"""

        if current_segment == 1:
            # 第一段数据的处理
            return f"""请对以下行业数据进行初步分析，为行业研报图表生成做准备。

**{chart_info}**

**数据处理进度:** 第{current_segment}/{total_segments}段数据

**数据内容:**
{data_content}

请进行初步的行业数据分析，提取关键信息、市场指标和发展趋势。这是多段数据处理的第一段，请为后续数据整合做好基础。

要求：
1. 提取所有相关的具体行业数据和市场指标
2. 识别行业发展趋势、竞争格局、政策技术影响
3. 分析数据的行业价值和图表展示意义
4. 为后续数据整合准备分析框架"""
        
        else:
            # 后续段数据的增量处理
            return f"""请基于之前的分析结果，整合当前数据段进行增量增强。

**{chart_info}**

**数据处理进度:** 第{current_segment}/{total_segments}段数据

**之前的分析结果:**
{previous_enhancement}

**当前数据段内容:**
{data_content}

请在之前分析基础上进行增量增强：
1. 整合新数据与已有分析结果
2. 更新和补充行业指标、市场数据
3. 保持分析的连贯性和行业逻辑
4. 丰富行业洞察和竞争分析
5. 如果是最后一段，请提供完整的综合分析结果

返回增强后的完整分析内容。"""
