#!/usr/bin/env python3
"""PoLaRIS 电路拓扑生成器 Group A（5 种矩阵/阵列拓扑）。

为 1000 电路测试集提供 5 种生成器：
- ClementsMatrixGenerator: Clements 酉矩阵分解（交错网格 MZI 阵列）
- ReckMatrixGenerator: Reck 三角分解（上三角 MZI 阵列）
- SpankeMatrixGenerator: Spanke 网络（级联 DC 树，Banyan 拓扑）
- MMIArrayGenerator: MMI 阵列（1x2 MMI 级联分光树）
- DCCouplerArrayGenerator: 定向耦合器阵列（DC 级联滤波器组）

参考文献（规则 18 学术诚信，所有参数标注来源）：
- Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460
- Reck et al., PRL 1994, https://doi.org/10.1103/PhysRevLett.73.58
- Spanke & Murphy, JLT 1988
- Soldano & Pennings, JLT 1995
- SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
"""

from __future__ import annotations

import math

from scripts.generate_1000_circuits import (
    CircuitGenerator,
    PlatformConfig,
    ScaleConfig,
)

# =============================================================================
# 通用端口与参数定义（来源: SiEPIC EBeam PDK / 公开文献）
# =============================================================================

# DC（定向耦合器）端口: in1(W), in2(W), out1(E), out2(E)
DC_PORTS = [
    ["in1", 0.0, 7.0, "W"], ["in2", 0.0, 3.0, "W"],
    ["out1", 30.0, 7.0, "E"], ["out2", 30.0, 3.0, "E"],
]
# phase_shifter 端口: in(W), out(E)
PS_PORTS = [["in", 0.0, 5.0, "W"], ["out", 20.0, 5.0, "E"]]
# waveguide 端口: in(W), out(E)
WG_PORTS = [["in", 0.0, 0.0, "W"], ["out", 50.0, 0.0, "E"]]
# 1x2 MMI 端口: in(W), out1(E), out2(E)
MMI12_PORTS = [
    ["in", 0.0, 5.0, "W"],
    ["out1", 30.0, 8.0, "E"], ["out2", 30.0, 2.0, "E"],
]

# 器件参数（均标注 source 字段）
DC_PARAMS = {
    "gap_um": 0.2, "coupling_length_um": 20.0,
    "source": "SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
}
PS_PARAMS = {
    "phase_rad": 0.0, "loss_db": 0.1,
    "source": "SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
}
MMI_PARAMS = {
    "type": "1x2", "gap_um": 0.5,
    "source": "Soldano & Pennings, JLT 1995",
}
WG_PARAMS_BASE = {
    "length_um": 50.0,
    "source": "SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
}


# =============================================================================
# 辅助函数
# =============================================================================

def _matrix_dims(scale_name: str) -> tuple[int, int]:
    """根据规模名返回 (矩阵维度 N, 阵列数)。

    矩阵拓扑规模映射（调整: 器件数符合规模定义 4-500 器件）：
    - XS: 2x2 单阵列 (MZI=1, 器件~5)
    - S:  4x4 单阵列 (MZI=6, 器件~20)
    - M:  6x6 单阵列 (MZI=15, 器件~50)
    - L:  8x8 单阵列 (MZI=28, 器件~90)
    - XL: 12x12 单阵列 (MZI=66, 器件~200)

    注: 原 M=16x16 产生 371 器件 581 连接, 布线 364s 不可接受。
    Clements/Reck/Spanke 矩阵器件数 = N(N-1)/2 * 3 + 2N (MZI=2DC+1PS)。
    """
    mapping = {
        "XS": (2, 1), "S": (4, 1), "M": (6, 1),
        "L": (8, 1), "XL": (12, 1),
    }
    return mapping.get(scale_name, (2, 1))


def _array_count(scale_name: str) -> int:
    """根据规模名返回阵列器件数（用于 MMI/DC 阵列）。"""
    mapping = {"XS": 2, "S": 4, "M": 8, "L": 16, "XL": 32}
    return mapping.get(scale_name, 2)


def _wg_params(platform: PlatformConfig, role: str) -> dict:
    """构造波导参数 dict（标注来源与角色）。"""
    return {
        **WG_PARAMS_BASE,
        "width_um": platform.waveguide_width_um,
        "role": role,
    }


# =============================================================================
# 1. Clements 矩阵生成器
# =============================================================================


class ClementsMatrixGenerator(CircuitGenerator):
    """Clements 酉矩阵分解生成器。

    器件组成：N×N 酉矩阵分解，使用 MZI 单元（每个 MZI = 2 DC + 1 phase_shifter）
    + N 个输入波导 + N 个输出波导。

    拓扑：交错网格（column-based），共 N-1 列，每列 floor(N/2) 个 MZI。
    偶数列 MZI 连接 (0,1),(2,3),...；奇数列连接 (1,2),(3,4),...。
    总 MZI 数 = N(N-1)/2。

    来源: Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="clements_matrix", scale=scale,
                         platform=platform, seed=seed)

    def _make_mzi_unit(self) -> dict:
        """创建一个 MZI 单元（2 DC + 1 phase_shifter + 内部连接）。

        MZI 内部结构：dc1 -> ps -> dc2（干涉臂上调相）。
        外部端口：in1=dc1.in1, in2=dc1.in2, out1=dc2.out1, out2=dc2.out2。
        """
        dc1 = self._next_device_name("dc")
        dc2 = self._next_device_name("dc")
        ps = self._next_device_name("ps")
        devices = [
            self._make_device(dc1, "directional_coupler", DC_PORTS, 30.0, 10.0, DC_PARAMS),
            self._make_device(dc2, "directional_coupler", DC_PORTS, 30.0, 10.0, DC_PARAMS),
            self._make_device(ps, "phase_shifter", PS_PORTS, 20.0, 2.0, PS_PARAMS),
        ]
        # MZI 内部连接：dc1.out1 -> ps.in, ps.out -> dc2.in1, dc1.out2 -> dc2.in2
        connections = [
            self._make_connection(dc1, "out1", ps, "in"),
            self._make_connection(ps, "out", dc2, "in1"),
            self._make_connection(dc1, "out2", dc2, "in2"),
        ]
        return {
            "devices": devices, "connections": connections,
            "in1": (dc1, "in1"), "in2": (dc1, "in2"),
            "out1": (dc2, "out1"), "out2": (dc2, "out2"),
        }

    def _build_single_matrix(self, n: int, devices: list,
                             connections: list) -> None:
        """构建单个 N×N Clements 矩阵（追加到 devices/connections）。"""
        # 创建 N 个输入波导
        wg_in_names = []
        for i in range(n):
            wg = self._next_device_name("wg")
            wg_in_names.append(wg)
            devices.append(self._make_device(
                wg, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"input_{i}")))

        # lines[i] = (dev, port) 表示第 i 条线的当前右端
        lines = [(wg_in_names[i], "out") for i in range(n)]

        # Clements 交错网格：N-1 列
        for col in range(n - 1):
            # 偶数列：MZI 连接 (0,1), (2,3), ...
            # 奇数列：MZI 连接 (1,2), (3,4), ...
            start = 0 if col % 2 == 0 else 1
            for i in range(start, n - 1, 2):
                mzi = self._make_mzi_unit()
                devices.extend(mzi["devices"])
                connections.extend(mzi["connections"])
                # 连接 lines[i] -> mzi.in1, lines[i+1] -> mzi.in2
                connections.append(self._make_connection(
                    lines[i][0], lines[i][1], mzi["in1"][0], mzi["in1"][1]))
                connections.append(self._make_connection(
                    lines[i + 1][0], lines[i + 1][1],
                    mzi["in2"][0], mzi["in2"][1]))
                # 更新 lines
                lines[i] = mzi["out1"]
                lines[i + 1] = mzi["out2"]

        # 创建 N 个输出波导并连接
        for i in range(n):
            wg = self._next_device_name("wg")
            devices.append(self._make_device(
                wg, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"output_{i}")))
            connections.append(self._make_connection(
                lines[i][0], lines[i][1], wg, "in"))

    def generate(self) -> dict:
        """生成 Clements 矩阵电路。"""
        n, num_arrays = _matrix_dims(self.scale.name)
        name = f"clements_matrix_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"Clements {n}x{n} 酉矩阵分解 ({self.scale.name}/{self.platform.name})")
        circuit["metadata"]["matrix_size"] = n
        circuit["metadata"]["num_arrays"] = num_arrays
        circuit["metadata"]["source"] = (
            "Clements et al., Optica 2016, https://doi.org/10.1364/OPTICA.3.001460")

        devices: list = []
        connections: list = []
        for _ in range(num_arrays):
            self._build_single_matrix(n, devices, connections)

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit


# =============================================================================
# 2. Reck 矩阵生成器
# =============================================================================


class ReckMatrixGenerator(CircuitGenerator):
    """Reck 三角酉矩阵分解生成器。

    器件组成：三角分解酉矩阵，使用 MZI 单元 + 输入/输出波导。

    拓扑：上三角排列，MZI(i,j) for i < j，共 N(N-1)/2 个 MZI。
    处理顺序：按 j 从小到大，每个 j 内按 i 从大到小（从右下到左上）。

    来源: Reck et al., PRL 1994, https://doi.org/10.1103/PhysRevLett.73.58
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="reck_matrix", scale=scale,
                         platform=platform, seed=seed)

    def _make_mzi_unit(self) -> dict:
        """创建一个 MZI 单元（2 DC + 1 phase_shifter + 内部连接）。"""
        dc1 = self._next_device_name("dc")
        dc2 = self._next_device_name("dc")
        ps = self._next_device_name("ps")
        devices = [
            self._make_device(dc1, "directional_coupler", DC_PORTS, 30.0, 10.0, DC_PARAMS),
            self._make_device(dc2, "directional_coupler", DC_PORTS, 30.0, 10.0, DC_PARAMS),
            self._make_device(ps, "phase_shifter", PS_PORTS, 20.0, 2.0, PS_PARAMS),
        ]
        connections = [
            self._make_connection(dc1, "out1", ps, "in"),
            self._make_connection(ps, "out", dc2, "in1"),
            self._make_connection(dc1, "out2", dc2, "in2"),
        ]
        return {
            "devices": devices, "connections": connections,
            "in1": (dc1, "in1"), "in2": (dc1, "in2"),
            "out1": (dc2, "out1"), "out2": (dc2, "out2"),
        }

    def generate(self) -> dict:
        """生成 Reck 三角矩阵电路。"""
        n, _ = _matrix_dims(self.scale.name)
        name = f"reck_matrix_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"Reck {n}x{n} 三角矩阵分解 ({self.scale.name}/{self.platform.name})")
        circuit["metadata"]["matrix_size"] = n
        circuit["metadata"]["source"] = (
            "Reck et al., PRL 1994, https://doi.org/10.1103/PhysRevLett.73.58")

        devices: list = []
        connections: list = []

        # 创建 N 个输入波导
        wg_in_names = []
        for i in range(n):
            wg = self._next_device_name("wg")
            wg_in_names.append(wg)
            devices.append(self._make_device(
                wg, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"input_{i}")))

        lines = [(wg_in_names[i], "out") for i in range(n)]

        # Reck 三角：MZI(i,j) for i < j
        # 处理顺序：j 从 1 到 N-1，每个 j 内 i 从 j-1 到 0
        for j in range(1, n):
            for i in range(j - 1, -1, -1):
                mzi = self._make_mzi_unit()
                devices.extend(mzi["devices"])
                connections.extend(mzi["connections"])
                connections.append(self._make_connection(
                    lines[i][0], lines[i][1], mzi["in1"][0], mzi["in1"][1]))
                connections.append(self._make_connection(
                    lines[j][0], lines[j][1], mzi["in2"][0], mzi["in2"][1]))
                lines[i] = mzi["out1"]
                lines[j] = mzi["out2"]

        # 创建 N 个输出波导
        for i in range(n):
            wg = self._next_device_name("wg")
            devices.append(self._make_device(
                wg, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"output_{i}")))
            connections.append(self._make_connection(
                lines[i][0], lines[i][1], wg, "in"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit


# =============================================================================
# 3. Spanke 网络生成器
# =============================================================================


class SpankeMatrixGenerator(CircuitGenerator):
    """Spanke 网络分解生成器。

    器件组成：Spanke 网络分解，使用 DC + phase_shifter + 波导。

    拓扑：级联 DC 树（Banyan 拓扑），log2(N) 级，每级 N/2 个 DC。
    每级 DC 按 step=2^level 的间距连接线对，每个 DC 后接 phase_shifter 调相。

    来源: Spanke & Murphy, JLT 1988
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="spanke_matrix", scale=scale,
                         platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成 Spanke 网络电路。"""
        n, _ = _matrix_dims(self.scale.name)
        name = f"spanke_matrix_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"Spanke {n}x{n} 网络 ({self.scale.name}/{self.platform.name})")
        circuit["metadata"]["matrix_size"] = n
        circuit["metadata"]["source"] = "Spanke & Murphy, JLT 1988"

        devices: list = []
        connections: list = []

        # 创建 N 个输入波导
        wg_in_names = []
        for i in range(n):
            wg = self._next_device_name("wg")
            wg_in_names.append(wg)
            devices.append(self._make_device(
                wg, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"input_{i}")))

        lines = [(wg_in_names[i], "out") for i in range(n)]

        # Spanke Banyan 网络：log2(N) 级 DC 树
        levels = int(math.log2(n)) if n > 1 else 0
        for level in range(levels):
            step = 2 ** level
            for i in range(0, n, 2 * step):
                for j in range(step):
                    a = i + j
                    b = i + j + step
                    if b >= n:
                        continue
                    dc = self._next_device_name("dc")
                    ps = self._next_device_name("ps")
                    devices.append(self._make_device(
                        dc, "directional_coupler", DC_PORTS, 30.0, 10.0, DC_PARAMS))
                    devices.append(self._make_device(
                        ps, "phase_shifter", PS_PORTS, 20.0, 2.0, PS_PARAMS))
                    # 连接 lines[a] -> dc.in1, lines[b] -> dc.in2
                    connections.append(self._make_connection(
                        lines[a][0], lines[a][1], dc, "in1"))
                    connections.append(self._make_connection(
                        lines[b][0], lines[b][1], dc, "in2"))
                    # dc.out1 -> ps.in（主路调相）
                    connections.append(self._make_connection(dc, "out1", ps, "in"))
                    # 更新 lines
                    lines[a] = (ps, "out")
                    lines[b] = (dc, "out2")

        # 创建输出波导
        for i in range(n):
            wg = self._next_device_name("wg")
            devices.append(self._make_device(
                wg, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"output_{i}")))
            connections.append(self._make_connection(
                lines[i][0], lines[i][1], wg, "in"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit


# =============================================================================
# 4. MMI 阵列生成器
# =============================================================================


class MMIArrayGenerator(CircuitGenerator):
    """MMI 阵列生成器。

    器件组成：1x2 MMI（多模干涉耦合器）阵列 + 波导。

    拓扑：级联 MMI 链，每个 MMI 从主路分出一支（out2），
    主路继续（out1），形成 1x(N+1) 分光器。

    来源: Soldano & Pennings, JLT 1995
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="mmi_array", scale=scale,
                         platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成 MMI 阵列电路。"""
        n_mmi = _array_count(self.scale.name)
        name = f"mmi_array_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"MMI 阵列 {n_mmi} 单元 ({self.scale.name}/{self.platform.name})")
        circuit["metadata"]["n_mmi"] = n_mmi
        circuit["metadata"]["source"] = "Soldano & Pennings, JLT 1995"

        devices: list = []
        connections: list = []

        # 输入波导
        wg_in = self._next_device_name("wg")
        devices.append(self._make_device(
            wg_in, "strip_waveguide", WG_PORTS, 50.0, 0.5,
            _wg_params(self.platform, "input")))

        # 级联 1x2 MMI：每个 MMI 从主路分出一支
        prev_dev = wg_in
        prev_port = "out"
        for i in range(n_mmi):
            mmi = self._next_device_name("mmi")
            devices.append(self._make_device(
                mmi, "mmi_coupler", MMI12_PORTS, 30.0, 10.0,
                {**MMI_PARAMS, "index": i}))
            # 连接 prev -> mmi.in
            connections.append(self._make_connection(prev_dev, prev_port, mmi, "in"))
            # out2 分光路 -> 输出波导
            wg_tap = self._next_device_name("wg")
            devices.append(self._make_device(
                wg_tap, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"tap_{i}")))
            connections.append(self._make_connection(mmi, "out2", wg_tap, "in"))
            # 主路继续：mmi.out1
            prev_dev = mmi
            prev_port = "out1"

        # 最后主路 -> 输出波导
        wg_final = self._next_device_name("wg")
        devices.append(self._make_device(
            wg_final, "strip_waveguide", WG_PORTS, 50.0, 0.5,
            _wg_params(self.platform, "through")))
        connections.append(self._make_connection(prev_dev, prev_port, wg_final, "in"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit


# =============================================================================
# 5. DC 耦合器阵列生成器
# =============================================================================


class DCCouplerArrayGenerator(CircuitGenerator):
    """定向耦合器阵列生成器。

    器件组成：定向耦合器（DC）阵列 + 波导。

    拓扑：级联 DC 链，每个 DC 从主路分出一支（out2），
    主路继续（out1），形成滤波器组（1x(N+1) 分光）。

    来源: SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    """

    def __init__(self, scale: ScaleConfig, platform: PlatformConfig, seed: int) -> None:
        super().__init__(topology="dc_array", scale=scale,
                         platform=platform, seed=seed)

    def generate(self) -> dict:
        """生成 DC 阵列电路。"""
        n_dc = _array_count(self.scale.name)
        name = f"dc_array_{self.scale.name}_{self.platform.name}_{self.seed:03d}"
        circuit = self._base_circuit_dict(
            name, f"DC 阵列 {n_dc} 单元 ({self.scale.name}/{self.platform.name})")
        circuit["metadata"]["n_dc"] = n_dc
        circuit["metadata"]["source"] = (
            "SiEPIC EBeam PDK, https://github.com/SiEPIC/SiEPIC_EBeam_PDK")

        devices: list = []
        connections: list = []

        # 输入波导
        wg_in = self._next_device_name("wg")
        devices.append(self._make_device(
            wg_in, "strip_waveguide", WG_PORTS, 50.0, 0.5,
            _wg_params(self.platform, "input")))

        # 级联 DC：每个 DC 从主路分出一支
        prev_dev = wg_in
        prev_port = "out"
        for i in range(n_dc):
            dc = self._next_device_name("dc")
            devices.append(self._make_device(
                dc, "directional_coupler", DC_PORTS, 30.0, 10.0,
                {**DC_PARAMS, "index": i}))
            # 连接 prev -> dc.in1
            connections.append(self._make_connection(prev_dev, prev_port, dc, "in1"))
            # out2 分光路 -> 输出波导
            wg_tap = self._next_device_name("wg")
            devices.append(self._make_device(
                wg_tap, "strip_waveguide", WG_PORTS, 50.0, 0.5,
                _wg_params(self.platform, f"tap_{i}")))
            connections.append(self._make_connection(dc, "out2", wg_tap, "in"))
            # 主路继续：dc.out1
            prev_dev = dc
            prev_port = "out1"

        # 最后主路 -> 输出波导
        wg_final = self._next_device_name("wg")
        devices.append(self._make_device(
            wg_final, "strip_waveguide", WG_PORTS, 50.0, 0.5,
            _wg_params(self.platform, "through")))
        connections.append(self._make_connection(prev_dev, prev_port, wg_final, "in"))

        circuit["devices"] = devices
        circuit["connections"] = connections
        return circuit
