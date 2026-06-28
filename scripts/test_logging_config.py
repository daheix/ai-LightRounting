"""logging_config 模块单元测试。

覆盖 spec 要求的 4 个测试用例：
1. get_logger() 返回有效 logger，可写日志
2. 日志文件达到 max_bytes 时自动轮转（生成 .1 备份）
3. 日志目录不可写时 raise RuntimeError
4. 重复调用 get_logger 不产生重复 handler

来源（R02 学术诚信）:
    [1] Python logging: https://docs.python.org/3/library/logging.html
    [2] RotatingFileHandler:
        https://docs.python.org/3/library/logging.handlers.html#rotatingfilehandler
    [3] pytest 官方文档: https://docs.pytest.org/en/stable/
    [4] unittest.mock: https://docs.python.org/3/library/unittest.mock.html
    [5] logging cookbook: https://docs.python.org/3/howto/logging-cookbook.html
"""

import logging

import pytest

from scripts.logging_config import get_logger


@pytest.fixture(autouse=True)
def _reset_loggers():
    """每个测试后清理所有非 root logger 的 handler，防止 FD 泄漏与跨测试污染。"""
    yield
    for lg in list(logging.Logger.manager.loggerDict.values()):
        if isinstance(lg, logging.Logger):
            for handler in list(lg.handlers):
                handler.close()
                lg.removeHandler(handler)


def test_get_logger_returns_valid_logger(tmp_path):
    """测试 1：get_logger() 返回有效 logger，可写日志到文件。"""
    log = get_logger("test_basic", log_dir=str(tmp_path))
    assert isinstance(log, logging.Logger)
    log.info("hello world")
    log_path = tmp_path / "test_basic.log"
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "hello world" in content


def test_rotation_creates_backup(tmp_path):
    """测试 2：日志文件达到 max_bytes 时自动轮转，生成 .1 备份。"""
    log = get_logger(
        "test_rotation",
        log_dir=str(tmp_path),
        max_bytes=100,
        backup_count=1,
    )
    long_msg = "X" * 200
    # 写入多条超长消息，触发轮转
    for _ in range(3):
        log.info(long_msg)
    backup_path = tmp_path / "test_rotation.log.1"
    assert backup_path.exists()


def test_unwritable_dir_raises(tmp_path):
    """测试 3：日志目录不可写时 raise RuntimeError。

    用一个文件占位作为目录父级，使 os.makedirs 触发 NotADirectoryError
    （OSError 子类），从而验证 RuntimeError 转换路径（R03 禁止 fall-back）。
    """
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    bad_log_dir = str(blocker / "subdir")
    with pytest.raises(RuntimeError):
        get_logger("test_unwritable", log_dir=bad_log_dir)


def test_no_duplicate_handlers(tmp_path):
    """测试 4：重复调用 get_logger 不产生重复 handler。"""
    log = get_logger("test_dup", log_dir=str(tmp_path))
    count1 = len(log.handlers)
    log2 = get_logger("test_dup", log_dir=str(tmp_path))
    count2 = len(log2.handlers)
    # 同名 logger 是全局单例
    assert log is log2
    # 两次调用后 handler 数量一致（文件 + 控制台 = 2）
    assert count1 == count2 == 2
