"""器件到 S 参数模型映射（51 器件全覆盖）。

将 PoLaRIS PDK 中的每个器件映射到对应的 S 参数模型函数，
使每个器件都支持频率相关 S 参数仿真（而非仅标量损耗值）。

映射策略：
- 波导类 → waveguide_s（传播相位 + 损耗）
- 分束器类 → y_branch_s / mmi_1x2_s / mmi_2x2_s
- 耦合器类 → directional_coupler_s
- 环谐振器 → ring_resonator_s
- 光栅耦合器 → grating_coupler_s（高斯型波长响应）
- 交叉 → crossing_s
- 移相器 → phase_shifter_s
- 探测器/激光器 → 简化模型

来源:
- Simphony SiEPIC 模型库: https://simphonyphotonics.readthedocs.io/
- SiPANN 模型库: https://sipann.readthedocs.io/
- gdsfactory 器件库: https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np

from polaris.pdk.catalog import DeviceCatalog, build_default_catalog
from polaris.pdk.device import Device
from polaris.sim.models import (
    RingParams,
    crossing_s,
    directional_coupler_s,
    grating_coupler_s,
    mmi_1x2_s,
    mmi_2x2_s,
    phase_shifter_s,
    ring_resonator_s,
    terminator_s,
    waveguide_s,
    y_branch_s,
)
from polaris.sim.simulator import CircuitSimulator
from polaris.sim.types import SDict


def _parse_float(val, default=0.0):
    """从参数值中提取浮点数（处理字符串如 '<0.4 dB/cm'）。"""
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        # 提取字符串中的数字（如 "<0.4 dB/cm" → 0.4）
        import re

        m = re.search(r"[\d.]+", val)
        if m:
            return float(m.group())
    return default


# =============================================================================
# 器件 → S 参数模型分发表（dispatch table 模式）
#
# 将每种器件类型的「匹配逻辑」与「模型构建逻辑」提取为独立的私有函数，
# 通过 _SMODEL_DISPATCH 分发表按优先级顺序匹配，替代长 if-elif 链以降低
# 圈复杂度（规则 4.3 Extract Method + 表驱动）。
# =============================================================================

# 分发表类型别名
_SModelMatcher = Callable[[str], bool]
_SModelHandler = Callable[[dict, np.ndarray], SDict]


# --- 波导类 ---
def _matches_waveguide(name: str) -> bool:
    """匹配波导类器件（含 SiN/SiO2 各类波导）。"""
    return "waveguide" in name or name in (
        "strip_waveguide",
        "rib_waveguide",
        "waveguide_lpcvd",
        "waveguide_damascene",
        "waveguide_ull",
        "waveguide_epfl",
        "waveguide_trench",
        "triplex_double_stripe",
        "waveguide_high_q",
        "waveguide_low_loss",
        "waveguide_ull_record",
    )


def _waveguide_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """波导类 S 参数模型（传播相位 + 损耗）。"""
    neff = _parse_float(params.get("neff", 2.4), 2.4)
    loss_db_cm = _parse_float(params.get("loss_db_cm", 0.0), 0.0)
    # SiN 用 dB/m 的转换
    if "loss_db_m" in params:
        loss_db_cm = _parse_float(params["loss_db_m"], 0.0) / 100.0
    length = _parse_float(params.get("length", 100.0), 100.0)
    return waveguide_s(wl=wl_arr, length=length, neff=neff, loss_db_cm=loss_db_cm)


# --- 弯曲波导 ---
def _matches_bend(name: str) -> bool:
    """匹配弯曲波导。"""
    return "bend" in name


def _bend_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """弯曲波导 S 参数模型（按 90 度弧长等效为波导）。"""
    neff = float(params.get("neff", 2.4))
    loss_db_cm = float(params.get("loss_db_cm", 2.0))
    radius = float(params.get("radius_um", 5.0))
    length = 2.0 * np.pi * radius / 4.0  # 90度弯曲弧长
    return waveguide_s(wl=wl_arr, length=length, neff=neff, loss_db_cm=loss_db_cm)


# --- Y 分支 ---
def _matches_y_branch(name: str) -> bool:
    """匹配 Y 分支。"""
    return "y_branch" in name


def _y_branch_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """Y 分支 S 参数模型。"""
    il = float(params.get("insertion_loss_db", 0.3))
    return y_branch_s(wl=wl_arr, insertion_loss_db=il)


# --- 定向耦合器 ---
def _matches_directional_coupler(name: str) -> bool:
    """匹配定向/双向耦合器。"""
    return "directional_coupler" in name or "bidirectional_coupler" in name


def _directional_coupler_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """定向耦合器 S 参数模型。"""
    coupling = float(params.get("coupling", 0.5))
    gap = float(params.get("gap_um", 0.2))
    length = float(params.get("coupling_length_um", 10.0))
    return directional_coupler_s(wl=wl_arr, coupling=coupling, length=length, gap=gap)


# --- 环谐振器 ---
def _matches_ring_resonator(name: str) -> bool:
    """匹配环谐振器。"""
    return "ring" in name and "resonator" in name


def _ring_resonator_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """环谐振器 S 参数模型。"""
    radius = float(params.get("radius_um", 10.0))
    ring_params = RingParams(
        neff=float(params.get("neff", 2.4)),
        coupling=float(params.get("coupling", 0.01)),
        loss_db_cm=float(params.get("loss_db_cm", 2.0)),
    )
    return ring_resonator_s(wl=wl_arr, radius=radius, params=ring_params)


# --- 半环（SiEPIC half_ring） ---
def _matches_half_ring(name: str) -> bool:
    """匹配半环（SiEPIC half_ring）。"""
    return "half_ring" in name


def _half_ring_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """半环 S 参数模型（无损耗项的环谐振器近似）。"""
    radius = float(params.get("radius_um", 10.0))
    ring_params = RingParams(
        neff=float(params.get("neff", 2.4)),
        coupling=float(params.get("coupling", 0.01)),
    )
    return ring_resonator_s(wl=wl_arr, radius=radius, params=ring_params)


# --- MMI 1x2 ---
def _matches_mmi_1x2(name: str) -> bool:
    """匹配 MMI 1x2。"""
    return "mmi" in name and ("1x2" in name or "1_2" in name)


def _mmi_1x2_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """MMI 1x2 S 参数模型。"""
    il = float(params.get("insertion_loss_db", 0.4))
    return mmi_1x2_s(wl=wl_arr, insertion_loss_db=il)


# --- MMI 2x2 ---
def _matches_mmi_2x2(name: str) -> bool:
    """匹配 MMI 2x2。"""
    return "mmi" in name and ("2x2" in name or "2_2" in name)


def _mmi_2x2_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """MMI 2x2 S 参数模型。"""
    il = float(params.get("insertion_loss_db", 0.5))
    return mmi_2x2_s(wl=wl_arr, insertion_loss_db=il)


# --- MZI（由两个 Y 分支 + 波导组成，这里用简化模型） ---
def _matches_mzi(name: str) -> bool:
    """匹配 MZI。"""
    return "mzi" in name


def _mzi_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """MZI S 参数模型（简化为 MMI 2x2）。"""
    il = float(params.get("insertion_loss_db", 0.6))
    return mmi_2x2_s(wl=wl_arr, insertion_loss_db=il)


# --- 光栅耦合器 ---
def _matches_grating_coupler(name: str) -> bool:
    """匹配光栅耦合器。"""
    return "grating_coupler" in name


def _grating_coupler_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """光栅耦合器 S 参数模型（高斯型波长响应）。"""
    peak_wl = float(params.get("center_wavelength", 1.55))
    bw = float(params.get("bandwidth_3db", 0.04))
    il = float(params.get("peak_coupling_loss_db", params.get("coupling_loss_db", 1.9)))
    return grating_coupler_s(
        wl=wl_arr,
        peak_wl=peak_wl,
        bandwidth_3db=bw,
        insertion_loss_db=il,
    )


# --- 端面耦合器 ---
def _matches_edge_coupler(name: str) -> bool:
    """匹配端面耦合器。"""
    return "edge_coupler" in name


def _edge_coupler_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """端面耦合器 S 参数模型（近似平坦响应）。"""
    il = float(params.get("coupling_loss_db", 0.5))
    return grating_coupler_s(
        wl=wl_arr,
        peak_wl=1.55,
        bandwidth_3db=0.1,
        insertion_loss_db=il,
    )


# --- 交叉 ---
def _matches_crossing(name: str) -> bool:
    """匹配波导交叉。"""
    return "crossing" in name


def _crossing_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """交叉 S 参数模型。"""
    il = float(params.get("insertion_loss_db", 0.3))
    return crossing_s(wl=wl_arr, insertion_loss_db=il)


# --- 移相器 ---
def _matches_phase_shifter(name: str) -> bool:
    """匹配移相器。"""
    return "phase_shifter" in name


def _phase_shifter_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """移相器 S 参数模型。"""
    phase = float(params.get("phase_rad", 0.0))
    il = float(params.get("insertion_loss_db", 0.0))
    return phase_shifter_s(
        wl=wl_arr,
        phase_rad=phase,
        insertion_loss_db=il,
    )


# --- 调制器（MZM/MRM）→ 移相器 + 损耗 ---
def _matches_modulator(name: str) -> bool:
    """匹配调制器（MZM/MRM）。"""
    return "modulator" in name or "mzm" in name or "mrm" in name


def _modulator_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """调制器 S 参数模型（移相器 + 损耗）。"""
    il = float(params.get("insertion_loss_db", 3.0))
    return phase_shifter_s(
        wl=wl_arr,
        phase_rad=0.0,
        insertion_loss_db=il,
    )


# --- 探测器 ---
def _matches_detector(name: str) -> bool:
    """匹配探测器。"""
    return "detector" in name or "photodetector" in name or "pd" == name


def _detector_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """探测器 S 参数模型（简化为吸收模型）。"""
    # 探测器简化为吸收模型
    return terminator_s(wl=wl_arr, reflection_db=-40.0)


# --- 激光器（DFB/DBR/SGDBR）→ 简化为源模型 ---
def _matches_laser(name: str) -> bool:
    """匹配激光器（DFB/DBR/SGDBR）。"""
    return "laser" in name or "dfb" in name or "dbr" in name


def _laser_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """激光器 S 参数模型（简化为单向输出）。"""
    # 激光器简化为单向输出
    return waveguide_s(wl=wl_arr, length=0.0, neff=3.2, loss_db_cm=0.0)


# --- SOA（半导体光放大器）→ 增益模型 ---
def _matches_soa(name: str) -> bool:
    """匹配半导体光放大器（SOA）。"""
    return "soa" in name


def _soa_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """SOA S 参数模型（负损耗波导等效增益）。"""
    gain_db = float(params.get("gain_db", 15.0))
    # SOA 简化为负损耗波导
    return waveguide_s(
        wl=wl_arr,
        length=float(params.get("length", 500.0)),
        neff=3.2,
        loss_db_cm=-gain_db / float(params.get("length", 500.0)) * 1e4,
    )


# --- 材料参数器件（无 S 参数） ---
def _matches_material(name: str) -> bool:
    """匹配材料参数器件。"""
    return "material" in name or "review" in name


def _material_smodel(params: dict, wl_arr: np.ndarray) -> SDict:
    """材料参数器件 S 参数模型（返回零响应）。"""
    return {("in", "in"): np.zeros_like(wl_arr, dtype=complex)}


# 器件 → S 参数模型分发表（按匹配优先级顺序排列）
_SMODEL_DISPATCH: list[tuple[_SModelMatcher, _SModelHandler]] = [
    (_matches_waveguide, _waveguide_smodel),
    (_matches_bend, _bend_smodel),
    (_matches_y_branch, _y_branch_smodel),
    (_matches_directional_coupler, _directional_coupler_smodel),
    (_matches_ring_resonator, _ring_resonator_smodel),
    (_matches_half_ring, _half_ring_smodel),
    (_matches_mmi_1x2, _mmi_1x2_smodel),
    (_matches_mmi_2x2, _mmi_2x2_smodel),
    (_matches_mzi, _mzi_smodel),
    (_matches_grating_coupler, _grating_coupler_smodel),
    (_matches_edge_coupler, _edge_coupler_smodel),
    (_matches_crossing, _crossing_smodel),
    (_matches_phase_shifter, _phase_shifter_smodel),
    (_matches_modulator, _modulator_smodel),
    (_matches_detector, _detector_smodel),
    (_matches_laser, _laser_smodel),
    (_matches_soa, _soa_smodel),
    (_matches_material, _material_smodel),
]


def device_to_smodel(device: Device, wl: float | np.ndarray = 1.55) -> SDict:
    """将 PoLaRIS 器件映射到 S 参数模型。

    根据 device.name 和 device.params 选择对应的 S 参数模型函数，
    从 params 中提取参数（neff, loss_db_cm, coupling 等）。

    匹配逻辑通过 _SMODEL_DISPATCH 分发表按优先级顺序遍历，
    第一个匹配的处理器被调用；若无匹配则返回单位直通。

    Args:
        device: PoLaRIS 器件实例。
        wl: 波长（μm）或波长数组。

    Returns:
        S 参数字典 {(port_out, port_in): np.ndarray}。
    """
    name = device.name
    params = device.params
    wl_arr = np.asarray(wl, dtype=float)

    for matches, handler in _SMODEL_DISPATCH:
        if matches(name):
            return handler(params, wl_arr)

    # 默认：单位直通
    return waveguide_s(wl=wl_arr, length=0.0, neff=1.0, loss_db_cm=0.0)


def catalog_smodels(catalog: DeviceCatalog | None = None) -> dict[str, callable]:
    """为目录中所有器件生成 S 参数模型函数字典。

    Args:
        catalog: 器件目录（默认使用 build_default_catalog()）。

    Returns:
        {device_id: callable(wl, **kwargs) -> SDict} 字典。
    """
    if catalog is None:
        catalog = build_default_catalog()

    models: dict[str, callable] = {}
    for device in catalog:

        def make_model(dev):
            def model(wl=1.55, **kwargs):
                return device_to_smodel(dev, wl)

            return model

        models[device.device_id] = make_model(device)
    return models


def simulate_device(
    device: Device,
    wavelengths: np.ndarray | None = None,
) -> tuple[np.ndarray, SDict]:
    """仿真单个器件的 S 参数频率响应。

    Args:
        device: 器件实例。
        wavelengths: 波长数组（μm），默认 1.5-1.6μm 500点。

    Returns:
        (波长数组, S 参数字典)
    """
    if wavelengths is None:
        wavelengths = np.linspace(1.5, 1.6, 500)
    s = device_to_smodel(device, wavelengths)
    return wavelengths, s


def _netlist_to_sax_format(
    netlist_dict: dict,
) -> tuple[dict, list[tuple[str, str]], dict]:
    """将网表字典转换为 SAX 格式 (instances, connections, ports)。

    来源:
    - SAX 网表格式: https://flaport.github.io/sax/

    Args:
        netlist_dict: 网表字典 {devices, connections, ...}。

    Returns:
        (instances, connections, ports) 元组，分别对应 SAX 网表的
        实例映射、连接列表与外部端口。
    """
    instances = {}
    for inst in netlist_dict.get("devices", []):
        instances[inst["instance_id"]] = inst["device_id"]

    connections: list[tuple[str, str]] = []
    for conn in netlist_dict.get("connections", []):
        src = f"{conn['source_instance']}.{conn['source_port']}"
        dst = f"{conn['target_instance']}.{conn['target_port']}"
        connections.append((src, dst))

    # 外部端口（第一个器件的 in 和最后一个器件的 out）
    ports: dict[str, str] = {}
    if instances:
        first_inst = list(instances.keys())[0]
        last_inst = list(instances.keys())[-1]
        ports["in"] = f"{first_inst}.in"
        ports["out"] = f"{last_inst}.out"

    return instances, connections, ports


def simulate_circuit_from_netlist(
    netlist_dict: dict,
    catalog: DeviceCatalog | None = None,
    wavelengths: np.ndarray | None = None,
) -> tuple[np.ndarray, SDict]:
    """从网表执行电路级频率域仿真。

    将网表中的器件实例映射到 S 参数模型，级联计算电路传输谱。

    Args:
        netlist_dict: 网表字典 {devices, connections, ...}。
        catalog: 器件目录。
        wavelengths: 波长数组。

    Returns:
        (波长数组, 电路级 S 参数字典)
    """
    if wavelengths is None:
        wavelengths = np.linspace(1.5, 1.6, 500)

    if catalog is None:
        catalog = build_default_catalog()

    # 构建模型库
    sim = CircuitSimulator()
    for device in catalog:

        def make_model(dev):
            def model(wl=1.55, **kwargs):
                return device_to_smodel(dev, wl)

            return model

        sim.register_model(device.device_id, make_model(device))

    # 转换网表为 SAX 格式
    instances, connections, ports = _netlist_to_sax_format(netlist_dict)
    sax_netlist = {
        "instances": instances,
        "connections": connections,
        "ports": ports,
    }

    s = sim.simulate(sax_netlist, wavelengths)
    return wavelengths, s
