"""
日志配置模块
"""
import os
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(
    level: str = "INFO",
    log_file: str = "./logs/douyin_spark.log",
    max_size_mb: int = 10,
    backup_count: int = 5,
) -> None:
    """
    配置日志系统

    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_file: 日志文件路径
        max_size_mb: 单个日志文件最大大小（MB）
        backup_count: 日志文件备份数量
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 日志级别转换
    log_level = getattr(logging, level.upper(), logging.INFO)

    # 日志格式
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=date_fmt)

    # 根日志配置
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除已有handler，避免重复
    root_logger.handlers.clear()

    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件输出（滚动）
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size_mb * 1024 * 1024,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
