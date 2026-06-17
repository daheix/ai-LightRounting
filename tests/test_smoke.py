"""冒烟测试：验证 polaris 包可导入并暴露版本号。"""

import polaris


def test_polaris_importable() -> None:
    """polaris 包应可被导入。"""
    assert polaris is not None


def test_polaris_version() -> None:
    """polaris 应暴露字符串形式的 __version__。"""
    assert isinstance(polaris.__version__, str)
    assert polaris.__version__ == "0.1.0"
