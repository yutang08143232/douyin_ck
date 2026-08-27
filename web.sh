#!/bin/bash
# 启动Web管理面板
# 用法: ./web.sh start|stop|restart|status

APP_NAME="douyin_spark_web"
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PID_FILE="$APP_DIR/logs/web.pid"
LOG_FILE="$APP_DIR/logs/web.log"

mkdir -p "$APP_DIR/logs"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "服务已在运行中 (PID: $PID)"
            return 1
        else
            rm -f "$PID_FILE"
        fi
    fi

    echo "启动Web管理面板..."
    source "$VENV_DIR/bin/activate"
    nohup python -m web.app -c config.yaml > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2

    if kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "启动成功! PID: $(cat "$PID_FILE")"
        echo "访问地址: http://0.0.0.0:5000"
    else
        echo "启动失败，请查看日志: $LOG_FILE"
        return 1
    fi
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "服务未运行"
        return 1
    fi

    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "停止服务 (PID: $PID)..."
        kill "$PID"
        sleep 2
        if kill -0 "$PID" 2>/dev/null; then
            echo "强制停止..."
            kill -9 "$PID"
        fi
        echo "已停止"
    else
        echo "服务未运行"
    fi
    rm -f "$PID_FILE"
}

restart() {
    stop
    sleep 1
    start
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "服务运行中 (PID: $PID)"
            return 0
        else
            echo "服务已停止（PID文件存在但进程不存在）"
            return 1
        fi
    else
        echo "服务未运行"
        return 1
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
