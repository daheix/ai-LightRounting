"""强化学习（RL）子包。

R34-R35 路标：Google AlphaChip 强化学习布局对齐模块。
R351-R355 路标：RL 增强（纯 NumPy/SciPy，不依赖 torch）。

学术依据：
- Google DeepMind AlphaChip:
  https://deepmind.google/discover/blog/alphachip-a-new-approach-to-chip-layout/
- Mirhoseini et al., Nature 2024: https://doi.org/10.1038/s41586-024-07714-9
- R34 Edge-GNN: polaris.rl.edge_gnn（纯 NumPy CPU，对标 AlphaChip edge-based GNN）
- R351-R355: polaris.rl.rl_numpy_advanced（纯 NumPy/SciPy，R04 不参与 GPU）

R04 战略：alpha_chip / edge_gnn 等子模块可能依赖 torch。当 torch 不可用时，
延迟到实际访问时再报错（环境配置问题，非业务 fall-back），但 rl_numpy_advanced
（纯 NumPy）始终可导入，保证 R351-R355 增强模块在无 torch 环境下可用。
"""

import importlib

# alpha_chip / edge_gnn 依赖 torch，缺失时延迟报错（仅当用户实际访问时）
# rl_numpy_advanced 纯 NumPy，始终可导入（R04 不参与 GPU）
try:
    from polaris.rl.alpha_chip import (  # noqa: F401
        AlphaChipAgent,
        AlphaChipConfig,
        AlphaChipTrainer,
        PhotonicPlacementEncoder,
        PhotonicPlacementReward,
    )
    _ALPHA_CHIP_AVAILABLE = True
except ImportError as _e:  # torch 缺失等环境问题
    _ALPHA_CHIP_IMPORT_ERROR = _e
    _ALPHA_CHIP_AVAILABLE = False

try:
    from polaris.rl.edge_gnn import EdgeGNN, EdgeGNNConfig  # noqa: F401
    _EDGE_GNN_AVAILABLE = True
except ImportError as _e:
    _EDGE_GNN_IMPORT_ERROR = _e
    _EDGE_GNN_AVAILABLE = False

# R351-R355 纯 NumPy/SciPy 模块，无 torch 依赖，始终可导入
from polaris.rl.rl_numpy_advanced import (  # noqa: F401
    ALL_POLICIES,
    GPU_DISABLED_R04,
    HybridPlacementAgent,
    HybridPlacementConfig,
    LargeScalePlacementConfig,
    LargeScalePlacementEnv,
    MultiObjectiveParetoReward,
    MultiObjectiveRewardConfig,
    POLICY_CURRICULUM,
    POLICY_HEURISTIC,
    POLICY_RANDOM,
    PPOAdvConfig,
    PPOAdvantageOptimizer,
    PretrainedPolicyConfig,
    PretrainedPolicyLibrary,
)


def _require_alpha_chip() -> None:
    """访问 alpha_chip 模块前的环境检查（R03 无 fall-back）。

    Raises:
        ImportError: torch 不可用时 raise 明确错误。
    """
    if not _ALPHA_CHIP_AVAILABLE:
        raise ImportError(
            "polaris.rl.alpha_chip 不可用（依赖 torch，当前环境未安装）。"
            f"原始错误: {_ALPHA_CHIP_IMPORT_ERROR}。"
            "R04 战略：请使用 polaris.rl.rl_numpy_advanced（纯 NumPy）替代。"
        )


def __getattr__(name: str):  # PEP 562
    """延迟导入 alpha_chip / edge_gnn 符号（torch 可用时正常导出）。"""
    _alpha_chip_names = {
        "AlphaChipAgent", "AlphaChipConfig", "AlphaChipTrainer",
        "PhotonicPlacementEncoder", "PhotonicPlacementReward",
    }
    _edge_gnn_names = {"EdgeGNN", "EdgeGNNConfig"}
    if name in _alpha_chip_names:
        _require_alpha_chip()
        module = importlib.import_module("polaris.rl.alpha_chip")
        return getattr(module, name)
    if name in _edge_gnn_names:
        if not _EDGE_GNN_AVAILABLE:
            raise ImportError(
                "polaris.rl.edge_gnn 不可用。"
                f"原始错误: {_EDGE_GNN_IMPORT_ERROR}"
            )
        module = importlib.import_module("polaris.rl.edge_gnn")
        return getattr(module, name)
    raise AttributeError(f"module 'polaris.rl' has no attribute {name!r}")


__all__ = [
    "AlphaChipConfig",
    "PhotonicPlacementEncoder",
    "PhotonicPlacementReward",
    "AlphaChipAgent",
    "AlphaChipTrainer",
    "EdgeGNN",
    "EdgeGNNConfig",
    # R351-R355 纯 NumPy/SciPy
    "LargeScalePlacementConfig",
    "LargeScalePlacementEnv",
    "PPOAdvConfig",
    "PPOAdvantageOptimizer",
    "MultiObjectiveRewardConfig",
    "MultiObjectiveParetoReward",
    "PretrainedPolicyConfig",
    "PretrainedPolicyLibrary",
    "HybridPlacementConfig",
    "HybridPlacementAgent",
    "POLICY_HEURISTIC",
    "POLICY_RANDOM",
    "POLICY_CURRICULUM",
    "ALL_POLICIES",
    "GPU_DISABLED_R04",
]
