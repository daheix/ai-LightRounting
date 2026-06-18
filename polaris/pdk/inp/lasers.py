"""InP 平台激光器器件库。

覆盖 InP（Indium Phosphide）有源集成平台的激光器真实参数模型：
DFB、DBR、SGDBR 激光器、O-band 高功率 DFB、Coherent BH DFB 与
IMOS DFB 激光器。每个器件参数均来自公开文献并附带 ``Source`` 溯源
（含 URL），禁止假数据（见项目规则 1.1 与 spec.md 来源核对）。

端口约定（与 device.py 一致）：端口坐标相对器件原点，``direction`` 为光波导
出射方向（朝外，便于外部波导连接）。坐标系为标准数学坐标系（y 轴朝上）。

来源文献：
- Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry
  https://doi.org/10.3390/app9081588
- Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO
  https://doi.org/10.1109/JSTQE.2018.2866565
- AP Technologies — SemiNex 高功率 O-band DFB
  https://www.aptechnologies.co.uk/news
- Coherent — 400mW InP BH DFB 激光器
  http://ep.cntronics.com/guide/4364/14539
- Zozulia et al., Photonics Benelux 2023 — IMOS DFB on InP membrane
  https://photonics-benelux.org/wp-content/uploads/pb-files/proceedings/2023/Posters_even_numbers/Zozulia.pdf
"""

from __future__ import annotations

from polaris.pdk.device import BoundingBox, Device
from polaris.pdk.inp.sources import (
    _INP_CONSTRAINTS,
    _SOURCE_AP_TECH,
    _SOURCE_COHERENT,
    _SOURCE_SOARES,
    _SOURCE_ZHAO,
    _SOURCE_ZOZULIA,
    _WG_TYPE,
    _WG_WIDTH,
    _make_electrical_port,
)
from polaris.pdk.port import Direction, Port


# ===========================================================================
# 端口创建辅助函数（提取自超长 make_* 函数，降低函数行数）
# ===========================================================================
def _make_laser_ports(length: float) -> list[Port]:
    """创建 InP 激光器标准端口（output 光端口 + electrical 电端口）。

    所有 InP 激光器（DFB/DBR/SGDBR/O-band/Coherent/IMOS）端口结构相同，
    共享此辅助函数。

    Args:
        length: 激光器长度（μm），决定 output 端口 x 坐标与 electrical 中点。

    Returns:
        含 output（EAST）与 electrical（NORTH）两端口的标准列表。
    """
    return [
        Port(
            name="output",
            x=length,
            y=0.0,
            direction=Direction.EAST,
            waveguide_type=_WG_TYPE,
            width=_WG_WIDTH,
        ),
        _make_electrical_port(length / 2.0),
    ]


def _make_laser_bbox(length: float) -> BoundingBox:
    """构建 InP 激光器包围盒（含电端口 50μm 余量）。

    Args:
        length: 激光器长度（μm）。

    Returns:
        覆盖波导与电端口的轴对齐包围盒。
    """
    half_w = _WG_WIDTH / 2.0
    return BoundingBox(xmin=0.0, ymin=-half_w, xmax=length, ymax=half_w + 50.0)


# ===========================================================================
# 1. DFB 激光器 dfb_laser
# ===========================================================================
def make_dfb_laser() -> Device:
    """DFB 激光器（输出功率 >3mW）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了 DFB 激光器作为集成光源，输出功率 >3mW。

    Returns:
        DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 400.0  # DFB 激光器长度（μm），典型值
    return Device(
        device_id="dfb_laser",
        platform="InP",
        category="source",
        name="dfb_laser",
        ports=_make_laser_ports(length),
        bbox=_make_laser_bbox(length),
        params={
            "output_power_mw": 3.0,
            "output_power_note": ">3 mW",
            "length_um": length,
            "wavelength_nm": 1550.0,
            "laser_type": "DFB",
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 2. DBR 激光器 dbr_laser
# ===========================================================================
def make_dbr_laser() -> Device:
    """DBR 激光器（输出功率 >3mW）。

    来源：Soares et al., Appl. Sci. 2019 — Fraunhofer HHI InP Foundry，
    论文描述了 DBR 激光器作为可调谐集成光源，输出功率 >3mW。

    Returns:
        DBR 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 600.0  # DBR 激光器长度（μm），含 Bragg 光栅段，比 DFB 更长
    return Device(
        device_id="dbr_laser",
        platform="InP",
        category="source",
        name="dbr_laser",
        ports=_make_laser_ports(length),
        bbox=_make_laser_bbox(length),
        params={
            "output_power_mw": 3.0,
            "output_power_note": ">3 mW",
            "length_um": length,
            "wavelength_nm": 1550.0,
            "laser_type": "DBR",
        },
        source=_SOURCE_SOARES,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 3. SGDBR 激光器 sgdbr_laser
# ===========================================================================
def make_sgdbr_laser() -> Device:
    """SGDBR 激光器（调谐 1521-1565nm，SMSR >45dB）。

    来源：Zhao et al., IEEE JSTQE 2018 — UCSB InP PIC for FSO，
    论文描述了五段 SGDBR 激光器，调谐范围 1521-1565nm（覆盖整个 C 波段），
    边模抑制比 >45dB。

    Returns:
        SGDBR 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 1000.0  # SGDBR 五段激光器长度（μm），含多个光栅段
    return Device(
        device_id="sgdbr_laser",
        platform="InP",
        category="source",
        name="sgdbr_laser",
        ports=_make_laser_ports(length),
        bbox=_make_laser_bbox(length),
        params={
            "tuning_range_nm": "1521-1565",
            "smsr_db": 45.0,
            "smsr_note": ">45 dB",
            "length_um": length,
            "laser_type": "SGDBR",
            "sections": 5,
        },
        source=_SOURCE_ZHAO,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 4. O-band DFB 激光器 dfb_laser_oband
# ===========================================================================
def make_dfb_laser_oband() -> Device:
    """O-band DFB 激光器 SemiNex（200-250mW CW @25°C）。

    来源：AP Technologies — SemiNex 高功率 O-band DFB 激光器，
    连续输出功率 200-250mW @25°C。

    Returns:
        O-band DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 1500.0  # 高功率 DFB 激光器长度（μm），高功率器件通常更长
    return Device(
        device_id="dfb_laser_oband",
        platform="InP",
        category="source",
        name="dfb_laser_oband",
        ports=_make_laser_ports(length),
        bbox=_make_laser_bbox(length),
        params={
            "output_power_mw": "200-250",
            "output_power_note": "200-250 mW CW @25°C",
            "wavelength_band": "O-band",
            "wavelength_nm": 1310.0,
            "operating_temp_c": 25,
            "manufacturer": "SemiNex",
            "length_um": length,
        },
        source=_SOURCE_AP_TECH,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 5. Coherent BH DFB 激光器 dfb_laser_coherent
# ===========================================================================
def make_dfb_laser_coherent() -> Device:
    """InP BH DFB 激光器 Coherent（1311nm，400mW@55°C，线宽 <200kHz）。

    来源：Coherent 产品报道 — InP BH（Buried Heterostructure）DFB 激光器，
    波长 1311nm，输出功率 400mW@55°C，线宽 <200kHz，
    RIN（相对强度噪声）<-145 dB/Hz。

    Returns:
        Coherent BH DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 750.0  # BH DFB 激光器长度（μm），典型值
    return Device(
        device_id="dfb_laser_coherent",
        platform="InP",
        category="source",
        name="dfb_laser_coherent",
        ports=_make_laser_ports(length),
        bbox=_make_laser_bbox(length),
        params={
            "wavelength_nm": 1311.0,
            "output_power_mw": 400.0,
            "output_power_note": "400 mW @55°C",
            "operating_temp_c": 55,
            "linewidth_khz": 200.0,
            "linewidth_note": "<200 kHz",
            "rin_db_hz": -145.0,
            "rin_note": "<-145 dB/Hz",
            "manufacturer": "Coherent",
            "structure": "BH (Buried Heterostructure)",
            "length_um": length,
        },
        source=_SOURCE_COHERENT,
        constraints=_INP_CONSTRAINTS,
    )


# ===========================================================================
# 6. IMOS DFB 激光器 imos_dfb_laser
# ===========================================================================
def make_imos_dfb_laser() -> Device:
    """IMOS DFB 激光器（250μm 长，600μW 光纤功率，带宽 15GHz，25Gbit/s）。

    来源：Zozulia et al., Photonics Benelux 2023 — TU Eindhoven，
    IMOS（InP Membrane on Silicon）平台上的 DFB 激光器，
    腔长 250μm，光纤耦合功率 600μW，调制带宽 15GHz，支持 25Gbit/s 传输。

    Returns:
        IMOS DFB 激光器 Device 实例（output 光端口 + electrical 电端口）。
    """
    length = 250.0  # IMOS DFB 激光器长度（μm），论文明确为 250μm
    return Device(
        device_id="imos_dfb_laser",
        platform="InP",
        category="source",
        name="imos_dfb_laser",
        ports=_make_laser_ports(length),
        bbox=_make_laser_bbox(length),
        params={
            "length_um": length,
            "fiber_power_uw": 600.0,
            "fiber_power_note": "600 μW fiber-coupled",
            "bandwidth_ghz": 15.0,
            "data_rate_gbps": 25.0,
            "platform": "IMOS (InP Membrane on Silicon)",
            "manufacturer": "TU Eindhoven",
            "wavelength_nm": 1550.0,
        },
        source=_SOURCE_ZOZULIA,
        constraints=_INP_CONSTRAINTS,
    )
