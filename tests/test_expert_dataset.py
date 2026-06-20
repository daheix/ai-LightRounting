"""ExpertDataset 单元测试（规则 10）。

测试 polaris.trainer.expert_dataset.ExpertDataset 的加载、批量化、维度一致性。

来源:
- SiEPIC_EBeam_PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK (MIT, UBC)
- pytest 最佳实践: https://docs.pytest.org/en/stable/explanation/goodpractices.html
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from polaris.trainer.expert_dataset import (
    ACTION_DIM,
    OBS_DIM,
    ExpertDataset,
)

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent
EXPERT_DIR = ROOT / "data" / "expert_demos"


@pytest.fixture
def dataset() -> ExpertDataset:
    """加载专家示范数据集 fixture。"""
    ds = ExpertDataset(str(EXPERT_DIR))
    ds.load()
    return ds


def test_dataset_loads_successfully(dataset: ExpertDataset) -> None:
    """测试数据集能成功加载且非空。"""
    assert len(dataset) > 0, "专家数据集应为非空"


def test_obs_action_dim_consistent(dataset: ExpertDataset) -> None:
    """测试观测与动作维度与常量一致。"""
    obs, act = dataset.get_all()
    assert obs.shape[1] == OBS_DIM, f"obs_dim 不匹配: {obs.shape[1]} vs {OBS_DIM}"
    assert act.shape[1] == ACTION_DIM, f"action_dim 不匹配: {act.shape[1]} vs {ACTION_DIM}"
    assert obs.shape[0] == act.shape[0], "obs 与 action 样本数应一致"


def test_action_in_unit_range(dataset: ExpertDataset) -> None:
    """测试归一化动作落在 [0, 1] 区间。"""
    _, act = dataset.get_all()
    assert act.min() >= 0.0 - 1e-6, f"动作最小值 {act.min()} 不应小于 0"
    assert act.max() <= 1.0 + 1e-6, f"动作最大值 {act.max()} 不应大于 1"


def test_obs_finite(dataset: ExpertDataset) -> None:
    """测试观测无 NaN/Inf。"""
    obs, _ = dataset.get_all()
    assert np.isfinite(obs).all(), "观测包含 NaN 或 Inf"


def test_batch_iteration(dataset: ExpertDataset) -> None:
    """测试批量迭代返回正确形状。"""
    batch_size = 8
    total = 0
    n_batches = 0
    for obs_b, act_b in dataset.iter_batches(batch_size=batch_size, shuffle=False):
        assert obs_b.shape[0] == act_b.shape[0]
        assert obs_b.shape[1] == OBS_DIM
        assert act_b.shape[1] == ACTION_DIM
        total += obs_b.shape[0]
        n_batches += 1
    assert total == len(dataset), f"批量总数 {total} 应等于数据集大小 {len(dataset)}"
    assert n_batches > 0


def test_batch_shuffle_reproducible(dataset: ExpertDataset) -> None:
    """测试相同 seed 的 shuffle 顺序一致。"""
    batches1 = []
    for obs_b, _ in dataset.iter_batches(batch_size=4, shuffle=True, seed=123):
        batches1.append(obs_b.copy())
    batches2 = []
    for obs_b, _ in dataset.iter_batches(batch_size=4, shuffle=True, seed=123):
        batches2.append(obs_b.copy())
    assert len(batches1) == len(batches2)
    for b1, b2 in zip(batches1, batches2, strict=True):
        np.testing.assert_array_equal(b1, b2)


def test_empty_dataset_returns_empty() -> None:
    """测试空目录返回空数组。"""
    ds = ExpertDataset("/nonexistent/path/xyz")
    ds.load()
    assert len(ds) == 0
    obs, act = ds.get_all()
    assert obs.shape == (0, OBS_DIM)
    assert act.shape == (0, ACTION_DIM)


def test_meta_list_populated(dataset: ExpertDataset) -> None:
    """测试元信息列表包含来源标注。"""
    assert len(dataset.meta_list) == len(dataset)
    for meta in dataset.meta_list:
        assert "source" in meta
        assert "device" in meta
        assert "step" in meta
