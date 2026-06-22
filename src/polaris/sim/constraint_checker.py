"""约束检查器。

检查布局布线结果是否满足光子学设计约束，
包括弯曲半径、波导间距、插入损耗、串扰等。

## 架构（第63轮 P2-1 拆分）

- ``constraint_types.py``：基础类型（ViolationType/Violation/ConstraintConfig/CheckContext）
- ``constraint_checks_geometry.py``：几何 DRC 检查函数
- ``constraint_checks_performance.py``：性能 DRC 检查函数
- ``constraint_checker.py``（本文件）：ConstraintChecker 统一入口 + 重新导出

来源:
- LiDAR ISPD'25: 弯曲半径约束 + 交叉惩罚
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC EBeam PDK: 设计规则
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Latitude DA: 硅光EDA挑战
  https://www.latitudeda.com/document/353
"""

from __future__ import annotations

from polaris.sim.constraint_types import (
    CheckContext,
    ConstraintConfig,
    Violation,
    ViolationType,
)
from polaris.sim.constraint_checks_geometry import (
    check_bend_radius,
    check_coupling_gap,
    check_layer_density,
    check_min_area,
    check_min_width,
    check_overlap,
    check_port_connectivity,
    check_spacing,
    check_waveguide_length,
)
from polaris.sim.constraint_checks_performance import (
    CrosstalkConfig,
    check_crossings,
    check_crosstalk,
    check_insertion_loss,
    check_thermal,
)


class ConstraintChecker:
    """约束检查器。

    综合检查布局布线结果是否满足所有光子学设计约束。

    来源:
    - LiDAR ISPD'25: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    """

    def __init__(self, config: ConstraintConfig | None = None) -> None:
        self.config = config or ConstraintConfig()

    def check(
        self,
        placements: dict,
        paths: dict,
        context: CheckContext | None = None,
    ) -> list[Violation]:
        """综合约束检查。

        Args:
            placements: 器件布局。
            paths: 布线路径。
            context: DRC 上下文（损耗、交叉数、波导宽度、耦合间隙等）。

        Returns:
            所有违规列表。
        """
        cfg = self.config
        ctx = context or CheckContext()
        violations: list[Violation] = []
        violations.extend(check_overlap(placements))
        violations.extend(check_spacing(placements, cfg.min_spacing_um))
        violations.extend(check_bend_radius(paths, cfg.min_bend_radius_um))
        violations.extend(check_insertion_loss(ctx.total_loss_db, cfg.max_insertion_loss_db))
        violations.extend(check_crossings(ctx.n_crossings, cfg.max_crossings))
        violations.extend(self._check_optional(ctx, cfg))
        return violations

    def _check_optional(self, ctx: CheckContext, cfg: ConstraintConfig) -> list[Violation]:
        """执行可选 DRC 检查（基于 context 提供的输入）。"""
        violations: list[Violation] = []
        if ctx.waveguide_widths is not None:
            violations.extend(check_min_width(ctx.waveguide_widths, cfg.min_waveguide_width_um))
        if ctx.coupling_gaps is not None:
            violations.extend(check_coupling_gap(ctx.coupling_gaps, cfg.min_coupling_gap_um))
        if ctx.waveguide_lengths is not None:
            violations.extend(
                check_waveguide_length(
                    ctx.waveguide_lengths,
                    cfg.min_waveguide_length_um,
                    cfg.max_waveguide_length_um,
                )
            )
        if ctx.device_areas is not None:
            violations.extend(check_min_area(ctx.device_areas, cfg.min_device_area_um2))
        if ctx.port_connections is not None:
            violations.extend(check_port_connectivity(ctx.port_connections))
        if ctx.layer_densities is not None:
            violations.extend(check_layer_density(ctx.layer_densities, cfg.max_layer_density))
        return violations

    def check_passed(self, **kwargs) -> bool:
        """检查是否全部通过。"""
        return len(self.check(**kwargs)) == 0


__all__ = [
    "ConstraintChecker",
    "ConstraintConfig",
    "CheckContext",
    "Violation",
    "ViolationType",
    "CrosstalkConfig",
    "check_bend_radius",
    "check_spacing",
    "check_insertion_loss",
    "check_crossings",
    "check_overlap",
    "check_min_width",
    "check_coupling_gap",
    "check_waveguide_length",
    "check_min_area",
    "check_port_connectivity",
    "check_layer_density",
    "check_thermal",
    "check_crosstalk",
]
