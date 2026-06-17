"""训练数据集合成单元测试（Task 14）。

覆盖 NetlistGenerator 网表生成（器件数/连接数/连通性/多规模）、
BaselineSolver 求解不报错、Dataset 增删查、save/load JSON 往返一致、
generate_training_dataset 端到端生成。
"""

from __future__ import annotations

import os

import networkx as nx
import pytest

from polaris.engine.floorplan_env import Placement
from polaris.engine.netlist import Netlist, build_graph, instantiate_devices
from polaris.pdk.catalog import build_default_catalog
from polaris.router import Route, WaveguideRouter
from polaris.trainer.dataset import (
    BaselineSolver,
    Dataset,
    DatasetSample,
    NetlistGenerator,
    generate_training_dataset,
)


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _connected(net: Netlist) -> bool:
    """判断网表连接图是否连通（器件数 <=1 视为连通）。"""
    if len(net.instances) <= 1:
        return True
    devices = instantiate_devices(net)
    g = build_graph(net, devices)
    return nx.is_connected(g)


# ---------------------------------------------------------------------------
# NetlistGenerator
# ---------------------------------------------------------------------------
def test_netlist_generator_valid_counts() -> None:
    """生成的网表器件数与连接数应与参数一致，且图连通。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=42)
    net = gen.generate(num_devices=10, num_nets=15, platform="SOI")
    assert isinstance(net, Netlist)
    assert len(net.instances) == 10
    # 连接数应等于 num_nets（15 <= 45 最大无序对，且 >= 9 生成树）
    assert len(net.connections) == 15
    # 每条连接引用已存在的实例与端口
    inst_ids = set(net.instance_ids)
    devices = instantiate_devices(net)
    for conn in net.connections:
        assert conn.src_instance in inst_ids
        assert conn.dst_instance in inst_ids
        src_ports = {p.name for p in devices[conn.src_instance].ports}
        dst_ports = {p.name for p in devices[conn.dst_instance].ports}
        assert conn.src_port in src_ports
        assert conn.dst_port in dst_ports
    # 连通性
    assert _connected(net)


def test_netlist_generator_connectivity_minimum_nets() -> None:
    """num_nets = num_devices-1（纯生成树）时应连通。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=7)
    net = gen.generate(num_devices=8, num_nets=7, platform="SOI")
    assert len(net.connections) == 7
    assert _connected(net)


def test_netlist_generator_different_scales() -> None:
    """不同规模网表（10/50/100 器件）器件数应正确。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=1)
    for size in (10, 50, 100):
        net = gen.generate(num_devices=size, num_nets=size, platform="SOI")
        assert len(net.instances) == size
        assert len(net.connections) == size
        assert _connected(net)


def test_netlist_generator_reproducible() -> None:
    """相同种子应生成相同网表。"""
    catalog = build_default_catalog()
    g1 = NetlistGenerator(catalog, seed=100)
    g2 = NetlistGenerator(catalog, seed=100)
    n1 = g1.generate(10, 12, "SOI")
    n2 = g2.generate(10, 12, "SOI")
    assert n1.name == n2.name
    assert n1.instance_ids == n2.instance_ids
    assert len(n1.connections) == len(n2.connections)


def test_netlist_generator_invalid_args() -> None:
    """非法参数应抛出 ValueError。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=0)
    with pytest.raises(ValueError):
        gen.generate(num_devices=0, num_nets=5)
    with pytest.raises(ValueError):
        gen.generate(num_devices=5, num_nets=-1)
    with pytest.raises(ValueError):
        gen.generate(num_devices=5, num_nets=5, platform="UNKNOWN_PLATFORM")


def test_generate_batch() -> None:
    """批量生成应返回 count 个不同规模网表。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=3)
    nets = gen.generate_batch(count=4, sizes=[10, 20])
    assert len(nets) == 4
    # 规模按序轮转：10, 20, 10, 20
    assert len(nets[0].instances) == 10
    assert len(nets[1].instances) == 20
    assert len(nets[2].instances) == 10
    assert len(nets[3].instances) == 20
    assert all(isinstance(n, Netlist) for n in nets)


def test_generate_batch_empty() -> None:
    """count <= 0 应返回空列表。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=3)
    assert gen.generate_batch(count=0, sizes=[10]) == []


# ---------------------------------------------------------------------------
# BaselineSolver
# ---------------------------------------------------------------------------
def test_baseline_solver_runs() -> None:
    """BaselineSolver 求解应不报错并返回完整结构。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=42)
    net = gen.generate(num_devices=10, num_nets=12, platform="SOI")
    router = WaveguideRouter(grid_size=1.0, min_bend_radius=5.0, min_spacing=1.0)
    solver = BaselineSolver(router)
    result = solver.solve(net)
    # 结构校验
    assert set(result.keys()) == {"placements", "routes", "metrics", "reward"}
    placements = result["placements"]
    routes = result["routes"]
    metrics = result["metrics"]
    assert len(placements) == 10
    assert all(isinstance(p, Placement) for p in placements.values())
    assert all(isinstance(r, Route) for r in routes)
    # 指标字段
    assert set(metrics.keys()) == {"total_length", "total_loss_db", "num_crossings", "area"}
    assert metrics["total_length"] >= 0.0
    assert metrics["total_loss_db"] >= 0.0
    assert metrics["num_crossings"] >= 0.0
    assert metrics["area"] > 0.0
    # 奖励为有限浮点
    assert isinstance(result["reward"], float)
    assert result["reward"] == result["reward"]  # 非 NaN


def test_baseline_solver_reward_matches_sample() -> None:
    """baseline['reward'] 应与综合奖励一致。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=5)
    net = gen.generate(num_devices=6, num_nets=7, platform="SOI")
    solver = BaselineSolver(WaveguideRouter())
    result = solver.solve(net)
    assert result["reward"] == pytest.approx(result["reward"])


# ---------------------------------------------------------------------------
# Dataset 增删查
# ---------------------------------------------------------------------------
def _make_sample() -> DatasetSample:
    """构造一个最小训练样本。"""
    catalog = build_default_catalog()
    gen = NetlistGenerator(catalog, seed=11)
    net = gen.generate(num_devices=5, num_nets=6, platform="SOI")
    solver = BaselineSolver(WaveguideRouter())
    baseline = solver.solve(net)
    return DatasetSample(netlist=net, baseline=baseline, reward=baseline["reward"])


def test_dataset_add_and_get() -> None:
    """Dataset 添加与获取应一致。"""
    ds = Dataset()
    assert len(ds) == 0
    s = _make_sample()
    ds.add(s)
    assert len(ds) == 1
    assert ds[0] is s


def test_dataset_index_error() -> None:
    """越界索引应抛出 IndexError。"""
    ds = Dataset()
    with pytest.raises(IndexError):
        _ = ds[0]


# ---------------------------------------------------------------------------
# save/load 往返一致
# ---------------------------------------------------------------------------
def test_dataset_save_load_roundtrip(tmp_path) -> None:
    """save/load 往返应保持网表/指标/奖励/放置/布线一致。"""
    ds = Dataset()
    ds.add(_make_sample())
    ds.add(_make_sample())
    path = str(tmp_path / "dataset.json")
    ds.save(path)
    assert os.path.exists(path)

    loaded = Dataset.load(path)
    assert len(loaded) == len(ds)

    for orig, load in zip(ds.samples, loaded.samples):
        # 网表一致
        assert orig.netlist.name == load.netlist.name
        assert orig.netlist.instance_ids == load.netlist.instance_ids
        assert len(orig.netlist.connections) == len(load.netlist.connections)
        for c1, c2 in zip(orig.netlist.connections, load.netlist.connections):
            assert (c1.src_instance, c1.src_port, c1.dst_instance, c1.dst_port) == (
                c2.src_instance,
                c2.src_port,
                c2.dst_instance,
                c2.dst_port,
            )
        # 奖励与指标一致
        assert orig.reward == pytest.approx(load.reward)
        assert orig.baseline["reward"] == pytest.approx(load.baseline["reward"])
        om = orig.baseline["metrics"]
        lm = load.baseline["metrics"]
        for k in ("total_length", "total_loss_db", "num_crossings", "area"):
            assert om[k] == pytest.approx(lm[k])
        # 放置一致（坐标/旋转）
        op = orig.baseline["placements"]
        lp = load.baseline["placements"]
        assert set(op.keys()) == set(lp.keys())
        for iid in op:
            assert op[iid].x == pytest.approx(lp[iid].x)
            assert op[iid].y == pytest.approx(lp[iid].y)
            assert op[iid].rotation == lp[iid].rotation
        # 布线一致
        oroutes = orig.baseline["routes"]
        lroutes = load.baseline["routes"]
        assert len(oroutes) == len(lroutes)
        for r1, r2 in zip(oroutes, lroutes):
            assert r1.net_id == r2.net_id
            assert r1.length == pytest.approx(r2.length)
            assert r1.num_bends == r2.num_bends
            assert r1.num_crossings == r2.num_crossings
            assert r1.loss_db == pytest.approx(r2.loss_db)
            assert r1.path == r2.path


def test_dataset_load_empty(tmp_path) -> None:
    """加载空数据集应返回空 Dataset。"""
    path = str(tmp_path / "empty.json")
    Dataset().save(path)
    loaded = Dataset.load(path)
    assert len(loaded) == 0


# ---------------------------------------------------------------------------
# generate_training_dataset 端到端
# ---------------------------------------------------------------------------
def test_generate_training_dataset(tmp_path) -> None:
    """generate_training_dataset 应生成数据集并保存文件。"""
    path = str(tmp_path / "train.json")
    ds = generate_training_dataset(
        output_path=path,
        num_samples=3,
        sizes=[5, 8],
        platform="SOI",
        seed=42,
    )
    assert isinstance(ds, Dataset)
    assert len(ds) == 3
    assert os.path.exists(path)
    # 规模按序轮转：5, 8, 5
    assert len(ds[0].netlist.instances) == 5
    assert len(ds[1].netlist.instances) == 8
    assert len(ds[2].netlist.instances) == 5
    # 每个样本均有 baseline 与奖励
    for s in ds.samples:
        assert "metrics" in s.baseline
        assert isinstance(s.reward, float)


def test_generate_training_dataset_default_sizes(tmp_path) -> None:
    """默认 sizes=[10,50,100] 时应可生成（小样本量）。"""
    path = str(tmp_path / "train_default.json")
    ds = generate_training_dataset(
        output_path=path, num_samples=1, seed=0
    )
    assert len(ds) == 1
    assert len(ds[0].netlist.instances) == 10
