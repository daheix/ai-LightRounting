"""PoLaRIS 智能布线子模块（polaris-route）。

提供稳定的 Python API（route_circuit/compute_path_loss），对已布局电路执行
曲线波导布线，输出波导路径、总插入损耗、交叉数与弯曲数。

## 设计原则

- 对外 API 返回 JSON-serializable dict（与 polaris-core / polaris-place 一致）
- 纯 NumPy 实现（R04: 不参与 GPU）
- 禁止 fall-back（R03）: 布线失败 raise RuntimeError，不返回哨兵值
- 输出坐标约定: 路径点为画布绝对坐标 (μm)，与
  ``modules/_c_abi/polaris_types.h`` 中 ``polaris_path_t.xs/ys`` 一致

## 损耗模型（R02 学术诚信，参数可溯源）

- 传播损耗 3.0 dB/cm: Soref et al. 1993 IEEE Proc. 41(9) SOI 波导上界
- 单弯损耗 0.05 dB: SiEPIC EBeam PDK 通用路径保守上界
- 单次交叉损耗 0.3 dB: SiEPIC EBeam PDK crossing_te1550 上界
- 器件插入损耗: 从 ``device.params.insertion_loss_db`` 提取
  （polaris-pdk/polaris-sparam 按器件类型提供，如 GC 1.9dB、MMI1x2 0.4dB）
- 路径级 ``loss_db`` = 波导损耗(传播+弯曲+交叉) + 终点器件(dev2)插入损耗
- 电路级 ``total_loss_db`` = sum(所有波导损耗) + sum(所有器件插入损耗去重)
  （含起始器件如 gc1，反映全电路光功率预算，Chrostowski & Hochberg 2015 §3.3）

## 来源（R02 学术诚信，≥5 个文献 URL）

- LiDAR: Automated Curvy Waveguide Detailed Routing（ISPD'25）
  https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
- LiDAR 2.0: Hierarchical Curvy Waveguide Detailed Routing（TCAD 2025）
  https://scopex-asu.github.io/files/publications/PD_TCAD2025_LiDARv2.pdf
- SiEPIC EBeam PDK（bend_euler radius=5μm，0.05 dB/bend，0.3 dB/crossing）
  https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm 传播损耗基准）
  https://ieeexplore.ieee.org/document/1148303
- Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
  https://www.cambridge.org/core/books/silicon-photonics-design/
- Klauss et al., "Euler spiral waveguide bends", Opt Express 2018
  https://doi.org/10.1364/OE.26.029637
- Fujisawa et al. 2017, "Euler bend clothoid curve low-loss waveguide"
  (Optics Express 25(8) 9150) https://opg.optica.org/oe/fulltext.cfm?uri=oe-25-8-9150
- A* 搜索算法（Hart, Nilsson & Raphael 1968）
  https://en.wikipedia.org/wiki/A*_search_algorithm
- numpy ndarray C API
  https://numpy.org/doc/stable/reference/c-api/types-and-structures.html
"""

from __future__ import annotations

from typing import Any

from polaris_route.curvy import (
    BEND_LOSS_DB,
    CROSSING_LOSS_DB,
    PROPAGATION_LOSS_DB_CM,
    CurveType,
    CurvyRouteConfig,
    CurvyRouter,
    compute_path_loss as _compute_path_loss,
    count_bends,
    count_crossings,
    generate_arc_bend,
    generate_euler_bend,
    path_length,
    s_bend_bezier,
)

__version__ = "5.0.0"

# 布线模式 → CurvyRouter 实例化标记
_SUPPORTED_MODES = ("curvy",)


def _validate_circuit(circuit: dict) -> None:
    """校验 circuit dict 结构完整性（R03: 失败 raise）。

    Args:
        circuit: 待校验 circuit dict。

    Raises:
        RuntimeError: circuit 非 dict / 缺必要字段 / 画布尺寸非正。
    """
    if not isinstance(circuit, dict):
        raise RuntimeError(
            f"circuit 必须是 dict，得到 {type(circuit).__name__}"
        )
    for key in ("name", "devices", "connections", "canvas_w", "canvas_h"):
        if key not in circuit:
            raise RuntimeError(f"circuit 缺少必要字段: {key}")
    if circuit["canvas_w"] <= 0 or circuit["canvas_h"] <= 0:
        raise RuntimeError(
            f"画布尺寸必须为正: canvas_w={circuit['canvas_w']}, "
            f"canvas_h={circuit['canvas_h']}（R03 禁止 fall-back）"
        )
    if not isinstance(circuit["devices"], list):
        raise RuntimeError("circuit.devices 必须是 list")
    if not isinstance(circuit["connections"], list):
        raise RuntimeError("circuit.connections 必须是 list")


def _validate_placements(placements: dict) -> None:
    """校验 placements dict 结构完整性（R03: 失败 raise）。

    Args:
        placements: 待校验 placements dict。

    Raises:
        RuntimeError: placements 非 dict / 器件缺 x,y 字段。
    """
    if not isinstance(placements, dict):
        raise RuntimeError(
            f"placements 必须是 dict，得到 {type(placements).__name__}"
        )
    for name, pl in placements.items():
        if not isinstance(pl, dict):
            raise RuntimeError(
                f"placements['{name}'] 必须是 dict，得到 {type(pl).__name__}"
            )
        for key in ("x", "y"):
            if key not in pl:
                raise RuntimeError(
                    f"placements['{name}'] 缺少字段: {key}"
                    f"（R03 禁止 fall-back）"
                )


def _build_device_map(circuit: dict) -> dict[str, dict]:
    """构建器件名 → 器件 dict 的映射。

    Args:
        circuit: circuit dict。

    Returns:
        {device_name: device_dict}。

    Raises:
        RuntimeError: 器件名重复或缺失。
    """
    device_map: dict[str, dict] = {}
    for dev in circuit["devices"]:
        if "name" not in dev:
            raise RuntimeError(
                f"器件缺 name 字段: {dev}（R03 禁止 fall-back）"
            )
        name = dev["name"]
        if name in device_map:
            raise RuntimeError(
                f"器件名重复: {name}（R03 禁止 fall-back）"
            )
        device_map[name] = dev
    return device_map


def _find_port(
    device: dict, port_name: str,
) -> tuple[float, float, str]:
    """在器件规格中查找指定端口。

    Args:
        device: 器件 dict（含 ports 列表）。
        port_name: 端口名。

    Returns:
        (dx, dy, direction) 端口相对偏移与方向。

    Raises:
        RuntimeError: 端口未找到（R03 禁止 fall-back）。
    """
    ports = device.get("ports", [])
    for port in ports:
        if len(port) < 3:
            raise RuntimeError(
                f"端口格式非法（至少含 name, dx, dy）: {port}"
                f"（R03 禁止 fall-back）"
            )
        if str(port[0]) == port_name:
            direction = str(port[3]) if len(port) >= 4 else "unknown"
            return (float(port[1]), float(port[2]), direction)
    raise RuntimeError(
        f"器件 {device.get('name', '?')} 未找到端口: {port_name}"
        f"（R03 禁止 fall-back，可用端口: "
        f"{[p[0] for p in ports]}）"
    )


def _get_device_insertion_loss(device: dict) -> float:
    """从器件 params 中提取插入损耗 (dB)（R02 学术诚信，参数可溯源）。

    器件插入损耗来源: ``device["params"]["insertion_loss_db"]``，
    由 polaris-pdk / polaris-sparam 按器件类型与工艺节点提供
    （SiEPIC EBeam PDK 1550nm 典型值: GC 1.9dB, MMI1x2 0.4dB, MMI2x2 0.5dB）。

    若器件未指定 ``insertion_loss_db``（如纯波导 phase_shifter 只给 neff），
    则插入损耗为 0.0（器件本身无插入损耗，仅波导有传播损耗）。

    来源（R02 学术诚信）:
    - SiEPIC EBeam PDK grating_coupler 1.9 dB
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - polaris-sparam mmi_1x2_s/mmi_2x2_s/grating_coupler_s 默认值
      (modules/sparam/src/polaris_sparam/models.py)
    - Chrostowski & Hochberg 2015 §3.3 光子链路功率预算
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Args:
        device: 器件 dict（含 params 字段）。

    Returns:
        插入损耗 (dB)，未指定则为 0.0。

    Raises:
        RuntimeError: params 非 dict / insertion_loss_db 非数值 / 为负
            （R03 禁止 fall-back）。
    """
    params = device.get("params", {})
    if not isinstance(params, dict):
        raise RuntimeError(
            f"器件 {device.get('name', '?')} 的 params 必须是 dict，"
            f"得到 {type(params).__name__}（R03 禁止 fall-back）"
        )
    if "insertion_loss_db" not in params:
        return 0.0
    raw = params["insertion_loss_db"]
    try:
        loss = float(raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"器件 {device.get('name', '?')} 的 insertion_loss_db 非数值: {raw}"
            f"（R03 禁止 fall-back）"
        ) from exc
    if loss < 0:
        raise RuntimeError(
            f"器件 {device.get('name', '?')} 的 insertion_loss_db 不能为负: {loss}"
            f"（R03 禁止 fall-back）"
        )
    return loss


def _port_absolute_position(
    placement: dict, port_dx: float, port_dy: float,
) -> tuple[float, float]:
    """计算端口的画布绝对坐标。

    端口绝对坐标 = 器件左下角坐标 + 端口相对偏移
    （与 modules/_c_abi/polaris_types.h polaris_placement_t 一致）

    Args:
        placement: 器件布局 {x, y, w, h}，x/y 为左下角。
        port_dx: 端口相对器件原点的 x 偏移 (μm)。
        port_dy: 端口相对器件原点的 y 偏移 (μm)。

    Returns:
        (abs_x, abs_y) 画布绝对坐标 (μm)。
    """
    return (float(placement["x"]) + port_dx, float(placement["y"]) + port_dy)


def _count_path_crossings(
    paths: list[list[tuple[float, float]]],
) -> list[int]:
    """统计每条路径与其他路径的交叉数。

    对每对路径 (i, j) i<j 调用 count_crossings，交叉数同时累加到两条路径。

    Args:
        paths: 所有路径点列表的列表。

    Returns:
        每条路径的交叉数列表（长度 = len(paths)）。
    """
    n = len(paths)
    counts = [0] * n
    for i in range(n):
        for j in range(i + 1, n):
            c = count_crossings(paths[i], paths[j])
            counts[i] += c
            counts[j] += c
    return counts


def _route_resolve_connection(
    conn, device_map: dict, placements: dict, router: CurvyRouter,
) -> tuple[dict, list[tuple[float, float]]]:
    """解析单条连接 (dev1.port1 → dev2.port2) 生成路径点。

    Args:
        conn: [dev1, port1, dev2, port2] 长度 4。
        device_map: 器件名 → 器件 dict 映射。
        placements: 布局结果 {name: {x, y, w, h}}。
        router: CurvyRouter 实例。

    Returns:
        (raw_path_dict, points_list)。

    Raises:
        RuntimeError: conn 格式非法 / 器件不存在 / 端口未找到
            （R03 禁止 fall-back）。
    """
    if not isinstance(conn, (list, tuple)) or len(conn) != 4:
        raise RuntimeError(
            f"connection 必须是长度 4 的 list/tuple "
            f"[dev1, port1, dev2, port2]，得到: {conn}"
            f"（R03 禁止 fall-back）"
        )
    dev1_name, port1_name, dev2_name, port2_name = conn

    # 查找器件
    for name in (dev1_name, dev2_name):
        if name not in device_map:
            raise RuntimeError(
                f"连接 {conn} 引用了不存在的器件: {name}"
                f"（R03 禁止 fall-back）"
            )
        if name not in placements:
            raise RuntimeError(
                f"连接 {conn} 的器件 {name} 不在 placements 中"
                f"（R03 禁止 fall-back）"
            )

    # 查找端口 + 计算端口绝对坐标
    dev1 = device_map[dev1_name]
    dev2 = device_map[dev2_name]
    port1_dx, port1_dy, _ = _find_port(dev1, port1_name)
    port2_dx, port2_dy, _ = _find_port(dev2, port2_name)
    start = _port_absolute_position(placements[dev1_name], port1_dx, port1_dy)
    end = _port_absolute_position(placements[dev2_name], port2_dx, port2_dy)

    # 生成曲线波导路径
    points = router.route(start, end)
    raw_path = {
        "dev1": dev1_name, "port1": port1_name,
        "dev2": dev2_name, "port2": port2_name,
        "points": points,
    }
    return raw_path, points


def _route_compute_losses(
    raw_paths: list[dict],
    crossing_counts: list[int],
    device_map: dict,
) -> tuple[list[dict], float, int, int]:
    """计算每条路径损耗与弯曲数（第三遍）。

    损耗模型（R02 学术诚信，参数可溯源）:
    - 路径级 loss_db = 波导损耗(传播+弯曲+交叉) + 终点器件(dev2)插入损耗
    - 电路级 total_loss_db = sum(所有波导损耗) + sum(所有器件插入损耗去重)

    来源: Soref 1993; SiEPIC EBeam PDK; Chrostowski & Hochberg 2015 §3.3
    """
    paths_out: list[dict] = []
    total_waveguide_loss = 0.0
    total_bends = 0
    total_crossing_pairs = 0
    for idx, raw in enumerate(raw_paths):
        points = raw["points"]
        n_bends = count_bends(points)
        propagation_bend = _compute_path_loss(points, PROPAGATION_LOSS_DB_CM)
        crossing_loss = crossing_counts[idx] * CROSSING_LOSS_DB
        waveguide_loss = propagation_bend + crossing_loss
        dev2 = device_map[raw["dev2"]]
        dev2_insertion_loss = _get_device_insertion_loss(dev2)
        loss_db = waveguide_loss + dev2_insertion_loss
        paths_out.append({
            "dev1": raw["dev1"], "port1": raw["port1"],
            "dev2": raw["dev2"], "port2": raw["port2"],
            "points": [[float(p[0]), float(p[1])] for p in points],
            "loss_db": float(loss_db),
            "n_bends": int(n_bends),
            "n_crossings": int(crossing_counts[idx]),
        })
        total_waveguide_loss += waveguide_loss
        total_bends += n_bends
        total_crossing_pairs += crossing_counts[idx]
    total_crossing_pairs //= 2
    # 电路级器件插入损耗（device_map 已按器件名去重，含起始器件如 gc1）
    total_device_insertion_loss = sum(
        _get_device_insertion_loss(dev) for dev in device_map.values()
    )
    total_loss_db = total_waveguide_loss + total_device_insertion_loss
    return paths_out, total_loss_db, total_bends, total_crossing_pairs


def _route_first_pass(
    circuit: dict, device_map: dict, placements: dict, router: CurvyRouter,
) -> tuple[list[dict], list[list[tuple[float, float]]]]:
    """第一遍: 解析所有连接生成路径点。

    对每条 connection 调用 _route_resolve_connection 得到 raw_path 与 points。

    Returns:
        (raw_paths, path_points)
    """
    raw_paths: list[dict] = []
    path_points: list[list[tuple[float, float]]] = []
    for conn in circuit["connections"]:
        raw_path, points = _route_resolve_connection(
            conn, device_map, placements, router,
        )
        raw_paths.append(raw_path)
        path_points.append(points)
    return raw_paths, path_points


def route_circuit(
    circuit: dict,
    placements: dict,
    mode: str = "curvy",
) -> dict:
    """对已布局电路执行智能布线，返回布线结果 dict。

    对电路的每条连接 (dev1.port1 → dev2.port2):
    1. 从 placements 查找 dev1/dev2 的左下角坐标
    2. 从 circuit.devices 查找端口相对偏移，计算端口绝对坐标
    3. 用 CurvyRouter 生成 S-bend 曲线波导路径
    4. 统计弯曲数、交叉数，计算路径损耗（波导损耗 + 器件插入损耗）

    损耗模型（R02 学术诚信，参数可溯源）:
    - 路径级 ``loss_db`` = 波导损耗(传播+弯曲+交叉) + 终点器件(dev2)插入损耗
    - 电路级 ``total_loss_db`` = sum(所有波导损耗) + sum(所有器件插入损耗去重)
    - 传播损耗 3.0 dB/cm（Soref 1993），单弯 0.05 dB，单次交叉 0.3 dB（SiEPIC）

    Args:
        circuit: polaris-core 风格 circuit dict。
        placements: polaris-place 输出 {name: {x, y, w, h}}。
        mode: 布线模式（"curvy"）。

    Returns:
        布线结果 dict: {paths, total_loss_db, n_crossings, n_bends, router_type}

    Raises:
        RuntimeError: mode 非法 / 结构非法 / 端口未找到（R03 禁止 fall-back）。
    """
    _validate_circuit(circuit)
    _validate_placements(placements)
    if mode not in _SUPPORTED_MODES:
        raise RuntimeError(
            f"不支持的布线模式: {mode}（可选: {_SUPPORTED_MODES}）"
        )
    device_map = _build_device_map(circuit)
    router = CurvyRouter()
    raw_paths, path_points = _route_first_pass(
        circuit, device_map, placements, router,
    )
    crossing_counts = _count_path_crossings(path_points)
    paths_out, total_loss_db, total_bends, total_crossing_pairs = (
        _route_compute_losses(raw_paths, crossing_counts, device_map)
    )
    return {
        "paths": paths_out,
        "total_loss_db": float(total_loss_db),
        "n_crossings": int(total_crossing_pairs),
        "n_bends": int(total_bends),
        "router_type": "curvy",
    }


def compute_path_loss(
    points: list,
    loss_db_cm: float = PROPAGATION_LOSS_DB_CM,
) -> float:
    """计算波导路径损耗（传播损耗 + 弯曲损耗）。

    损耗模型::

        loss_db = propagation + n_bends * 0.05

    - 传播损耗 = ``loss_db_cm`` × 路径长度(μm) / 1e4（cm = 1e4 μm）
    - 弯曲损耗 = 弯曲数 × 0.05 dB（SiEPIC EBeam PDK 通用路径上界）

    默认 ``loss_db_cm=3.0`` dB/cm 为 SOI 波导传播损耗上界
    （Soref 1993 + SiEPIC PDK）。

    来源（R02 学术诚信）:
    - Soref et al. 1993 IEEE Proc. 41(9) 1182-1183（SOI 3 dB/cm）
      https://ieeexplore.ieee.org/document/1148303
    - SiEPIC EBeam PDK（0.05 dB/bend 上界）
      https://github.com/SiEPIC/SiEPIC_EBeam_PDK
    - Chrostowski & Hochberg 2015 §6.4 Silicon Photonics Design
      https://www.cambridge.org/core/books/silicon-photonics-design/

    Args:
        points: 路径点序列 [[x, y], ...] 或 [(x, y), ...]，坐标单位 μm。
        loss_db_cm: 传播损耗系数 (dB/cm)，默认 3.0。

    Returns:
        路径总损耗 (dB)。

    Raises:
        RuntimeError: loss_db_cm 为负（R03 禁止 fall-back）。
    """
    return _compute_path_loss(points, loss_db_cm)


__all__ = [
    "route_circuit",
    "compute_path_loss",
    "CurvyRouter",
    "CurvyRouteConfig",
    "CurveType",
    "count_bends",
    "count_crossings",
    "path_length",
    "s_bend_bezier",
    "generate_euler_bend",
    "generate_arc_bend",
    "__version__",
]
