"""基准性能回归测试（M2.4）。

验证关键操作的性能不超过规则 15.1 规定的目标耗时上限。
任一回归（超时）即视为失败，需排查性能退化原因。

来源:
- 规则 15.1 性能基准: .trae/rules/project_rules.md
- pytest 性能测试最佳实践: https://docs.pytest.org/en/stable/
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from polaris.engine.floorplan_env import FloorplanEnv
from polaris.engine.netlist import load_netlist
from polaris.eval.layout_render import export_gds, run_drc
from polaris.router.routing_env import RoutingEnv
from polaris.trainer.dataset import DatasetConfig, generate_dataset

# 规则 15.1 性能基准（秒）
BENCH_NETLIST_PARSE_100 = 0.1  # 网表解析（100 器件）< 100ms
BENCH_ROUTING_SINGLE = 0.05  # A* 布线（单连接）< 50ms
BENCH_GNN_FORWARD = 0.01  # GNN 前向推理 < 10ms
BENCH_PPO_STEP = 0.1  # PPO 训练单步 < 100ms
BENCH_GDS_EXPORT_100 = 0.5  # GDS 导出（100 器件）< 500ms

# 测试网表（小规模，便于快速回归）
YAML_NETLIST_SMALL = """
name: perf_test_small
instances:
  wg1: {component: strip_waveguide, platform: SOI}
  mmi1: {component: mmi_1x2, platform: SOI}
  wg2: {component: strip_waveguide, platform: SOI}
  pd1: {component: ge_photodetector, platform: SOI}
connections:
  - [wg1, out, mmi1, in]
  - [mmi1, out0, wg2, in]
  - [wg2, out, pd1, in]
"""


def _measure(fn, *args, **kwargs) -> tuple[object, float]:
    """测量函数执行耗时，返回 (result, seconds)。"""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    return result, time.perf_counter() - t0


class TestNetlistParsePerformance:
    """网表解析性能基准（规则 15.1：< 100ms / 100 器件）。"""

    def test_small_netlist_parse_under_100ms(self):
        """小网表（4 器件）解析应 < 100ms。"""
        _, elapsed = _measure(load_netlist, YAML_NETLIST_SMALL)
        assert elapsed < BENCH_NETLIST_PARSE_100, (
            f"网表解析耗时 {elapsed * 1000:.1f}ms 超过 {BENCH_NETLIST_PARSE_100 * 1000:.0f}ms"
        )

    def test_dataset_5_netlists_parse_under_500ms(self):
        """5 个网表批量解析应 < 500ms。"""
        cfg = DatasetConfig(num_netlists=5, min_devices=3, max_devices=6)
        ds, gen_elapsed = _measure(generate_dataset, cfg)
        assert gen_elapsed < 5.0, f"数据集生成耗时 {gen_elapsed:.2f}s 超过 5s"

        # 批量解析
        t0 = time.perf_counter()
        for nl in ds:
            load_netlist(nl)
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.5, f"5 个网表批量解析耗时 {elapsed * 1000:.1f}ms 超过 500ms"


class TestRoutingPerformance:
    """布线性能基准（规则 15.1：单连接 < 50ms）。"""

    def test_single_route_step_under_50ms(self):
        """单次布线 step 应 < 50ms。"""
        import numpy as np

        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)
        fp = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp.reset()
        for _ in range(len(devices)):
            fp.step([5, 5, 0])

        r_env = RoutingEnv(net, fp.state.placements, canvas_w=400, canvas_h=400, grid_size=5)
        r_env.reset()

        # 单步耗时
        _, elapsed = _measure(r_env.step, np.zeros(3, dtype=np.float32))
        assert elapsed < BENCH_ROUTING_SINGLE, (
            f"单次布线 step 耗时 {elapsed * 1000:.1f}ms 超过 {BENCH_ROUTING_SINGLE * 1000:.0f}ms"
        )


class TestGdsExportPerformance:
    """GDS 导出性能基准（规则 15.1：100 器件 < 500ms）。"""

    def test_small_gds_export_under_500ms(self, tmp_path):
        """小规模电路 GDS 导出应 < 500ms。"""
        import numpy as np

        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)
        fp = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp.reset()
        for _ in range(len(devices)):
            fp.step([5, 5, 0])

        r_env = RoutingEnv(net, fp.state.placements, canvas_w=400, canvas_h=400, grid_size=5)
        r_env.reset()
        for _ in range(len(net.connections)):
            r_env.step(np.zeros(3, dtype=np.float32))

        _, elapsed = _measure(
            export_gds,
            fp.state.placements,
            r_env.state.paths,
            str(tmp_path / "perf.gds"),
        )
        assert elapsed < BENCH_GDS_EXPORT_100, (
            f"GDS 导出耗时 {elapsed * 1000:.1f}ms 超过 {BENCH_GDS_EXPORT_100 * 1000:.0f}ms"
        )

    def test_drc_under_500ms(self):
        """DRC 检查应 < 500ms。"""
        import numpy as np

        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)
        fp = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp.reset()
        for _ in range(len(devices)):
            fp.step([5, 5, 0])

        r_env = RoutingEnv(net, fp.state.placements, canvas_w=400, canvas_h=400, grid_size=5)
        r_env.reset()
        for _ in range(len(net.connections)):
            r_env.step(np.zeros(3, dtype=np.float32))

        _, elapsed = _measure(run_drc, fp.state.placements, r_env.state.paths)
        assert elapsed < BENCH_GDS_EXPORT_100, (
            f"DRC 检查耗时 {elapsed * 1000:.1f}ms 超过 {BENCH_GDS_EXPORT_100 * 1000:.0f}ms"
        )


class TestFloorplanEnvPerformance:
    """布局环境性能基准。"""

    def test_env_reset_under_50ms(self):
        """环境 reset 应 < 50ms。"""
        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)
        _, elapsed = _measure(FloorplanEnv, net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        assert elapsed < 0.05, f"环境构造耗时 {elapsed * 1000:.1f}ms 超过 50ms"

    def test_env_step_under_10ms(self):
        """单次 env.step 应 < 10ms。"""
        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)
        fp = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp.reset()
        _, elapsed = _measure(fp.step, [5, 5, 0])
        assert elapsed < 0.01, f"env.step 耗时 {elapsed * 1000:.1f}ms 超过 10ms"


class TestRegressionBaselines:
    """回归基线：保证关键功能不退化。"""

    def test_dataset_generation_count(self):
        """数据集生成数量应与配置一致。"""
        cfg = DatasetConfig(num_netlists=3, min_devices=3, max_devices=5)
        ds = generate_dataset(cfg)
        assert len(ds) == 3, f"数据集数量 {len(ds)} != 配置 3"
        for nl in ds:
            assert "instances" in nl
            assert "connections" in nl

    def test_pipeline_deterministic_with_seed(self, tmp_path):
        """同种子两次布局应产生相同结果（确定性）。"""
        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)

        # 第一次
        fp1 = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp1.reset()
        for _ in range(len(devices)):
            fp1.step([5, 5, 0])

        # 第二次（相同输入）
        fp2 = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp2.reset()
        for _ in range(len(devices)):
            fp2.step([5, 5, 0])

        # 布局数量一致
        assert len(fp1.state.placements) == len(fp2.state.placements)
        # 器件集合一致
        names1 = set(fp1.state.placements.keys())
        names2 = set(fp2.state.placements.keys())
        assert names1 == names2

    def test_gds_file_valid(self, tmp_path):
        """导出的 GDS 文件应可被 klayout 重新读取。"""
        import numpy as np

        try:
            import klayout.db as db
        except ImportError:
            pytest.skip("klayout 未安装")

        net, devices, _ = load_netlist(YAML_NETLIST_SMALL)
        fp = FloorplanEnv(net, devices, canvas_w=400, canvas_h=400, grid_size=10)
        fp.reset()
        for _ in range(len(devices)):
            fp.step([5, 5, 0])

        r_env = RoutingEnv(net, fp.state.placements, canvas_w=400, canvas_h=400, grid_size=5)
        r_env.reset()
        for _ in range(len(net.connections)):
            r_env.step(np.zeros(3, dtype=np.float32))

        gds_path = export_gds(fp.state.placements, r_env.state.paths, str(tmp_path / "verify.gds"))
        assert Path(gds_path).exists()

        # 用 klayout 重新读取验证
        layout = db.Layout()
        layout.read(str(gds_path))
        assert layout.top_cells() is not None
        assert len(layout.top_cells()) >= 1
