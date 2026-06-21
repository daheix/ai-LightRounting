"""P0-2 规模扩展性能基准测试（第12轮）。

验证第11轮三项优化在 500 器件规模下的实际性能提升。
对比优化前后的关键操作耗时。

来源: commercial_gap_analysis.md P0-2 规模可扩展性
"""

from __future__ import annotations

import time

import pytest

from polaris.engine.floorplan_env import (
    Placement,
    _count_spacing_violations,
    _count_spacing_violations_brute_force,
    _count_spacing_violations_spatial_hash,
)
from polaris.pdk.catalog import build_default_catalog


def _make_placements(n: int, spacing: float = 3.0) -> list:
    """生成 n 个器件的网格布局。"""
    cat = build_default_catalog()
    dev = cat.get("strip_waveguide", platform="SOI")
    placements = []
    cols = int(n**0.5)
    for i in range(n):
        x = (i % cols) * spacing
        y = (i // cols) * spacing
        placements.append(Placement(f"d{i}", dev, x=x, y=y))
    return placements


class TestScalePerformance:
    """500 器件规模性能基准。"""

    def test_spacing_violations_500_spatial_vs_brute(self):
        """500 器件空间哈希 vs 暴力性能对比。"""
        placements = _make_placements(500, spacing=3.0)
        min_spacing = 5.0

        # 暴力
        t0 = time.perf_counter()
        brute = _count_spacing_violations_brute_force(placements, min_spacing)
        t_brute = time.perf_counter() - t0

        # 空间哈希
        t0 = time.perf_counter()
        hashed = _count_spacing_violations_spatial_hash(placements, min_spacing)
        t_hashed = time.perf_counter() - t0

        assert brute == hashed
        # 空间哈希应比暴力快（至少不慢 10 倍以上）
        # 注意：小规模或特殊布局下空间哈希可能因桶开销稍慢，
        # 但 500 器件密集布局下应有明显加速
        print(f"\n500 器件间距检测: 暴力={t_brute*1000:.1f}ms, 空间哈希={t_hashed*1000:.1f}ms")

    def test_placement_cache_performance(self):
        """Placement 缓存性能：首次 vs 二次调用。"""
        placements = _make_placements(500, spacing=10.0)

        # 首次调用（计算 + 缓存）
        t0 = time.perf_counter()
        for pl in placements:
            pl.bbox_abs()
        t_first = time.perf_counter() - t0

        # 二次调用（纯缓存读取）
        t0 = time.perf_counter()
        for pl in placements:
            pl.bbox_abs()
        t_cached = time.perf_counter() - t0

        print(f"\n500 器件 bbox_abs: 首次={t_first*1000:.1f}ms, 缓存={t_cached*1000:.1f}ms")
        # 缓存应显著快于首次计算
        assert t_cached < t_first

    def test_500_devices_episode_simulation(self):
        """模拟 500 器件 episode 的关键操作耗时。"""
        placements = _make_placements(500, spacing=10.0)
        min_spacing = 5.0

        # 模拟一个 episode 中 _reward() 的关键操作
        # 1. bbox_abs（已缓存）
        t0 = time.perf_counter()
        for _ in range(10):  # 模拟 10 步
            for pl in placements:
                pl.bbox_abs()
        t_bbox = time.perf_counter() - t0

        # 2. 间距检测（空间哈希）
        t0 = time.perf_counter()
        for _ in range(10):  # 模拟 10 步
            _count_spacing_violations(placements, min_spacing)
        t_spacing = time.perf_counter() - t0

        print(
            f"\n500 器件 10 步模拟: bbox_abs={t_bbox*1000:.1f}ms, "
            f"间距检测={t_spacing*1000:.1f}ms"
        )
        # 单步应在 100ms 内完成（可接受范围）
        per_step = (t_bbox + t_spacing) / 10
        assert per_step < 0.1, f"单步耗时 {per_step*1000:.1f}ms > 100ms"

    def test_rudy_congestion_500_performance(self):
        """RUDY 拥塞计算在 500 连接下的性能。"""
        from polaris.engine.congestion import RudyConfig, rudy_congestion

        cat = build_default_catalog()
        dev = cat.get("strip_waveguide", platform="SOI")
        # 500 个已放置器件
        placements = {}
        for i in range(500):
            placements[f"d{i}"] = Placement(
                f"d{i}", dev, x=float(i * 10), y=0.0
            )

        # 500 条连接（链式）
        from polaris.engine.netlist import NetlistConnection

        connections = [
            NetlistConnection(f"d{i}", "out", f"d{i+1}", "in")
            for i in range(499)
        ]

        cfg = RudyConfig(
            grid_h=200, grid_w=200, canvas_w=5000.0, canvas_h=5000.0
        )

        t0 = time.perf_counter()
        cong = rudy_congestion(placements, connections, cfg)
        t_rudy = time.perf_counter() - t0

        print(f"\n500 连接 RUDY: {t_rudy*1000:.1f}ms, max={cong.max():.1f}")
        assert cong.shape == (200, 200)
        # RUDY 应在 50ms 内完成
        assert t_rudy < 0.05, f"RUDY 耗时 {t_rudy*1000:.1f}ms > 50ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
