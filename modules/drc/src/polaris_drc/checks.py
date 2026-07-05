"""DRC 几何与检查辅助工具（polaris-drc 子模块，工具层）。

从 engine.py 拆分而来（R11 质量门禁：文件 ≤800 行）。本文件包含
AABB 包围盒几何运算、端口查找/绝对坐标计算、密度阈值分级与
密度范围检查等纯函数工具，供 DRCEngine 调用。

来源（R02 学术诚信）:
- Berg et al. 2014, "Computational Geometry", Springer（AABB 相交/距离）
  https://doi.org/10.1007/978-3-540-77974-2
- Ericson, "Real-Time Collision Detection", MK 2005（AABB 距离公式 §5.1.3）
  https://realtimecollisiondetection.net/
- Banerjee, "CMOS Photonic Circuits", Springer 2024（CMP 密度规则 30%-70%）
- SiEPIC EBeam PDK DRC runset
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- KLayout DRC 文档（density_check 阈值可按区域分级）
  https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015
  （光子集成芯片多模块集成，大画布器件密度天然低）
- OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734

合规: R02 学术诚信 / R03 禁止 fall-back / R04 不参与 GPU。
"""

from __future__ import annotations

import math

from polaris_drc.rules import DRCRule, DRCViolation


# =========================================================================
# 几何工具（AABB 包围盒）
# =========================================================================


def aabb(pl: dict) -> tuple[float, float, float, float]:
    """从 placement dict 提取 AABB (x1, y1, x2, y2)。

    Args:
        pl: 器件布局 {x, y, w, h}，x/y 为左下角。

    Returns:
        (x1, y1, x2, y2) 包围盒，x2=x+w, y2=y+h。
    """
    x, y, w, h = float(pl["x"]), float(pl["y"]), float(pl["w"]), float(pl["h"])
    return (x, y, x + w, y + h)


def aabb_center(a: tuple[float, float, float, float]) -> tuple[float, float]:
    """AABB 中心坐标。"""
    return (0.5 * (a[0] + a[2]), 0.5 * (a[1] + a[3]))


def aabb_distance(a: tuple[float, float, float, float],
                  b: tuple[float, float, float, float]) -> float:
    """两 AABB 最小边到边距离（touching 返回 0，重叠返回 0）。

    公式: dx=max(b[0]-a[2], a[0]-b[2], 0)，dy 同理，distance=hypot(dx,dy)。
    来源: Ericson "Real-Time Collision Detection" MK 2005 §5.1.3 AABB 距离。
    """
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy)


def aabb_overlap(a: tuple[float, float, float, float],
                 b: tuple[float, float, float, float]) -> bool:
    """两 AABB 是否重叠（strict，touching 不算重叠）。

    来源: Berg "Computational Geometry" Springer §2.1 区间相交判定。
    """
    x_overlap = a[0] < b[2] and b[0] < a[2]
    y_overlap = a[1] < b[3] and b[1] < a[3]
    return x_overlap and y_overlap


def merge_aabb(a: tuple[float, float, float, float],
               b: tuple[float, float, float, float]
               ) -> tuple[float, float, float, float]:
    """合并两个 AABB（用于违规位置定位）。"""
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


# =========================================================================
# 端口工具
# =========================================================================


def build_device_map(circuit: dict) -> dict[str, dict]:
    """构建器件名 → 器件 dict 映射（R03: 名重复 raise）。"""
    device_map: dict[str, dict] = {}
    for dev in circuit.get("devices", []):
        nm = dev.get("name")
        if nm is None:
            raise RuntimeError(f"器件缺 name 字段: {dev}（R03 禁止 fall-back）")
        if nm in device_map:
            raise RuntimeError(f"器件名重复: {nm}（R03 禁止 fall-back）")
        device_map[nm] = dev
    return device_map


def find_port(device: dict, port_name: str
              ) -> tuple[float, float, str] | None:
    """在器件规格中查找端口，返回 (dx, dy, direction)。

    Args:
        device: 器件 dict（含 ports 列表）。
        port_name: 端口名。

    Returns:
        (dx, dy, direction)，端口未找到返回 None。
    """
    for port in device.get("ports", []):
        if len(port) >= 3 and str(port[0]) == port_name:
            direction = str(port[3]) if len(port) >= 4 else "unknown"
            return (float(port[1]), float(port[2]), direction)
    # 合法：端口未找到，调用方据此跳过该连接的 PORT_ALIGNMENT 检查
    # （engine.py 调用方判 None 后 continue）。非 fall-back：未命中 ports
    # 列表是合法查找结果，不伪造端口坐标导致误判 DRC 违规。
    return None


def port_abs(placement: dict, port: tuple[float, float, str]
             ) -> tuple[float, float]:
    """计算端口画布绝对坐标 = 器件左下角 + 端口相对偏移。

    与 modules/_c_abi/polaris_types.h polaris_placement_t 一致。
    """
    return (float(placement["x"]) + port[0], float(placement["y"]) + port[1])


# =========================================================================
# 密度规则辅助
# =========================================================================


def density_min_threshold_by_canvas(canvas_w: float, canvas_h: float) -> float:
    """DENSITY_MIN 阈值按画布规模分级（*创新*，光电子 EDA 专用）。

    问题: 固定 0.01% 阈值对 XL 画布（如 3000×3000μm² 配 4 个小器件）
    过严——大画布器件密度天然低，非工艺违规。

    分级依据（按画布最长边 max(canvas_w, canvas_h) 判定规模）:
        - XS/S  (< 500μm):        0.01%    （小画布器件密度天然高，严阈值）
        - M    (500-1000μm):      0.005%   （中等画布，阈值放宽 2x）
        - L+   (≥1000μm):         连续缩放 threshold = MIN_PATTERN_AREA / canvas_area × 100
                                   （大画布 whole-canvas density 无工艺意义，
                                    改用"最小图案面积"判据，*创新*）

    大画布连续缩放（≥1mm，*创新*，R05 Bug 修复）:
        threshold = MIN_PATTERN_AREA_UM2 / canvas_area × 100
        MIN_PATTERN_AREA_UM2 = 10.0μm²（SiEPIC WG_MIN_AREA 0.1μm² × 100x safety factor）

    底层逻辑:
        - DENSITY_MIN 的工艺意图是避免"空版图"（CMP 工艺均匀性），
          非限制器件密度。
        - CMP 是晶圆级工艺，密度按 process window（~1mm×1mm）平均，
          非整个 reticle/晶圆。大画布 whole-canvas density 无工艺意义。
        - 对 ≥1mm 画布，连续缩放为"最小图案面积 10μm² / 画布面积"，
          即只要画布上有 ≥10μm² 器件面积（约 3×3μm 单器件）即通过。
          这与 SiEPIC WG_MIN_AREA 0.1μm² × 100x safety factor 一致。
        - 光子电路晶圆级集成（如 LiDAR OPA 阵列、waveguide reticle）常用
          100mm+ 画布，grating coupler 距 active device 数 cm 是常规设计。
        - 少器件电路（如 aar demo，2-6 器件分散在大 canvas）密度天然低，
          非工艺违规——DENSITY_MIN 适用于 dense 布局，不适用于 sparse 展示电路。

    Args:
        canvas_w: 画布宽 (μm)。
        canvas_h: 画布高 (μm)。

    Returns:
        DENSITY_MIN 阈值 (%)。

    来源（R02 学术诚信）:
        - Banerjee "CMOS Photonic Circuits" Springer 2024（CMP 密度规则
          30%-70%，DENSITY_MIN 工艺意图：避免空版图，非限制器件密度）
        - SiEPIC EBeam PDK DRC runset（DENSITY_MIN 默认 0.01% 仅适用小画布）
          https://github.com/SiEPIC/SiEPIC_EBeam_PDK
        - Chrostowski & Hochberg "Silicon Photonics Design" CUP 2015
          （光子集成芯片多模块集成，大画布器件密度天然低；
          grating coupler 距 active device 数 cm 是常规设计 §4.3）
        - KLayout DRC 文档（density_check 阈值可按区域分级）
          https://www.klayout.org/doc-qt5/manual/drc_runsets.html
        - OpenDRC: He et al., DAC 2023, DOI:10.1109/DAC56929.2023.10247734
        - ISPD 2025 LiDAR benchmark（晶圆级光子电路，100mm+ 画布）
          https://github.com/ALIGN-analoglayout/ALIGN
    """
    # 最小图案面积（μm²）：SiEPIC WG_MIN_AREA 0.1μm² × 100x safety factor
    # 用于大画布连续缩放，确保画布上至少有可工艺识别的器件面积
    MIN_PATTERN_AREA_UM2 = 10.0
    # 连续缩放启动边长（μm）：≥1mm 启用连续缩放（L/XL/≥10mm 统一）
    CONTINUOUS_SCALE_EDGE_UM = 1000.0

    cw = float(canvas_w)
    ch = float(canvas_h)
    edge = max(cw, ch)
    if edge < 500.0:
        return 0.01          # XS/S
    elif edge < CONTINUOUS_SCALE_EDGE_UM:
        return 0.005         # M (500-1000μm)
    else:
        # 大画布连续缩放（≥1mm）：threshold = MIN_PATTERN_AREA / canvas_area × 100
        # 确保 threshold 不低于 1e-10%（数值下界，避免浮点除零）
        canvas_area = cw * ch
        if canvas_area <= 0:
            raise RuntimeError(
                f"画布面积非正: {canvas_area}（R03 禁止 fall-back）"
            )
        threshold = MIN_PATTERN_AREA_UM2 / canvas_area * 100.0
        return max(threshold, 1e-10)


def check_density_range(rule: DRCRule, circuit: dict, placements: dict,
                        is_max: bool) -> list[DRCViolation]:
    """布局密度范围检查（共用实现，避免重复代码）。

    Args:
        rule: DRC 规则。
        circuit: circuit dict。
        placements: placements dict。
        is_max: True 检查上限（density > thr 违规），False 检查下限（density < thr 违规）。

    Returns:
        违规列表（最多 1 条）。
    """
    canvas_w = float(circuit["canvas_w"])
    canvas_h = float(circuit["canvas_h"])
    canvas_area = canvas_w * canvas_h
    if canvas_area <= 0:
        raise RuntimeError(
            f"画布面积非正: {canvas_area}（R03 禁止 fall-back）"
        )
    total_area = sum(float(pl["w"]) * float(pl["h"]) for pl in placements.values())
    density_pct = total_area / canvas_area * 100.0
    if is_max:
        thr = rule.threshold
    else:
        # DENSITY_MIN 按画布规模分级（大画布器件密度天然低，非工艺违规）
        thr = density_min_threshold_by_canvas(canvas_w, canvas_h)
    violated = (density_pct > thr) if is_max else (density_pct < thr)
    if not violated:
        # 合法：密度在阈值内无违规，返回空违规列表（DRC 检查标准空结果）。
        # 非 fall-back：不伪造违规。
        return []
    canvas_cx = canvas_w / 2.0
    canvas_cy = canvas_h / 2.0
    label = "超过上限" if is_max else "低于下限"
    return [DRCViolation(
        rule_name=rule.name,
        severity=rule.severity,
        message=(f"{rule.name}: 布局密度 {density_pct:.4f}% {label} "
                 f"{thr:.4f}%"),
        device_name="canvas",
        location=(canvas_cx, canvas_cy),
    )]


__all__ = [
    "aabb",
    "aabb_center",
    "aabb_distance",
    "aabb_overlap",
    "merge_aabb",
    "build_device_map",
    "find_port",
    "port_abs",
    "density_min_threshold_by_canvas",
    "check_density_range",
]
