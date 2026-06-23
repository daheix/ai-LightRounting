"""统一日志配置模块。

提供控制台彩色输出与 JSONL 文件日志，以及阶段日志记录器 StageLogger。

控制台彩色方案（ANSI 转义码）：
- 绿色 = 阶段开始
- 黄色 = 进行中（info/warn/log_input/log_output）
- 红色 = 失败
- 蓝色 = 完成

JSONL 日志格式：
    {"stage_id": int, "stage_name": str, "status": "running"|"done"|"failed",
     "start_time": str, "end_time": str, "duration_s": float,
     "inputs": dict, "outputs": dict, "error": str|null}

来源:
- ANSI 转义码: https://en.wikipedia.org/wiki/ANSI_escape_code
- Python logging: https://docs.python.org/3/library/logging.html
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ANSI 颜色码
_COLOR_GREEN = "\033[32m"
_COLOR_YELLOW = "\033[33m"
_COLOR_RED = "\033[31m"
_COLOR_BLUE = "\033[34m"
_COLOR_RESET = "\033[0m"

# JSONL 日志文件名
_JSONL_FILENAME = "showcase.jsonl"

# Showcase 专用日志器名称
_LOGGER_NAME = "e2e_showcase"


def setup_logging(output_dir: Path) -> logging.Logger:
    """配置根日志器，返回 showcase 专用日志器。

    创建控制台 handler（带时间戳格式）并初始化 JSONL 日志文件。

    Args:
        output_dir: 输出目录（如 out/e2e_showcase）。

    Returns:
        配置好的 Logger 实例。
    """
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    jsonl_path = logs_dir / _JSONL_FILENAME
    jsonl_path.touch()
    return logger


class StageLogger:
    """阶段日志记录器，作为上下文管理器包裹单个阶段执行。

    在进入时打印绿色阶段头并记录开始时间，在退出时打印蓝色（成功）
    或红色（失败）阶段尾并计算耗时，同时将结构化日志追加写入 JSONL 文件。

    用法:
        with StageLogger(1, "PDK 目录", output_dir) as sl:
            sl.log_input("platforms", ["SOI", "SiN"])
            result = do_work()
            sl.log_output("device_count", 42)
    """

    def __init__(self, stage_id: int, stage_name: str, output_dir: Path) -> None:
        """初始化阶段日志记录器。

        Args:
            stage_id: 阶段编号（1-9）。
            stage_name: 阶段名称。
            output_dir: 输出目录，JSONL 日志写入 output_dir/logs/showcase.jsonl。
        """
        self.stage_id = stage_id
        self.stage_name = stage_name
        self.output_dir = output_dir
        self._logger = logging.getLogger(_LOGGER_NAME)
        self._start_time: float = 0.0
        self._start_str: str = ""
        self._inputs: dict[str, Any] = {}
        self._outputs: dict[str, Any] = {}
        self._error: str | None = None

    def __enter__(self) -> StageLogger:
        """进入阶段：记录开始时间，打印绿色阶段头。"""
        self._start_time = time.time()
        self._start_str = datetime.now(timezone.utc).isoformat()
        bar = "=" * 60
        header = f"{bar}\n阶段 {self.stage_id}: {self.stage_name} — 开始\n{bar}"
        self._logger.info("%s%s%s", _COLOR_GREEN, header, _COLOR_RESET)
        return self

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, exc_tb: Any) -> bool:
        """退出阶段：打印蓝色（成功）或红色（失败）阶段尾，写入 JSONL。

        Args:
            exc_type: 异常类型（若有）。
            exc_val: 异常值（若有）。
            exc_tb: 异常 traceback（若有）。

        Returns:
            False，不抑制异常（规则 14.1：错误必须 raise）。
        """
        end_time = time.time()
        end_str = datetime.now(timezone.utc).isoformat()
        duration = end_time - self._start_time

        if exc_type is not None:
            status = "failed"
            self._error = f"{exc_type.__name__}: {exc_val}"
            footer = (
                f"阶段 {self.stage_id}: {self.stage_name} — 失败 ({duration:.2f}s)\n"
                f"错误: {self._error}"
            )
            self._logger.error("%s%s%s", _COLOR_RED, footer, _COLOR_RESET)
        else:
            status = "done"
            footer = f"阶段 {self.stage_id}: {self.stage_name} — 完成 ({duration:.2f}s)"
            self._logger.info("%s%s%s", _COLOR_BLUE, footer, _COLOR_RESET)

        self._write_jsonl(status, end_str, duration)
        return False

    def _write_jsonl(self, status: str, end_str: str, duration: float) -> None:
        """将结构化日志追加写入 JSONL 文件。

        Args:
            status: 阶段状态（"done" 或 "failed"）。
            end_str: 结束时间 ISO 字符串。
            duration: 耗时（秒）。
        """
        entry = {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "status": status,
            "start_time": self._start_str,
            "end_time": end_str,
            "duration_s": round(duration, 4),
            "inputs": self._inputs,
            "outputs": self._outputs,
            "error": self._error,
        }
        jsonl_path = self.output_dir / "logs" / _JSONL_FILENAME
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def log_input(self, key: str, value: Any) -> None:
        """记录输入摘要（黄色，进行中）。

        Args:
            key: 输入键名。
            value: 输入值（将存入 JSONL inputs 字段）。
        """
        self._inputs[key] = value
        self._logger.info("%s  [输入] %s: %s%s", _COLOR_YELLOW, key, value, _COLOR_RESET)

    def log_output(self, key: str, value: Any) -> None:
        """记录输出摘要（黄色，进行中）。

        Args:
            key: 输出键名。
            value: 输出值（将存入 JSONL outputs 字段）。
        """
        self._outputs[key] = value
        self._logger.info("%s  [输出] %s: %s%s", _COLOR_YELLOW, key, value, _COLOR_RESET)

    def info(self, msg: str) -> None:
        """普通信息日志（黄色，进行中）。

        Args:
            msg: 信息消息。
        """
        self._logger.info("%s  %s%s", _COLOR_YELLOW, msg, _COLOR_RESET)

    def warn(self, msg: str) -> None:
        """警告日志（黄色，进行中）。

        Args:
            msg: 警告消息。
        """
        self._logger.warning("%s  [警告] %s%s", _COLOR_YELLOW, msg, _COLOR_RESET)
