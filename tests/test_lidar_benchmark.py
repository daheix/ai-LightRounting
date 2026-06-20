"""LiDAR 公开 Benchmark 加载与验证测试。

测试 LiDAR (ISPD 2025) 公开 benchmark 的加载、解析、规模量化。
9 个 benchmark 覆盖 6-319 器件规模，对标 Apollo/LiDAR 论文。

来源:
- LiDAR 仓库: https://github.com/ScopeX-ASU/LiDAR (MIT)
- LiDAR 论文: Zhou et al., "Automated Curvy Waveguide Detailed Routing",
  ISPD 2025, https://arxiv.org/abs/2410.01260
- Apollo 论文: Zhou et al., "Automated Routing-Informed Placement",
  ICCAD 2025, https://arxiv.org/abs/2504.18813
"""

from __future__ import annotations

from pathlib import Path

import pytest

from polaris.data.data_loader import load_pic_ir

LIDAR_DIR = Path(__file__).resolve().parent.parent / "data" / "benchmarks" / "lidar"

# 9 个 LiDAR benchmark 的预期规模（devices, connections）
# 来源: 实际加载验证 2026-06-20
EXPECTED_BENCHMARKS = {
    "toy_example": (6, 2),
    "clements_8x8": (52, 79),
    "clements_16x16": (168, 287),
    "mrr_weight_bank_4x4": (31, 30),
    "mrr_weight_bank_8x8": (95, 94),
    "mrr_weight_bank_16x16": (319, 318),
    "multiportmmi_8x8": (82, 111),
    "multiportmmi_16x16": (162, 223),
    "multiportmmi_32x32": (318, 447),
}


def _find_benchmark_yml(name: str) -> Path:
    """查找 benchmark YAML 文件（容忍目录结构差异）。"""
    candidates = list(LIDAR_DIR.rglob(f"{name}*.yml"))
    if not candidates:
        pytest.skip(f"Benchmark {name} 不存在（data/benchmarks/lidar/ 未安装）")
    return candidates[0]


@pytest.fixture(scope="module")
def lidar_dir() -> Path:
    """LiDAR benchmark 根目录。"""
    if not LIDAR_DIR.exists():
        pytest.skip("LiDAR benchmark 未安装（data/benchmarks/lidar/ 不存在）")
    return LIDAR_DIR


class TestLiDARBenchmarkLoading:
    """LiDAR benchmark 加载测试。"""

    def test_lidar_dir_exists(self, lidar_dir: Path) -> None:
        """验证 LiDAR benchmark 目录存在。"""
        assert lidar_dir.exists(), f"LiDAR 目录不存在: {lidar_dir}"
        yml_files = list(lidar_dir.rglob("*.yml"))
        assert len(yml_files) >= 9, f"应有 ≥9 个 YAML，实际 {len(yml_files)}"

    def test_lidar_license_exists(self, lidar_dir: Path) -> None:
        """验证 MIT 许可证文件存在（合规性）。"""
        assert (lidar_dir / "LICENSE").exists(), "LICENSE 文件缺失"

    @pytest.mark.parametrize("name,expected", list(EXPECTED_BENCHMARKS.items()))
    def test_benchmark_loads(self, name: str, expected: tuple[int, int]) -> None:
        """验证每个 benchmark 能正确加载，器件数和连接数符合预期。"""
        path = _find_benchmark_yml(name)
        circuit = load_pic_ir(path)
        n_dev, n_conn = expected
        assert len(circuit.devices) == n_dev, (
            f"{name}: 器件数 {len(circuit.devices)} != 预期 {n_dev}"
        )
        assert len(circuit.connections) == n_conn, (
            f"{name}: 连接数 {len(circuit.connections)} != 预期 {n_conn}"
        )

    @pytest.mark.parametrize("name,expected", list(EXPECTED_BENCHMARKS.items()))
    def test_benchmark_ports_inferred(self, name: str, expected: tuple[int, int]) -> None:
        """验证端口从 component 类型正确推断（LiDAR YAML 不含 ports 字段）。"""
        path = _find_benchmark_yml(name)
        circuit = load_pic_ir(path)
        for dev in circuit.devices:
            if dev.device_type in {
                "mmi1x2",
                "mzi",
                "grating_coupler_elliptical_lumerical",
                "ring_single_pn",
                "ring_double_pn",
                "straight",
                "straight_heater_metal_undercut",
            }:
                assert len(dev.ports) >= 1, (
                    f"{name}/{dev.name}({dev.device_type}): 端口未推断"
                )

    def test_python_tuple_tag_parsed(self) -> None:
        """验证 !!python/tuple 标签能被解析（clements 系列含此标签）。"""
        path = _find_benchmark_yml("clements_8x8")
        circuit = load_pic_ir(path)
        # clements_8x8 的 gc1 含 !!python/tuple 参数，若解析失败会抛异常
        gc1 = next((d for d in circuit.devices if d.name == "gc1"), None)
        assert gc1 is not None, "gc1 器件未加载"
        assert gc1.device_type == "grating_coupler_elliptical_lumerical"


class TestLiDARBenchmarkScale:
    """LiDAR benchmark 规模量化（对标 Apollo/LiDAR 论文）。"""

    def test_scale_range_covers_small_to_large(self, lidar_dir: Path) -> None:
        """验证 benchmark 规模覆盖 6-319 器件（对标 Apollo 100-10k）。"""
        sizes: list[int] = []
        for name in EXPECTED_BENCHMARKS:
            path = _find_benchmark_yml(name)
            circuit = load_pic_ir(path)
            sizes.append(len(circuit.devices))
        assert min(sizes) <= 10, f"最小规模 {min(sizes)} 过大"
        assert max(sizes) >= 300, f"最大规模 {max(sizes)} 不足（应≥300 对标 Apollo）"

    def test_total_benchmark_count(self, lidar_dir: Path) -> None:
        """验证至少 9 个 benchmark（对标 Apollo 论文 Table 1）。"""
        yml_files = list(lidar_dir.rglob("*.yml"))
        assert len(yml_files) >= 9

    def test_benchmark_types_diverse(self, lidar_dir: Path) -> None:
        """验证 benchmark 类型多样（Clements/MRR/MMI 三类架构）。"""
        types: set[str] = set()
        for name in EXPECTED_BENCHMARKS:
            path = _find_benchmark_yml(name)
            circuit = load_pic_ir(path)
            for dev in circuit.devices:
                types.add(dev.device_type)
        # 应至少覆盖 5 种器件类型
        assert len(types) >= 5, f"器件类型仅 {len(types)} 种: {types}"


class TestLiDARBenchmarkConnectivity:
    """LiDAR benchmark 连接性验证。"""

    def test_all_connections_reference_valid_devices(self) -> None:
        """验证所有连接引用的器件名都存在于 devices 列表中。"""
        path = _find_benchmark_yml("clements_8x8")
        circuit = load_pic_ir(path)
        dev_names = {d.name for d in circuit.devices}
        for src_dev, _src_port, dst_dev, _dst_port in circuit.connections:
            assert src_dev in dev_names, f"连接引用未知器件: {src_dev}"
            assert dst_dev in dev_names, f"连接引用未知器件: {dst_dev}"

    def test_no_self_loop_connections(self) -> None:
        """验证无自环连接（src == dst）。"""
        path = _find_benchmark_yml("mrr_weight_bank_4x4")
        circuit = load_pic_ir(path)
        for src_dev, _src_port, dst_dev, _dst_port in circuit.connections:
            assert src_dev != dst_dev, f"自环连接: {src_dev}"

    def test_connection_count_reasonable(self) -> None:
        """验证连接数与器件数比例合理（toy_example 除外，非玩具 0.5-3.0 倍）。"""
        for name, (n_dev, n_conn) in EXPECTED_BENCHMARKS.items():
            if name == "toy_example" or n_dev < 5:
                continue
            ratio = n_conn / n_dev
            assert 0.5 <= ratio <= 3.0, (
                f"{name}: 连接/器件比 {ratio:.2f} 超出 [0.5, 3.0]"
            )
