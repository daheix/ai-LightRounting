#!/usr/bin/env python3
"""PoLaRIS 电路生成器组 B（Task 5 - 5 种拓扑）。

包含 5 种光子集成电路拓扑生成器：
1. WDMMuxDemuxGenerator: WDM 复用/解复用器（AWG + 波导）
2. OpticalSwitchMatrixGenerator: 光开关矩阵（Benes 网络）
3. ModulatorArrayGenerator: 调制器阵列（并联 MZM）
4. QuantumPhotonicsGenerator: 量子光子电路（HOM/KLM/玻色采样）
5. LatticeFilterGenerator: 格栅滤波器（DC-PS 级联）

参数来源（规则 18 学术诚信）：
- AWG: Takada et al., 1984; SiEPIC EBeam PDK
- Benes 网络: Benes 1965; Spanke & Murphy JLT 1988
- MZM: SiEPIC EBeam PDK; LNOI 电光调制器
- 量子光子: HOM 1987; KLM 2001; Clements 2016
- 格栅滤波器: Madsen & Zhao, Optical Filter Design, 1999
"""

from __future__ import annotations

import math

from scripts.generate_1000_circuits import (
    CircuitGenerator,
    PlatformConfig,
    ScaleConfig,
)

# =============================================================================
# 1. WDM 复用/解复用器生成器
# =============================================================================


class WDMMuxDemuxGenerator(CircuitGenerator):
    """WDM 复用/解复用器生成器（AWG + 波导）。

    器件组成：1 个 AWG（阵列波导光栅）+ N 个输入波导 + N 个输出波导。
    AWG 端口：N 个输入(W) + N 个输出(E)。
    规模映射：XS=4, S=8, M=16, L=32, XL=64 通道。
    来源: Takada et al., 1984; SiEPIC EBeam PDK。
    """

    # 规模 → 通道数映射
    CHANNEL_MAP = {"XS": 4, "S": 8, "M": 16, "L": 32, "XL": 64}

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="wdm_mux_demux", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成 WDM 复用/解复用器电路。"""
        n = self.CHANNEL_MAP[self.scale.name]
        name = f"wdm_mux_demux_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"WDM 复用/解复用器 {n} 通道 ({self.scale.name}/{self.platform.name})"
        )

        # AWG 端口：N 个输入(W) + N 个输出(E)，垂直排列
        port_spacing = 10.0
        awg_h = max(n * port_spacing, 20.0)
        awg_ports = []
        for i in range(n):
            y = (i + 0.5) * port_spacing
            awg_ports.append([f"in{i+1}", 0.0, y, "W"])
        for i in range(n):
            y = (i + 0.5) * port_spacing
            awg_ports.append([f"out{i+1}", 100.0, y, "E"])

        awg_params = {
            "channels": n, "fsr_nm": 20.0 * n, "insertion_loss_db": 3.0,
            "source": "Takada et al., 1984; SiEPIC EBeam PDK",
        }
        awg_name = self._next_device_name("awg")
        circuit["devices"].append(
            self._make_device(awg_name, "arrayed_waveguide_grating",
                              awg_ports, 100.0, awg_h, awg_params)
        )

        # 波导参数
        wg_params = {
            "width_um": self.platform.waveguide_width_um, "length_um": 50.0,
            "source": self.platform.source_url,
        }
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]

        # 输入/输出波导
        in_wgs, out_wgs = [], []
        for _ in range(n):
            in_wg = self._next_device_name("wg_in")
            out_wg = self._next_device_name("wg_out")
            in_wgs.append(in_wg)
            out_wgs.append(out_wg)
            circuit["devices"].append(
                self._make_device(in_wg, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params)
            )
            circuit["devices"].append(
                self._make_device(out_wg, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params)
            )

        # 连接：输入波导.out → AWG.in_i, AWG.out_i → 输出波导.in
        for i in range(n):
            circuit["connections"].append(
                self._make_connection(in_wgs[i], "out", awg_name, f"in{i+1}")
            )
            circuit["connections"].append(
                self._make_connection(awg_name, f"out{i+1}", out_wgs[i], "in")
            )

        return circuit


# =============================================================================
# 2. 光开关矩阵生成器
# =============================================================================


class OpticalSwitchMatrixGenerator(CircuitGenerator):
    """光开关矩阵生成器（Benes 网络）。

    器件组成：2x2 光开关单元级联。
    2x2 开关端口：in1(W), in2(W), out1(E), out2(E)。
    规模映射：XS=2x2, S=4x4, M=8x8, L=16x16, XL=32x32。
    连接：Benes 网络拓扑（级联 2x2 开关）。
    来源: Benes 1965; Spanke & Murphy JLT 1988。
    """

    # 规模 → 端口数映射
    PORT_MAP = {"XS": 2, "S": 4, "M": 8, "L": 16, "XL": 32}

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="switch_matrix", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成光开关矩阵电路。

        Benes 网络: N×N 无阻塞开关矩阵, 由 2x2 开关单元级联构成。
        - stages = 2*log2(N) - 1 (Benes 1965)
        - 每级 N/2 个 2x2 开关
        - 级间按 Benes 拓扑连接 (此处简化为直通级联, 保证连通性)

        修复: 原 XS(n=2) 时 stages=1, range(0) 不生成连接。
        现添加输入/输出波导, 并保证至少有 I/O 连接 (即使单级开关也有连接)。
        """
        n = self.PORT_MAP[self.scale.name]
        name = f"switch_matrix_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"光开关矩阵 {n}x{n} Benes ({self.scale.name}/{self.platform.name})"
        )

        # Benes 网络：stages = 2*log2(N) - 1, 每级 N/2 个开关
        # n=2 时 stages=1 (单级即可实现 2x2 交换), n=4 时 stages=3, n=8 时 stages=5
        stages = 2 * int(math.log2(n)) - 1 if n >= 2 else 1
        switches_per_stage = n // 2

        sw_params = {
            "insertion_loss_db": 0.5, "crosstalk_db": -30.0, "switch_time_ns": 10.0,
            "source": "Benes 1965; Spanke & Murphy JLT 1988",
        }
        sw_ports = [["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
                    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"]]

        # 生成所有开关（按级排列）
        switch_grid: list[list[str]] = []
        for _ in range(stages):
            stage_switches = []
            for _ in range(switches_per_stage):
                sw_name = self._next_device_name("sw")
                stage_switches.append(sw_name)
                circuit["devices"].append(
                    self._make_device(sw_name, "optical_switch_2x2",
                                      sw_ports, 30.0, 10.0, sw_params)
                )
            switch_grid.append(stage_switches)

        # 输入/输出波导 (N 条输入 + N 条输出)
        wg_params = {
            "width_um": self.platform.waveguide_width_um, "length_um": 50.0,
            "source": self.platform.source_url,
        }
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]
        in_wgs: list[str] = []
        out_wgs: list[str] = []
        for _ in range(n):
            in_wg = self._next_device_name("wg_in")
            out_wg = self._next_device_name("wg_out")
            in_wgs.append(in_wg)
            out_wgs.append(out_wg)
            circuit["devices"].append(
                self._make_device(in_wg, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params)
            )
            circuit["devices"].append(
                self._make_device(out_wg, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params)
            )

        # 级间连接：简化 Benes 拓扑（直通级联）
        # 第 i 级开关 j 的 out1 → 第 i+1 级开关 j 的 in1
        # 第 i 级开关 j 的 out2 → 第 i+1 级开关 j 的 in2
        for stage in range(stages - 1):
            for idx in range(switches_per_stage):
                circuit["connections"].append(
                    self._make_connection(switch_grid[stage][idx], "out1",
                                          switch_grid[stage + 1][idx], "in1")
                )
                circuit["connections"].append(
                    self._make_connection(switch_grid[stage][idx], "out2",
                                          switch_grid[stage + 1][idx], "in2")
                )

        # 输入波导 → 第一级开关 (N 条输入对应 N/2 个开关的 2 个输入端)
        # 输入 i (i=0..N-1): 偶数 i → sw[i//2].in1, 奇数 i → sw[i//2].in2
        for i in range(n):
            sw_idx = i // 2
            port = "in1" if i % 2 == 0 else "in2"
            circuit["connections"].append(
                self._make_connection(in_wgs[i], "out", switch_grid[0][sw_idx], port)
            )

        # 最后一级开关 → 输出波导 (N/2 个开关的 2 个输出端对应 N 条输出)
        # 开关 j: out1 → 输出[2j], out2 → 输出[2j+1]
        last_stage = switch_grid[-1]
        for j in range(switches_per_stage):
            circuit["connections"].append(
                self._make_connection(last_stage[j], "out1", out_wgs[2 * j], "in")
            )
            circuit["connections"].append(
                self._make_connection(last_stage[j], "out2", out_wgs[2 * j + 1], "in")
            )

        return circuit


# =============================================================================
# 3. 调制器阵列生成器
# =============================================================================


class ModulatorArrayGenerator(CircuitGenerator):
    """调制器阵列生成器（并联 MZM）。

    器件组成：MZM 阵列 + 输入波导 + 探测器。
    MZM 端口：in(W), rf_in(N), out(E)。
    规模映射：XS=2, S=4, M=8, L=16, XL=32 MZM。
    连接：并联 MZM 阵列（输入分光 → 各 MZM → 探测器）。
    来源: SiEPIC EBeam PDK; LNOI 电光调制器。
    """

    # 规模 → MZM 数量映射
    MZM_MAP = {"XS": 2, "S": 4, "M": 8, "L": 16, "XL": 32}

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="modulator_array", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成调制器阵列电路。"""
        n = self.MZM_MAP[self.scale.name]
        name = f"modulator_array_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"调制器阵列 {n} MZM ({self.scale.name}/{self.platform.name})"
        )

        # 输入波导（共享光源，分光至各 MZM）
        wg_params = {
            "width_um": self.platform.waveguide_width_um, "length_um": 50.0,
            "source": self.platform.source_url,
        }
        wg_ports = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]
        wg_in = self._next_device_name("wg_in")
        circuit["devices"].append(
            self._make_device(wg_in, "strip_waveguide", wg_ports, 50.0, 0.5, wg_params)
        )

        # MZM 阵列
        mzm_params = {
            "vpi_V": 3.5, "bandwidth_GHz": 40.0, "insertion_loss_db": 4.0,
            "source": "SiEPIC EBeam PDK; LNOI 电光调制器",
        }
        mzm_ports = [["in", 0.0, 5.0, "W"], ["rf_in", 25.0, 15.0, "N"],
                     ["out", 50.0, 5.0, "E"]]
        mzm_names = []
        for _ in range(n):
            mzm = self._next_device_name("mzm")
            mzm_names.append(mzm)
            circuit["devices"].append(
                self._make_device(mzm, "mach_zehnder_modulator",
                                  mzm_ports, 50.0, 15.0, mzm_params)
            )

        # 探测器阵列
        det_params = {"responsivity_A_W": 0.8, "bandwidth_GHz": 40.0,
                      "source": self.platform.source_url}
        det_ports = [["in", 0.0, 5.0, "W"]]
        det_names = []
        for _ in range(n):
            det = self._next_device_name("det")
            det_names.append(det)
            circuit["devices"].append(
                self._make_device(det, "photodetector", det_ports, 20.0, 20.0, det_params)
            )

        # 连接：wg_in.out → 各 MZM.in, MZM.out → 各探测器.in
        for i in range(n):
            circuit["connections"].append(
                self._make_connection(wg_in, "out", mzm_names[i], "in")
            )
            circuit["connections"].append(
                self._make_connection(mzm_names[i], "out", det_names[i], "in")
            )

        return circuit


# =============================================================================
# 4. 量子光子电路生成器
# =============================================================================


class QuantumPhotonicsGenerator(CircuitGenerator):
    """量子光子电路生成器。

    器件组成：DC + phase_shifter + 单光子源 + 单光子探测器。
    规模映射：
    - XS=HOM(2源+2探+1DC)
    - S=KLM CNOT(4源+4探+6DC+3PS)
    - M=玻色采样4模(4源+4探+6DC)
    - L=玻色采样8模
    - XL=玻色采样16模
    来源: HOM 1987; KLM 2001; Clements 2016。
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="quantum_photonics", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成量子光子电路。"""
        name = f"quantum_photonics_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"量子光子电路 ({self.scale.name}/{self.platform.name})"
        )

        if self.scale.name == "XS":
            self._gen_hom(circuit)
        elif self.scale.name == "S":
            self._gen_klm_cnot(circuit)
        else:
            # M=4模, L=8模, XL=16模
            modes = {"M": 4, "L": 8, "XL": 16}[self.scale.name]
            self._gen_boson_sampling(circuit, modes)

        return circuit

    def _gen_hom(self, circuit: dict) -> None:
        """生成 HOM 干涉仪（2源+2探+1DC）。来源: HOM 1987。"""
        src_params = {"wavelength_nm": self.platform.wavelength_nm, "source": "HOM 1987"}
        det_params = {"dark_count_hz": 100, "efficiency": 0.9, "source": "HOM 1987"}
        dc_params = {"coupling_ratio": 0.5, "source": "HOM 1987"}

        src_ports = [["out", 50.0, 5.0, "E"]]
        det_ports = [["in", 0.0, 5.0, "W"]]
        dc_ports = [["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
                    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"]]

        s1 = self._next_device_name("src")
        s2 = self._next_device_name("src")
        dc1 = self._next_device_name("dc")
        d1 = self._next_device_name("det")
        d2 = self._next_device_name("det")

        circuit["devices"] = [
            self._make_device(s1, "single_photon_source", src_ports, 50.0, 10.0, src_params),
            self._make_device(s2, "single_photon_source", src_ports, 50.0, 10.0, src_params),
            self._make_device(dc1, "directional_coupler", dc_ports, 30.0, 10.0, dc_params),
            self._make_device(d1, "single_photon_detector", det_ports, 20.0, 10.0, det_params),
            self._make_device(d2, "single_photon_detector", det_ports, 20.0, 10.0, det_params),
        ]
        circuit["connections"] = [
            self._make_connection(s1, "out", dc1, "in1"),
            self._make_connection(s2, "out", dc1, "in2"),
            self._make_connection(dc1, "out1", d1, "in"),
            self._make_connection(dc1, "out2", d2, "in"),
        ]

    def _gen_klm_cnot(self, circuit: dict) -> None:
        """生成 KLM CNOT 门（4源+4探+6DC+3PS）。来源: KLM 2001。"""
        src_params = {"wavelength_nm": self.platform.wavelength_nm, "source": "KLM 2001"}
        det_params = {"dark_count_hz": 100, "efficiency": 0.9, "source": "KLM 2001"}
        dc_params = {"coupling_ratio": 0.5, "source": "KLM 2001"}
        ps_params = {"phase_rad": math.pi, "source": "KLM 2001"}

        src_ports = [["out", 50.0, 5.0, "E"]]
        det_ports = [["in", 0.0, 5.0, "W"]]
        dc_ports = [["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
                    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"]]
        ps_ports = [["in", 0.0, 5.0, "W"], ["out", 30.0, 5.0, "E"]]

        # 4 源 + 6 DC + 3 PS + 4 探 = 17 器件
        s = [self._next_device_name("src") for _ in range(4)]
        dc = [self._next_device_name("dc") for _ in range(6)]
        ps = [self._next_device_name("ps") for _ in range(3)]
        d = [self._next_device_name("det") for _ in range(4)]

        for nm in s:
            circuit["devices"].append(
                self._make_device(nm, "single_photon_source", src_ports, 50.0, 10.0, src_params)
            )
        for nm in dc:
            circuit["devices"].append(
                self._make_device(nm, "directional_coupler", dc_ports, 30.0, 10.0, dc_params)
            )
        for nm in ps:
            circuit["devices"].append(
                self._make_device(nm, "phase_shifter", ps_ports, 30.0, 10.0, ps_params)
            )
        for nm in d:
            circuit["devices"].append(
                self._make_device(nm, "single_photon_detector", det_ports, 20.0, 10.0, det_params)
            )

        # 连接（简化 KLM CNOT 拓扑：两路干涉 + 合束）
        # 上路: s0,s1 → dc0 → ps0 → dc1 → dc2 → d0,d1
        # 下路: s2,s3 → dc3 → ps2 → dc4 → dc5 → d2,d3
        # 中间: dc1.out2 → ps1 → dc2.in2
        circuit["connections"] = [
            self._make_connection(s[0], "out", dc[0], "in1"),
            self._make_connection(s[1], "out", dc[0], "in2"),
            self._make_connection(dc[0], "out1", ps[0], "in"),
            self._make_connection(ps[0], "out", dc[1], "in1"),
            self._make_connection(dc[0], "out2", dc[1], "in2"),
            self._make_connection(dc[1], "out1", dc[2], "in1"),
            self._make_connection(dc[1], "out2", ps[1], "in"),
            self._make_connection(ps[1], "out", dc[2], "in2"),
            self._make_connection(s[2], "out", dc[3], "in1"),
            self._make_connection(s[3], "out", dc[3], "in2"),
            self._make_connection(dc[3], "out1", ps[2], "in"),
            self._make_connection(ps[2], "out", dc[4], "in1"),
            self._make_connection(dc[3], "out2", dc[4], "in2"),
            self._make_connection(dc[4], "out1", dc[5], "in1"),
            self._make_connection(dc[4], "out2", dc[5], "in2"),
            self._make_connection(dc[2], "out1", d[0], "in"),
            self._make_connection(dc[2], "out2", d[1], "in"),
            self._make_connection(dc[5], "out1", d[2], "in"),
            self._make_connection(dc[5], "out2", d[3], "in"),
        ]

    def _gen_boson_sampling(self, circuit: dict, modes: int) -> None:
        """生成玻色采样电路（Clements 拓扑）。来源: Clements 2016。

        Clements 拓扑：modes 层 DC，总 modes*(modes-1)/2 个 DC。
        偶数层：DC 连接 (0,1), (2,3), ...
        奇数层：DC 连接 (1,2), (3,4), ...
        """
        src_params = {"wavelength_nm": self.platform.wavelength_nm, "source": "Clements 2016"}
        det_params = {"dark_count_hz": 100, "efficiency": 0.9, "source": "Clements 2016"}
        dc_params = {"coupling_ratio": 0.5, "source": "Clements 2016"}

        src_ports = [["out", 50.0, 5.0, "E"]]
        det_ports = [["in", 0.0, 5.0, "W"]]
        dc_ports = [["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
                    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"]]

        # 源和探测器
        srcs = [self._next_device_name("src") for _ in range(modes)]
        dets = [self._next_device_name("det") for _ in range(modes)]
        for nm in srcs:
            circuit["devices"].append(
                self._make_device(nm, "single_photon_source", src_ports, 50.0, 10.0, src_params)
            )
        for nm in dets:
            circuit["devices"].append(
                self._make_device(nm, "single_photon_detector", det_ports, 20.0, 10.0, det_params)
            )

        # Clements 拓扑：modes 层 DC
        layers = modes
        layer_dcs: list[list[tuple[str, int, int]]] = []
        for layer in range(layers):
            if layer % 2 == 0:
                # 偶数层：连接 (0,1), (2,3), ...
                pairs = [(i, i + 1) for i in range(0, modes - 1, 2)]
            else:
                # 奇数层：连接 (1,2), (3,4), ...
                pairs = [(i, i + 1) for i in range(1, modes - 1, 2)]
            dcs_in_layer = []
            for m1, m2 in pairs:
                dc_name = self._next_device_name("dc")
                circuit["devices"].append(
                    self._make_device(dc_name, "directional_coupler",
                                      dc_ports, 30.0, 10.0, dc_params)
                )
                dcs_in_layer.append((dc_name, m1, m2))
            layer_dcs.append(dcs_in_layer)

        # 连接：源 → 各层 DC 级联 → 探测器
        # 跟踪每个 mode 的当前输出 (device, port)
        mode_outputs: list[tuple[str, str]] = [(srcs[i], "out") for i in range(modes)]

        for layer in range(layers):
            new_outputs = list(mode_outputs)
            for dc_name, m1, m2 in layer_dcs[layer]:
                d1, p1 = mode_outputs[m1]
                d2, p2 = mode_outputs[m2]
                circuit["connections"].append(
                    self._make_connection(d1, p1, dc_name, "in1")
                )
                circuit["connections"].append(
                    self._make_connection(d2, p2, dc_name, "in2")
                )
                new_outputs[m1] = (dc_name, "out1")
                new_outputs[m2] = (dc_name, "out2")
            mode_outputs = new_outputs

        # 最后一层 → 探测器
        for i in range(modes):
            d, p = mode_outputs[i]
            circuit["connections"].append(self._make_connection(d, p, dets[i], "in"))


# =============================================================================
# 5. 格栅滤波器生成器
# =============================================================================


class LatticeFilterGenerator(CircuitGenerator):
    """格栅滤波器生成器（DC-PS 级联）。

    器件组成：DC + phase_shifter 交替级联形成 FIR/IIR 格栅滤波器。
    DC 端口：in1(W), in2(W), out1(E), out2(E)。
    phase_shifter 端口：in(W), out(E)。
    规模映射：XS=2, S=4, M=8, L=16, XL=32 级。
    连接：DC-PS-DC-PS 交替级联。
    来源: Madsen & Zhao, Optical Filter Design, 1999。
    """

    # 规模 → 级数映射
    STAGE_MAP = {"XS": 2, "S": 4, "M": 8, "L": 16, "XL": 32}

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="lattice_filter", scale=scale, platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成格栅滤波器电路。"""
        n = self.STAGE_MAP[self.scale.name]
        name = f"lattice_filter_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"格栅滤波器 {n} 级 ({self.scale.name}/{self.platform.name})"
        )

        dc_params = {"coupling_ratio": 0.5, "source": "Madsen & Zhao, 1999"}
        ps_params = {"phase_rad": math.pi, "source": "Madsen & Zhao, 1999"}

        dc_ports = [["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
                    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"]]
        ps_ports = [["in", 0.0, 5.0, "W"], ["out", 30.0, 5.0, "E"]]

        # 生成 N 级 DC-PS
        dcs, pss = [], []
        for _ in range(n):
            dc = self._next_device_name("dc")
            ps = self._next_device_name("ps")
            dcs.append(dc)
            pss.append(ps)
            circuit["devices"].append(
                self._make_device(dc, "directional_coupler", dc_ports, 30.0, 10.0, dc_params)
            )
            circuit["devices"].append(
                self._make_device(ps, "phase_shifter", ps_ports, 30.0, 10.0, ps_params)
            )

        # 连接：DC-PS-DC-PS 交替级联
        # dc[i].out1 → ps[i].in（主路径）
        # ps[i].out → dc[i+1].in1（到下一级主路径）
        # dc[i].out2 → dc[i+1].in2（平行耦合路径）
        for i in range(n):
            circuit["connections"].append(
                self._make_connection(dcs[i], "out1", pss[i], "in")
            )
            if i < n - 1:
                circuit["connections"].append(
                    self._make_connection(pss[i], "out", dcs[i + 1], "in1")
                )
                circuit["connections"].append(
                    self._make_connection(dcs[i], "out2", dcs[i + 1], "in2")
                )

        return circuit
