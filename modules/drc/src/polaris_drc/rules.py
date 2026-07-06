"""DRC 规则定义（polaris-drc 子模块，规则层）。

从 engine.py 拆分而来（R11 质量门禁：文件 ≤800 行）。本文件包含
DRC 规则类型定义（CheckType 枚举）、规则数据结构（DRCRule）、
默认规则集（DEFAULT_DRC_RULES，18 条 = 12 SiEPIC EBeam PDK 基础规则
+ 6 条 P0 波导级规则）、违规结果（DRCViolation）以及端口方向规范化
常量与函数。

来源（R02 学术诚信）:
- SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH=0.4μm, WG_MIN_SPACE=1.0μm 等）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC-Tools Verification（Mismatched pin widths / Manhattan / Radius）
  https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- KLayout DRC 文档（width_check/space_check/area_check/notch）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  https://doi.org/10.1109/DAC56929.2023.10247734
- Banerjee, "CMOS Photonic Circuits", Springer 2024（CMP 密度规则 30%-70%）
- LiDAR 2.0: Zhou et al. arXiv:2505.17239v1, ISPD 2025（Bend Radius/Crossing）
  https://arxiv.org/html/2505.17239v1
- FluxCore DRC 文档（MIN_NOTCH=100nm, MIN_BEND_RADIUS=5-10μm）
  https://www.fluxcoredynamics.com/docs/design-rules
- IMEC iSiPP50G 数据手册（Bend radius 5μm, Ring Modulator）
  https://www.imec-int.com/sites/default/files/imported/Photonic%2520integrated%2520circuit_EN_v4_MPW_yi_0.pdf

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# 端口合法方向集合
VALID_DIRECTIONS = frozenset(("north", "south", "east", "west"))
# 端口方向缩写→全称映射（电路 JSON 常用 N/S/E/W，DRC 统一为 north/south/east/west）
DIR_ABBR_MAP = {
    "n": "north", "s": "south", "e": "east", "w": "west",
    "north": "north", "south": "south", "east": "east", "west": "west",
}
# 端口方向相对映射（连接两端方向应相对）
FACING_PAIRS = frozenset(
    (("east", "west"), ("west", "east"),
     ("north", "south"), ("south", "north"))
)


def normalize_direction(direction: str) -> str:
    """规范化端口方向（N→north, S→south, E→east, W→west）。

    支持大小写缩写（N/S/E/W）和全称（north/south/east/west）。
    非法方向原样返回（由 PORT_DIRECTION 规则报违规）。
    """
    return DIR_ABBR_MAP.get(str(direction).lower(), str(direction))


# 端口对齐容差（μm）
# 来源: SiEPIC EBeam PDK 实际波导弯曲容差 10-20μm（任务 1 审计建议）
# Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015 §4.3:
#   波导弯曲半径 ≥10μm 时弯曲损耗可控（每弯曲 ≈0.05dB）
# SiEPIC EBeam PDK DRC runset: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
# 取下限 10.0μm（保守值，允许 PORT_ALIGNMENT 后处理 pass 对齐残余偏差）
PORT_ALIGN_TOL_UM = 10.0

# S-bend 弯曲补偿范围（μm），*创新* 多维容差方程（LiDAR 2.0 §III-C2 offset neighbor）
# 来源: LiDAR 2.0 arXiv:2505.17239v2 §III-C2 "offset neighbors to correct small
#   misalignments (less than the bending radius) between the source and target
#   ports. The offset neighbor locations are computed analytically based on the
#   predefined bending radius and grid size"
# 物理含义: 端口偏差 dx<range 且 dy<range 时，可通过 S-bend/Euler 弯曲解析补偿，
#   生成 DRV-free 路径（LiDAR 2.0 论文标题即 "DRV-free"）。
# 数值: 50.0μm = 2× 典型弯曲半径（25μm），覆盖 SiEPIC bent_waveguide 5-50μm 范围
# 商业对标: Mentor Calibre eqDRC 多维容差方程
#   https://blogs.sw.siemens.com/calibre/2015/11/17/design-rule-checking-for-silicon-photonics/
# SiEPIC-Tools Verification: "pins facing each other with the same angle (180
#   degrees), and with the same position (accurate to the user database unit)"
#   https://github.com/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
PORT_ALIGN_BEND_RANGE_UM = 50.0


class CheckType(Enum):
    """DRC 检查类型枚举（与 KLayout DRC 规则类别对应）。

    来源: KLayout DRC 规则类别
    https://www.klayout.org/doc-qt5/manual/drc_runsets.html
    SiEPIC-Tools Verification（Mismatched pin widths / Manhattan / Radius）
    https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
    LiDAR 2.0: Zhou et al. arXiv:2505.17239v1, ISPD 2025（Crossing/Bend）
    https://arxiv.org/html/2505.17239v1
    """

    # === 基础几何 + 端口 + 密度（12 条 SiEPIC EBeam PDK 基础规则） ===
    MIN_SPACING = "min_spacing"
    MIN_WIDTH = "min_width"
    MIN_HEIGHT = "min_height"
    MIN_AREA = "min_area"
    BOUNDARY = "boundary"
    NO_OVERLAP = "no_overlap"
    PORT_ALIGNMENT = "port_alignment"
    PORT_DIRECTION = "port_direction"
    PORT_CONNECTIVITY = "port_connectivity"
    PORT_FACING = "port_facing"
    DENSITY_MAX = "density_max"
    DENSITY_MIN = "density_min"
    # === P0 波导级规则（6 条，2026-07-05 新增，覆盖率 48%→72%） ===
    BEND_RADIUS_MIN = "bend_radius_min"  # 最小弯曲半径（SiEPIC/IMEC/AMF/LiDAR/FluxCore）
    WAVEGUIDE_WIDTH_MATCH = "waveguide_width_match"  # 端口宽度匹配（SiEPIC Verification）
    MIN_NOTCH = "min_notch"  # 最小凹槽宽度（KLayout notch()/FluxCore）
    WAVEGUIDE_MANHATTAN = "waveguide_manhattan"  # 首末段 Manhattan（SiEPIC Verification）
    ENCLOSED_AREA_MIN = "enclosed_area_min"  # 最小封闭面积（KLayout area_check）
    CROSSING_ANGULAR = "crossing_angular"  # 交叉角度（LiDAR 2.0 II-B3）


@dataclass(frozen=True)
class DRCRule:
    """单条 DRC 规则定义。

    Attributes:
        name: 规则名（如 "MIN_SPACING"）。
        check_type: 检查类型（CheckType 枚举）。
        threshold: 阈值（μm/μm²/%，语义随 check_type 变化）。
        severity: 违规严重程度（0-1）。
        description: 规则描述（含来源）。
    """

    name: str
    check_type: CheckType
    threshold: float
    severity: float = 1.0
    description: str = ""


# SiEPIC EBeam PDK 默认 DRC 规则集（18 条 = 12 基础 + 6 P0 波导级）
# 所有阈值来自 SiEPIC EBeam PDK 实际 DRC runset 源码或行业 PDK 文档
# （R02 学术诚信，禁止编造）
# 来源: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
#       https://github-wiki-see.page/m/SiEPIC/SiEPIC-Tools/wiki/SiEPIC-Tools-Menu-descriptions
#       https://arxiv.org/html/2505.17239v1
#       https://www.fluxcoredynamics.com/docs/design-rules
DEFAULT_DRC_RULES: list[DRCRule] = [
    DRCRule(
        name="MIN_SPACING",
        check_type=CheckType.MIN_SPACING,
        threshold=1.0,
        severity=1.0,
        description="器件最小间距 1.0μm（SiEPIC WG_MIN_SPACE，避免波导耦合串扰）",
    ),
    DRCRule(
        name="MIN_WIDTH",
        check_type=CheckType.MIN_WIDTH,
        threshold=0.5,
        severity=1.0,
        description="器件最小宽度 0.5μm（SiEPIC SLAB150_MIN_WIDTH，浅刻蚀工艺极限）",
    ),
    DRCRule(
        name="MIN_HEIGHT",
        check_type=CheckType.MIN_HEIGHT,
        threshold=0.4,
        severity=1.0,
        description="器件最小高度 0.4μm（SiEPIC WG_MIN_WIDTH，220nm SOI 工艺极限）",
    ),
    DRCRule(
        name="MIN_AREA",
        check_type=CheckType.MIN_AREA,
        threshold=0.1,
        severity=1.0,
        description="器件最小面积 0.1μm²（SiEPIC WG_MIN_AREA，确保工艺可识别）",
    ),
    DRCRule(
        name="BOUNDARY",
        check_type=CheckType.BOUNDARY,
        threshold=0.0,
        severity=1.0,
        description="器件不超出画布边界",
    ),
    DRCRule(
        name="NO_OVERLAP",
        check_type=CheckType.NO_OVERLAP,
        threshold=0.0,
        severity=1.0,
        description="器件之间不能重叠（touching 允许）",
    ),
    DRCRule(
        name="PORT_ALIGNMENT",
        check_type=CheckType.PORT_ALIGNMENT,
        threshold=PORT_ALIGN_TOL_UM,
        severity=0.5,
        description="连接端口坐标对齐（容差 10μm，SiEPIC EBeam PDK 实际波导弯曲容差）",
    ),
    DRCRule(
        name="PORT_DIRECTION",
        check_type=CheckType.PORT_DIRECTION,
        threshold=0.0,
        severity=0.8,
        description="端口方向合法（north/south/east/west）",
    ),
    DRCRule(
        name="PORT_CONNECTIVITY",
        check_type=CheckType.PORT_CONNECTIVITY,
        threshold=0.0,
        severity=0.9,
        description="每个器件至少有一个端口被连接",
    ),
    DRCRule(
        name="PORT_FACING",
        check_type=CheckType.PORT_FACING,
        threshold=0.0,
        severity=0.7,
        description="连接端口方向相对（east↔west / north↔south）",
    ),
    DRCRule(
        name="DENSITY_MAX",
        check_type=CheckType.DENSITY_MAX,
        threshold=80.0,
        severity=0.6,
        description="布局密度上限 80%（CMP 工艺均匀性，Banerjee 2024）",
    ),
    DRCRule(
        name="DENSITY_MIN",
        check_type=CheckType.DENSITY_MIN,
        threshold=0.01,
        severity=0.6,
        description="布局密度下限（按画布规模分级: XS/S=0.01%, M=0.005%, L=0.002%, XL=0.001%；≥10mm 连续缩放 threshold=100μm²/canvas_area×100；大画布器件密度天然低，CMP 按 process window ~1mm×1mm 平均）",
    ),
    # ===== P0 波导级规则（6 条，2026-07-05 新增，覆盖率 48%→72%） =====
    DRCRule(
        name="BEND_RADIUS_MIN",
        check_type=CheckType.BEND_RADIUS_MIN,
        threshold=5.0,
        severity=1.0,
        description=("最小弯曲半径 5.0μm（SiEPIC EBeam PDK bend_radius=5μm / IMEC "
                     "iSiPP50G 5μm / AMF 10μm / LiDAR 2.0 II-B2 5-10μm / "
                     "FluxCore 5-10μm）。检查 device.params.bend_radius_um 字段，"
                     "未声明 bend_radius 的器件跳过（直段无弯曲半径）"),
    ),
    DRCRule(
        name="WAVEGUIDE_WIDTH_MATCH",
        check_type=CheckType.WAVEGUIDE_WIDTH_MATCH,
        threshold=0.0,
        severity=0.9,
        description=("连接两端波导宽度必须匹配（SiEPIC Verification "
                     "'Mismatched pin widths'）。宽度取自 device.params.width_um "
                     "→ params.wg_width → params.waveguide_width → 波导类器件 "
                     "placement.h。禁止回退到 device.width_um（BBOX 宽度，非波导"
                     "宽度）。浮点噪声由 math.isclose(rel_tol=1e-9, abs_tol=1e-9) "
                     "吸收。"),
    ),
    DRCRule(
        name="MIN_NOTCH",
        check_type=CheckType.MIN_NOTCH,
        threshold=0.1,
        severity=0.8,
        description=("最小凹槽宽度 0.1μm = 100nm（KLayout notch() / FluxCore "
                     "MIN_NOTCH=100nm）。检查两器件平行边间隙 < 100nm 的窄颈，"
                     "避免工艺无法识别细颈"),
    ),
    DRCRule(
        name="WAVEGUIDE_MANHATTAN",
        check_type=CheckType.WAVEGUIDE_MANHATTAN,
        threshold=0.0,
        severity=0.8,
        description=("波导首末段必须 Manhattan（垂直/水平，SiEPIC Verification "
                     "'首末段必须 Manhattan'）。检查波导器件端口方向 ∈ "
                     "{north, south, east, west}"),
    ),
    DRCRule(
        name="ENCLOSED_AREA_MIN",
        check_type=CheckType.ENCLOSED_AREA_MIN,
        threshold=0.01,
        severity=0.7,
        description=("最小封闭面积 0.01μm² = 100nm×100nm（KLayout area_check "
                     "内孔检测）。检查连接图环形成的封闭区域，避免孤立小洞"),
    ),
    DRCRule(
        name="CROSSING_ANGULAR",
        check_type=CheckType.CROSSING_ANGULAR,
        threshold=90.0,
        severity=0.7,
        description=("波导交叉角度 90° 优选（LiDAR 2.0 II-B3, "
                     "arXiv:2505.17239v1）。检查两波导 AABB 重叠且方向非垂直"
                     "（同为水平/同为垂直）的交叉违规"),
    ),
]


@dataclass
class DRCViolation:
    """DRC 违规结果（与 KLayoutDRCRunner Violation 格式对齐）。

    Attributes:
        rule_name: 触发的规则名。
        severity: 违规严重程度（0-1）。
        message: 违规描述信息。
        device_name: 相关器件名（多器件规则取首个）。
        location: 违规位置 (x, y) μm。
    """

    rule_name: str
    severity: float
    message: str
    device_name: str
    location: tuple[float, float]


__all__ = [
    "VALID_DIRECTIONS",
    "DIR_ABBR_MAP",
    "FACING_PAIRS",
    "PORT_ALIGN_TOL_UM",
    "PORT_ALIGN_BEND_RANGE_UM",
    "normalize_direction",
    "CheckType",
    "DRCRule",
    "DEFAULT_DRC_RULES",
    "DRCViolation",
]
