"""
Web管理面板 - Flask后端
提供配置管理、好友管理、任务触发、日志查看等API
"""
import os
import sys
import threading
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory

# 将项目根目录加入路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.config_loader import Config
from src.cookie_manager import CookieManager
from src.message_provider import create_message_provider
from src.email_notifier import create_email_notifier
import yaml

logger = logging.getLogger("web")


def create_app(config_path: str = "config.yaml") -> Flask:
    """创建Flask应用"""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # 加载配置
    config = Config(config_path)
    cookie_mgr = CookieManager(config_path)

    # 应用配置
    app.secret_key = config.get("web.secret_key", "douyin-spark-secret")
    app.config["CONFIG_PATH"] = config_path
    app.config["CONFIG"] = config

    # 发送任务状态（用于异步发送）
    send_status = {
        "running": False,
        "progress": 0,
        "total": 0,
        "results": [],
        "start_time": None,
        "end_time": None,
    }

    # ========== 工具函数 ==========

    def login_required(f):
        """登录验证装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get("logged_in"):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "未登录"}), 401
                return redirect(url_for("login_page"))
            return f(*args, **kwargs)
        return decorated_function

    def save_config(new_config: dict) -> bool:
        """保存配置到文件"""
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            # 重新加载配置
            config.load()
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def get_config_dict() -> dict:
        """获取完整配置字典"""
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    # ========== 页面路由 ==========

    @app.route("/login", methods=["GET"])
    def login_page():
        """登录页面"""
        if session.get("logged_in"):
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/api/login", methods=["POST"])
    def api_login():
        """登录API"""
        data = request.get_json()
        username = data.get("username", "")
        password = data.get("password", "")

        correct_user = config.get("web.username", "admin")
        correct_pass = config.get("web.password", "admin123")

        if username == correct_user and password == correct_pass:
            session["logged_in"] = True
            session["username"] = username
            return jsonify({"success": True, "message": "登录成功"})
        else:
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401

    @app.route("/api/logout", methods=["POST"])
    def api_logout():
        """登出API"""
        session.clear()
        return jsonify({"success": True})

    @app.route("/")
    @login_required
    def dashboard():
        """仪表盘页面"""
        return render_template("dashboard.html")

    # ========== 配置管理API ==========

    @app.route("/api/config", methods=["GET"])
    @login_required
    def get_config():
        """获取配置"""
        cfg = get_config_dict()
        # 不返回完整cookie（安全考虑，只返回前50字符和长度）
        if cfg.get("douyin", {}).get("cookie"):
            cookie = cfg["douyin"]["cookie"]
            cfg["douyin"]["cookie_preview"] = cookie[:50] + "..." if len(cookie) > 50 else cookie
            cfg["douyin"]["cookie_length"] = len(cookie)
            cfg["douyin"]["cookie"] = ""  # 清空不返回
        return jsonify(cfg)

    @app.route("/api/config/douyin", methods=["POST"])
    @login_required
    def update_douyin_config():
        """更新抖音配置"""
        data = request.get_json()
        cfg = get_config_dict()

        if "douyin" not in cfg:
            cfg["douyin"] = {}

        # 更新cookie（如果提供了新的）
        if data.get("cookie"):
            cfg["douyin"]["cookie"] = data["cookie"]

        if "headless" in data:
            cfg["douyin"]["headless"] = data["headless"]

        if save_config(cfg):
            return jsonify({"success": True, "message": "保存成功"})
        return jsonify({"success": False, "message": "保存失败"}), 500

    @app.route("/api/config/email", methods=["POST"])
    @login_required
    def update_email_config():
        """更新邮箱配置"""
        data = request.get_json()
        cfg = get_config_dict()

        if "email" not in cfg:
            cfg["email"] = {}

        cfg["email"]["enabled"] = data.get("enabled", cfg["email"].get("enabled", False))
        cfg["email"]["smtp_server"] = data.get("smtp_server", cfg["email"].get("smtp_server", ""))
        cfg["email"]["smtp_port"] = data.get("smtp_port", cfg["email"].get("smtp_port", 465))
        cfg["email"]["use_ssl"] = data.get("use_ssl", cfg["email"].get("use_ssl", True))
        cfg["email"]["sender"] = data.get("sender", cfg["email"].get("sender", ""))
        cfg["email"]["password"] = data.get("password", cfg["email"].get("password", ""))
        cfg["email"]["receivers"] = data.get("receivers", cfg["email"].get("receivers", []))

        if "notify_on" in data:
            if "notify_on" not in cfg["email"]:
                cfg["email"]["notify_on"] = {}
            cfg["email"]["notify_on"].update(data["notify_on"])

        if save_config(cfg):
            return jsonify({"success": True, "message": "保存成功"})
        return jsonify({"success": False, "message": "保存失败"}), 500

    @app.route("/api/config/message-api", methods=["POST"])
    @login_required
    def update_message_api_config():
        """更新消息API配置"""
        data = request.get_json()
        cfg = get_config_dict()

        if "message_api" not in cfg:
            cfg["message_api"] = {}

        cfg["message_api"]["mode"] = data.get("mode", cfg["message_api"].get("mode", "mock"))

        if "real" in data:
            if "real" not in cfg["message_api"]:
                cfg["message_api"]["real"] = {}
            cfg["message_api"]["real"].update(data["real"])

        if "mock" in data:
            if "mock" not in cfg["message_api"]:
                cfg["message_api"]["mock"] = {}
            cfg["message_api"]["mock"].update(data["mock"])

        if "sticker" in data:
            if "sticker" not in cfg["message_api"]:
                cfg["message_api"]["sticker"] = {}
            cfg["message_api"]["sticker"].update(data["sticker"])

        if save_config(cfg):
            return jsonify({"success": True, "message": "保存成功"})
        return jsonify({"success": False, "message": "保存失败"}), 500

    @app.route("/api/config/send", methods=["POST"])
    @login_required
    def update_send_config():
        """更新发送设置"""
        data = request.get_json()
        cfg = get_config_dict()

        if "send" not in cfg:
            cfg["send"] = {}

        cfg["send"]["retry_times"] = data.get("retry_times", cfg["send"].get("retry_times", 3))
        cfg["send"]["retry_delay"] = data.get("retry_delay", cfg["send"].get("retry_delay", 5))
        cfg["send"]["friend_interval"] = data.get("friend_interval", cfg["send"].get("friend_interval", 10))

        if save_config(cfg):
            return jsonify({"success": True, "message": "保存成功"})
        return jsonify({"success": False, "message": "保存失败"}), 500

    # ========== 好友管理API ==========

    @app.route("/api/friends", methods=["GET"])
    @login_required
    def get_friends():
        """获取好友列表"""
        friends = config.friends
        return jsonify({"friends": friends, "total": len(friends)})

    @app.route("/api/friends", methods=["POST"])
    @login_required
    def add_friend():
        """添加好友"""
        data = request.get_json()
        cfg = get_config_dict()

        if "friends" not in cfg:
            cfg["friends"] = []

        new_friend = {
            "nickname": data.get("nickname", ""),
            "sec_uid": data.get("sec_uid", ""),
            "user_id": data.get("user_id", ""),
            "remark": data.get("remark", ""),
        }

        cfg["friends"].append(new_friend)

        if save_config(cfg):
            return jsonify({"success": True, "message": "添加成功", "friend": new_friend})
        return jsonify({"success": False, "message": "保存失败"}), 500

    @app.route("/api/friends/<int:index>", methods=["PUT"])
    @login_required
    def update_friend(index: int):
        """更新好友"""
        data = request.get_json()
        cfg = get_config_dict()

        if "friends" not in cfg or index >= len(cfg["friends"]):
            return jsonify({"success": False, "message": "好友不存在"}), 404

        friend = cfg["friends"][index]
        for key in ["nickname", "sec_uid", "user_id", "remark"]:
            if key in data:
                friend[key] = data[key]

        if save_config(cfg):
            return jsonify({"success": True, "message": "更新成功", "friend": friend})
        return jsonify({"success": False, "message": "保存失败"}), 500

    @app.route("/api/friends/<int:index>", methods=["DELETE"])
    @login_required
    def delete_friend(index: int):
        """删除好友"""
        cfg = get_config_dict()

        if "friends" not in cfg or index >= len(cfg["friends"]):
            return jsonify({"success": False, "message": "好友不存在"}), 404

        deleted = cfg["friends"].pop(index)

        if save_config(cfg):
            return jsonify({"success": True, "message": "删除成功", "friend": deleted})
        return jsonify({"success": False, "message": "保存失败"}), 500

    # ========== 消息测试API ==========

    @app.route("/api/test/message", methods=["GET"])
    @login_required
    def test_message():
        """测试消息API获取"""
        try:
            msg_provider = create_message_provider(config)
            mode = config.get("message_api.mode", "mock")
            
            result = {"success": True, "mode": mode}
            
            if mode == "sticker":
                # 表情包模式：获取图片URL
                image_url = msg_provider.get_image_url()
                if image_url:
                    result["image_url"] = image_url
                    result["message"] = f"获取到表情包: {image_url}"
                else:
                    result["message"] = "获取表情包失败"
                    result["success"] = False
            else:
                # 文本模式
                message = msg_provider.get_message()
                result["message"] = message
            
            return jsonify(result)
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @app.route("/api/test/email", methods=["POST"])
    @login_required
    def test_email():
        """测试邮件发送"""
        try:
            notifier = create_email_notifier(config)
            subject = "【测试】抖音续火花邮件通知"
            content = f"""
这是一封测试邮件。

发送时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
如果您收到这封邮件，说明邮件配置正确！

-- 抖音续火花脚本
"""
            success = notifier.send(subject, content.strip())
            if success:
                return jsonify({"success": True, "message": "测试邮件已发送，请查收"})
            else:
                return jsonify({"success": False, "message": "邮件发送失败"}), 500
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    # ========== 发送任务API ==========

    @app.route("/api/send/status", methods=["GET"])
    @login_required
    def get_send_status():
        """获取发送任务状态"""
        return jsonify({
            "running": send_status["running"],
            "progress": send_status["progress"],
            "total": send_status["total"],
            "results": send_status["results"],
            "start_time": send_status["start_time"].strftime("%Y-%m-%d %H:%M:%S") if send_status["start_time"] else None,
            "end_time": send_status["end_time"].strftime("%Y-%m-%d %H:%M:%S") if send_status["end_time"] else None,
        })

    @app.route("/api/send/start", methods=["POST"])
    @login_required
    def start_send():
        """开始发送任务"""
        if send_status["running"]:
            return jsonify({"success": False, "message": "已有任务在运行中"}), 400

        # 重置状态
        send_status["running"] = True
        send_status["progress"] = 0
        send_status["results"] = []
        send_status["start_time"] = datetime.now()
        send_status["end_time"] = None

        # 在后台线程中执行
        def run_send_task():
            try:
                from src.douyin_sender import DouyinSender
                from src.message_provider import create_message_provider
                import time

                friends = config.friends
                send_status["total"] = len(friends)

                msg_provider = create_message_provider(config)

                sender = DouyinSender(
                    cookie_str=config.douyin_cookie,
                    headless=config.headless,
                    user_data_dir=config.user_data_dir,
                )

                try:
                    sender.start()

                    # 检查登录
                    if not sender.is_logged_in():
                        send_status["results"].append({
                            "error": "未登录，Cookie可能失效",
                            "success": False,
                        })
                        return

                    # 逐个发送
                    for i, friend in enumerate(friends):
                        remark = friend.get("remark", friend.get("nickname", "未知"))

                        try:
                            message = msg_provider.get_message()
                        except Exception:
                            message = "早安~ 今天也要开心哦！"

                        success = False
                        error_msg = ""

                        # 重试
                        for attempt in range(config.retry_times):
                            try:
                                if sender.send_message(friend, message):
                                    success = True
                                    break
                            except Exception as e:
                                error_msg = str(e)
                            if attempt < config.retry_times - 1:
                                time.sleep(config.retry_delay)

                        result = {
                            "index": i + 1,
                            "remark": remark,
                            "nickname": friend.get("nickname", ""),
                            "success": success,
                            "message": message,
                            "error": error_msg,
                        }
                        send_status["results"].append(result)
                        send_status["progress"] = i + 1

                        # 好友间隔
                        if i < len(friends) - 1:
                            time.sleep(config.friend_interval)

                    # 刷新cookie
                    try:
                        new_cookie = sender.refresh_cookies()
                        if new_cookie:
                            cookie_mgr.save_cookie(new_cookie)
                    except Exception:
                        pass

                finally:
                    sender.close()

            except Exception as e:
                send_status["results"].append({
                    "error": f"严重错误: {str(e)}",
                    "success": False,
                })
            finally:
                send_status["running"] = False
                send_status["end_time"] = datetime.now()

        thread = threading.Thread(target=run_send_task, daemon=True)
        thread.start()

        return jsonify({"success": True, "message": "任务已启动"})

    # ========== 日志API ==========

    @app.route("/api/logs", methods=["GET"])
    @login_required
    def get_logs():
        """获取日志内容"""
        log_file = config.get("logging.file", "./logs/douyin_spark.log")
        lines = request.args.get("lines", 100, type=int)

        if not os.path.exists(log_file):
            return jsonify({"logs": [], "total": 0})

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return jsonify({
                "logs": [line.strip() for line in recent_lines],
                "total": len(all_lines),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ========== 仪表盘统计API ==========

    @app.route("/api/stats", methods=["GET"])
    @login_required
    def get_stats():
        """获取仪表盘统计数据"""
        friends = config.friends
        log_file = config.get("logging.file", "./logs/douyin_spark.log")

        # 统计今日发送情况
        today = datetime.now().strftime("%Y-%m-%d")
        today_success = 0
        today_fail = 0
        today_runs = 0

        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if today in line:
                            if "执行完成" in line or "全部成功" in line:
                                today_runs += 1
            except Exception:
                pass

        # Cookie状态
        cookie_str = config.douyin_cookie
        cookie_valid = len(cookie_str) > 100

        return jsonify({
            "total_friends": len(friends),
            "cookie_valid": cookie_valid,
            "cookie_length": len(cookie_str),
            "today_runs": today_runs,
            "email_enabled": config.email_enabled,
            "message_mode": config.get("message_api.mode", "mock"),
            "headless": config.headless,
            "send_running": send_status["running"],
        })

    return app


def main():
    """启动Web服务"""
    import argparse

    parser = argparse.ArgumentParser(description="抖音续火花 - Web管理面板")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件路径")
    args = parser.parse_args()

    config = Config(args.config)
    app = create_app(args.config)

    host = config.get("web.host", "0.0.0.0")
    port = config.get("web.port", 5000)

    https_enabled = config.get("web.https.enabled", False)
    cert_file = config.get("web.https.cert_file", "")
    key_file = config.get("web.https.key_file", "")

    ssl_context = None
    if https_enabled and cert_file and key_file:
        ssl_context = (cert_file, key_file)
        print(f"HTTPS已启用: https://{host}:{port}")
    else:
        print(f"Web管理面板启动: http://{host}:{port}")

    print(f"默认账号: {config.get('web.username', 'admin')}")
    print("请及时修改默认密码！")

    app.run(host=host, port=port, ssl_context=ssl_context, debug=False)


if __name__ == "__main__":
    main()
