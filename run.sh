#!/bin/bash
# ==========================================
# 抖音续火花脚本 - 运行入口
# 供 crontab 调用
# ==========================================

# 项目目录（脚本所在目录）
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 运行主程序
python main.py -c config.yaml

# 记录退出码
EXIT_CODE=$?

# 输出执行时间
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 执行完成，退出码: $EXIT_CODE"

exit $EXIT_CODE
