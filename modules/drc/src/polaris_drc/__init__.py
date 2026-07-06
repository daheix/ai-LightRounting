"""polaris-drc 子模块：DRC 设计规则检查（单一职责，从 polaris-verify 拆分）。

PoLaRIS v5.0 把原 polaris-verify 拆分为 polaris-drc + polaris-lvs 两个独立子模块
（R13 代码清理，禁止多个 vx 文件并存；单一职责："DRC 就是 DRC，LVS 是 LVS"）。
本子模块仅负责 DRC（Design Rule Check），保持原 ``run_drc`` Python API 名与返回
结构不变，便于后续 orchestrator 平滑迁移。

## Input → Process → Output 三段式文档

### Input
- ``circuit: dict`` — polaris-core 风格电路规格
  - 必含字段: ``name`` (str)、``devices`` (list[dict])、``canvas_w`` (μm)、
    ``canvas_h`` (μm)
  - 每个 device 含 ``name`` / ``device_type`` / ``ports``
    （端口格式 ``[(name, dx, dy, direction), ...]``）
  - 含 ``connections`` 列表 ``[(dev1, port1, dev2, port2), ...]``（可空）
- ``placements: dict`` — polaris-place 输出的布局结果
  - 格式 ``{device_name: {x, y, w, h}}``，μm
  - ``x, y`` 为器件**左下角**坐标（与 ``modules/_c_abi/polaris_types.h``
    ``polaris_placement_t`` 一致）

### Process
18 条 DRC 规则（12 SiEPIC EBeam PDK 基础 + 6 P0 波导级，阈值全部来自
SiEPIC 真实 runset 源码或行业 PDK 文档）:
1. ``MIN_SPACING`` 1.0μm（避免波导耦合串扰，WG_MIN_SPACE）
2. ``MIN_WIDTH`` 0.5μm（浅刻蚀工艺极限，SLAB150_MIN_WIDTH）
3. ``MIN_HEIGHT`` 0.4μm（220nm SOI 工艺极限，WG_MIN_WIDTH）
4. ``MIN_AREA`` 0.1μm²（确保工艺可识别，WG_MIN_AREA）
5. ``BOUNDARY``（器件不超出画布边界）
6. ``NO_OVERLAP``（器件之间不能重叠，touching 允许）
7. ``PORT_ALIGNMENT`` 10μm（连接端口坐标对齐容差，SiEPIC 弯曲容差 10-20μm）
8. ``PORT_DIRECTION``（端口方向合法 north/south/east/west）
9. ``PORT_CONNECTIVITY``（每个器件至少有一个端口被连接）
10. ``PORT_FACING``（连接端口方向相对 east↔west / north↔south）
11. ``DENSITY_MAX`` 80%（CMP 工艺均匀性密度上限）
12. ``DENSITY_MIN`` 0.01%（避免空版图密度下限）
13. ``BEND_RADIUS_MIN`` 5.0μm（最小弯曲半径，SiEPIC/IMEC/AMF/LiDAR/FluxCore）
14. ``WAVEGUIDE_WIDTH_MATCH`` 0（连接两端波导宽度匹配，SiEPIC Verification）
15. ``MIN_NOTCH`` 0.1μm（最小凹槽宽度，KLayout notch()/FluxCore 100nm）
16. ``WAVEGUIDE_MANHATTAN``（波导首末段 Manhattan，SiEPIC Verification）
17. ``ENCLOSED_AREA_MIN`` 0.01μm²（最小封闭面积，KLayout area_check）
18. ``CROSSING_ANGULAR`` 90°（交叉角度，LiDAR 2.0 II-B3 arXiv:2505.17239v1）

几何算法: AABB（Axis-Aligned Bounding Box）包围盒
- AABB 距离: Ericson "Real-Time Collision Detection" §5.1.3
- AABB 相交: Berg "Computational Geometry" §2.1 区间相交判定
- 密度: ``Σ(device_area) / canvas_area × 100%``

### Output
- ``dict``::

      {
          "n_rules": int,           # 规则总数（18）
          "n_violations": int,      # 违规总数
          "n_passed": int,          # 通过规则数（无违规的规则数）
          "pass_rate": float,       # 通过率 = n_passed / n_rules，范围 [0, 1]
          "violations": list[dict], # 违规清单
      }
  - 每个 violation dict: ``{rule_name, severity, message, device_name, location}``
  - ``pass_rate = n_passed / n_rules``，范围 ``[0, 1]``
  - 物理含义: ``pass_rate=1.0`` 表示 DRC clean，工艺可流片；
    ``pass_rate<1.0`` 表示存在违规，需修复后方可流片

## 设计原则
- 对外 API 返回 JSON-serializable dict（与 polaris-core / polaris-place 一致）
- 纯 NumPy 实现（R04: 不参与 GPU；禁止 CuPy/CUDA/ROCm）
- 禁止 fall-back（R03）: 校验失败 raise RuntimeError，不返回哨兵值/假数据
- 函数 ≤80 行 / 文件 ≤800 行 / 圈复杂度 ≤15（AGENTS.md 质量门禁）

## 来源（R02 学术诚信，≥5 个文献 URL）
- SiEPIC EBeam PDK DRC runset（WG_MIN_WIDTH=0.4μm, WG_MIN_SPACE=1.0μm 等真实
  工艺规则源码）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015, p.353
  https://www.cambridge.org/core/search?searchField=isbn&searchTerms=1107007731
- KLayout DRC 文档（width_check / space_check / area_check 算子语义）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
  https://doi.org/10.1109/DAC56929.2023.10247734
- Banerjee, "CMOS Photonic Circuits", Springer 2024（CMP 密度规则 30%-70%）
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  https://doi.org/10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离公式 §5.1.3）
  https://realtimecollisiondetection.net/
"""

from __future__ import annotations

from polaris_drc.engine import (
    DEFAULT_DRC_RULES,
    DRCEngine,
    DRCRule,
    DRCViolation,
    CheckType,
    run_drc_rules,
)

__version__ = "5.0.0"


def run_drc(circuit: dict, placements: dict,
            bend_compensate: bool = True) -> dict:
    """对已布局电路执行 DRC 设计规则检查，返回结果 dict（Input→Process→Output）。

    Input:
        circuit: polaris-core 风格 circuit dict（含 name/devices/connections/
            canvas_w/canvas_h）。每个 device 含 ports 列表
            ``[(name, dx, dy, direction), ...]``。
        placements: polaris-place 输出的布局结果 ``{name: {x, y, w, h}}``，
            x/y 为器件左下角坐标 (μm)。
        bend_compensate: 是否启用波导弯曲补偿（默认 True）。详见 DRCEngine。
            *创新*（光电子 EDA 专用）: SiEPIC PDK PORT_FACING 规则假设直连，
            但光子电路实际可通过波导弯曲补偿任意方向组合
            （Chrostowski & Hochberg 2015 §4.3，每 90° 弯曲 ≈ 0.05dB）。
            非 fall-back: 弯曲补偿是物理可实现的真实连接方式。

    Process:
        运行 18 条 DRC 规则（12 SiEPIC EBeam PDK 基础 + 6 P0 波导级：
        min_spacing / min_width / min_height / min_area / boundary /
        no_overlap / port_alignment / port_direction / port_connectivity /
        port_facing / density_max / density_min / bend_radius_min /
        waveguide_width_match / min_notch / waveguide_manhattan /
        enclosed_area_min / crossing_angular），使用 AABB 几何算法
        （Ericson §5.1.3）+ DFS 环检测（Cormen §22.3）。

    Output:
        DRC 结果 dict::

            {
                "n_rules": int,           # 规则总数（18）
                "n_violations": int,      # 违规总数
                "n_passed": int,          # 通过规则数
                "pass_rate": float,       # 通过率 = n_passed / n_rules
                "violations": list[dict], # 违规清单
            }
        每个 violation dict 含 ``{rule_name, severity, message, device_name,
        location}``。``pass_rate=1.0`` 表示 DRC clean，工艺可流片。

    Raises:
        RuntimeError: circuit/placements 结构非法（R03 禁止 fall-back）。
    """
    rules = DEFAULT_DRC_RULES
    engine = DRCEngine(rules, bend_compensate=bend_compensate)
    violations = engine.run(circuit, placements)
    # 统计通过的规则数（某规则无违规即视为通过）
    violated_rules = {v.rule_name for v in violations}
    n_passed = sum(1 for r in rules if r.name not in violated_rules)
    n_rules = len(rules)
    pass_rate = n_passed / n_rules if n_rules > 0 else 0.0
    return {
        "n_rules": n_rules,
        "n_violations": len(violations),
        "n_passed": n_passed,
        "pass_rate": pass_rate,
        "violations": [
            {
                "rule_name": v.rule_name,
                "severity": v.severity,
                "message": v.message,
                "device_name": v.device_name,
                "location": list(v.location),
            }
            for v in violations
        ],
    }


__all__ = [
    "run_drc",
    "DRCEngine",
    "DRCRule",
    "DRCViolation",
    "CheckType",
    "DEFAULT_DRC_RULES",
    "run_drc_rules",
    "__version__",
]
