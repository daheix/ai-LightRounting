"""R34 AlphaChip Edge-GNN 测试套件（polaris.rl.edge_gnn）。

覆盖 spec 要求的 12 个测试点 + R03 无 fall-back + R04 纯 CPU 验证。

学术依据:
- Mirhoseini et al., Nature 2021, https://www.nature.com/articles/s41586-021-03544-w
- Schlichtkrull et al., ESWC 2018, https://arxiv.org/abs/1703.06103
- Veličković et al., ICLR 2018, https://arxiv.org/abs/1710.10903
"""

from __future__ import annotations

import re

import numpy as np
import pytest

from polaris.rl.edge_gnn import (
    NUM_RELATIONS,
    PHOTONIC_EDGE_DIM,
    RELATION_ELECTRICAL,
    RELATION_OPTICAL,
    RELATION_OPTOELECTRICAL,
    EdgeGNN,
    EdgeGNNConfig,
)


# =============================================================================
# 测试辅助
# =============================================================================


@pytest.fixture
def gnn() -> EdgeGNN:
    """默认 EdgeGNN（seed=42 可复现）。"""
    return EdgeGNN(EdgeGNNConfig(seed=42))


@pytest.fixture
def small_graph() -> dict:
    """8 节点小图（含两关系）。"""
    rng = np.random.default_rng(0)
    n = 8
    nf = rng.standard_normal((n, 64))
    edges = [(i, (i + 1) % n) for i in range(n)] + [
        (i, (i + 3) % n) for i in range(n)
    ]
    relations = np.array([RELATION_OPTICAL] * n + [RELATION_ELECTRICAL] * n)
    return {"node_feats": nf, "edges": edges, "relations": relations}


# =============================================================================
# 1. 配置验证
# =============================================================================


def test_config_validation():
    """测试 EdgeGNNConfig 校验（非法参数 raise，R03 禁止 fall-back）。"""
    cfg = EdgeGNNConfig()
    assert cfg.n_edge_features == PHOTONIC_EDGE_DIM  # 15
    assert cfg.n_relations == NUM_RELATIONS  # 3
    assert cfg.n_heads >= 1
    # 非法参数必须 raise（R03）
    with pytest.raises(ValueError):
        EdgeGNNConfig(n_relations=0)
    with pytest.raises(ValueError):
        EdgeGNNConfig(n_heads=0)
    with pytest.raises(ValueError):
        EdgeGNNConfig(hidden_dim=0)
    with pytest.raises(ValueError):
        EdgeGNNConfig(n_edge_features=7)  # 须为 15


# =============================================================================
# 2. 15 维边特征编码
# =============================================================================


def test_encode_edge_features(gnn: EdgeGNN):
    """测试 15 维光子边特征编码（*创新* 1）。"""
    edge = {
        "distance": 500.0,
        "bandwidth": 4,
        "edge_type": 1,
        "wavelength": 1.55,  # C-band
        "relation": RELATION_ELECTRICAL,
        "loss_db_cm": 3.0,
        "crosstalk_db": 25.0,
        "bend_radius": 10.0,
        "delta_neff": 0.5,
    }
    feat = gnn.encode_edge_features(edge)
    assert feat.shape == (PHOTONIC_EDGE_DIM,)
    assert feat[3 + 1] == 1.0  # edge_type=1 → one-hot[4]
    assert feat[7 + 0] == 1.0  # 1.55μm → C-band
    assert feat[14] == float(RELATION_ELECTRICAL)
    # O-band
    feat_o = gnn.encode_edge_features({"wavelength": 1.31})
    assert feat_o[7 + 2] == 1.0  # O-band
    # 非法 edge_type raise
    with pytest.raises(ValueError):
        gnn.encode_edge_features({"edge_type": 5})
    # 非法 relation raise
    with pytest.raises(ValueError):
        gnn.encode_edge_features({"relation": 99})


# =============================================================================
# 3. R-GCN 单层
# =============================================================================


def test_rgcn_layer(gnn: EdgeGNN, small_graph: dict):
    """测试 R-GCN 单层（Schlichtkrull 2018 basis decomposition）。"""
    h = small_graph["node_feats"] @ gnn._w.node_proj
    r_edges = [
        e
        for i, e in enumerate(small_graph["edges"])
        if small_graph["relations"][i] == RELATION_OPTICAL
    ]
    out = gnn.rgcn_layer(h, r_edges, RELATION_OPTICAL, layer=0)
    assert out.shape == h.shape
    assert np.isfinite(out).all()
    # 无边时返回零矩阵（不崩溃）
    out_empty = gnn.rgcn_layer(h, [], RELATION_OPTICAL, layer=0)
    assert out_empty.shape == h.shape
    assert (out_empty == 0).all()


# =============================================================================
# 4. GAT 注意力层
# =============================================================================


def test_gat_layer(gnn: EdgeGNN, small_graph: dict):
    """测试 GAT 多头注意力层（Veličković 2018）。"""
    h = small_graph["node_feats"] @ gnn._w.node_proj
    out = gnn.gat_layer(h, small_graph["edges"], layer=0)
    assert out.shape == h.shape  # 多头平均保持维度
    assert np.isfinite(out).all()
    # 无边时返回多头变换平均
    out_empty = gnn.gat_layer(h, [], layer=0)
    assert out_empty.shape == h.shape


# =============================================================================
# 5. GlobalAttention 全局聚合
# =============================================================================


def test_global_attention(gnn: EdgeGNN, small_graph: dict):
    """测试 GlobalAttention 全局聚合（Li 2016 GatedGraph）。"""
    h = small_graph["node_feats"] @ gnn._w.node_proj
    out = gnn.global_attention(h)
    assert out.shape == (gnn.config.hidden_dim,)
    assert np.isfinite(out).all()


# =============================================================================
# 6. 前向传播
# =============================================================================


def test_forward(gnn: EdgeGNN, small_graph: dict):
    """测试前向传播 R-GCN → GAT → GlobalAttention。"""
    emb = gnn.forward(small_graph)
    assert emb.shape == (gnn.config.hidden_dim,)
    assert np.isfinite(emb).all()
    # 错误输入 raise（R03）
    with pytest.raises(ValueError):
        gnn.forward({"node_feats": small_graph["node_feats"], "edges": [], "relations": np.array([0])})
    with pytest.raises(ValueError):
        bad = dict(small_graph)
        bad["relations"] = np.array([9] * len(small_graph["edges"]))
        gnn.forward(bad)


# =============================================================================
# 7. 布局预测
# =============================================================================


def test_predict_placement(gnn: EdgeGNN, small_graph: dict):
    """测试布局预测（坐标归一化到 [0,1]）。"""
    placement = gnn.predict_placement(small_graph)
    assert len(placement) == small_graph["node_feats"].shape[0]
    for nid, (x, y) in placement.items():
        assert 0.0 <= x <= 1.0
        assert 0.0 <= y <= 1.0
    # 空图 raise
    with pytest.raises(ValueError):
        gnn.predict_placement({"node_feats": np.zeros((0, 64)), "edges": [], "relations": np.array([])})


# =============================================================================
# 8. HPWL 计算
# =============================================================================


def test_compute_hpwl(gnn: EdgeGNN):
    """测试 HPWL 计算（VLSI 经典公式: Σ(maxX-minX + maxY-minY)）。"""
    placement = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (0.0, 1.0), 3: (1.0, 1.0)}
    netlist = {"nets": [[0, 1, 2, 3], [0, 1]]}
    # net0 包围盒 (0,0)-(1,1): HPWL=2; net1 [0,1]: HPWL=1; total=3
    hpwl = gnn.compute_hpwl(placement, netlist)
    assert hpwl == pytest.approx(3.0)
    # 缺 nets 键 raise（R03）
    with pytest.raises(ValueError):
        gnn.compute_hpwl(placement, {})
    # 空 net 跳过
    assert gnn.compute_hpwl(placement, {"nets": [[]]}) == 0.0


# =============================================================================
# 9. Ariane benchmark（HPWL 优于 R-GCN ≥5%）
# =============================================================================


def test_benchmark_ariane(gnn: EdgeGNN):
    """测试 Ariane RISC-V benchmark（HPWL 优于纯 R-GCN ≥5%，*创新* 3）。"""
    res = gnn.benchmark_ariane()
    assert res["passed"] is True
    assert res["improvement_pct"] >= res["target_pct"]  # ≥5%
    assert res["hpwl_edge_gnn"] < res["hpwl_rgcn"]  # EdgeGNN 更优
    assert res["n_nodes"] == 24
    assert res["n_nets"] == 12
    # 多种子稳定性
    for seed in (1, 7, 100, 2024):
        g = EdgeGNN(EdgeGNNConfig(seed=seed))
        r = g.benchmark_ariane()
        assert r["passed"], f"seed={seed} 未达 5%: {r['improvement_pct']}"


# =============================================================================
# 10. 三关系处理
# =============================================================================


def test_three_relations(gnn: EdgeGNN):
    """测试三关系（光-光/光-电/电-电）均被处理。"""
    netlist, graph = gnn._build_ariane_like_netlist()
    relations = graph["relations"]
    assert set(relations.tolist()) == {RELATION_OPTICAL, RELATION_OPTOELECTRICAL, RELATION_ELECTRICAL}
    # 三关系 forward 正常
    emb = gnn.forward(graph)
    assert emb.shape == (gnn.config.hidden_dim,)
    assert np.isfinite(emb).all()
    # 每关系边数 > 0
    for r in (RELATION_OPTICAL, RELATION_OPTOELECTRICAL, RELATION_ELECTRICAL):
        assert (relations == r).sum() > 0


# =============================================================================
# 11. 多头注意力
# =============================================================================


def test_multi_head_attention():
    """测试多头 GAT（不同头数，输出维度保持 H）。"""
    for n_heads in (1, 4, 8):
        cfg = EdgeGNNConfig(n_heads=n_heads, seed=42)
        g = EdgeGNN(cfg)
        rng = np.random.default_rng(0)
        nf = rng.standard_normal((6, 64))
        edges = [(i, (i + 1) % 6) for i in range(6)]
        out = g.gat_layer(nf @ g._w.node_proj, edges, layer=0)
        assert out.shape == (6, 64)  # 多头平均保持 H
        assert np.isfinite(out).all()


# =============================================================================
# 12. R04 CPU 实现验证
# =============================================================================


def test_cpu_only(gnn: EdgeGNN, small_graph: dict):
    """测试 R04 纯 NumPy CPU 实现（不参与 GPU）。"""
    import polaris.rl.edge_gnn as mod

    src = open(mod.__file__).read()
    # 不导入 GPU 库
    assert "import cupy" not in src
    assert "import torch" not in src
    # 无 GPU 调用
    assert ".cuda" not in src
    assert ".to('cuda')" not in src and '.to("cuda")' not in src
    # 权重为 numpy ndarray（CPU 张量）
    assert isinstance(gnn._w.node_proj, np.ndarray)
    assert isinstance(gnn._w.gat_w[0][0], np.ndarray)
    # 实际计算在 CPU（无 GPU 报错）
    emb = gnn.forward(small_graph)
    assert np.isfinite(emb).all()


# =============================================================================
# 13. R03 无 fall-back 验证
# =============================================================================


def test_no_fallback():
    """测试 R03 无 fall-back（无 except:pass / return None 假数据兜底）。"""
    import polaris.rl.edge_gnn as mod

    src = open(mod.__file__).read()
    # 禁止 except: pass / except: return None / return [] 假数据兜底
    bad_patterns = [
        r"except[^:]*:\s*pass",
        r"except[^:]*:\s*return\s+None",
        r"except[^:]*:\s*return\s+\[\]",
    ]
    for pat in bad_patterns:
        assert not re.search(pat, src), f"发现 fall-back 模式: {pat}"


# =============================================================================
# 14. 学术诚信：文献 URL 与 *创新* 标注
# =============================================================================


def test_academic_integrity():
    """测试 R02 学术诚信（≥5 文献 URL，*创新* 标注）。"""
    import polaris.rl.edge_gnn as mod

    src = open(mod.__file__).read()
    # ≥5 个文献 URL
    urls = re.findall(r"https?://[^\s,)]+", src)
    assert len(urls) >= 5, f"文献 URL 不足 5 个: {len(urls)}"
    # *创新* 标注
    assert "*创新*" in src or "创新" in src
    # 关键文献存在
    assert "s41586-021-03544-w" in src  # Mirhoseini Nature 2021
    assert "1703.06103" in src  # Schlichtkrull R-GCN
    assert "1710.10903" in src  # Veličković GAT
