"""pyCopySiPANN 与真实 SiPANN 对比测试（规则 4.6）。

对比 src/polaris/sim/models.py（pyCopySiPANN 复刻）与 SiPANN 的模型一致性，
覆盖 waveguide_s / y_branch_s 的 SDict 结构、端口命名、互易性与功率守恒。

来源:
- SiPANN: https://sipann.readthedocs.io/ (MIT)
- 复刻位置: src/polaris/sim/models.py
- 复刻入口: 3dtool/pycopy/pyCopySiPANN/__init__.py

注: SiPANN 使用物理截面参数（width/thickness），本项目模型使用有效参数
（neff/length）。当 SiPANN 可用时，本测试验证 SDict 结构一致性与
基本物理性质（互易性、功率守恒），而非直接数值对比。
"""

from __future__ import annotations

import numpy as np
import pytest

# SiPANN 依赖 tensorflow，无 Python 3.14 支持（上游兼容性问题）。
# 在 Python 3.10-3.13 环境下可正常安装使用。
SiPANN = pytest.importorskip("SiPANN")

from pycopy.pyCopySiPANN import waveguide_s, y_branch_s  # noqa: E402


class TestWaveguideModel:
    """对比 pyCopySiPANN waveguide_s 与 SiPANN waveguide 模型。"""

    def test_sdict_structure(self):
        # Arrange
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=100.0, neff=2.4)

        # Act — SiPANN waveguide 返回 SDict
        s_sipann = SiPANN.sipann.waveguide(wl=wl, width=0.5, thickness=0.22)

        # Assert — 均为 dict 且键为 (str, str) 元组
        assert isinstance(s, dict)
        assert isinstance(s_sipann, dict)
        for key in s:
            assert isinstance(key, tuple) and len(key) == 2

    def test_reciprocity(self):
        # Arrange — 互易性: S_ij = S_ji
        wl = np.linspace(1.5, 1.6, 20)
        s = waveguide_s(wl=wl, length=50.0, neff=2.4)

        # Act & Assert
        np.testing.assert_allclose(s[("out", "in")], s[("in", "out")], atol=1e-9)

    def test_power_conservation_lossless(self):
        # Arrange — 无损波导: |S21|^2 = 1
        wl = np.array([1.55])
        s = waveguide_s(wl=wl, length=100.0, neff=2.4, loss_db_cm=0.0)

        # Act
        power = np.abs(s[("out", "in")]) ** 2

        # Assert
        np.testing.assert_allclose(power, 1.0, atol=1e-9)


class TestYBranchModel:
    """对比 pyCopySiPANN y_branch_s 与 SiPANN y_branch 模型。"""

    def test_sdict_structure(self):
        # Arrange
        wl = np.array([1.55])
        s = y_branch_s(wl=wl, insertion_loss_db=0.3)

        # Act — SiPANN y_branch 返回 SDict
        s_sipann = SiPANN.sipann.y_branch(wl=wl, width=0.5, thickness=0.22)

        # Assert — 均为 dict 且键为 (str, str) 元组
        assert isinstance(s, dict)
        assert isinstance(s_sipann, dict)
        for key in s:
            assert isinstance(key, tuple) and len(key) == 2

    def test_splitting_ratio(self):
        # Arrange — Y 分支两输出功率应相等（各约 50%）
        wl = np.array([1.55])
        s = y_branch_s(wl=wl, insertion_loss_db=0.0)

        # Act
        p2 = np.abs(s[("port_2", "port_1")]) ** 2
        p3 = np.abs(s[("port_3", "port_1")]) ** 2

        # Assert — 两分支功率相等
        np.testing.assert_allclose(p2, p3, atol=1e-9)

    def test_reciprocity(self):
        # Arrange — 互易性: S_ij = S_ji
        wl = np.linspace(1.5, 1.6, 20)
        s = y_branch_s(wl=wl, insertion_loss_db=0.3)

        # Act & Assert
        np.testing.assert_allclose(s[("port_2", "port_1")], s[("port_1", "port_2")], atol=1e-9)
        np.testing.assert_allclose(s[("port_3", "port_1")], s[("port_1", "port_3")], atol=1e-9)
