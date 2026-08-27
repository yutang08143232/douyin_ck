"""
抖音续火花 - 主程序入口
每天定时给多个好友发送私信，维持火花
"""
import sys
import os
import time
import logging
from datetime import datetime
from typing import List, Dict

# 将 src 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.config_loader import Config
from src.logger_setup import setup_logging
from src.message_provider import create_message_provider
from src.douyin_sender import DouyinSender
from src.cookie_manager import CookieManager
from src.email_notifier import create_email_notifier

logger = logging.getLogger("main")


def send_with_retry(
    sender: DouyinSender,
    friend: Dict[str, str],
    message: str,
    retry_times: int,
    retry_delay: int,
    image_url: str = None,
) -> Dict:
    """
    带重试地给单个好友发消息/图片

    Args:
        sender: DouyinSender实例
        friend: 好友信息
        message: 文本消息内容
        retry_times: 重试次数
        retry_delay: 重试间隔（秒）
        image_url: 图片URL（提供则发图片，否则发文字）

    Returns:
        包含发送结果的字典
    """
    remark = friend.get("remark", friend.get("nickname", "未知"))
    last_error = ""
    is_image = image_url is not None

    for attempt in range(1, retry_times + 1):
        send_type = "图片" if is_image else "消息"
        logger.info(f"[{remark}] 第 {attempt}/{retry_times} 次尝试发送{send_type}...")

        try:
            if is_image:
                success = sender.send_image_from_url(friend, image_url)
            else:
                success = sender.send_message(friend, message)

            if success:
                logger.info(f"[{remark}] 发送成功！")
                return {
                    "friend": friend,
                    "remark": remark,
                    "success": True,
                    "attempts": attempt,
                    "error": "",
                    "is_image": is_image,
                }
            else:
                last_error = "发送返回失败"
                logger.warning(f"[{remark}] 第 {attempt} 次发送失败")
        except Exception as e:
            last_error = str(e)
            logger.error(f"[{remark}] 第 {attempt} 次发送异常: {e}")

        # 不是最后一次才等待
        if attempt < retry_times:
            time.sleep(retry_delay)

    logger.error(f"[{remark}] 所有 {retry_times} 次尝试均失败")
    return {
        "friend": friend,
        "remark": remark,
        "success": False,
        "attempts": retry_times,
        "error": last_error,
        "is_image": is_image,
    }


def run(config_path: str = "config.yaml") -> int:
    """
    主执行流程

    Returns:
        退出码 (0=成功, 1=部分失败, 2=全部失败/严重错误)
    """
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"{'='*50}")
    logger.info(f"抖音续火花脚本启动 - {date_str}")
    logger.info(f"{'='*50}")

    # 1. 加载配置
    try:
        config = Config(config_path)
    except Exception as e:
        logger.critical(f"加载配置失败: {e}")
        return 2

    # 2. 设置日志
    log_cfg = config.get("logging", {})
    setup_logging(
        level=log_cfg.get("level", "INFO"),
        log_file=log_cfg.get("file", "./logs/douyin_spark.log"),
        max_size_mb=log_cfg.get("max_size_mb", 10),
        backup_count=log_cfg.get("backup_count", 5),
    )

    # 3. 初始化组件
    friends = config.friends
    if not friends:
        logger.error("好友列表为空，退出")
        return 2

    logger.info(f"共有 {len(friends)} 位好友需要发送消息")

    # 消息提供者
    try:
        msg_provider = create_message_provider(config)
    except Exception as e:
        logger.error(f"初始化消息提供者失败: {e}")
        return 2

    # Cookie 管理器
    cookie_mgr = CookieManager(config_path)
    cookie_str = cookie_mgr.load_cookie()

    # 邮件通知器
    notifier = None
    if config.email_enabled:
        try:
            notifier = create_email_notifier(config)
        except Exception as e:
            logger.warning(f"初始化邮件通知器失败: {e}")

    # 4. 启动浏览器并检查登录状态
    sender = DouyinSender(
        cookie_str=cookie_str,
        headless=config.headless,
        user_data_dir=config.user_data_dir,
    )

    try:
        sender.start()

        # 检查登录状态
        if not sender.is_logged_in():
            logger.error("Cookie已过期，无法登录")
            if notifier and config.get("email.notify_on.cookie_expired", True):
                notifier.notify_cookie_expired(date_str)
            return 2

        logger.info("登录状态正常")

        # 尝试刷新cookie（自动续期）
        logger.info("尝试自动刷新Cookie...")
        new_cookie = sender.refresh_cookies()
        if new_cookie and new_cookie != cookie_str:
            cookie_mgr.save_cookie(new_cookie)
            logger.info("Cookie已自动更新")
        else:
            logger.info("Cookie无需更新或刷新失败")

        # 5. 遍历好友发送消息
        results = []
        retry_times = config.retry_times
        retry_delay = config.retry_delay
        friend_interval = config.friend_interval
        mode = config.get("message_api.mode", "mock")

        for i, friend in enumerate(friends):
            remark = friend.get("remark", friend.get("nickname", "未知"))

            # 获取消息/图片
            message = ""
            image_url = None

            try:
                if mode == "sticker":
                    # 表情包模式：获取图片URL
                    image_url = msg_provider.get_image_url()
                    if not image_url:
                        logger.warning("获取表情包失败，降级为文本消息")
                        message = msg_provider.get_message()
                    else:
                        message = "[表情包]"  # 仅用于日志显示
                else:
                    # 文本模式
                    message = msg_provider.get_message()
            except Exception as e:
                logger.error(f"获取消息失败，使用默认消息: {e}")
                message = "早安~ 今天也要开心哦！"

            logger.info(f"--- [{i+1}/{len(friends)}] 给 {remark} 发送消息 ---")
            if image_url:
                logger.info(f"表情包URL: {image_url[:80]}...")
            else:
                logger.info(f"消息内容: {message[:50]}{'...' if len(message) > 50 else ''}")

            # 发送消息（带重试）
            result = send_with_retry(
                sender, friend, message, retry_times, retry_delay, image_url
            )
            results.append(result)

            # 好友之间间隔
            if i < len(friends) - 1:
                logger.info(f"等待 {friend_interval} 秒后处理下一位好友...")
                time.sleep(friend_interval)

        # 6. 统计结果
        success_list = [r for r in results if r["success"]]
        fail_list = [r for r in results if not r["success"]]

        logger.info(f"\n{'='*50}")
        logger.info(f"执行完成：成功 {len(success_list)} 人，失败 {len(fail_list)} 人")
        logger.info(f"{'='*50}")

        for r in results:
            status = "成功" if r["success"] else "失败"
            logger.info(f"  [{status}] {r['remark']} (尝试 {r['attempts']} 次)")

        # 7. 发送通知
        if notifier:
            # 全部失败通知
            if len(fail_list) == len(results) and config.get("email.notify_on.all_failed", True):
                logger.warning("所有好友全部发送失败，发送告警邮件")
                failed_friends = [r["friend"] for r in fail_list]
                notifier.notify_all_failed(failed_friends, date_str)

            # 每日简报
            if config.get("email.notify_on.daily_summary", False):
                details = [
                    {
                        "remark": r["remark"],
                        "success": r["success"],
                        "error": r["error"],
                    }
                    for r in results
                ]
                notifier.notify_daily_summary(
                    date_str, len(success_list), len(fail_list), details
                )

        # 返回退出码
        if len(fail_list) == 0:
            return 0  # 全部成功
        elif len(success_list) == 0:
            return 2  # 全部失败
        else:
            return 1  # 部分失败

    except KeyboardInterrupt:
        logger.info("用户中断")
        return 1
    except Exception as e:
        logger.critical(f"程序运行异常: {e}", exc_info=True)
        if notifier:
            try:
                notifier.send(
                    subject=f"【严重】抖音续火花脚本异常 - {date_str}",
                    content=f"脚本运行发生严重异常:\n\n{e}\n\n请及时检查。",
                )
            except Exception:
                pass
        return 2
    finally:
        sender.close()


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="抖音续火花 - 自动发私信脚本")
    parser.add_argument(
        "-c", "--config",
        default="config.yaml",
        help="配置文件路径 (默认: config.yaml)",
    )
    parser.add_argument(
        "--test-message",
        action="store_true",
        help="仅测试消息API获取，不发送",
    )
    parser.add_argument(
        "--check-login",
        action="store_true",
        help="仅检查登录状态，不发送",
    )

    args = parser.parse_args()

    # 测试消息API模式
    if args.test_message:
        config = Config(args.config)
        msg_provider = create_message_provider(config)
        msg = msg_provider.get_message()
        print(f"获取到的消息: {msg}")
        return 0

    # 检查登录状态模式
    if args.check_login:
        config = Config(args.config)
        cookie_mgr = CookieManager(args.config)
        cookie_str = cookie_mgr.load_cookie()
        sender = DouyinSender(
            cookie_str=cookie_str,
            headless=False,  # 检查登录时显示界面方便查看
            user_data_dir=config.user_data_dir,
        )
        try:
            sender.start()
            logged_in = sender.is_logged_in()
            print(f"登录状态: {'已登录' if logged_in else '未登录'}")
            return 0 if logged_in else 1
        finally:
            sender.close()

    # 正常运行模式
    exit_code = run(args.config)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
