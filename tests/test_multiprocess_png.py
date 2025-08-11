#!/usr/bin/env python3
"""
测试多进程PNG生成性能
"""

import time
import multiprocessing
from data_process.base_visualization_processor import _process_png_task

def test_single_png_generation():
    """测试单个PNG生成"""
    print("🧪 测试单个PNG生成...")
    
    # 简单的HTML内容
    test_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>测试图表</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.2/dist/echarts.min.js"></script>
    </head>
    <body>
        <div id="container" style="width: 800px; height: 600px;"></div>
        <script>
            var chart = echarts.init(document.getElementById('container'));
            var option = {
                title: { text: '测试柱状图' },
                xAxis: { type: 'category', data: ['A', 'B', 'C', 'D'] },
                yAxis: { type: 'value' },
                series: [{
                    data: [120, 200, 150, 80],
                    type: 'bar'
                }]
            };
            chart.setOption(option);
        </script>
    </body>
    </html>
    """
    
    # 创建临时HTML文件
    import os
    html_path = "test_chart.html"
    png_path = "test_chart.png"
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(test_html)
    
    # 测试PNG生成
    task_data = {
        "html_path": html_path,
        "png_path": png_path,
        "chart_title": "测试图表"
    }
    
    start_time = time.time()
    result = _process_png_task(task_data)
    end_time = time.time()
    
    print(f"   结果: {result}")
    print(f"   耗时: {end_time - start_time:.2f}秒")
    
    # 清理文件
    try:
        os.remove(html_path)
        if os.path.exists(png_path):
            print(f"   ✅ PNG文件生成成功: {png_path}")
            print(f"   📏 文件大小: {os.path.getsize(png_path)} 字节")
            # os.remove(png_path)  # 保留PNG文件以便查看
        else:
            print(f"   ❌ PNG文件未生成")
    except Exception as e:
        print(f"   ⚠️ 清理文件时出错: {e}")

def test_multiprocess_performance():
    """测试多进程性能"""
    print(f"\n🚀 测试多进程PNG生成性能...")
    
    total_cores = multiprocessing.cpu_count()
    worker_cores = max(1, total_cores - 2)
    
    print(f"   系统总核心数: {total_cores}")
    print(f"   PNG生成进程数: {worker_cores}")
    
    # 创建多个测试任务
    task_count = worker_cores * 2  # 创建2倍于进程数的任务
    print(f"   测试任务数: {task_count}")
    
    # 这里可以扩展更复杂的性能测试...

if __name__ == "__main__":
    print("🧪 开始PNG生成测试...")
    print("=" * 50)
    
    test_single_png_generation()
    test_multiprocess_performance()
    
    print("\n✅ 测试完成！")
