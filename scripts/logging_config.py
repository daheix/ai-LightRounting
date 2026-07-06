"""循环日志工厂模块。

模块用途:
    提供 get_logger() 工厂函数，基于 logging.handlers.RotatingFileHandler
    创建按字节大小自动轮转的日志器（达到 max_bytes 时滚动并保留
    backup_count 个备份），同时附加控制台 StreamHandler 便于调试。

    默认配置（用户规则 2026-07-06 "日志上限提高到 99MB"）:
    - max_bytes = 99 MB (99 * 1024 * 1024 = 103809024)
    - backup_count = 1 (保留 1 个备份，总磁盘上限 = 99 + 99 = 198 MB)
    - 日志目录 /tmp/polaris_logs/（自动创建）
    - 默认级别 logging.INFO

    日志格式:
        %(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s

    R03 无 fall-back 设计:
    - 日志目录无法创建或不可写时，必须 raise RuntimeError，禁止静默兜底。
    - 不返回 None / 不返回降级 logger，失败即 raise。

来源（R02 学术诚信，≥5 个文献 URL）:
    [1] Python logging 官方文档
        https://docs.python.org/3/library/logging.html
    [2] RotatingFileHandler 官方文档
        https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler
    [3] logging HOWTO（日志器与 handler）
        https://docs.python.org/3/howto/logging.html
    [4] logging cookbook（多次调用去重 handler）
        https://docs.python.org/3/howto/logging-cookbook.html
    [5] os.makedirs 官方文档
        https://docs.python.org/3/library/os.html#os.makedirs

参数说明:
    name: 日志器名称（同时作为日志文件名 {name}.log）。
    log_dir: 日志目录，默认 /tmp/polaris_logs。
    max_bytes: 单个日志文件最大字节数，达到后触发轮转，默认 103809024 (99 MB)。
    backup_count: 保留的备份文件数，默认 1（总上限 = 99 + 99 = 198 MB）。
    level: 日志级别，默认 logging.INFO，可通过该参数覆盖。

*创新* 点:
    - 工厂函数内置 handler 去重：每次调用先关闭并清除已有 handler 再添加，
      避免长生命周期进程中因重复调用 get_logger() 导致同一日志被多次写入。
      底层逻辑：Python logging 中同名 logger 是全局单例
      （logging.Logger.manager.loggerDict），重复 addHandler 会累积 handler，
      必须先关闭（释放文件描述符）再清除。案例：服务进程多次初始化模块时，
      若不去重会出现日志行数翻倍。支持理论见 [4] logging cookbook。
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

__all__ = ["get_logger"]

# 默认参数常量（用户规则 2026-07-06 "日志上限提高到 99MB"）
# 总上限 = max_bytes × (backup_count + 1) = 99 MB × 2 = 198 MB
DEFAULT_LOG_DIR = "/tmp/polaris_logs"
DEFAULT_MAX_BYTES = 99 * 1024 * 1024  # 99 MB = 103809024（×2 备份 = 198 MB）
DEFAULT_BACKUP_COUNT = 1
DEFAULT_LEVEL = logging.INFO

# 日志格式（spec 规定）
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"


def get_logger(
    name: str,
    log_dir: str = DEFAULT_LOG_DIR,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
    level: int = DEFAULT_LEVEL,
) -> logging.Logger:
    """创建或获取带文件轮转的日志器。

    基于 logging.handlers.RotatingFileHandler：当日志文件达到 max_bytes
    时自动轮转——当前文件重命名为 {name}.log.1，并新建 {name}.log 继续写入，
    最多保留 backup_count 个备份。

    Args:
        name: 日志器名称（同时用于日志文件名 {name}.log）。
        log_dir: 日志目录，默认 /tmp/polaris_logs（自动创建）。
        max_bytes: 单文件最大字节数，默认 10485760 (10 MB)。
        backup_count: 保留备份数，默认 1。
        level: 日志级别，默认 logging.INFO。

    Returns:
        配置好文件轮转 + 控制台 handler 的 logging.Logger 实例。

    Raises:
        RuntimeError: 日志目录无法创建或不可写时抛出（R03 禁止 fall-back）。
    """
    # 1. 创建日志目录（自动）；失败即 raise，禁止 fall-back
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"无法创建日志目录 {log_dir}: {e}") from e

    # 2. 构造 RotatingFileHandler；目录不可写时 open 失败即 raise
    log_path = os.path.join(log_dir, f"{name}.log")
    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
    except OSError as e:
        raise RuntimeError(f"日志目录不可写或日志文件无法创建: {log_path} ({e})") from e

    formatter = logging.Formatter(_LOG_FORMAT)
    file_handler.setFormatter(formatter)

    # 3. 控制台 handler（stdout），便于调试
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # 4. 获取 logger（同名全局单例），先关闭并清除已有 handler 防止重复
    logger = logging.getLogger(name)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    logger.setLevel(level)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    # 避免向 root logger 传播导致重复输出
    logger.propagate = False

    return logger
