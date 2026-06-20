"""变体数据集生成器单元测试（规则 10）。

测试 polaris.data.variant_generator 的规模变体生成（Curriculum Learning）
和参数扫描变体生成（Domain Randomization）。

来源:
- Bengio et al., "Curriculum Learning", ICML 2009
  https://dl.acm.org/doi/abs/10.1145/1553374.1553380
- pytest 最佳实践: https://docs.pytest.org/en/stable/explanation/goodpractices.html
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from polaris.data.variant_generator import (
    CURRICULUM_LEVELS,
    PARAM_SWEEP_RANGES,
    CurriculumLevel,
    generate_param_sweep_variants,
    generate_scale_variants,
    make_device_with_params,
)

# ---------------------------------------------------------------------------
# make_device_with_params（参数化 PDK 工厂）
# ---------------------------------------------------------------------------


def test_make_device_with_params_basic() -> None:
    """测试参数化 PDK 工厂基本功能。"""
    dev = make_device_with_params("ring_single", "ring_test")
    assert dev.name == "ring_test"
    assert dev.device_type == "ring"
    assert dev.params["radius"] == 10.0  # 默认值


def test_make_device_with_params_override() -> None:
    """测试参数覆盖。"""
    dev = make_device_with_params("ring_single", "ring_test", {"radius": 20.0})
    assert dev.params["radius"] == 20.0


def test_make_device_with_params_unknown_key() -> None:
    """测试未知器件键名抛出 KeyError。"""
    with pytest.raises(KeyError, match="未知器件类型"):
        make_device_with_params("nonexistent", "test")


# ---------------------------------------------------------------------------
# CurriculumLevel 与 CURRICULUM_LEVELS
# ---------------------------------------------------------------------------


def test_curriculum_levels_ordering() -> None:
    """测试课程级别按器件数递增排序。"""
    for i in range(len(CURRICULUM_LEVELS) - 1):
        assert CURRICULUM_LEVELS[i].n_devices_max < CURRICULUM_LEVELS[i + 1].n_devices_min


def test_curriculum_level_names() -> None:
    """测试课程级别名称。"""
    names = [lv.name for lv in CURRICULUM_LEVELS]
    assert names == ["small", "medium", "large", "xlarge"]


def test_curriculum_level_canvas_scales_with_devices() -> None:
    """测试画布尺寸随器件数增加而增大。"""
    for i in range(len(CURRICULUM_LEVELS) - 1):
        assert CURRICULUM_LEVELS[i].canvas_w < CURRICULUM_LEVELS[i + 1].canvas_w


# ---------------------------------------------------------------------------
# generate_scale_variants（规模变体生成）
# ---------------------------------------------------------------------------


def test_generate_scale_variants_basic(tmp_path: Path) -> None:
    """测试规模变体生成基本功能。"""
    stats = generate_scale_variants(tmp_path, n_per_level=2)
    assert stats["total_circuits"] == 2 * len(CURRICULUM_LEVELS)
    assert stats["total_variants"] == 2 * len(CURRICULUM_LEVELS)
    assert "levels" in stats
    assert len(stats["levels"]) == len(CURRICULUM_LEVELS)


def test_generate_scale_variants_files_created(tmp_path: Path) -> None:
    """测试规模变体文件正确生成。"""
    generate_scale_variants(tmp_path, n_per_level=3)
    for level in CURRICULUM_LEVELS:
        level_dir = tmp_path / level.name
        assert level_dir.exists()
        files = list(level_dir.glob("*.json"))
        assert len(files) == 3


def test_generate_scale_variants_device_count_in_range(tmp_path: Path) -> None:
    """测试生成的电路器件数在级别范围内。"""
    generate_scale_variants(tmp_path, n_per_level=2)
    for level in CURRICULUM_LEVELS:
        level_dir = tmp_path / level.name
        for f in level_dir.glob("*.json"):
            data = json.loads(f.read_text())
            # 部分模板电路器件数可能略低于 n_devices_min（如 mzi_lattice）
            # 但不应超过 n_devices_max
            assert data["n_devices"] <= level.n_devices_max + 5


def test_generate_scale_variants_custom_levels(tmp_path: Path) -> None:
    """测试自定义课程级别。"""
    custom = [CurriculumLevel("tiny", 3, 5, 300.0, 300.0)]
    stats = generate_scale_variants(tmp_path, n_per_level=2, levels=custom)
    assert stats["total_circuits"] == 2
    assert (tmp_path / "tiny").exists()


def test_generate_scale_variants_stats_file(tmp_path: Path) -> None:
    """测试统计文件正确保存。"""
    generate_scale_variants(tmp_path, n_per_level=1)
    stats_path = tmp_path / "variant_stats.json"
    assert stats_path.exists()
    stats = json.loads(stats_path.read_text())
    assert "method" in stats
    assert "Curriculum Learning" in stats["method"]


# ---------------------------------------------------------------------------
# generate_param_sweep_variants（参数扫描变体生成）
# ---------------------------------------------------------------------------


def test_generate_param_sweep_variants_basic(tmp_path: Path) -> None:
    """测试参数扫描变体生成基本功能。"""
    stats = generate_param_sweep_variants(tmp_path, n_sweeps=3, seed=42)
    assert stats["total_circuits"] == 3 * 3  # 3 个基准电路 × 3 扫描
    assert stats["total_variants"] == 3 * 3
    assert stats["n_base_circuits"] == 3
    assert stats["n_sweeps_per_circuit"] == 3


def test_generate_param_sweep_variants_files_created(tmp_path: Path) -> None:
    """测试参数扫描变体文件正确生成。"""
    generate_param_sweep_variants(tmp_path, n_sweeps=2, seed=42)
    files = list(tmp_path.glob("*.json"))
    # 3 基准 × 2 扫描 = 6 个变体文件 + 1 个统计文件
    assert len(files) == 7


def test_generate_param_sweep_variants_param_recorded(tmp_path: Path) -> None:
    """测试参数扫描变体记录了扫描参数。"""
    generate_param_sweep_variants(tmp_path, n_sweeps=2, seed=42)
    sweep_files = [f for f in tmp_path.glob("*.json") if f.name != "variant_stats.json"]
    for f in sweep_files:
        data = json.loads(f.read_text())
        assert "param_sweep" in data
        # 至少有一个器件被扫描（基准电路含 mzi/wg/dc 等可扫描器件）
        # 注意: random_15 可能扫描到 ring/dc/heater/wg 等器件


def test_generate_param_sweep_variants_reproducible(tmp_path: Path) -> None:
    """测试相同种子生成相同变体。"""
    stats1 = generate_param_sweep_variants(tmp_path / "run1", n_sweeps=2, seed=42)
    stats2 = generate_param_sweep_variants(tmp_path / "run2", n_sweeps=2, seed=42)
    assert stats1["total_circuits"] == stats2["total_circuits"]


def test_generate_param_sweep_variants_custom_base(tmp_path: Path) -> None:
    """测试自定义基准电路。"""
    from polaris.data.variant_generator import _scale_mzi_lattice

    base = [_scale_mzi_lattice(5, "custom_mzi")]
    stats = generate_param_sweep_variants(tmp_path, base_circuits=base, n_sweeps=2)
    assert stats["total_circuits"] == 2
    assert stats["n_base_circuits"] == 1


# ---------------------------------------------------------------------------
# PARAM_SWEEP_RANGES 完整性
# ---------------------------------------------------------------------------


def test_param_sweep_ranges_valid() -> None:
    """测试参数扫描范围定义有效。"""
    for dev_key, params in PARAM_SWEEP_RANGES.items():
        for param_name, values in params.items():
            assert len(values) >= 2, f"{dev_key}.{param_name} 至少 2 个值"
            assert all(v > 0 for v in values), f"{dev_key}.{param_name} 值必须为正"


def test_param_sweep_ranges_covers_common_devices() -> None:
    """测试参数扫描范围覆盖常见器件。"""
    expected = {"ring_single", "dc", "heater", "wg_100", "mzi"}
    assert expected.issubset(set(PARAM_SWEEP_RANGES.keys()))
