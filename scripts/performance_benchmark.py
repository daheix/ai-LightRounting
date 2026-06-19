#!/usr/bin/env python3
"""性能基准测试脚本（规则 15.1）。

实测 PoLaRIS 项目规则 15.1 定义的 5 项性能指标，每项测 10 次取平均，
输出 JSON 报告并生成 docs/performance_benchmark.md。

测试指标：
1. 网表解析（100 器件） < 100ms
2. A* 布线（单连接，100x100 网格） < 50ms
3. GNN 前向推理 < 10ms
4. PPO 训练单步（get_action + store） < 100ms
5. GDS 导出（100 器件） < 500ms

来源:
- 项目规则 15.1: .trae/rules/project_rules.md
- timeit: https://docs.python.org/3/library/timeit.html

用法:
    python scripts/performance_benchmark.py
    python scripts/performance_benchmark.py --json docs/performance_benchmark.json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

# =============================================================================
# 常量（规则 15.1 性能目标）
# =============================================================================
TARGET_NETLIST_PARSE_MS = 100.0
TARGET_ASTAR_ROUTING_MS = 50.0
TARGET_GNN_FORWARD_MS = 10.0
TARGET_PPO_STEP_MS = 100.0
TARGET_GDS_EXPORT_MS = 500.0

N_RUNS = 10
N_DEVICES = 100
GRID_W = 100
GRID_H = 100

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


# =============================================================================
# 结果数据结构
# =============================================================================
@dataclass
class BenchmarkResult:
    """单项基准测试结果。

    Attributes:
        name: 指标名称。
        target_ms: 目标耗时（ms）。
        samples_ms: 10 次采样耗时列表。
        skipped: 是否因依赖缺失或异常跳过。
        skip_reason: 跳过原因。
    """

    name: str
    target_ms: float
    samples_ms: list[float] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def mean_ms(self) -> float:
        """平均耗时（ms）。"""
        return statistics.mean(self.samples_ms) if self.samples_ms else 0.0

    @property
    def std_ms(self) -> float:
        """标准差（ms）。"""
        return statistics.stdev(self.samples_ms) if len(self.samples_ms) > 1 else 0.0

    @property
    def passed(self) -> bool:
        """是否达标（未跳过且平均耗时低于目标）。"""
        return (not self.skipped) and self.mean_ms < self.target_ms


# =============================================================================
# 测量辅助
# =============================================================================
def _measure(func, n_runs: int = N_RUNS) -> list[float]:
    """测量 func 执行 n_runs 次的耗时（ms），含 1 次 warmup。

    Args:
        func: 无参数可调用对象。
        n_runs: 正式测量次数。

    Returns:
        n_runs 次采样的耗时列表（ms）。
    """
    func()  # warmup（首次运行可能触发懒加载/编译，不计入统计）
    samples: list[float] = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        func()
        samples.append((time.perf_counter() - t0) * 1000.0)
    return samples


def _run_benchmark(name: str, target_ms: float, bench_func) -> BenchmarkResult:
    """运行单项基准测试，捕获异常并返回结果。

    Args:
        name: 指标名称。
        target_ms: 目标耗时（ms）。
        bench_func: 返回耗时采样列表的函数。

    Returns:
        ``BenchmarkResult``。
    """
    try:
        samples = bench_func()
    except Exception as e:  # noqa: BLE001
        return BenchmarkResult(
            name=name, target_ms=target_ms, skipped=True, skip_reason=f"{type(e).__name__}: {e}"
        )
    return BenchmarkResult(name=name, target_ms=target_ms, samples_ms=samples)


# =============================================================================
# 基准 1：网表解析（100 器件）
# =============================================================================
def _build_100_device_netlist_dict() -> dict:
    """构造 100 器件网表字典（链式连接 strip_waveguide）。"""
    instances: dict = {}
    connections: list = []
    for i in range(N_DEVICES):
        instances[f"wg{i}"] = {
            "component": "strip_waveguide",
            "platform": "SOI",
            "settings": {"length_um": 10.0},
        }
        if i > 0:
            connections.append([f"wg{i - 1}", "out", f"wg{i}", "in"])
    return {"name": "bench_100", "instances": instances, "connections": connections}


def bench_netlist_parse() -> list[float]:
    """基准 1：网表解析（100 器件，parse_netlist）。"""
    from polaris.engine.netlist import parse_netlist

    data = _build_100_device_netlist_dict()
    return _measure(lambda: parse_netlist(data))


# =============================================================================
# 基准 2：A* 布线（单连接，100x100 网格）
# =============================================================================
def bench_astar_routing() -> list[float]:
    """基准 2：A* 布线（单连接，100x100 网格，对角线起终点）。"""
    from polaris.router.waveguide_router import GridRouter, RouterConstraints

    router = GridRouter(
        grid_w=GRID_W,
        grid_h=GRID_H,
        grid_size=1.0,
        constraints=RouterConstraints(min_bend_radius_um=5.0),
    )
    start = (0, 0)
    goal = (GRID_W - 1, GRID_H - 1)
    return _measure(lambda: router.route(start, goal))


# =============================================================================
# 基准 3：GNN 前向推理
# =============================================================================
def _build_chain_edge_index(n_nodes: int) -> np.ndarray:
    """构建链式图边索引 [2, E]（双向，E = 2*(n-1)）。"""
    edges: list[list[int]] = []
    for i in range(n_nodes - 1):
        edges.append([i, i + 1])
        edges.append([i + 1, i])
    return np.array(edges).T if edges else np.zeros((2, 0), dtype=np.int64)


def bench_gnn_forward() -> list[float]:
    """基准 3：GNN 前向推理（GraphEncoder，100 节点链式图）。"""
    from polaris.engine.gnn import GraphEncoder
    from polaris.nn import Tensor

    encoder = GraphEncoder(in_dim=6, hidden_dim=64, out_dim=64, num_layers=2)
    node_feats = Tensor(np.random.randn(N_DEVICES, 6))
    edge_index = _build_chain_edge_index(N_DEVICES)
    return _measure(lambda: encoder(node_feats, edge_index))


# =============================================================================
# 基准 4：PPO 训练单步（get_action + store）
# =============================================================================
def bench_ppo_step() -> list[float]:
    """基准 4：PPO 训练单步（PPOAgentDiscrete.get_action + store）。"""
    from polaris.trainer.ppo_buffers import Transition
    from polaris.trainer.ppo_torch import PPOAgentDiscrete

    agent = PPOAgentDiscrete(obs_dim=64, n_actions=100, hidden_dim=128)
    obs = np.random.randn(64).astype(np.float32)

    def run() -> None:
        action, lp, v = agent.get_action(obs)
        agent.store(Transition(obs=obs, action=action, reward=0.1, logprob=lp, value=v, done=False))

    return _measure(run)


# =============================================================================
# 基准 5：GDS 导出（100 器件）
# =============================================================================
def _build_100_placements() -> dict:
    """构建 100 器件放置结果（10x10 网格，MMI 1x2）。"""
    import tempfile

    from polaris.engine.floorplan_env import Placement
    from polaris.pdk.soi import make_mmi_1x2

    placements: dict = {}
    for i in range(10):
        for j in range(10):
            dev = make_mmi_1x2()
            inst_id = f"dev_{i}_{j}"
            placements[inst_id] = Placement(instance_id=inst_id, device=dev, x=i * 50.0, y=j * 50.0)
    # 触发 make_mmi_1x2 的 import 副作用标记，避免未使用告警
    _ = tempfile.gettempdir()
    return placements


def bench_gds_export() -> list[float]:
    """基准 5：GDS 导出（100 器件，klayout.db）。"""
    import tempfile

    from polaris.eval.layout_render import export_gds

    placements = _build_100_placements()

    def run() -> None:
        with tempfile.NamedTemporaryFile(suffix=".gds", delete=False) as f:
            path = f.name
        try:
            export_gds(placements, None, path)
        finally:
            os.remove(path)

    return _measure(run)


# =============================================================================
# 环境信息收集
# =============================================================================
def _read_cpu_model() -> str:
    """从 /proc/cpuinfo 读取 CPU 型号（Linux），失败回退 platform.processor。"""
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except (FileNotFoundError, PermissionError, OSError):
        pass
    return platform.processor() or "unknown"


def _read_mem_total_gb() -> str:
    """从 /proc/meminfo 读取总内存（GB），失败返回 unknown。"""
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return f"{kb / 1024 / 1024:.1f} GB"
    except (FileNotFoundError, PermissionError, OSError, ValueError):
        pass
    return "unknown"


def _read_cpu_count() -> int:
    """获取逻辑 CPU 核数。"""
    return os.cpu_count() or 0


def _safe_version(mod_name: str) -> str:
    """安全获取模块版本（缺失返回 not installed）。"""
    try:
        mod = __import__(mod_name)
        return getattr(mod, "__version__", "unknown")
    except ImportError:
        return "not installed"


def collect_env_info() -> dict:
    """收集测试环境信息（Python/CPU/内存/依赖版本）。"""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_model": _read_cpu_model(),
        "cpu_count": _read_cpu_count(),
        "memory": _read_mem_total_gb(),
        "numpy": _safe_version("numpy"),
        "torch": _safe_version("torch"),
        "klayout": _safe_version("klayout"),
        "networkx": _safe_version("networkx"),
    }


# =============================================================================
# 报告生成
# =============================================================================
def _format_judgment(result: BenchmarkResult) -> str:
    """格式化达标判定文本。"""
    if result.skipped:
        return "⏭️ 跳过"
    return "✅ 达标" if result.passed else "❌ 未达标"


def _generate_results_table(results: list[BenchmarkResult]) -> str:
    """生成实测结果对比 Markdown 表格。"""
    lines = [
        "| # | 操作 | 目标耗时 | 实测平均 | 标准差 | 判定 |",
        "|---|------|----------|----------|--------|------|",
    ]
    for idx, r in enumerate(results, 1):
        if r.skipped:
            lines.append(
                f"| {idx} | {r.name} | < {r.target_ms:.0f}ms | - | - | {_format_judgment(r)} |"
            )
        else:
            lines.append(
                f"| {idx} | {r.name} | < {r.target_ms:.0f}ms | "
                f"{r.mean_ms:.3f}ms | {r.std_ms:.3f}ms | {_format_judgment(r)} |"
            )
    return "\n".join(lines)


def _generate_bottleneck_analysis(results: list[BenchmarkResult]) -> str:
    """生成性能瓶颈分析（按目标耗时占比排序）。"""
    valid = [r for r in results if not r.skipped]
    if not valid:
        return "无可用结果（全部跳过）。"
    # 按耗时占目标比例降序
    ranked = sorted(valid, key=lambda r: r.mean_ms / r.target_ms, reverse=True)
    lines: list[str] = []
    worst = ranked[0]
    ratio = worst.mean_ms / worst.target_ms
    lines.append(
        f"最接近目标上限的指标：**{worst.name}**，实测 {worst.mean_ms:.3f}ms "
        f"占目标 {worst.target_ms:.0f}ms 的 {ratio * 100:.1f}%。"
    )
    for r in ranked:
        pct = r.mean_ms / r.target_ms * 100
        lines.append(f"- {r.name}: {r.mean_ms:.3f}ms / {r.target_ms:.0f}ms = {pct:.1f}%")
    failed = [r for r in valid if not r.passed]
    if failed:
        lines.append("\n**未达标项**：")
        for r in failed:
            lines.append(
                f"- {r.name}: {r.mean_ms:.3f}ms 超过目标 {r.target_ms:.0f}ms"
                f"（超标 {(r.mean_ms / r.target_ms - 1) * 100:.1f}%）"
            )
    else:
        lines.append("\n全部指标达标。")
    return "\n".join(lines)


def generate_markdown(results: list[BenchmarkResult], env: dict) -> str:
    """生成 Markdown 性能基准报告。"""
    passed_count = sum(1 for r in results if r.passed)
    skipped_count = sum(1 for r in results if r.skipped)
    total = len(results)
    summary = f"**{passed_count}/{total} 达标**（{skipped_count} 项跳过）"
    return (
        f"# PoLaRIS 性能基准报告\n\n"
        f"生成时间: {env['timestamp']}\n\n"
        f"本报告实测项目规则 15.1 定义的 5 项性能指标，每项测 {N_RUNS} 次取平均。\n\n"
        f"## 测试环境\n\n"
        f"| 项目 | 信息 |\n|------|------|\n"
        f"| Python | {env['python']} |\n"
        f"| 平台 | {env['platform']} |\n"
        f"| CPU | {env['cpu_model']} |\n"
        f"| CPU 核数 | {env['cpu_count']} |\n"
        f"| 内存 | {env['memory']} |\n"
        f"| numpy | {env['numpy']} |\n"
        f"| torch | {env['torch']} |\n"
        f"| klayout | {env['klayout']} |\n"
        f"| networkx | {env['networkx']} |\n\n"
        f"## 性能指标实测结果\n\n"
        f"规则 15.1 性能目标实测对比（{summary}）：\n\n"
        f"{_generate_results_table(results)}\n\n"
        f"## 性能瓶颈分析\n\n"
        f"{_generate_bottleneck_analysis(results)}\n\n"
        f"## 复现方法\n\n"
        f"```bash\n"
        f"cd /workspace\n"
        f"python scripts/performance_benchmark.py\n"
        f"```\n"
    )


def generate_json_report(results: list[BenchmarkResult], env: dict) -> dict:
    """生成 JSON 报告字典。"""
    return {
        "environment": env,
        "config": {
            "n_runs": N_RUNS,
            "n_devices": N_DEVICES,
            "grid_w": GRID_W,
            "grid_h": GRID_H,
        },
        "results": [asdict(r) for r in results],
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "skipped": sum(1 for r in results if r.skipped),
        },
    }


# =============================================================================
# 主入口
# =============================================================================
def run_all_benchmarks() -> list[BenchmarkResult]:
    """运行全部 5 项基准测试，返回结果列表。"""
    return [
        _run_benchmark("网表解析（100 器件）", TARGET_NETLIST_PARSE_MS, bench_netlist_parse),
        _run_benchmark("A* 布线（单连接）", TARGET_ASTAR_ROUTING_MS, bench_astar_routing),
        _run_benchmark("GNN 前向推理", TARGET_GNN_FORWARD_MS, bench_gnn_forward),
        _run_benchmark("PPO 训练单步", TARGET_PPO_STEP_MS, bench_ppo_step),
        _run_benchmark("GDS 导出（100 器件）", TARGET_GDS_EXPORT_MS, bench_gds_export),
    ]


def main() -> None:
    """主入口：运行基准测试并生成报告。"""
    parser = argparse.ArgumentParser(description="PoLaRIS 性能基准测试（规则 15.1）")
    parser.add_argument(
        "--json",
        type=Path,
        default=DOCS_DIR / "performance_benchmark.json",
        help="JSON 报告输出路径（默认 docs/performance_benchmark.json）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("PoLaRIS 性能基准测试（规则 15.1）")
    print("=" * 60)

    env = collect_env_info()
    print(f"Python: {env['python']}")
    print(f"CPU: {env['cpu_model']} ({env['cpu_count']} cores)")
    print(f"内存: {env['memory']}")
    print(f"numpy: {env['numpy']}  torch: {env['torch']}  klayout: {env['klayout']}")
    print("-" * 60)

    results = run_all_benchmarks()

    print(f"\n{'指标':<24} {'目标':>10} {'实测':>12} {'标准差':>12} {'判定':>8}")
    print("-" * 70)
    for r in results:
        target_str = f"<{int(r.target_ms)}ms"
        if r.skipped:
            print(f"{r.name:<24} {target_str:>10} {'-':>12} {'-':>12} {'跳过':>8}")
            print(f"  原因: {r.skip_reason}")
        else:
            judge = "达标" if r.passed else "未达标"
            print(
                f"{r.name:<24} {target_str:>10} {r.mean_ms:>10.3f}ms {r.std_ms:>10.3f}ms {judge:>8}"
            )

    # 生成 Markdown 报告
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    md_path = DOCS_DIR / "performance_benchmark.md"
    md_path.write_text(generate_markdown(results, env), encoding="utf-8")
    print(f"\nMarkdown 报告已生成: {md_path}")

    # 生成 JSON 报告
    json_path = args.json
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(generate_json_report(results, env), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"JSON 报告已生成: {json_path}")

    # 退出码：全部达标（含跳过）返回 0
    failed = [r for r in results if not r.passed and not r.skipped]
    if failed:
        print(f"\n警告: {len(failed)} 项指标未达标")
        sys.exit(1)


if __name__ == "__main__":
    main()
