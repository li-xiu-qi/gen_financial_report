#!/bin/bash
# Ubuntu/Linux 一键运行 quick_run_examples.py 脚本

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境（如有）
# source venv/bin/activate

# 检查 .env 文件
if [ ! -f .env ]; then
  echo "⚠️ 未找到 .env 文件，请先配置 API 密钥等环境变量！"
fi

# 运行 quick_run_examples.py
python3 quick_run_examples.py
