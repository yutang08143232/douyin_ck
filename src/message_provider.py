"""
消息/表情包API模块
支持：mock文本、真实API文本、表情包图片
"""
import random
import os
import tempfile
import requests
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MessageProvider:
    """消息提供者基类"""

    def get_message(self) -> str:
        """获取一条文本消息"""
        raise NotImplementedError

    def get_image_url(self) -> Optional[str]:
        """获取一张图片URL（返回None表示不支持图片）"""
        return None


class MockMessageProvider(MessageProvider):
    """Mock消息提供者，从预设消息池中随机选取"""

    def __init__(self, messages: list):
        self.messages = messages or ["早安~ 今天也要开心哦！"]

    def get_message(self) -> str:
        msg = random.choice(self.messages)
        logger.debug(f"[Mock] 获取消息: {msg}")
        return msg


class RealMessageProvider(MessageProvider):
    """真实API消息提供者"""

    def __init__(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[dict] = None,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
        message_path: str = "data.content",
    ):
        self.url = url
        self.method = method.upper()
        self.headers = headers or {}
        self.params = params or {}
        self.body = body or {}
        self.message_path = message_path

    def _extract_by_path(self, data: dict, path: str):
        """根据点分隔路径从字典中提取值"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ValueError(f"无法从响应中提取值，路径: {path}")
        return value

    def get_message(self) -> str:
        """调用真实API获取消息"""
        try:
            if self.method == "GET":
                resp = requests.get(
                    self.url, headers=self.headers, params=self.params, timeout=10
                )
            else:  # POST
                resp = requests.post(
                    self.url,
                    headers=self.headers,
                    params=self.params,
                    json=self.body,
                    timeout=10,
                )

            resp.raise_for_status()
            data = resp.json()
            msg = str(self._extract_by_path(data, self.message_path))
            logger.debug(f"[API] 获取消息成功: {msg[:30]}...")
            return msg

        except Exception as e:
            logger.error(f"[API] 获取消息失败: {e}")
            raise


class StickerProvider(MessageProvider):
    """表情包提供者，从表情包API获取随机表情包图片"""

    def __init__(
        self,
        url: str = "https://api.yutangxiaowu.cn/api/gif/random",
        local: str = "王者荣耀局内表情包",
        n: int = 1,
        image_list_path: str = "data.list",
        image_url_path: str = "url",
    ):
        self.url = url
        self.local = local
        self.n = n
        self.image_list_path = image_list_path
        self.image_url_path = image_url_path

    def _extract_by_path(self, data: dict, path: str):
        """根据点分隔路径从字典中提取值"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ValueError(f"无法从响应中提取值，路径: {path}")
        return value

    def get_image_url(self) -> Optional[str]:
        """获取一张随机表情包图片的URL"""
        try:
            params = {"n": self.n, "local": self.local}
            resp = requests.get(self.url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            # 检查返回码
            if data.get("code", 0) != 0:
                logger.error(f"[Sticker] API返回错误: {data.get('msg', '未知错误')}")
                return None

            # 提取图片列表
            img_list = self._extract_by_path(data, self.image_list_path)
            if not img_list or not isinstance(img_list, list):
                logger.error("[Sticker] 图片列表为空")
                return None

            # 随机选一张
            img_item = random.choice(img_list)
            img_url = self._extract_by_path(img_item, self.image_url_path)

            logger.debug(f"[Sticker] 获取表情包成功: {img_url}")
            return img_url

        except Exception as e:
            logger.error(f"[Sticker] 获取表情包失败: {e}")
            return None

    def download_image(self, image_url: str, save_dir: Optional[str] = None) -> Optional[str]:
        """下载图片到本地临时文件，返回文件路径"""
        try:
            resp = requests.get(image_url, timeout=15, stream=True)
            resp.raise_for_status()

            # 从URL中提取文件名
            filename = image_url.split("/")[-1].split("?")[0]
            if not filename or "." not in filename:
                filename = "sticker.png"

            # 确定保存目录
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                filepath = os.path.join(save_dir, filename)
            else:
                # 用临时文件
                suffix = os.path.splitext(filename)[1] or ".png"
                fd, filepath = tempfile.mkstemp(suffix=suffix, prefix="sticker_")
                os.close(fd)

            # 写入文件
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"[Sticker] 图片下载成功: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[Sticker] 下载图片失败: {e}")
            return None

    def get_message(self) -> str:
        """表情包模式也返回一个默认文本消息"""
        return "来斗图！"


def create_message_provider(config) -> MessageProvider:
    """
    根据配置创建消息提供者
    支持模式: mock, real, sticker
    """
    mode = config.get("message_api.mode", "mock")

    if mode == "real":
        real_cfg = config.get("message_api.real", {})
        return RealMessageProvider(
            url=real_cfg.get("url", ""),
            method=real_cfg.get("method", "GET"),
            headers=real_cfg.get("headers", {}),
            params=real_cfg.get("params", {}),
            body=real_cfg.get("body", {}),
            message_path=real_cfg.get("message_path", "data.content"),
        )
    elif mode == "sticker":
        sticker_cfg = config.get("message_api.sticker", {})
        return StickerProvider(
            url=sticker_cfg.get("url", "https://api.yutangxiaowu.cn/api/gif/random"),
            local=sticker_cfg.get("local", "王者荣耀局内表情包"),
            n=sticker_cfg.get("n", 1),
            image_list_path=sticker_cfg.get("image_list_path", "data.list"),
            image_url_path=sticker_cfg.get("image_url_path", "url"),
        )
    else:
        mock_cfg = config.get("message_api.mock", {})
        return MockMessageProvider(mock_cfg.get("messages", []))
