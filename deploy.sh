#!/bin/bash
# ==========================================
# 抖音续火花脚本 - Linux 一键部署脚本
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  抖音续火花脚本 - Linux 部署${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 项目目录（脚本所在目录）
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_DIR"

echo "项目目录: $PROJECT_DIR"
echo ""

# 1. 检查 Python
echo -e "${YELLOW}[1/7] 检查 Python 环境...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON=python3
    echo "Python3 版本: $(python3 --version)"
elif command -v python &> /dev/null; then
    PYTHON=python
    echo "Python 版本: $(python --version)"
else
    echo -e "${RED}错误: 未找到 Python，请先安装 Python 3.8+${NC}"
    exit 1
fi

# 2. 创建虚拟环境
echo ""
echo -e "${YELLOW}[2/7] 创建 Python 虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    $PYTHON -m venv venv
    echo "虚拟环境创建成功"
else
    echo "虚拟环境已存在，跳过"
fi

# 激活虚拟环境
source venv/bin/activate

# 3. 安装依赖
echo ""
echo -e "${YELLOW}[3/7] 安装 Python 依赖...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 4. 安装 Playwright 浏览器
echo ""
echo -e "${YELLOW}[4/7] 安装 Playwright 浏览器...${NC}"
python -m playwright install chromium

# Linux 依赖（针对无头模式）
if command -v apt-get &> /dev/null; then
    echo "检测到 Debian/Ubuntu 系统，安装系统依赖..."
    python -m playwright install-deps chromium 2>/dev/null || true
elif command -v yum &> /dev/null; then
    echo "检测到 CentOS/RHEL 系统，请确保已安装必要的系统库"
    echo "如运行报错请执行: python -m playwright install-deps chromium"
fi

# 5. 初始化配置文件
echo ""
echo -e "${YELLOW}[5/7] 初始化配置文件...${NC}"
if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
    echo "已创建 config.yaml，请修改配置后使用"
else
    echo "config.yaml 已存在，跳过"
fi

# 6. 创建日志目录
echo ""
echo -e "${YELLOW}[6/7] 创建日志目录...${NC}"
mkdir -p logs
mkdir -p browser_data

# 7. 设置脚本权限
echo ""
echo -e "${YELLOW}[7/7] 设置脚本权限...${NC}"
chmod +x run.sh web.sh deploy.sh

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  部署完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "下一步操作："
echo ""
echo "方式一：Web 管理面板（推荐）"
echo "  ./web.sh start          # 启动Web面板"
echo "  ./web.sh status         # 查看状态"
echo "  访问 http://服务器IP:5000"
echo "  默认账号: admin / admin123 （请及时修改！）"
echo ""
echo "方式二：命令行手动配置"
echo "  编辑配置文件: vim config.yaml"
echo "   - 填入抖音 Cookie"
echo "   - 添加好友列表"
echo "   - 配置消息 API"
echo "   - 配置邮箱通知（可选）"
echo ""
echo "测试运行："
echo "   source venv/bin/activate"
echo "   python main.py --test-message   # 测试消息API"
echo "   python main.py --check-login    # 检查登录状态"
echo "   python main.py                  # 正式运行"
echo ""
echo "设置定时任务（每天凌晨1点执行）："
echo "   crontab -e"
echo "   添加一行: 0 1 * * * cd $PROJECT_DIR && ./run.sh >> logs/cron.log 2>&1"
echo ""
echo "详细说明请查看 README.md"
