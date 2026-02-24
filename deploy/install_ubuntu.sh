#!/bin/bash
# YI-CORE OS - Ubuntu 本地物理节点部署引导
set -e

echo "=========================================="
echo "🚀 YI-CORE 物理降临协议（Ubuntu神舟）"
echo "=========================================="

echo "[1/4] 安装底层物理环境..."
sudo apt-update
sudo apt install -y python3 python3-venv python3-pip git

echo "[2/4] 初始化神经沙盒 (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt

echo "[3/4] 拷贝神权护身符 (.env)..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️ 警告：已为您生成纯净的 .env 文件。"
    echo "请执行 'nano .env' 填入您的 OpenRouter Key, TG Token 和 本地局域网代理 Proxy 端口！"
fi

echo "[4/4] 下放守护进程权限与开机驻留引导..."
echo "请确保您已经填好了 .env！如果您确认无误，请按照以下几句天规在终端执行以获得深海永生："
echo ""
echo "1. 编辑守护进程配置路径："
echo "   sudo nano deploy/yicore.service"
echo "   (把里面的 User=xxx 和 WorkingDirectory=xxx 换成您存放该代码夹的实际地址)"
echo ""
echo "2. 烙印至系统内核："
echo "   sudo cp deploy/yicore.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable yicore.service"
echo "   sudo systemctl start yicore.service"
echo ""
echo "🔥 物理降落完毕。输入 'sudo systemctl status yicore.service' 或直接点开手机里的 Telegram 验收奇迹吧！"
