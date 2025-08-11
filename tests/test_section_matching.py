#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from unified_report_generator import UnifiedReportGenerator
import json

def test_section_matching():
    """测试章节智能匹配"""
    
    # 创建报告生成器
    generator = UnifiedReportGenerator.from_env(report_type='company')
    
    # 模拟大纲章节
    outline_sections = [
        '一、投资摘要与核心观点',
        '二、公司基本面分析：AI解决方案提供商',
        '三、财务分析与预测',
        '四、估值分析与投资建议',
        '五、风险因素分析'
    ]
    
    # 测试图表章节匹配
    chart_sections = [
        '四、估值与预测模型',
        '二、公司基本面与行业地位分析',
        '三、三大会计报表与财务比率分析',
        '一、投资摘要与核心观点'
    ]
    
    print('章节匹配测试:')
    print('=' * 60)
    
    for chart_section in chart_sections:
        matched = generator.data_processor._smart_section_match(chart_section, outline_sections)
        print(f'图表章节: "{chart_section}"')
        print(f'匹配结果: "{matched}"')
        print(f'匹配成功: {"✅" if matched else "❌"}')
        print('-' * 60)

if __name__ == "__main__":
    test_section_matching()
