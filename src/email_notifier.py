"""
邮箱通知模块
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import logging
from typing import List

logger = logging.getLogger(__name__)


class EmailNotifier:
    """邮箱通知器"""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        use_ssl: bool,
        sender: str,
        password: str,
        receivers: List[str],
    ):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.use_ssl = use_ssl
        self.sender = sender
        self.password = password
        self.receivers = receivers

    def send(self, subject: str, content: str, is_html: bool = False) -> bool:
        """
        发送邮件

        Args:
            subject: 邮件主题
            content: 邮件内容
            is_html: 是否为HTML格式

        Returns:
            是否发送成功
        """
        if not self.receivers:
            logger.warning("没有配置收件人，跳过邮件发送")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = Header(f"抖音续火花脚本 <{self.sender}>")
            msg["To"] = Header(", ".join(self.receivers))
            msg["Subject"] = Header(subject, "utf-8")

            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(content, content_type, "utf-8"))

            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=15)
                server.starttls()

            server.login(self.sender, self.password)
            server.sendmail(self.sender, self.receivers, msg.as_string())
            server.quit()

            logger.info(f"邮件发送成功: {subject}")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False

    def notify_all_failed(self, failed_friends: list, date_str: str) -> None:
        """所有好友发送失败通知"""
        subject = f"【警告】抖音续火花全部失败 - {date_str}"
        content = f"""
抖音续火花脚本执行结果：
日期：{date_str}
状态：全部失败

失败的好友列表：
"""
        for friend in failed_friends:
            remark = friend.get("remark", friend.get("nickname", "未知"))
            content += f"  - {remark}\n"

        content += """
请及时检查脚本运行状态和Cookie有效性。

-- 抖音续火花脚本自动发送
"""
        self.send(subject, content.strip())

    def notify_cookie_expired(self, date_str: str) -> None:
        """Cookie过期/刷新失败通知"""
        subject = f"【紧急】抖音Cookie已过期 - {date_str}"
        content = f"""
抖音Cookie已过期，自动刷新失败。

日期：{date_str}

请尽快手动更新Cookie：
1. 在浏览器中登录抖音网页版
2. 按F12打开开发者工具
3. 切换到 Network（网络）标签
4. 刷新页面，找到任意请求
5. 从请求头中复制完整的Cookie字符串
6. 更新到 config.yaml 中的 douyin.cookie 字段

-- 抖音续火花脚本自动发送
"""
        self.send(subject, content.strip())

    def notify_daily_summary(
        self, date_str: str, success_count: int, fail_count: int, details: list
    ) -> None:
        """每日发送简报"""
        subject = f"【日报】抖音续火花执行报告 - {date_str}"

        content = f"""
抖音续火花每日执行报告
日期：{date_str}
成功：{success_count} 人
失败：{fail_count} 人

详细情况：
"""
        for item in details:
            remark = item.get("remark", item.get("nickname", "未知"))
            status = "成功" if item.get("success") else "失败"
            error = item.get("error", "")
            content += f"  [{status}] {remark}"
            if error:
                content += f" - {error}"
            content += "\n"

        content += """
-- 抖音续火花脚本自动发送
"""
        self.send(subject, content.strip())


def create_email_notifier(config) -> EmailNotifier:
    """根据配置创建邮件通知器"""
    email_cfg = config.get("email", {})
    return EmailNotifier(
        smtp_server=email_cfg.get("smtp_server", "smtp.qq.com"),
        smtp_port=email_cfg.get("smtp_port", 465),
        use_ssl=email_cfg.get("use_ssl", True),
        sender=email_cfg.get("sender", ""),
        password=email_cfg.get("password", ""),
        receivers=email_cfg.get("receivers", []),
    )
