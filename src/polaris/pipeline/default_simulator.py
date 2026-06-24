"""默认仿真器（从 integrated.py 拆分，规则 7.1 控制文件行数 ≤600）。

支持两种独立模式（非 fallback，按需选择）：
1. 真实 S 参数仿真：调用 polaris.sim.simulator.CircuitSimulator
2. 查表估算：基于器件类型损耗查表的快速估算（独立接口，用于快速可行性筛查）

仿真来源:
- simphony: https://simphonyphotonics.readthedocs.io/
- sax: https://flapport.github.io/sax/
- 查表损耗值来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
"""

from __future__ import annotations

import logging

from polaris.data.specs import CircuitSpec

logger = logging.getLogger(__name__)


class _DefaultSimulator:
    """默认仿真器。

    支持两种独立模式（非 fallback，按需选择）：
    1. 真实 S 参数仿真：调用 polaris.sim.simulator.CircuitSimulator
    2. 查表估算：基于器件类型损耗查表的快速估算（独立接口，用于快速可行性筛查）

    仿真来源:
    - simphony: https://simphonyphotonics.readthedocs.io/
    - sax: https://flapport.github.io/sax/
    - 查表损耗值来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
    """

    # 器件类型 → 单位损耗 (dB)
    # 来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
    # 波导类器件按 dB/cm × length(μm)/1e4 计算，其余为固定插损。
    _LOSS_TABLE: dict[str, float] = {
        "waveguide": 3.0,  # SOI strip waveguide 3.0 dB/cm，需乘以 length/1e4
        "straight": 3.0,  # 直波导（gdsfactory/LiDAR 命名），同 waveguide
        "strip_waveguide": 3.0,  # PoLaRIS PDK 标准波导名，同 waveguide
        "waveguide_bump$1": 3.0,  # SiEPIC 波导弯曲，同 waveguide
        "mzi": 1.0,  # MZI 插损 1.0 dB
        "ring": 0.3,  # 环谐振器插损 0.3 dB
        "ring_resonator": 0.3,  # 环谐振器（SiEPIC 命名），同 ring
        "grating_coupler": 1.9,  # GC 耦合损耗 1.9 dB
        "grating_coupler_1d": 1.9,  # SiEPIC ebeam_gc_te1550，同 grating_coupler
        "mmi": 0.4,  # MMI 1x2/2x2 插损 0.4 dB
        "mmi_1x2": 0.4,  # MMI 1x2（gdsfactory 命名），同 mmi
        "mmi_2x2": 0.4,  # MMI 2x2（gdsfactory 命名），同 mmi
        "y_branch": 0.3,  # Y 分支插损 0.3 dB
        "directional_coupler": 0.2,  # DC 插损 0.2 dB
        "ebeam_dc_halfring_straight$1": 0.2,  # SiEPIC 半环 DC，同 directional_coupler
        "DirectionalCoupler_SeriesRings$1": 0.2,  # SiEPIC 串联环 DC，同 directional_coupler
        "crossing": 0.2,  # 波导交叉插损 0.2 dB
        "ebeam_crossing4": 0.2,  # SiEPIC ebeam_crossing4，同 crossing
        "terminator": 0.1,  # 终端吸收器插损 0.1 dB
        "phase_shifter": 0.5,  # 热光移相器插损 0.5 dB
        "thermo_optic_phase_shifter": 0.5,  # PoLaRIS PDK 标准移相器名，同 phase_shifter
        "heater": 0.5,  # 加热器（同 phase_shifter）
        "ge_photodetector": 0.5,  # Ge 光电探测器耦合损耗 0.5 dB
        "avalanche_photodetector": 0.5,  # 雪崩光电探测器耦合损耗 0.5 dB
        "mzm_modulator": 4.0,  # MZM 调制器插损 4.0 dB（含分束+合束）
        "mrm_modulator": 0.5,  # MRM 调制器环耦合损耗 0.5 dB
        "thermo_optic_tuned_ring_modulator": 0.5,  # 热光环调制器，同 mrm_modulator
        "thermo_optic_switch": 1.0,  # 热光开关插损 1.0 dB
    }

    # 波导类器件类型集合（按长度计算损耗，需 length/wg_length 参数）
    _WAVEGUIDE_TYPES: frozenset[str] = frozenset(
        {"waveguide", "straight", "strip_waveguide", "waveguide_bump$1"}
    )

    def __init__(self, mode: str = "table") -> None:
        """初始化仿真器。

        Args:
            mode: 仿真模式，"real" 使用真实 S 参数仿真器，
                  "table" 使用查表估算（默认，快速）。
        """
        self._mode = mode
        self._sim = None
        if mode == "real":
            self._init_real_simulator()

    def _init_real_simulator(self) -> None:
        """初始化真实 S 参数仿真器。"""
        try:
            from polaris.sim.simulator import CircuitSimulator

            self._sim = CircuitSimulator()
            logger.info("真实 S 参数仿真器初始化成功")
        except Exception as e:
            raise RuntimeError(f"真实仿真器初始化失败: {e}") from e

    def simulate(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """仿真 S 参数（按初始化模式选择）。"""
        if self._mode == "real" and self._sim is not None:
            return self._simulate_real(circuit, placements, paths)
        return self._simulate_table(circuit, placements, paths)

    def _simulate_real(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """真实 S 参数级联仿真。"""
        result = self._sim.simulate(circuit)
        return {
            "total_loss_db": float(result.get("total_loss_db", 0.0)),
            "n_crossings": int(result.get("n_crossings", 0)),
        }

    def _simulate_table(self, circuit: CircuitSpec, placements: dict, paths: dict) -> dict:
        """查表估算损耗（独立接口，用于快速可行性筛查）。

        修复（违规 6/7/8）：
        - 违规 6：未知器件类型不再默认返回 0.0，改为 raise KeyError。
        - 违规 7：波导长度参数缺失不再用宽度代替，改为 raise ValueError。
        - 违规 8：n_crossings 不再固定返回 0，改为基于 paths 几何实际
          计算交叉数（线段相交检测）。

        来源: SiEPIC EBeam PDK (https://github.com/SiEPIC/SiEPIC_EBeam_PDK)
        """
        total_loss = 0.0
        for dev in circuit.devices:
            if dev.device_type not in self._LOSS_TABLE:
                raise KeyError(
                    f"器件类型 '{dev.device_type}' 不在损耗表中，"
                    f"已知类型: {sorted(self._LOSS_TABLE.keys())}。"
                    f"请在 _LOSS_TABLE 中补充该器件类型的损耗值。"
                )
            loss = self._LOSS_TABLE[dev.device_type]
            if dev.device_type in self._WAVEGUIDE_TYPES:
                # 波导类器件按长度计算损耗，支持 length/wg_length/length_um 参数名
                # length_um 为 SiEPIC/gdsfactory 标准命名
                length = dev.params.get(
                    "length", dev.params.get("wg_length", dev.params.get("length_um"))
                )
                if length is None:
                    raise ValueError(
                        f"波导器件 '{dev.name}'（类型 '{dev.device_type}'）"
                        f"缺少 length 参数，无法计算波导损耗。"
                        f"请在器件 params 中提供 length/length_um（μm）。"
                    )
                total_loss += loss * length / 1e4
            else:
                total_loss += loss
        n_crossings = _count_path_crossings(paths)
        return {"total_loss_db": total_loss, "n_crossings": n_crossings}


def _count_path_crossings(paths: dict) -> int:
    """基于路径几何计算交叉数（违规 8 修复）。

    遍历所有不同连接的线段对，检测是否相交（不含共享端点，不含同一路径内的相邻线段）。
    使用方向叉积（CCW）判断线段相交，复杂度 O(n^2 * m^2)，
    其中 n 为连接数，m 为单条路径线段数。对典型 PIC 规模（<100 连接）可接受。

    来源: 计算几何经典线段相交算法（Bentley-Ottmann 简化版）。
    """
    # 按路径分组存储线段，避免同一路径内的线段自相交误报
    path_segs: list[tuple[str, tuple[float, float], tuple[float, float]]] = []
    for net_id, pts in paths.items():
        if len(pts) < 2:
            continue
        for i in range(len(pts) - 1):
            p1 = (float(pts[i][0]), float(pts[i][1]))
            p2 = (float(pts[i + 1][0]), float(pts[i + 1][1]))
            path_segs.append((net_id, p1, p2))

    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    def _segments_intersect(p1, p2, p3, p4):
        """检测线段 p1p2 与 p3p4 是否真相交（不含共享端点）。"""
        d1 = _cross(p3, p4, p1)
        d2 = _cross(p3, p4, p2)
        d3 = _cross(p1, p2, p3)
        d4 = _cross(p1, p2, p4)
        if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and (
            (d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)
        ):
            return True
        return False

    crossings = 0
    n = len(path_segs)
    for i in range(n):
        for j in range(i + 1, n):
            # 跳过同一路径内的线段对（避免自相交误报）
            if path_segs[i][0] == path_segs[j][0]:
                continue
            _, p1, p2 = path_segs[i]
            _, p3, p4 = path_segs[j]
            if _segments_intersect(p1, p2, p3, p4):
                crossings += 1
    return crossings


__all__ = ["_DefaultSimulator"]
