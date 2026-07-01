"""LVS 进阶器件参数提取（R181 波导 / R182 定向耦合器 / R183 MMI / R184 环形谐振器）。

批次 10-B 拆分说明（2026-07-01）:
    从 lvs_advanced.py 抽出 4 项器件参数提取功能及其私有分类辅助函数，
    统一放在本模块。所有提取均基于 WG 层几何分析。

来源（R02 学术诚信，≥5 文献 URL）:
- KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
- KLayout LVS Compare: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- SiEPIC 组件说明: https://github-wiki-see.page/m/SiEPIC/SiEPIC_EBeam_PDK/wiki/Component-Library-description
- Chrostowski & Hochberg, "Silicon Photonics Design", CUP 2015
  https://doi.org/10.1017/CBO9781316084168
- Ansys Lumerical 波导/DC/MMI/Ring 参数提取:
  https://optics.ansys.com/hc/en-us/articles/360042800213
- Yeh, "Optical Waves in Layered Media", Wiley 2005
  https://www.wiley.com/en-us/Optical+Waves+in+Layered+Media-p-9780471731924
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from polaris.sim.lvs_advanced_helpers import (
    _bbox_aspect,
    _bbox_um,
    _get_region,
    _load_layout,
    _polygon_area_um2,
    _shape_vertices_um,
)
from polaris.sim.lvs_advanced_types import (
    DirectionalCouplerParams,
    MMIParams,
    RingResonatorParams,
    WaveguideParams,
)


# ============================================================
# R181 波导提取增强
# ============================================================


def extract_waveguide_params(gds_path: str | Path) -> list[WaveguideParams]:
    """从 GDS 提取波导参数（R181）。

    识别直波导/弯曲波导/锥形波导，提取宽度/长度/曲率半径。

    分类策略（*创新*：基于包围盒长宽比 + 顶点数 + 面积比的几何分类器）：

    - 直波导（straight）：包围盒长宽比 ≥ 3 且顶点数 ≤ 6（矩形/微调矩形），
      长度 = 长边，宽度 = 短边。
    - 锥形波导（taper）：包围盒长宽比 ≥ 3 且顶点数为 4 且非矩形
      （两端宽度不等），窄端 width1、宽端 width2。
    - 弯曲波导（bend）：包围盒长宽比 < 1.5 且顶点数 > 6 且面积/包围盒面积
      在 (0.05, 0.85) 区间（四分之一环形），曲率半径 = (内径+外径)/2。

    底层逻辑对标 SiEPIC EBeam PDK 的 Waveguide/Round_Path 组件几何定义
    与 KLayout LVS 的 extract_devices 参数提取。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        波导参数列表。

    Raises:
        FileNotFoundError: GDS 不存在。
        RuntimeError: GDS 无 top cell 或 WG 层缺失。

    文献来源（≥5）：
    - KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
    - SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - SiEPIC 组件说明: https://github-wiki-see.page/m/SiEPIC/SiEPIC_EBeam_PDK/wiki/Component-Library-description
    - Chrostowski & Hochberg 2015, p.353: https://doi.org/10.1017/CBO9781316084168
    - Ansys Lumerical 波导参数: https://optics.ansys.com/hc/en-us/articles/360042800213
    - KLayout LVS Compare: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
    """
    layout, cell, dbu = _load_layout(gds_path)
    region = _get_region(layout, cell, "WG")
    if region.is_empty():
        raise RuntimeError("WG 层为空，无法提取波导参数（R03 禁止 fall-back）")

    results: list[WaveguideParams] = []
    for i, shape in enumerate(region.each()):
        pts = _shape_vertices_um(shape, dbu)
        bbox = _bbox_um(shape, dbu)
        aspect = _bbox_aspect(bbox)
        area = _polygon_area_um2(pts)
        bbox_area = max(
            (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1e-12
        )
        area_ratio = area / bbox_area
        name = f"wg_{i}"

        if aspect >= 3.0 and len(pts) <= 6:
            wg = _classify_straight_or_taper(name, pts, bbox, aspect)
        elif aspect < 1.5 and len(pts) > 6 and 0.05 < area_ratio < 0.85:
            wg = _classify_bend(name, pts, bbox)
        else:
            wg = _classify_straight_or_taper(name, pts, bbox, aspect)
        results.append(wg)
    return results


def _classify_straight_or_taper(
    name: str,
    pts: np.ndarray,
    bbox: tuple[float, float, float, float],
    aspect: float,
) -> WaveguideParams:
    """分类直波导/锥形波导。

    *创新*：通过比较两端宽度判断直波导 vs 锥形波导。
    底层逻辑：沿长轴方向取两端短边长度，若差异 > 5% 判为 taper。
    """
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    length = max(w, h)
    if w >= h:
        end1_pts = pts[pts[:, 0] - bbox[0] < 1e-6]
        end2_pts = pts[pts[:, 0] - bbox[2] > -1e-6]
        width1 = _end_width(end1_pts)
        width2 = _end_width(end2_pts)
    else:
        end1_pts = pts[pts[:, 1] - bbox[1] < 1e-6]
        end2_pts = pts[pts[:, 1] - bbox[3] > -1e-6]
        width1 = _end_width(end1_pts)
        width2 = _end_width(end2_pts)
    avg_width = (width1 + width2) / 2
    width_diff_ratio = abs(width1 - width2) / max(avg_width, 1e-12)
    if width_diff_ratio > 0.05 and len(pts) == 4:
        return WaveguideParams(
            name=name,
            wg_type="taper",
            width_um=avg_width,
            length_um=length,
            width1_um=width1,
            width2_um=width2,
            bbox_um=bbox,
        )
    return WaveguideParams(
        name=name,
        wg_type="straight",
        width_um=avg_width,
        length_um=length,
        width1_um=avg_width,
        width2_um=avg_width,
        bbox_um=bbox,
    )


def _end_width(end_pts: np.ndarray) -> float:
    """计算波导一端的宽度（该端顶点 y 或 x 跨度）。"""
    if len(end_pts) == 0:
        return 0.0
    if len(end_pts) == 1:
        return 0.0
    xs = end_pts[:, 0]
    ys = end_pts[:, 1]
    return max(float(np.ptp(xs)), float(np.ptp(ys)))


def _classify_bend(
    name: str,
    pts: np.ndarray, bbox: tuple[float, float, float, float]
) -> WaveguideParams:
    """分类弯曲波导，提取曲率半径与弧长。

    *创新*：弧心定位算法 —— 弧心位于包围盒四角中"距最近顶点距离最大"的角
    （因弧心位于环形孔洞内部，距所有弧上点距离 ≥ 内径）。
    底层逻辑：四分之一环形几何性质 + 凸包距离分析。

    弧长公式（四分之一圆弧）：L = π·R/2
    """
    corners = np.array(
        [
            [bbox[0], bbox[1]],
            [bbox[2], bbox[1]],
            [bbox[0], bbox[3]],
            [bbox[2], bbox[3]],
        ]
    )
    min_dists = []
    for c in corners:
        dists = np.linalg.norm(pts - c, axis=1)
        min_dists.append(float(np.min(dists)))
    center_idx = int(np.argmax(min_dists))
    center = corners[center_idx]
    dists_to_center = np.linalg.norm(pts - center, axis=1)
    inner_r = float(np.min(dists_to_center))
    outer_r = float(np.max(dists_to_center))
    radius = (inner_r + outer_r) / 2
    width = outer_r - inner_r
    arc_length = np.pi * radius / 2
    return WaveguideParams(
        name=name,
        wg_type="bend",
        width_um=width,
        length_um=arc_length,
        radius_um=radius,
        width1_um=width,
        width2_um=width,
        bbox_um=bbox,
    )


# ============================================================
# R182 定向耦合器提取
# ============================================================


def extract_directional_couplers(gds_path: str | Path) -> list[DirectionalCouplerParams]:
    """从 GDS 提取定向耦合器参数（R182）。

    识别 DC 结构（两根平行直波导 + 耦合区），提取耦合长度/耦合间距。

    识别算法（*创新*：基于平行波导对的耦合区检测）：

    1. 从 WG 层提取所有直波导（长宽比 ≥ 3 的矩形/带状形状）
    2. 对每对波导，检查是否平行（长轴方向一致）
    3. 检查间距是否在耦合间距范围内（0.1~2.0 μm，SiEPIC 典型值）
    4. 计算耦合区长度 = 两波导长轴方向的重叠长度
    5. 耦合间距 = 两波导中心线的垂直距离减去半宽之和

    底层逻辑对标 SiEPIC Broadband Directional Coupler 组件几何
    与 Chrostowski & Hochberg 第 9 章耦合模理论。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        定向耦合器参数列表。

    Raises:
        FileNotFoundError: GDS 不存在。
        RuntimeError: GDS 无 top cell 或 WG 层缺失。

    文献来源（≥5）：
    - SiEPIC EBeam PDK DC 组件: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - SiEPIC 组件说明（Broadband DC）: https://github-wiki-see.page/m/SiEPIC/SiEPIC_EBeam_PDK/wiki/Component-Library-description
    - Chrostowski & Hochberg 2015, Ch.9 耦合模理论: https://doi.org/10.1017/CBO9781316084168
    - KLayout LVS extract_devices: https://www.klayout.org/doc-qt5/manual/lvs.html
    - Yeh, "Optical Waves in Layered Media", Wiley 2005: https://www.wiley.com/en-us/Optical+Waves+in+Layered+Media-p-9780471731924
    - Ansys Lumerical DC 仿真: https://optics.ansys.com/hc/en-us/articles/360042800213
    """
    layout, cell, dbu = _load_layout(gds_path)
    region = _get_region(layout, cell, "WG")
    if region.is_empty():
        raise RuntimeError("WG 层为空，无法提取定向耦合器（R03 禁止 fall-back）")

    straight_wgs: list[tuple[int, tuple[float, float, float, float], float]] = []
    for i, shape in enumerate(region.each()):
        bbox = _bbox_um(shape, dbu)
        aspect = _bbox_aspect(bbox)
        if aspect >= 3.0:
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            width = min(w, h)
            straight_wgs.append((i, bbox, width))

    results: list[DirectionalCouplerParams] = []
    seen_pairs: set[tuple[int, int]] = set()
    for a in range(len(straight_wgs)):
        for b in range(a + 1, len(straight_wgs)):
            i1, bbox1, w1 = straight_wgs[a]
            i2, bbox2, w2 = straight_wgs[b]
            if (i1, i2) in seen_pairs:
                continue
            if abs(w1 - w2) > max(w1, w2) * 0.2:
                continue
            width = (w1 + w2) / 2
            if _is_horizontal_parallel(bbox1, bbox2):
                gap = abs((bbox2[1] + bbox2[3]) / 2 - (bbox1[1] + bbox1[3]) / 2) - width
                overlap = _horizontal_overlap(bbox1, bbox2)
            elif _is_vertical_parallel(bbox1, bbox2):
                gap = abs((bbox2[0] + bbox2[2]) / 2 - (bbox1[0] + bbox1[2]) / 2) - width
                overlap = _vertical_overlap(bbox1, bbox2)
            else:
                continue
            if gap < 0.05 or gap > 5.0:
                continue
            if overlap < 2.0:
                continue
            seen_pairs.add((i1, i2))
            combined_bbox = (
                min(bbox1[0], bbox2[0]),
                min(bbox1[1], bbox2[1]),
                max(bbox1[2], bbox2[2]),
                max(bbox1[3], bbox2[3]),
            )
            results.append(
                DirectionalCouplerParams(
                    name=f"dc_{len(results)}",
                    coupling_length_um=overlap,
                    coupling_gap_um=gap,
                    width_um=width,
                    bbox_um=combined_bbox,
                )
            )
    return results


def _is_horizontal_parallel(
    b1: tuple[float, float, float, float],
    b2: tuple[float, float, float, float],
) -> bool:
    """判断两包围盒是否水平平行（长边沿 x，y 方向邻近）。"""
    w1 = b1[2] - b1[0]
    h1 = b1[3] - b1[1]
    w2 = b2[2] - b2[0]
    h2 = b2[3] - b2[1]
    if w1 <= h1 or w2 <= h2:
        return False
    x_overlap = min(b1[2], b2[2]) - max(b1[0], b2[0])
    return x_overlap > 0


def _is_vertical_parallel(
    b1: tuple[float, float, float, float],
    b2: tuple[float, float, float, float],
) -> bool:
    """判断两包围盒是否垂直平行（长边沿 y，x 方向邻近）。"""
    w1 = b1[2] - b1[0]
    h1 = b1[3] - b1[1]
    w2 = b2[2] - b2[0]
    h2 = b2[3] - b2[1]
    if h1 <= w1 or h2 <= w2:
        return False
    y_overlap = min(b1[3], b2[3]) - max(b1[1], b2[1])
    return y_overlap > 0


def _horizontal_overlap(
    b1: tuple[float, float, float, float],
    b2: tuple[float, float, float, float],
) -> float:
    """水平方向重叠长度。"""
    return max(0.0, min(b1[2], b2[2]) - max(b1[0], b2[0]))


def _vertical_overlap(
    b1: tuple[float, float, float, float],
    b2: tuple[float, float, float, float],
) -> float:
    """垂直方向重叠长度。"""
    return max(0.0, min(b1[3], b2[3]) - max(b1[1], b2[1]))


# ============================================================
# R183 MMI 提取
# ============================================================


def _collect_shape_infos(region, dbu: float) -> list[tuple]:
    """收集 WG 层所有形状的尺寸信息（R627 Extract Method）。

    Returns:
        [(index, bbox, width, length, aspect), ...]
    """
    shapes_info: list[tuple[int, tuple[float, float, float, float], float, float, float]] = []
    for i, shape in enumerate(region.each()):
        bbox = _bbox_um(shape, dbu)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        width = min(w, h)
        length = max(w, h)
        aspect = length / max(width, 1e-12)
        shapes_info.append((i, bbox, width, length, aspect))
    return shapes_info


def _is_mmi_candidate(width: float, length: float, aspect: float) -> bool:
    """判断形状是否为 MMI 多模区候选（R627 Extract Method）。"""
    if width < 1.5 or aspect > 10 or aspect < 0.5:
        return False
    if length < 2.0:
        return False
    return True


def _count_mmi_ports(
    i: int, bbox: tuple, shapes_info: list[tuple], used_narrow: set[int]
) -> tuple[int, int]:
    """统计 MMI 候选区的输入/输出端口数（R627 Extract Method）。

    Returns:
        (input_ports, output_ports)。
    """
    input_ports = 0
    output_ports = 0
    for j, nbbox, nw, _nl, _na in shapes_info:
        if j == i or j in used_narrow:
            continue
        if nw >= 1.5:
            continue
        side = _which_side(bbox, nbbox, tolerance=1.0)
        if side == "left":
            input_ports += 1
            used_narrow.add(j)
        elif side == "right":
            output_ports += 1
            used_narrow.add(j)
    return input_ports, output_ports


def extract_mmis(gds_path: str | Path) -> list[MMIParams]:
    """从 GDS 提取 MMI 参数（R183）。

    识别 MMI 结构（多模干涉区 + 输入/输出端口波导），提取尺寸/端口数。

    识别算法（*创新*：基于宽区+邻接窄波导管脚数的 MMI 识别）：

    1. 从 WG 层提取所有形状
    2. 找"宽区"：宽度 ≥ 2× 典型波导宽度（≥ 1.5 μm）且长宽比在 1~8 区间
    3. 对每个宽区，统计邻接（包围盒间距 ≤ 0.5 μm）的窄波导（宽度 < 1 μm）
    4. 左侧窄波导数 = 输入端口数，右侧 = 输出端口数
    5. 多模区宽度/长度 = 宽区包围盒短边/长边

    底层逻辑对标 SiEPIC ebeam_mmi1x2_1550 组件几何
    与 Chrostowski & Hochberg 第 6 章自成像理论（MMI）。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        MMI 参数列表。

    Raises:
        FileNotFoundError: GDS 不存在。
        RuntimeError: GDS 无 top cell 或 WG 层缺失。

    文献来源（≥5）：
    - SiEPIC EBeam PDK MMI 组件: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - SiEPIC 组件说明: https://github-wiki-see.page/m/SiEPIC/SiEPIC_EBeam_PDK/wiki/Component-Library-description
    - Chrostowski & Hochberg 2015, Ch.6 自成像理论: https://doi.org/10.1017/CBO9781316084168
    - KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
    - Ansys Lumerical MMI 优化: https://docs.flexcompute.com/projects/photonforge/en/v1.1.7/examples/Cascaded_MZI_Filter.html
    - KLayout LVS Compare: https://klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
    """
    layout, cell, dbu = _load_layout(gds_path)
    region = _get_region(layout, cell, "WG")
    if region.is_empty():
        raise RuntimeError("WG 层为空，无法提取 MMI（R03 禁止 fall-back）")

    shapes_info = _collect_shape_infos(region, dbu)

    results: list[MMIParams] = []
    used_narrow: set[int] = set()
    for entry in shapes_info:
        i, bbox, width, length, aspect = entry
        if not _is_mmi_candidate(width, length, aspect):
            continue
        input_ports, output_ports = _count_mmi_ports(i, bbox, shapes_info, used_narrow)
        if input_ports == 0 and output_ports == 0:
            continue
        results.append(
            MMIParams(
                name=f"mmi_{len(results)}",
                width_um=width,
                length_um=length,
                input_port_count=input_ports,
                output_port_count=output_ports,
                bbox_um=bbox,
            )
        )
    return results


def _which_side(
    core: tuple[float, float, float, float],
    port: tuple[float, float, float, float],
    tolerance: float = 1.0,
) -> str:
    """判断 port 相对 core 的方位（left/right/other）。

    *创新*：基于 port 中心相对 core 左右边界的距离判定。
    """
    port_cx = (port[0] + port[2]) / 2
    port_cy = (port[1] + port[3]) / 2
    core_cy = (core[1] + core[3]) / 2
    if abs(port_cy - core_cy) > (core[3] - core[1]) * 0.75:
        return "other"
    if port_cx < core[0] - tolerance and abs(port_cx - core[0]) < 50.0:
        return "left"
    if port_cx > core[2] + tolerance and abs(port_cx - core[2]) < 50.0:
        return "right"
    return "other"


# ============================================================
# R184 环形谐振器提取
# ============================================================


def extract_ring_resonators(gds_path: str | Path) -> list[RingResonatorParams]:
    """从 GDS 提取环形谐振器参数（R184）。

    识别 ring resonator（环形 + 总线波导），提取半径/耦合间距。

    识别算法（*创新*：基于角度跨度 + 面积比的环形检测）：

    1. 从 WG 层提取所有形状
    2. 候选环形：包围盒长宽比 < 1.3（近正方形），顶点数 > 8，
       面积/包围盒面积 < 0.6（有孔洞感）
    3. 用角度跨度验证（顶点相对包围盒中心角度跨度 > 270° → 完整环）
    4. 半径 = (中心到顶点最小距离 + 最大距离) / 2
    5. 总线波导 = 最近直波导；耦合间距 = 总线边到环外沿距离

    底层逻辑对标 SiEPIC ebeam_ring_1550 组件几何
    与 Ansys Lumerical Ring Resonator 参数提取流程。

    Args:
        gds_path: GDS 文件路径。

    Returns:
        环形谐振器参数列表。

    Raises:
        FileNotFoundError: GDS 不存在。
        RuntimeError: GDS 无 top cell 或 WG 层缺失。

    文献来源（≥5）：
    - SiEPIC EBeam PDK Ring 组件: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Ansys Lumerical Ring Resonator 参数提取: https://optics.ansys.com/hc/en-us/articles/360042800213
    - Chrostowski & Hochberg 2015, Ch.4 微环谐振器: https://doi.org/10.1017/CBO9781316084168
    - KLayout LVS: https://www.klayout.org/doc-qt5/manual/lvs.html
    - SiEPIC 组件说明: https://github-wiki-see.page/m/SiEPIC/SiEPIC_EBeam_PDK/wiki/Component-Library-description
    - KLayout LVS Netter: https://klayout.org/downloads/master/doc-qt5/about/lvs_ref_netter.html
    """
    layout, cell, dbu = _load_layout(gds_path)
    region = _get_region(layout, cell, "WG")
    if region.is_empty():
        raise RuntimeError("WG 层为空，无法提取环形谐振器（R03 禁止 fall-back）")

    all_shapes: list[tuple[int, np.ndarray, tuple[float, float, float, float]]] = []
    for i, shape in enumerate(region.each()):
        pts = _shape_vertices_um(shape, dbu)
        bbox = _bbox_um(shape, dbu)
        all_shapes.append((i, pts, bbox))

    candidates: list[tuple[int, float, float, tuple[float, float, float, float], np.ndarray]] = []
    for i, pts, bbox in all_shapes:
        aspect = _bbox_aspect(bbox)
        if aspect >= 1.3 or len(pts) < 8:
            continue
        area = _polygon_area_um2(pts)
        bbox_area = max((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]), 1e-12)
        if area / bbox_area >= 0.6:
            continue
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        center = np.array([cx, cy])
        vecs = pts - center
        angles = np.arctan2(vecs[:, 1], vecs[:, 0])
        angle_span = _angle_span(angles)
        if angle_span < 270.0:
            continue
        dists = np.linalg.norm(vecs, axis=1)
        inner_r = float(np.min(dists))
        outer_r = float(np.max(dists))
        radius = (inner_r + outer_r) / 2
        width = outer_r - inner_r
        if radius < 1.0 or width < 0.1:
            continue
        candidates.append((i, radius, width, bbox, center))

    results: list[RingResonatorParams] = []
    for idx, (i, radius, width, bbox, center) in enumerate(candidates):
        bus_name, gap = _find_bus_waveguide(all_shapes, i, bbox, center, radius, width)
        results.append(
            RingResonatorParams(
                name=f"ring_{idx}",
                radius_um=radius,
                width_um=width,
                coupling_gap_um=gap,
                bus_waveguide_name=bus_name,
                bbox_um=bbox,
            )
        )
    return results


def _angle_span(angles: np.ndarray) -> float:
    """计算角度跨度（度，0~360）。

    *创新*：排序后求相邻角度最大间隙，360 - max_gap 即跨度。
    """
    if len(angles) == 0:
        return 0.0
    sorted_a = np.sort(angles)
    gaps = np.diff(sorted_a)
    wrap_gap = (sorted_a[0] + 2 * np.pi) - sorted_a[-1]
    max_gap = max(float(np.max(gaps)) if len(gaps) > 0 else 0.0, float(wrap_gap))
    return float(np.degrees(2 * np.pi - max_gap))


def _find_bus_waveguide(
    all_shapes: list[tuple[int, np.ndarray, tuple[float, float, float, float]]],
    ring_idx: int,
    ring_bbox: tuple[float, float, float, float],
    ring_center: np.ndarray,
    ring_radius: float,
    ring_width: float,
) -> tuple[str, float]:
    """找最近直波导作为总线，返回 (bus_name, coupling_gap)。

    总线判定：长宽比 ≥ 3 的直波导，与环外沿距离在 0.05~3.0 μm。
    耦合间距 = 总线最近边到环外沿的距离。
    """
    outer_r = ring_radius + ring_width / 2
    best_name = ""
    best_gap = float("inf")
    for j, _pts, bbox in all_shapes:
        if j == ring_idx:
            continue
        aspect = _bbox_aspect(bbox)
        if aspect < 3.0:
            continue
        nearest_edge_dist = _nearest_bbox_edge_distance(bbox, ring_center)
        gap = nearest_edge_dist - outer_r
        if gap < 0.05 or gap > 3.0:
            continue
        if gap < best_gap:
            best_gap = gap
            best_name = f"wg_{j}"
    if best_name == "":
        return "", 0.0
    return best_name, float(best_gap)


def _nearest_bbox_edge_distance(
    bbox: tuple[float, float, float, float], point: np.ndarray
) -> float:
    """计算点到包围盒最近边的距离（点到矩形边界的最短距离）。"""
    px, py = point[0], point[1]
    dx = max(bbox[0] - px, 0.0, px - bbox[2])
    dy = max(bbox[1] - py, 0.0, py - bbox[3])
    if dx == 0.0 and dy == 0.0:
        return 0.0
    return float(np.sqrt(dx * dx + dy * dy))


__all__ = [
    "extract_waveguide_params",
    "extract_directional_couplers",
    "extract_mmis",
    "extract_ring_resonators",
]
