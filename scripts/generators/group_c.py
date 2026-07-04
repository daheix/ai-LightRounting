#!/usr/bin/env python3
"""PoLaRIS 1000 电路生成器 - Group C（拓扑组 C）。

包含 3 种光子拓扑生成器，作为 1000 电路测试集的一部分：
1. RingDelayLineGenerator: 环形延迟线（CROW/SCISSOR 拓扑）
2. PolarizationArrayGenerator: 偏振分束/合束阵列
3. HybridTopologyGenerator: 混合 MZI+Ring+DC 拓扑

参数来源（规则 18 学术诚信，禁止造假）：
- CROW: Yariv et al., Optics Express 2002
  "Coupled-resonator optical waveguides: a reduced Bloch-mode formulation"
- SCISSOR: Poon JOSA B 2004
  "Design of side-coupled integrated spaced sequences of resonators"
- PBS/PBC: SiEPIC EBeam PDK; T.Barwicz IBM J Res 2007
  "Polarization splitter based on silicon-on-insulator waveguides"
- 混合拓扑: SiEPIC EBeam PDK + gdsfactory 示例（混合拓扑设计）
"""

from __future__ import annotations

from scripts.generate_1000_circuits import (
    CircuitGenerator,
    PlatformConfig,
    ScaleConfig,
)

# =============================================================================
# 规模映射表（每个生成器的 ring/组/单元数量，按 scale.name 索引）
# =============================================================================

# RingDelayLine: ring 数量（CROW/SCISSOR 谐振器链长度）
_RING_DELAY_LINE_SCALE: dict[str, int] = {
    "XS": 2, "S": 4, "M": 8, "L": 16, "XL": 32,
}

# PolarizationArray: PBS+PBC 组数（每组 1 PBS + 1 PBC + 2 waveguide）
_POLARIZATION_ARRAY_SCALE: dict[str, int] = {
    "XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16,
}

# HybridTopology: MZI+Ring 单元数（每单元 7 器件）
_HYBRID_TOPOLOGY_SCALE: dict[str, int] = {
    "XS": 1, "S": 2, "M": 3, "L": 4, "XL": 6,
}


# =============================================================================
# 生成器 1: RingDelayLineGenerator（环形延迟线，CROW/SCISSOR 拓扑）
# =============================================================================


class RingDelayLineGenerator(CircuitGenerator):
    """环形延迟线生成器（CROW / SCISSOR 拓扑）。

    器件组成：ring_resonator + strip_waveguide
    - CROW（Coupled Resonator Optical Waveguide）拓扑：
      ring.through → next ring.in（谐振器串联，信号沿 through 总线传播）
    - SCISSOR（Side-Coupled Integrated Spaced-Sequence of Resonators）拓扑：
      ring.drop → next ring.add（谐振器侧向耦合，信号沿 drop 总线传播）

    规模映射（ring 数量）：
      XS=2, S=4, M=8, L=16, XL=32
    每个规模的总器件数 = N ring + (N-1) 中间波导 + 1 输入波导 + 1 输出波导 = 2N+1
      XS=5, S=9, M=17, L=33, XL=65（均落在规模映射规则的合法区间内）

    拓扑选择：根据 seed 奇偶性选择 CROW（偶数）或 SCISSOR（奇数），
    增加测试集多样性。

    来源:
      - CROW: Yariv et al., Optics Express 2002
      - SCISSOR: Poon JOSA B 2004
    """

    # 学术诚信：参数来源标注
    CROW_SOURCE = "Yariv et al., Optics Express 2002 (CROW)"
    SCISSOR_SOURCE = "Poon JOSA B 2004 (SCISSOR)"

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        """初始化环形延迟线生成器。

        Args:
            scale: 规模配置。
            platform: 平台配置。
            seed: 随机种子（奇偶性决定 CROW/SCISSOR 拓扑）。
        """
        super().__init__(
            topology="ring_delay_line",
            scale=scale, platform=platform, seed=seed,
        )
        # 根据 seed 奇偶性选择拓扑（偶数→CROW，奇数→SCISSOR）
        self.use_crow = (seed % 2 == 0)

    def generate(self) -> dict:
        """生成环形延迟线电路。"""
        n_rings = _RING_DELAY_LINE_SCALE[self.scale.name]
        topology_type = "CROW" if self.use_crow else "SCISSOR"
        source = self.CROW_SOURCE if self.use_crow else self.SCISSOR_SOURCE

        name = (
            f"ring_delay_line_{topology_type.lower()}_"
            f"{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        )
        circuit = self._base_circuit_dict(
            name,
            f"环形延迟线 {topology_type} ({self.scale.name}/{self.platform.name})",
        )

        # 器件参数（来源标注于 params.source）
        ring_params = {
            "radius_um": self.platform.r_min_um,
            "gap_um": 0.2,
            "topology": topology_type,
            "source": source,
        }
        wg_params = {
            "width_um": self.platform.waveguide_width_um,
            "length_um": 30.0,
            "source": self.platform.source_url,
        }

        # Ring 端口: in(W), through(E), drop(E), add(W)
        ring_ports = [
            ["in", 0.0, 0.0, "W"],
            ["through", 10.0, 0.0, "E"],
            ["drop", 10.0, 11.0, "E"],
            ["add", 0.0, 11.0, "W"],
        ]
        # waveguide 端口: in(W), out(E)
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 30.0, 0.0, "E"]]

        devices: list[dict] = []
        connections: list[list] = []

        # 输入 waveguide（信号入口）
        wg_in_name = self._next_device_name("wg")
        devices.append(
            self._make_device(wg_in_name, "strip_waveguide", wg_ports, 30.0, 0.5, wg_params)
        )

        # 生成 N 个 ring
        ring_names: list[str] = []
        for _ in range(n_rings):
            ring_name = self._next_device_name("ring")
            ring_names.append(ring_name)
            devices.append(
                self._make_device(ring_name, "ring_resonator", ring_ports, 10.0, 11.0, ring_params)
            )

        # 输入 waveguide → 第一个 ring.in
        connections.append(self._make_connection(wg_in_name, "out", ring_names[0], "in"))

        # ring 之间通过 waveguide 级联
        for i in range(n_rings - 1):
            wg_name = self._next_device_name("wg")
            devices.append(
                self._make_device(wg_name, "strip_waveguide", wg_ports, 30.0, 0.5, wg_params)
            )
            if self.use_crow:
                # CROW: ring.through → wg → next ring.in
                connections.append(self._make_connection(ring_names[i], "through", wg_name, "in"))
                connections.append(self._make_connection(wg_name, "out", ring_names[i + 1], "in"))
            else:
                # SCISSOR: ring.drop → wg → next ring.add
                connections.append(self._make_connection(ring_names[i], "drop", wg_name, "in"))
                connections.append(self._make_connection(wg_name, "out", ring_names[i + 1], "add"))

        # 输出 waveguide（信号出口）
        wg_out_name = self._next_device_name("wg")
        devices.append(
            self._make_device(wg_out_name, "strip_waveguide", wg_ports, 30.0, 0.5, wg_params)
        )
        if self.use_crow:
            # CROW: 最后 ring.through → 输出 waveguide
            connections.append(self._make_connection(ring_names[-1], "through", wg_out_name, "in"))
        else:
            # SCISSOR: 最后 ring.drop → 输出 waveguide
            connections.append(self._make_connection(ring_names[-1], "drop", wg_out_name, "in"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit


# =============================================================================
# 生成器 2: PolarizationArrayGenerator（偏振分束/合束阵列）
# =============================================================================


class PolarizationArrayGenerator(CircuitGenerator):
    """偏振分束/合束阵列生成器。

    器件组成：PBS（偏振分束器）+ PBC（偏振合束器）+ strip_waveguide
    每组结构：
      PBS.in(W) → PBS.through(TE,E) → waveguide → PBC.in1(TE,W)
                → PBS.drop(TM,S)   → waveguide → PBC.in2(TM,N)
                → PBC.out(E)

    规模映射（PBS+PBC 组数）：
      XS=1, S=2, M=4, L=8, XL=16
    每组器件数 = 1 PBS + 1 PBC + 2 waveguide = 4
      XS=4, S=8, M=16, L=32, XL=64（均落在规模映射规则的合法区间内）

    来源: SiEPIC EBeam PDK; T.Barwicz IBM J Res 2007
    """

    # 学术诚信：参数来源标注
    PBS_SOURCE = "SiEPIC EBeam PDK; T.Barwicz IBM J Res 2007"

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        """初始化偏振阵列生成器。

        Args:
            scale: 规模配置。
            platform: 平台配置。
            seed: 随机种子。
        """
        super().__init__(
            topology="polarization_array",
            scale=scale, platform=platform, seed=seed,
        )

    def generate(self) -> dict:
        """生成偏振分束/合束阵列电路。"""
        n_groups = _POLARIZATION_ARRAY_SCALE[self.scale.name]

        name = (
            f"polarization_array_"
            f"{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        )
        circuit = self._base_circuit_dict(
            name,
            f"偏振分束/合束阵列 ({self.scale.name}/{self.platform.name})",
        )

        # 器件参数（来源标注于 params.source）
        pbs_params = {
            "extinction_ratio_db": 20.0,
            "insertion_loss_db": 0.5,
            "source": self.PBS_SOURCE,
        }
        pbc_params = {
            "extinction_ratio_db": 20.0,
            "insertion_loss_db": 0.5,
            "source": self.PBS_SOURCE,
        }
        wg_params = {
            "width_um": self.platform.waveguide_width_um,
            "length_um": 40.0,
            "source": self.platform.source_url,
        }

        # PBS 端口: in(W), through(TE,E), drop(TM,S)
        pbs_ports = [
            ["in", 0.0, 5.0, "W"],
            ["through", 20.0, 5.0, "E"],
            ["drop", 10.0, 0.0, "S"],
        ]
        # PBC 端口: in1(TE,W), in2(TM,N), out(E)
        pbc_ports = [
            ["in1", 0.0, 5.0, "W"],
            ["in2", 10.0, 0.0, "N"],
            ["out", 20.0, 5.0, "E"],
        ]
        # TE 路径波导（水平）: in(W), out(E)
        # 用于 PBS.through(E) → wg_te.in(W) → wg_te.out(E) → PBC.in1(W)
        # 连接方向: east↔west 相对（合法）
        wg_te_ports = [["in", 0.0, 0.0, "W"], ["out", 40.0, 0.0, "E"]]
        # TM 路径波导（垂直）: in(N), out(S)
        # 用于 PBS.drop(S) → wg_tm.in(N) → wg_tm.out(S) → PBC.in2(N)
        # 连接方向: south↔north 相对（合法，修复 PORT_FACING 真违规）
        # 修复说明: 原设计 wg_tm 用水平波导 in(W)/out(E)，导致
        #   PBS.drop(S)→wg_tm.in(W) south↔west 非相对，
        #   wg_tm.out(E)→PBC.in2(N) east↔north 非相对。
        # 改为垂直波导后两端连接均为 south↔north 相对。
        wg_tm_ports = [["in", 0.0, 40.0, "N"], ["out", 0.0, 0.0, "S"]]

        devices: list[dict] = []
        connections: list[list] = []

        for _ in range(n_groups):
            pbs_name = self._next_device_name("pbs")
            pbc_name = self._next_device_name("pbc")
            wg_te_name = self._next_device_name("wg")  # TE 路径波导（水平）
            wg_tm_name = self._next_device_name("wg")  # TM 路径波导（垂直）

            devices.append(
                self._make_device(pbs_name, "polarization_beam_splitter",
                                  pbs_ports, 20.0, 10.0, pbs_params)
            )
            devices.append(
                self._make_device(pbc_name, "polarization_beam_combiner",
                                  pbc_ports, 20.0, 10.0, pbc_params)
            )
            # TE 路径波导: 水平 40×0.5μm
            devices.append(
                self._make_device(wg_te_name, "strip_waveguide",
                                  wg_te_ports, 40.0, 0.5, wg_params)
            )
            # TM 路径波导: 垂直 0.5×40μm（与 PBS.drop(S)/PBC.in2(N) 方向相对）
            devices.append(
                self._make_device(wg_tm_name, "strip_waveguide",
                                  wg_tm_ports, 0.5, 40.0, wg_params)
            )

            # PBS.through(TE,E) → waveguide(W) → PBC.in1(TE,W)  [east↔west 相对]
            connections.append(self._make_connection(pbs_name, "through", wg_te_name, "in"))
            connections.append(self._make_connection(wg_te_name, "out", pbc_name, "in1"))
            # PBS.drop(TM,S) → waveguide(N) → PBC.in2(TM,N)  [south↔north 相对]
            connections.append(self._make_connection(pbs_name, "drop", wg_tm_name, "in"))
            connections.append(self._make_connection(wg_tm_name, "out", pbc_name, "in2"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit


# =============================================================================
# 生成器 3: HybridTopologyGenerator（混合 MZI+Ring+DC 拓扑）
# =============================================================================


class HybridTopologyGenerator(CircuitGenerator):
    """混合 MZI+Ring+DC 拓扑生成器（模拟真实 OEIC）。

    器件组成：directional_coupler + ring_resonator + strip_waveguide
              + phase_shifter + photodetector

    每个单元（1 MZI + 1 Ring）= 7 器件：
      - 2 × directional_coupler（MZI 的输入/输出耦合器）
      - 1 × strip_waveguide（MZI 上臂）
      - 1 × phase_shifter（MZI 下臂，含相位调制）
      - 1 × ring_resonator（WDM 滤波）
      - 1 × strip_waveguide（Ring → detector 连接波导）
      - 1 × photodetector（光探测）

    连接链路（模拟 WDM 滤波+检测）：
      dc1.out1 → wg_arm.in → dc2.in1   （MZI 上臂）
      dc1.out2 → ps_arm.in → dc2.in2   （MZI 下臂，含相移）
      dc2.out1 → ring.in               （MZI 输出 → Ring 滤波）
      ring.through → wg_out.in → det.in（Ring 输出 → 探测）

    规模映射（MZI+Ring 单元数）：
      XS=1, S=2, M=3, L=4, XL=6
    每单元 7 器件：
      XS=7, S=14, M=21, L=28, XL=42（任务明确指定映射）

    来源: 混合拓扑设计，参考 SiEPIC EBeam PDK + gdsfactory 示例
    """

    # 学术诚信：参数来源标注（混合拓扑设计，参考公开 PDK 与示例）
    HYBRID_SOURCE = "SiEPIC EBeam PDK + gdsfactory 示例（混合拓扑设计）"

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        """初始化混合拓扑生成器。

        Args:
            scale: 规模配置。
            platform: 平台配置。
            seed: 随机种子。
        """
        super().__init__(
            topology="hybrid_topology",
            scale=scale, platform=platform, seed=seed,
        )

    def generate(self) -> dict:
        """生成混合 MZI+Ring+DC 拓扑电路。"""
        n_units = _HYBRID_TOPOLOGY_SCALE[self.scale.name]

        name = (
            f"hybrid_topology_"
            f"{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        )
        circuit = self._base_circuit_dict(
            name,
            f"混合 MZI+Ring+DC 拓扑 ({self.scale.name}/{self.platform.name})",
        )

        # 器件参数（来源标注于 params.source）
        dc_params = {
            "gap_um": 0.2,
            "coupling_length_um": 20.0,
            "source": self.HYBRID_SOURCE,
        }
        ring_params = {
            "radius_um": self.platform.r_min_um,
            "gap_um": 0.2,
            "source": self.HYBRID_SOURCE,
        }
        wg_params = {
            "width_um": self.platform.waveguide_width_um,
            "length_um": 50.0,
            "source": self.platform.source_url,
        }
        ps_params = {
            "phase_shift_rad": 3.14159265,  # π 相移（MZI 调制）
            "length_um": 50.0,
            "source": self.HYBRID_SOURCE,
        }
        det_params = {
            "responsivity_A_W": 0.8,
            "source": self.HYBRID_SOURCE,
        }

        # DC 端口: in1(W), in2(W), out1(E), out2(E)
        dc_ports = [
            ["in1", 0.0, 7.0, "W"],
            ["in2", 0.0, 3.0, "W"],
            ["out1", 30.0, 7.0, "E"],
            ["out2", 30.0, 3.0, "E"],
        ]
        # Ring 端口: in(W), through(E), drop(E), add(W)
        ring_ports = [
            ["in", 0.0, 0.0, "W"],
            ["through", 10.0, 0.0, "E"],
            ["drop", 10.0, 11.0, "E"],
            ["add", 0.0, 11.0, "W"],
        ]
        # waveguide 端口: in(W), out(E)
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]
        # phase_shifter 端口: in(W), out(E)
        ps_ports = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]
        # detector 端口: in(W)
        det_ports = [["in", 0.0, 10.0, "W"]]

        devices: list[dict] = []
        connections: list[list] = []

        for _ in range(n_units):
            # MZI: 2 DC + 1 waveguide(上臂) + 1 phase_shifter(下臂)
            dc1_name = self._next_device_name("dc")
            dc2_name = self._next_device_name("dc")
            wg_arm_name = self._next_device_name("wg")
            ps_arm_name = self._next_device_name("ps")
            # Ring 滤波器
            ring_name = self._next_device_name("ring")
            # Ring → detector 连接波导
            wg_out_name = self._next_device_name("wg")
            # 光探测器
            det_name = self._next_device_name("det")

            devices.append(
                self._make_device(dc1_name, "directional_coupler",
                                  dc_ports, 30.0, 10.0, dc_params)
            )
            devices.append(
                self._make_device(dc2_name, "directional_coupler",
                                  dc_ports, 30.0, 10.0, dc_params)
            )
            devices.append(
                self._make_device(wg_arm_name, "strip_waveguide",
                                  wg_ports, 50.0, 0.5, wg_params)
            )
            devices.append(
                self._make_device(ps_arm_name, "phase_shifter",
                                  ps_ports, 50.0, 1.0, ps_params)
            )
            devices.append(
                self._make_device(ring_name, "ring_resonator",
                                  ring_ports, 10.0, 11.0, ring_params)
            )
            devices.append(
                self._make_device(wg_out_name, "strip_waveguide",
                                  wg_ports, 50.0, 0.5, wg_params)
            )
            devices.append(
                self._make_device(det_name, "photodetector",
                                  det_ports, 20.0, 20.0, det_params)
            )

            # MZI 内部连接（上下两臂）
            # dc1.out1 → wg_arm.in（上臂波导）
            connections.append(self._make_connection(dc1_name, "out1", wg_arm_name, "in"))
            # dc1.out2 → ps_arm.in（下臂相移器）
            connections.append(self._make_connection(dc1_name, "out2", ps_arm_name, "in"))
            # wg_arm.out → dc2.in1（上臂汇合）
            connections.append(self._make_connection(wg_arm_name, "out", dc2_name, "in1"))
            # ps_arm.out → dc2.in2（下臂汇合）
            connections.append(self._make_connection(ps_arm_name, "out", dc2_name, "in2"))

            # MZI 输出 → Ring 输入（WDM 滤波）
            # dc2.out1 → ring.in
            connections.append(self._make_connection(dc2_name, "out1", ring_name, "in"))

            # Ring 输出 → waveguide → 探测器（光检测）
            # ring.through → wg_out.in
            connections.append(self._make_connection(ring_name, "through", wg_out_name, "in"))
            # wg_out.out → det.in
            connections.append(self._make_connection(wg_out_name, "out", det_name, "in"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit
