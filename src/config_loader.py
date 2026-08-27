"""
配置加载模块
"""
import os
import yaml
from typing import Any, Dict, List


class Config:
    """配置管理类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """加载配置文件"""
        if not os.path.exists(self.config_path):
            # 尝试加载 example 配置
            example_path = self.config_path.replace(".yaml", ".example.yaml")
            if os.path.exists(example_path):
                raise FileNotFoundError(
                    f"配置文件 {self.config_path} 不存在，请复制 {example_path} 为 {self.config_path} 并修改配置"
                )
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")

        with open(self.config_path, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项，支持点分隔路径，如 "douyin.cookie"
        """
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    @property
    def douyin_cookie(self) -> str:
        """获取抖音cookie字符串"""
        cookie_str = self.get("douyin.cookie", "")
        if cookie_str:
            return cookie_str

        # 尝试从 cookies 字典组装
        cookies = self.get("douyin.cookies", {})
        if cookies:
            return "; ".join([f"{k}={v}" for k, v in cookies.items()])

        return ""

    @property
    def friends(self) -> List[Dict[str, str]]:
        """获取好友列表"""
        return self.get("friends", [])

    @property
    def headless(self) -> bool:
        """是否无头模式"""
        return self.get("douyin.headless", True)

    @property
    def user_data_dir(self) -> str:
        """浏览器数据目录"""
        return self.get("douyin.user_data_dir", "./browser_data")

    @property
    def retry_times(self) -> int:
        """重试次数"""
        return self.get("send.retry_times", 3)

    @property
    def retry_delay(self) -> int:
        """重试间隔（秒）"""
        return self.get("send.retry_delay", 5)

    @property
    def friend_interval(self) -> int:
        """好友间隔（秒）"""
        return self.get("send.friend_interval", 10)

    @property
    def email_enabled(self) -> bool:
        """是否启用邮件通知"""
        return self.get("email.enabled", False)
