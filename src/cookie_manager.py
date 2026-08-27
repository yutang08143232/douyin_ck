"""
Cookie 管理模块
负责 Cookie 的持久化、自动刷新和过期检测
"""
import os
import yaml
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class CookieManager:
    """Cookie 管理器"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path

    def load_cookie(self) -> str:
        """从配置文件加载cookie"""
        if not os.path.exists(self.config_path):
            logger.error(f"配置文件不存在: {self.config_path}")
            return ""

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            douyin_cfg = config.get("douyin", {})
            cookie_str = douyin_cfg.get("cookie", "")

            if cookie_str:
                return cookie_str

            # 尝试从 cookies 字典组装
            cookies = douyin_cfg.get("cookies", {})
            if cookies:
                return "; ".join([f"{k}={v}" for k, v in cookies.items()])

            return ""

        except Exception as e:
            logger.error(f"加载Cookie失败: {e}")
            return ""

    def save_cookie(self, cookie_str: str) -> bool:
        """
        将新的cookie保存到配置文件
        只更新 douyin.cookie 字段，不改动其他配置

        Args:
            cookie_str: 新的cookie字符串

        Returns:
            是否保存成功
        """
        if not cookie_str:
            logger.warning("Cookie为空，跳过保存")
            return False

        try:
            if not os.path.exists(self.config_path):
                logger.error(f"配置文件不存在: {self.config_path}")
                return False

            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # 更新cookie
            if "douyin" not in config:
                config["douyin"] = {}
            config["douyin"]["cookie"] = cookie_str

            # 写回文件
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

            logger.info("Cookie已保存到配置文件")
            return True

        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
            return False

    def is_cookie_valid(self, cookie_str: str) -> bool:
        """
        简单检查cookie是否有效（格式检查）
        真正的有效性需要通过登录检测来验证

        Args:
            cookie_str: cookie字符串

        Returns:
            格式上是否有效
        """
        if not cookie_str:
            return False

        # 至少有几个关键cookie
        key_cookies = ["sessionid", "sid_guard", "msToken", "kpn"]
        found = 0
        for key in key_cookies:
            if f"{key}=" in cookie_str:
                found += 1

        # 至少找到2个关键cookie就算格式上有效
        return found >= 2
