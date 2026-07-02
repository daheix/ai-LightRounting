"""PoLaRIS 光子电路规格数据类（re-export from polaris-core）。

为避免类型分裂（polaris_core.CircuitSpec 与 polaris_nn.data.specs.CircuitSpec
isinstance 不互认），本模块直接 re-export polaris_core 的 specs，保持单一来源。

polaris-nn 的 data 子包内其他模块从 ``polaris_nn.data.specs`` 导入，
对外用户也可直接从 ``polaris_core`` 导入，二者为同一对象。

来源:
- GDSFactory 组件库: https://gdsfactory.github.io/gdsfactory/
- TILOS MacroPlacement benchmark: https://github.com/TILOS-AI-CAD-Institute/MacroPlacement
- Apollo PTC/oNoC 光子 benchmark: https://github.com/ASU-LOPE-Group/Apollo
- LiDAR ISPD'25 benchmark: https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- SiEPIC PDK 设计规则: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

from polaris_core.specs import (
    BenchmarkSource,
    CircuitSpec,
    DeviceSpec,
    TargetMetric,
)

__all__ = ["BenchmarkSource", "TargetMetric", "DeviceSpec", "CircuitSpec"]
