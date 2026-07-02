"""LVS 进阶数据类定义（R181-R187 公共，从 v4 polaris.sim.lvs_advanced_types 迁移）。

批次 10-B 拆分说明:
    从 lvs_advanced.py（原 1371 行）抽出全部 10 个 dataclass，集中管理
    LVS 进阶功能的数据结构，便于各子模块共享引用。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://doi.org/10.1017/CBO9781316084168
- Synopsys Calibre nmLVS: https://eda.sw.siemens.com/en-US/calibre/
- Cadence Pegasus LVS: https://community.cadence.com/cadence_blogs_8/b/di/posts/pegasus-get-your-wings-pegasus-results-viewer--lvs

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU / R13 不保留 v4 兼容。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ._types import LVSMismatchType


@dataclass
class WaveguideParams:
    """波导参数（R181）。

    Attributes:
        name: 波导实例名。
        wg_type: 波导类型 ``"straight"`` / ``"bend"`` / ``"taper"``。
        width_um: 波导宽度（μm）。taper 取较窄端。
        length_um: 波导长度（μm）。bend 取弧长。
        radius_um: 弯曲波导曲率半径（μm），直波导/锥形波导为 0。
        width1_um: 锥形波导窄端宽度（μm），非 taper 与 width_um 相同。
        width2_um: 锥形波导宽端宽度（μm），非 taper 与 width_um 相同。
        bbox_um: 包围盒 (left, bottom, right, top)（μm）。
    """

    name: str
    wg_type: str
    width_um: float
    length_um: float
    radius_um: float = 0.0
    width1_um: float = 0.0
    width2_um: float = 0.0
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class DirectionalCouplerParams:
    """定向耦合器参数（R182）。

    Attributes:
        name: DC 实例名。
        coupling_length_um: 耦合区长度（μm）。
        coupling_gap_um: 耦合间距（μm）。
        width_um: 单根波导宽度（μm）。
        bbox_um: 包围盒（μm）。
    """

    name: str
    coupling_length_um: float
    coupling_gap_um: float
    width_um: float
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class MMIParams:
    """MMI 参数（R183）。

    Attributes:
        name: MMI 实例名。
        width_um: MMI 多模区宽度（μm）。
        length_um: MMI 多模区长度（μm）。
        input_port_count: 输入端口数。
        output_port_count: 输出端口数。
        bbox_um: 包围盒（μm）。
    """

    name: str
    width_um: float
    length_um: float
    input_port_count: int
    output_port_count: int
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class RingResonatorParams:
    """环形谐振器参数（R184）。

    Attributes:
        name: Ring 实例名。
        radius_um: 环半径（μm）（中心线半径）。
        width_um: 环波导宽度（μm）。
        coupling_gap_um: 耦合间距（μm）。
        bus_waveguide_name: 关联总线波导名（未找到时为空串）。
        bbox_um: 包围盒（μm）。
    """

    name: str
    radius_um: float
    width_um: float
    coupling_gap_um: float
    bus_waveguide_name: str = ""
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)


@dataclass
class ConnectivityReport:
    """连接性报告（R185）。

    Attributes:
        device_nodes: 器件节点列表。
        connections: 连接列表 [(dev1, dev2), ...]。
        floating_devices: 悬浮器件列表（无连接的器件）。
        isolated_groups: 孤立子图分组（每组为器件名列表）。
    """

    device_nodes: list[str] = field(default_factory=list)
    connections: list[tuple[str, str]] = field(default_factory=list)
    floating_devices: list[str] = field(default_factory=list)
    isolated_groups: list[list[str]] = field(default_factory=list)


@dataclass
class ParamMismatch:
    """器件参数偏差（R186）。

    Attributes:
        device_name: 器件名。
        param_name: 参数名。
        reference_value: 参考值。
        extracted_value: 提取值。
        deviation: 绝对偏差。
        relative_deviation: 相对偏差（百分比）。
    """

    device_name: str
    param_name: str
    reference_value: float
    extracted_value: float
    deviation: float
    relative_deviation: float


@dataclass
class DeviceMatchResult:
    """器件匹配结果（R186）。

    Attributes:
        matched_devices: 匹配成功的器件名列表。
        param_mismatches: 参数偏差列表。
        missing_devices: 参考有但版图无的器件。
        extra_devices: 版图有但参考无的器件。
    """

    matched_devices: list[str] = field(default_factory=list)
    param_mismatches: list[ParamMismatch] = field(default_factory=list)
    missing_devices: list[str] = field(default_factory=list)
    extra_devices: list[str] = field(default_factory=list)


@dataclass
class LocatedError:
    """带坐标的错误项（R187）。

    Attributes:
        mtype: 不匹配类型。
        message: 描述信息。
        bbox_um: 错误位置包围盒 (left, bottom, right, top)（μm）。
        device_name: 相关器件名。
        net_name: 相关网名。
    """

    mtype: LVSMismatchType
    message: str
    bbox_um: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    device_name: str = ""
    net_name: str = ""


@dataclass
class StructuredErrorReport:
    """结构化错误报告（R187）。

    Attributes:
        short_errors: 短路错误列表（带坐标）。
        open_errors: 开路错误列表（带坐标）。
        device_errors: 器件错误列表（带坐标）。
        connection_errors: 连接错误列表（带坐标）。
        total_error_count: 错误总数。
        gds_path: 被检查的 GDS 路径。
    """

    short_errors: list[LocatedError] = field(default_factory=list)
    open_errors: list[LocatedError] = field(default_factory=list)
    device_errors: list[LocatedError] = field(default_factory=list)
    connection_errors: list[LocatedError] = field(default_factory=list)
    total_error_count: int = 0
    gds_path: str = ""


@dataclass
class ToleranceSpec:
    """参数容差规格（R186）。

    对标 KLayout LVS tolerance（绝对 + 相对）。

    Attributes:
        abs_tol: 绝对容差。
        rel_tol: 相对容差（0.05 = 5%）。
    """

    abs_tol: float = 0.0
    rel_tol: float = 0.05


__all__ = [
    "WaveguideParams",
    "DirectionalCouplerParams",
    "MMIParams",
    "RingResonatorParams",
    "ConnectivityReport",
    "ParamMismatch",
    "DeviceMatchResult",
    "LocatedError",
    "StructuredErrorReport",
    "ToleranceSpec",
]
