"""polaris-eme 2D EME 求解器测试套件（solve_eme_2d / mode_overlap_2d）。

覆盖 2D 任意截面 EME 全公开 API: mode_overlap_2d（2D 重叠积分）+
solve_eme_2d（多段 2D 波导级联，委托 polaris_fde.solve_modes 求模场 +
公共网格重采样 + Redheffer 星积级联）。

================================================================
学术诚信文献溯源（R02，≥5 篇）
================================================================
1. Bienstman 2001 PhD §2.3（2D EME 模式匹配 + Redheffer 星积）
   https://www.photonics.intec.ugent.be/download/phd_bienstman.pdf
2. Smit & van Dam 1996 IEEE/OSA JLT 14(7) 1746（模式展开理论）
   https://doi.org/10.1109/50.511954
3. Lumerical EME 2D 文档
   https://optics.ansys.com/hc/en-us/articles/360034902413
4. Snyder & Love 1983 "Optical Waveguide Theory"（模式正交性）
   https://link.springer.com/book/10.1007/978-94-009-6875-2
5. Collin 2001 "Foundations for Microwave Engineering" §5.1（阻抗反射）
   https://ieeexplore.ieee.org/book/5263073
6. Marcuse 1981 "Light Transmission Optics" §8.5（模式匹配 E/H 连续性）
   https://onlinelibrary.wiley.com/doi/book/10.1002/9783527619742
7. Soref 1993 IEEE JQE（Si/SiO2 折射率 3.476/1.444）
   https://ieeexplore.ieee.org/document/1148303

================================================================
合规声明
================================================================
- R02 学术诚信: 文献 URL 可溯源，SOI 折射率取自 Soref 1993
- R03 禁止 fall-back: 测试用真实 FDE 模场，无 mock 假数据
- R04 不参与 GPU: 纯 NumPy/SciPy CPU 实现
- R05 无 TODO/FIXME/HACK 残留
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

# 让测试既能从已安装包导入，也能从源码树导入
_SRC = str(Path(__file__).resolve().parents[1] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
# 2D EME 依赖 polaris_fde，补充其源码路径
_FDE_SRC = str(Path(__file__).resolve().parents[2] / "fde" / "src")
if _FDE_SRC not in sys.path:
    sys.path.insert(0, _FDE_SRC)

from polaris_eme import mode_overlap_2d, solve_eme_2d  # noqa: E402


# =============================================================================
# mode_overlap_2d 2D 模场重叠积分（Snyder & Love 1983 / Marcuse 1981）
# =============================================================================


class TestModeOverlap2d:
    """2D 模场重叠积分 ∫∫ E_a · E_b* dx dy。"""

    def test_overlap_same_normalized_field(self):
        """同场（已功率归一化 ∫∫|E|²dxdy=1）重叠 = 1。"""
        nx, ny, dx, dy = 40, 40, 0.05, 0.05
        x = np.arange(nx) * dx
        y = np.arange(ny) * dy
        xx, yy = np.meshgrid(x, y, indexing="ij")
        field = np.exp(-((xx - 1.0) ** 2 + (yy - 1.0) ** 2) / 0.1)
        norm = math.sqrt(np.sum(np.abs(field) ** 2) * dx * dy)
        field = field / norm
        overlap = mode_overlap_2d(field, field, dx, dy)
        assert abs(overlap - 1.0) < 1e-9, (
            f"同场重叠应 = 1.0，得到 {overlap}"
        )

    def test_overlap_orthogonal_fields_zero(self):
        """正交 2D 场（sin_x·cos_y 与 cos_x·sin_y）重叠 ≈ 0。"""
        nx, ny, dx, dy = 50, 50, 0.05, 0.05
        x = np.arange(nx) * dx
        y = np.arange(ny) * dy
        xx, yy = np.meshgrid(x, y, indexing="ij")
        Lx, Ly = nx * dx, ny * dy
        a = np.sin(2 * math.pi * xx / Lx) * np.cos(2 * math.pi * yy / Ly)
        b = np.cos(2 * math.pi * xx / Lx) * np.sin(2 * math.pi * yy / Ly)
        overlap = mode_overlap_2d(a, b, dx, dy)
        assert abs(overlap) < 1e-9, (
            f"正交场重叠应 ≈ 0，得到 {overlap}"
        )

    def test_overlap_returns_complex(self):
        """返回类型为 complex。"""
        f = np.ones((5, 5))
        overlap = mode_overlap_2d(f, f, 0.1, 0.1)
        assert isinstance(overlap, complex), (
            f"overlap 应为 complex，得到 {type(overlap)}"
        )

    def test_overlap_accepts_dict_with_field_2d(self):
        """接受含 field_2d 的 dict（与 polaris_fde.solve_modes 输出一致）。"""
        f = np.ones((4, 4))
        overlap = mode_overlap_2d({"field_2d": f.tolist()}, {"field_2d": f}, 0.1, 0.1)
        assert abs(overlap - 16.0 * 0.1 * 0.1) < 1e-12

    def test_overlap_invalid_shape(self):
        """形状不匹配 raise（R03 禁止 fall-back）。"""
        a = np.ones((4, 4))
        b = np.ones((3, 3))
        with pytest.raises(ValueError, match="2D 模场形状不匹配"):
            mode_overlap_2d(a, b, 0.1, 0.1)

    def test_overlap_invalid_dx(self):
        """dx_um <= 0 raise（R03 禁止 fall-back）。"""
        f = np.ones((4, 4))
        with pytest.raises(ValueError, match="dx_um"):
            mode_overlap_2d(f, f, 0.0, 0.1)
        with pytest.raises(ValueError, match="dx_um"):
            mode_overlap_2d(f, f, -0.1, 0.1)

    def test_overlap_invalid_1d_field(self):
        """1D 场 raise（R03 禁止 fall-back）。"""
        f = np.ones(5)
        with pytest.raises(ValueError, match="模场须 2D"):
            mode_overlap_2d(f, f, 0.1, 0.1)


# =============================================================================
# solve_eme_2d 端到端 2D EME 求解器
# =============================================================================


class TestSolveEme2d:
    """2D EME 多段均匀 2D 波导级联端到端测试。

    来源: Bienstman 2001 / Smit 1996 / Lumerical EME 2D
    """

    def _make_soi_section(self, width_um=0.5, length_um=5.0):
        """SOI 220nm 截面段（Si 3.476 / SiO2 1.444，Soref 1993）。"""
        return {
            "width_um": width_um,
            "height_um": 0.22,
            "length_um": length_um,
            "n_core": 3.476,
            "n_clad": 1.444,
        }

    def test_solve_eme_2d_straight_waveguide(self):
        """直波导（单段）: |T| ≈ 1（无界面，仅相位传播）。"""
        result = solve_eme_2d(
            sections=[self._make_soi_section(length_um=5.0)],
            wavelength_um=1.55, n_modes_per_section=2,
            dx_um=0.02, dy_um=0.02, pad_um=1.0,
        )
        t_abs = abs(result["transmission"])
        assert math.isclose(t_abs, 1.0, rel_tol=1e-9), (
            f"单段直波导 |T| 应 = 1，得到 {t_abs}"
        )
        r_abs = abs(result["reflection"])
        assert r_abs < 1e-10, f"单段反射应 ≈ 0，得到 {r_abs}"
        assert result["n_sections"] == 1

    def test_solve_eme_2d_taper(self):
        """锥形（宽→窄）: 0 < |T| < 1（有界面反射）。"""
        result = solve_eme_2d(
            sections=[
                self._make_soi_section(width_um=1.0, length_um=3.0),
                self._make_soi_section(width_um=0.5, length_um=3.0),
            ],
            wavelength_um=1.55, n_modes_per_section=2,
            dx_um=0.02, dy_um=0.02, pad_um=1.0,
        )
        t_abs = abs(result["transmission"])
        assert 0.0 < t_abs < 1.0, f"锥形 |T| 应在 (0,1)，得到 {t_abs}"
        r_abs = abs(result["reflection"])
        assert r_abs > 0, f"锥形反射应 > 0，得到 {r_abs}"
        assert r_abs < 0.2, f"锥形 |R| 应 < 0.2，得到 {r_abs}"
        # 功率守恒（单模近似上界）
        assert t_abs ** 2 + r_abs ** 2 <= 1.0 + 1e-9

    def test_solve_eme_2d_uniform_multisection(self):
        """多段相同波导: |T| ≈ 1（无界面失配）。"""
        result = solve_eme_2d(
            sections=[
                self._make_soi_section(length_um=3.0),
                self._make_soi_section(length_um=3.0),
            ],
            wavelength_um=1.55, n_modes_per_section=2,
            dx_um=0.02, dy_um=0.02, pad_um=1.0,
        )
        t_abs = abs(result["transmission"])
        assert math.isclose(t_abs, 1.0, rel_tol=1e-6), (
            f"多段相同波导 |T| 应 = 1，得到 {t_abs}"
        )
        assert result["n_sections"] == 2

    def test_solve_eme_2d_metadata_complete(self):
        """返回结果元数据完整。"""
        result = solve_eme_2d(
            sections=[self._make_soi_section(length_um=5.0)],
            wavelength_um=1.55,
        )
        for key in ("s_matrix", "modes_per_section", "wavelength_um",
                    "transmission", "reflection", "n_sections"):
            assert key in result, f"结果缺 {key}"
        assert result["wavelength_um"] == 1.55
        s_mat = np.array(result["s_matrix"])
        assert s_mat.shape == (2, 2)
        # 每段模式信息含 neff/beta
        m0 = result["modes_per_section"][0]
        for key in ("index", "width_um", "height_um", "length_um",
                    "n_core", "n_clad", "neff", "beta"):
            assert key in m0, f"modes_per_section[0] 缺 {key}"

    def test_solve_eme_2d_neff_in_guide_range(self):
        """各段基模 neff ∈ (n_clad, n_core)。"""
        result = solve_eme_2d(
            sections=[
                self._make_soi_section(width_um=1.0, length_um=3.0),
                self._make_soi_section(width_um=0.5, length_um=3.0),
            ],
            wavelength_um=1.55,
        )
        for m in result["modes_per_section"]:
            assert 1.444 < m["neff"] < 3.476, (
                f"neff {m['neff']} 应在 (1.444, 3.476)"
            )

    def test_solve_eme_2d_three_section_taper(self):
        """三段锥形（宽→窄→宽）: |T| 有限且 < 1。"""
        result = solve_eme_2d(
            sections=[
                self._make_soi_section(width_um=1.0, length_um=2.0),
                self._make_soi_section(width_um=0.5, length_um=2.0),
                self._make_soi_section(width_um=1.0, length_um=2.0),
            ],
            wavelength_um=1.55,
        )
        t_abs = abs(result["transmission"])
        assert 0.0 < t_abs <= 1.0
        assert result["n_sections"] == 3

    def test_solve_eme_2d_invalid_empty_sections(self):
        """空 sections raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="sections 不能为空"):
            solve_eme_2d(sections=[])

    def test_solve_eme_2d_invalid_wavelength(self):
        """非法 wavelength ≤ 0 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="wavelength_um"):
            solve_eme_2d(
                sections=[self._make_soi_section()], wavelength_um=0.0,
            )

    def test_solve_eme_2d_invalid_dx(self):
        """dx_um <= 0 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="dx_um"):
            solve_eme_2d(
                sections=[self._make_soi_section()], dx_um=0.0,
            )

    def test_solve_eme_2d_invalid_dy(self):
        """dy_um <= 0 raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="dy_um"):
            solve_eme_2d(
                sections=[self._make_soi_section()], dy_um=0.0,
            )

    def test_solve_eme_2d_section_missing_field(self):
        """段缺少 height_um raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="缺少必需字段"):
            solve_eme_2d(sections=[{"width_um": 0.5, "length_um": 5.0,
                                    "n_core": 3.476, "n_clad": 1.444}])

    def test_solve_eme_2d_section_not_dict(self):
        """段非 dict raise（R03 禁止 fall-back）。"""
        with pytest.raises(ValueError, match="段 0 须 dict"):
            solve_eme_2d(sections=["not_a_dict"])
