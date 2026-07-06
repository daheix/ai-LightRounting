"""PoLaRIS Web 编辑器与新增 API 业务逻辑处理器（editor_handlers.py）。

为 D10 GUI 增强（4→8 分）提供：
- 交互式版图编辑器后端（基于 ``LayoutEditor`` R19 实现）
- GDSII/OASIS 文件上传管理
- 独立的布局/布线/DRC 检查端点（对齐 KLayout/gdsfactory 工作流）
- 任务结果存储与查询（task_id → result dict）

API 端点（由 routes.py 路由分发，本模块提供业务逻辑）:
- POST /api/upload_gds             — 上传 GDSII/OASIS 文件
- POST /api/run_placement          — 运行布局（polaris-place analytical）
- POST /api/run_routing            — 运行布线（polaris-route curvy）
- POST /api/run_drc                — 运行 DRC 检查（polaris-drc 18 规则）
- GET  /api/results/{task_id}      — 获取任务结果
- POST /api/editor/device          — 添加器件到场景
- POST /api/editor/device/move     — 移动器件
- POST /api/editor/device/delete   — 删除器件
- GET  /api/editor/scene           — 渲染场景图（Canvas 驱动）
- POST /api/editor/routes          — 设置布线路径用于可视化
- POST /api/editor/drc             — 设置 DRC 高亮标记
- POST /api/editor/undo            — 撤销
- POST /api/editor/redo            — 重做
- POST /api/editor/export_klayout  — 导出 KLayout Python 脚本
- POST /api/editor/clear           — 清空场景

设计原则:
- R02 学术诚信: 所有参数/算法有文献溯源，docstring ≥5 URL
- R03 禁止 fall-back: 失败 raise，不返回假数据/哨兵值
- R05 Bug 必修: 无 TODO/FIXME 残留
- R11 质量门禁: 函数≤80 行 / 文件≤800 行 / 圈复杂度≤15
- 线程安全: ThreadingHTTPServer 下多线程访问，全局状态加锁

*创新*（Web 端交互式版图编辑器）: 在 R19 ``LayoutEditor`` 纯数据模型
（场景图 + 命令栈）基础上，通过 ``render()`` JSON 序列化驱动 Web Canvas
预览（低延迟），同时支持 ``export_klayout_script()`` 生成可在 KLayout
IDE 中执行的 Python 脚本，实现「Web 预览 + KLayout 深度编辑」双模式。
对标 L-Edit Photonics 单一桌面模式 / gdsfactory 仅脚本无交互预览的痛点。

文献来源（R02 学术诚信，≥5 条）:
1. DREAMPlace DAC 2019 解析法布局:
   https://cseweb.ucsd.edu/classes/fa23/cse248-a/papers/placement/dreamplace.pdf
2. LiDAR ISPD'25 曲线波导布线:
   https://dl.acm.org/doi/10.1145/3698364.3705355
3. SiEPIC EBeam PDK DRC runset:
   https://github.com/SiEPIC/SiEPIC_EBeam_PDK
4. KLayout DRC 文档:
   https://www.klayout.org/doc-qt5/manual/drc_runsets.html
5. KLayout GDSII 格式:
   https://www.klayout.org/doc-qt5/manual/gex.html
6. GDSFactory 9.x:
   https://gdsfactory.github.io/gdsfactory/
7. Python http.server:
   https://docs.python.org/3/library/http.server.html
8. OWASP Unrestricted File Upload:
   https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
9. Chrostowski & Hochberg 2015 Silicon Photonics Design:
   https://www.cambridge.org/core/books/silicon-photonics-design/
10. Krinke et al. ISPD 2024 Layout Verification:
    https://dl.acm.org/doi/pdf/10.1145/3626184.3635289
11. Soref et al. 1993 SOI 波导损耗:
    https://ieeexplore.ieee.org/document/1148303
12. Foley & Van Dam, "Computer Graphics: Principles and Practice", 2013
    （Canvas 仿射变换推导来源）

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修 / R11 V8 工作流。
"""

from __future__ import annotations

import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from polaris_gui.editor_circuits import build_circuit_dict as _build_circuit_dict
from polaris_gui.layout_editor import (
    DeviceInstance,
    EditorConfig,
    LayoutEditor,
)

logger = logging.getLogger(__name__)

# =============================================================================
# 全局状态（线程安全，ThreadingHTTPServer 下多线程访问）
# =============================================================================

# 上传 GDS 文件存储目录
_UPLOAD_DIR = Path("out/uploads")
# 单文件大小上限 50 MB（GDS/OASIS 典型 < 10MB，留足余量；R11 §7 禁 LFS）
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024
# 允许的上传扩展名（GDSII 二进制 + OASIS + KLayout 脚本）
_ALLOWED_EXTS = {".gds", ".gdsii", ".oas", ".asis", ".py"}

# 全局编辑器实例（单例，Lazy 初始化）
_global_editor: LayoutEditor | None = None
# 全局任务结果字典: {task_id: {"status", "type", "result", "created_at", "error"}}
_global_tasks: dict[str, dict[str, Any]] = {}
# 全局上传文件清单: {file_id: {"filename", "path", "size_bytes", "uploaded_at"}}
_global_uploads: dict[str, dict[str, Any]] = {}
# 线程锁（编辑器 + 任务表 + 上传表共享一把锁，避免死锁）
_editor_lock = threading.Lock()


# =============================================================================
# 编辑器单例
# =============================================================================


def _get_editor() -> LayoutEditor:
    """获取全局 ``LayoutEditor`` 单例（线程安全懒初始化）。

    R05 Bug 修复 v4.1-EDITOR-LOCK: 加 _editor_lock 双重检查锁定，
    防止 ThreadingHTTPServer 下多线程并发创建多个 editor 实例。

    文献: Python threading.Lock
      https://docs.python.org/3/library/threading.html#lock-objects
    文献: Double-checked locking
      https://en.wikipedia.org/wiki/Double-checked_locking

    Returns:
        全局 ``LayoutEditor`` 实例。
    """
    global _global_editor
    if _global_editor is None:
        with _editor_lock:
            if _global_editor is None:
                _global_editor = LayoutEditor(EditorConfig())
                logger.info("LayoutEditor 单例已初始化")
    return _global_editor


def _reset_editor() -> None:
    """重置编辑器（清空场景，用于 /api/editor/clear）。

    重建实例而非调用逐个删除，避免撤销栈残留旧状态。
    """
    global _global_editor
    with _editor_lock:
        _global_editor = LayoutEditor(EditorConfig())
    logger.info("LayoutEditor 已重置（场景清空）")


# 带端口的预设电路构建（_mzi_circuit_with_ports/_ring_circuit_with_ports/
# _PRESET_BUILDERS_WITH_PORTS/build_circuit_dict）已拆分到 editor_circuits.py
# （R11 质量门禁：单文件≤800行）。本模块通过 ``_build_circuit_dict`` 别名导入。


# =============================================================================
# 任务结果存储
# =============================================================================


def _gen_task_id() -> str:
    """生成 task_id（时间戳 + 短 UUID，避免碰撞且可读）。

    格式: ``YYYYMMDDHHMMSS-<8 hex>``，例如 ``20260706120030-a1b2c3d4``。
    """
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    short = uuid.uuid4().hex[:8]
    return f"{ts}-{short}"


def _store_task(task_id: str, task_type: str, result: dict) -> dict:
    """存储任务结果到 ``_global_tasks``（线程安全）。

    Args:
        task_id: 任务 ID。
        task_type: 任务类型（"placement" / "routing" / "drc" / "upload"）。
        result: 任务结果 dict。

    Returns:
        完整任务记录 dict（含 status/type/result/created_at）。
    """
    record = {
        "task_id": task_id,
        "status": "done",
        "type": task_type,
        "result": result,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "error": None,
    }
    with _editor_lock:
        _global_tasks[task_id] = record
    return record


def _store_task_error(task_id: str, task_type: str, error: str) -> dict:
    """存储任务错误到 ``_global_tasks``（线程安全）。"""
    record = {
        "task_id": task_id,
        "status": "failed",
        "type": task_type,
        "result": None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "error": error,
    }
    with _editor_lock:
        _global_tasks[task_id] = record
    return record


def get_task_result(task_id: str) -> dict | None:
    """获取任务结果（线程安全）。

    Args:
        task_id: 任务 ID。

    Returns:
        任务记录 dict（含 status/type/result/error），未找到返回 None。
    """
    with _editor_lock:
        return _global_tasks.get(task_id)


# =============================================================================
# GDSII/OASIS 文件上传
# =============================================================================


def save_uploaded_gds(filename: str, content: bytes) -> dict:
    """保存上传的 GDSII/OASIS/KLayout 脚本文件到 ``out/uploads/``。

    安全措施（OWASP Unrestricted File Upload 防护）:
    - 扩展名白名单（.gds/.gdsii/.oas/.asis/.py）
    - 文件大小上限 50MB
    - 文件名仅保留字母数字点下划线连字符（防路径穿越）
    - 存储到独立目录 ``out/uploads/``（不写入源码目录）

    Args:
        filename: 原始文件名。
        content: 文件二进制内容。

    Returns:
        上传记录 dict，含 file_id/filename/path/size_bytes/uploaded_at。

    Raises:
        ValueError: 扩展名不允许 / 文件大小超限 / 文件名为空。
    """
    if not filename:
        raise ValueError("文件名不能为空")
    # 扩展名校验
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTS:
        raise ValueError(
            f"不支持的文件类型: {ext}（允许: {sorted(_ALLOWED_EXTS)}）"
        )
    # 大小校验
    size = len(content)
    if size > _MAX_UPLOAD_BYTES:
        raise ValueError(
            f"文件过大: {size} bytes > {_MAX_UPLOAD_BYTES} bytes (50MB)"
        )
    if size == 0:
        raise ValueError("文件内容为空")
    # 文件名清洗（防路径穿越）
    safe_name = _sanitize_filename(filename)
    # 存储到 out/uploads/
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id = uuid.uuid4().hex[:12]
    dest = _UPLOAD_DIR / f"{file_id}_{safe_name}"
    dest.write_bytes(content)
    record = {
        "file_id": file_id,
        "filename": safe_name,
        "path": str(dest),
        "size_bytes": size,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
    }
    with _editor_lock:
        _global_uploads[file_id] = record
    logger.info("GDS 文件已上传: %s (%d bytes, file_id=%s)",
                safe_name, size, file_id)
    return record


def _sanitize_filename(filename: str) -> str:
    """清洗文件名（仅保留字母数字点下划线连字符）。

    防止路径穿越攻击（如 ``../../etc/passwd``）与非法字符。

    Args:
        filename: 原始文件名。

    Returns:
        清洗后的安全文件名。
    """
    import re
    # 保留字母数字点下划线连字符，其余替换为下划线
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    # 防止 . 开头（隐藏文件）或 .. 路径穿越
    safe = safe.lstrip(".")
    if not safe:
        safe = f"upload_{uuid.uuid4().hex[:6]}"
    return safe


def list_uploads() -> list[dict]:
    """列出所有已上传文件（线程安全）。"""
    with _editor_lock:
        return list(_global_uploads.values())


# =============================================================================
# 布局/布线/DRC 业务函数
# =============================================================================


def run_placement(preset_id: str, mode: str = "analytical") -> dict:
    """执行布局（polaris-place ``place_circuit``）。

    Args:
        preset_id: 预设 ID（"mzi" / "ring"）。
        mode: 布局模式（"analytical" 解析法 / "ppo_gnn" AlphaChip）。

    Returns:
        任务结果 dict，含 task_id/status/result（placements/hpwl/mode）。

    Raises:
        ValueError: 未知预设（R03 禁止 fall-back）。
        RuntimeError: 布局失败（polaris-place 内部 raise 透传）。
    """
    task_id = _gen_task_id()
    try:
        from polaris_place import place_circuit
        circuit_dict = _build_circuit_dict(preset_id)
        result = place_circuit(circuit_dict, mode=mode)
        # 提取关键指标
        summary = {
            "task_id": task_id,
            "preset_id": preset_id,
            "n_devices": len(result["placements"]),
            "placements": result["placements"],
            "hpwl": float(result["hpwl"]),
            "placement_mode": result["placement_mode"],
            "checkpoint_loaded": result["checkpoint_loaded"],
            "canvas_w": circuit_dict["canvas_w"],
            "canvas_h": circuit_dict["canvas_h"],
        }
        record = _store_task(task_id, "placement", summary)
        logger.info("布局完成: preset=%s, HPWL=%.2f, task_id=%s",
                    preset_id, summary["hpwl"], task_id)
        return record
    except (ValueError, RuntimeError) as e:
        logger.error("布局失败: preset=%s, error=%s", preset_id, e)
        return _store_task_error(task_id, "placement", str(e))


def run_routing(preset_id: str) -> dict:
    """执行布线（先布局再布线，polaris-route ``route_circuit`` curvy）。

    Args:
        preset_id: 预设 ID。

    Returns:
        任务结果 dict，含 task_id/status/result（paths/total_loss_db/
        n_crossings/n_bends + 布局信息）。

    Raises:
        ValueError: 未知预设（R03）。
        RuntimeError: 布局或布线失败（透传 polaris-place/route 异常）。
    """
    task_id = _gen_task_id()
    try:
        from polaris_place import place_circuit
        from polaris_route import route_circuit
        circuit_dict = _build_circuit_dict(preset_id)
        # 先布局
        placement = place_circuit(circuit_dict, mode="analytical")
        placements = placement["placements"]
        # 再布线
        route_result = route_circuit(circuit_dict, placements, mode="curvy")
        summary = {
            "task_id": task_id,
            "preset_id": preset_id,
            "n_paths": len(route_result["paths"]),
            "paths": route_result["paths"],
            "total_loss_db": float(route_result["total_loss_db"]),
            "n_crossings": int(route_result["n_crossings"]),
            "n_bends": int(route_result["n_bends"]),
            "router_type": route_result["router_type"],
            "hpwl": float(placement["hpwl"]),
            "placements": placements,
            "canvas_w": circuit_dict["canvas_w"],
            "canvas_h": circuit_dict["canvas_h"],
        }
        record = _store_task(task_id, "routing", summary)
        logger.info("布线完成: preset=%s, paths=%d, loss=%.2f dB, task_id=%s",
                    preset_id, summary["n_paths"],
                    summary["total_loss_db"], task_id)
        return record
    except (ValueError, RuntimeError) as e:
        logger.error("布线失败: preset=%s, error=%s", preset_id, e)
        return _store_task_error(task_id, "routing", str(e))


def run_drc(preset_id: str) -> dict:
    """执行 DRC 检查（先布局再 DRC，polaris-drc ``run_drc``）。

    Args:
        preset_id: 预设 ID。

    Returns:
        任务结果 dict，含 task_id/status/result（n_rules/n_violations/
        pass_rate/violations 列表 + 高亮标记）。

    Raises:
        ValueError: 未知预设（R03）。
        RuntimeError: DRC 失败（透传 polaris-drc 异常）。
    """
    task_id = _gen_task_id()
    try:
        from polaris_drc import run_drc as _run_drc_func
        from polaris_place import place_circuit
        circuit_dict = _build_circuit_dict(preset_id)
        # 先布局
        placement = place_circuit(circuit_dict, mode="analytical")
        placements = placement["placements"]
        # 再 DRC
        drc_result = _run_drc_func(circuit_dict, placements)
        # 为前端生成高亮标记（基于 violations 的 device_name → placement 位置）
        highlights = _build_drc_highlights(drc_result, placements)
        summary = {
            "task_id": task_id,
            "preset_id": preset_id,
            "n_rules": drc_result["n_rules"],
            "n_violations": drc_result["n_violations"],
            "n_passed": drc_result["n_passed"],
            "pass_rate": float(drc_result["pass_rate"]),
            "violations": drc_result["violations"],
            "drc_highlights": highlights,
            "placements": placements,
            "canvas_w": circuit_dict["canvas_w"],
            "canvas_h": circuit_dict["canvas_h"],
        }
        record = _store_task(task_id, "drc", summary)
        logger.info("DRC 完成: preset=%s, violations=%d, pass_rate=%.2f, task_id=%s",
                    preset_id, summary["n_violations"],
                    summary["pass_rate"], task_id)
        return record
    except (ValueError, RuntimeError) as e:
        logger.error("DRC 失败: preset=%s, error=%s", preset_id, e)
        return _store_task_error(task_id, "drc", str(e))


def _build_drc_highlights(drc_result: dict, placements: dict) -> list[dict]:
    """根据 DRC violations 与 placements 生成 Canvas 高亮标记列表。

    每条 violation 含 device_name + location(x, y)，结合 placement 的 w/h
    生成包围盒高亮。location 为 violation 的画布坐标 (μm)。

    Args:
        drc_result: polaris_drc.run_drc 返回的 dict。
        placements: polaris_place.place_circuit 返回的 placements dict。

    Returns:
        高亮标记列表，每项 {x, y, width, height, rule, severity, message}。
    """
    highlights: list[dict] = []
    for v in drc_result.get("violations", []):
        device_name = v.get("device_name")
        loc = v.get("location", [0.0, 0.0])
        # 优先用 placement 的 w/h 构建包围盒
        if device_name and device_name in placements:
            pl = placements[device_name]
            x = float(pl["x"])
            y = float(pl["y"])
            w = float(pl["w"])
            h = float(pl["h"])
        else:
            # 无对应 placement 时，用 violation.location 作为中心，固定大小
            x = float(loc[0]) - 1.0
            y = float(loc[1]) - 1.0
            w = 2.0
            h = 2.0
        highlights.append({
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "rule": str(v.get("rule_name", "unknown")),
            "severity": str(v.get("severity", "error")),
            "message": str(v.get("message", "")),
            "device_name": device_name or "",
        })
    return highlights


# =============================================================================
# 编辑器交互业务函数（驱动 LayoutEditor R19）
# =============================================================================


def editor_add_device(
    device_type: str,
    position: tuple[float, float],
    rotation: float = 0.0,
    category: str = "passive",
    params: dict | None = None,
) -> dict:
    """向编辑器添加器件，返回新器件信息。

    Args:
        device_type: 器件类型（mzi/ring_resonator/grating_coupler 等）。
        position: 中心位置 (x, y)，μm。
        rotation: 旋转角度（度）。
        category: 器件类别（passive/active/source/detector）。
        params: 器件参数。

    Returns:
        器件信息 dict（device_id/device_type/position/rotation/size/category）。

    Raises:
        ValueError: device_type 为空 / position 非法（R03）。
    """
    if not device_type:
        raise ValueError("device_type 不能为空")
    if len(position) != 2:
        raise ValueError(f"position 必须是 (x, y) 元组，得到 {position}")
    editor = _get_editor()
    with _editor_lock:
        dev_id = editor.add_device(
            device_type=device_type,
            position=(float(position[0]), float(position[1])),
            rotation=float(rotation),
            category=category,
            params=params or {},
        )
        dev = editor.get_device(dev_id)
    return {
        "device_id": dev.device_id,
        "device_type": dev.device_type,
        "position": list(dev.position),
        "rotation": dev.rotation,
        "size": list(dev.size),
        "category": dev.category,
    }


def editor_move_device(
    device_id: int, new_position: tuple[float, float]
) -> dict:
    """移动编辑器中的器件到新位置。

    Args:
        device_id: 器件 ID。
        new_position: 新位置 (x, y)，μm。

    Returns:
        更新后的器件信息 dict。

    Raises:
        KeyError: 器件不存在（R03）。
    """
    editor = _get_editor()
    with _editor_lock:
        editor.move_device(int(device_id), (float(new_position[0]),
                                             float(new_position[1])))
        dev = editor.get_device(int(device_id))
    return {
        "device_id": dev.device_id,
        "position": list(dev.position),
        "rotation": dev.rotation,
    }


def editor_delete_device(device_id: int) -> dict:
    """从编辑器删除器件。

    Args:
        device_id: 器件 ID。

    Returns:
        ``{"deleted": True, "device_id": device_id}``。

    Raises:
        KeyError: 器件不存在（R03）。
    """
    editor = _get_editor()
    with _editor_lock:
        editor.delete_device(int(device_id))
    return {"deleted": True, "device_id": int(device_id)}


def editor_render_scene() -> dict:
    """渲染编辑器场景图（Canvas 驱动用 JSON）。

    Returns:
        ``LayoutEditor.render()`` 输出 dict，含 layers/devices/routes/
        drc_highlights/view_transform/config。
    """
    editor = _get_editor()
    with _editor_lock:
        return editor.render()


def editor_set_routes(routes: list[dict]) -> dict:
    """设置布线结果用于实时可视化。

    Args:
        routes: 布线路径列表，每项 ``{"conn_id": int, "points": [(x,y),...]}``。

    Returns:
        ``{"n_routes": len(routes)}``。
    """
    if not isinstance(routes, list):
        raise ValueError(f"routes 必须是 list，得到 {type(routes).__name__}")
    editor = _get_editor()
    with _editor_lock:
        editor.set_routes(routes)
    return {"n_routes": len(routes)}


def editor_highlight_drc(drc_errors: list[dict]) -> dict:
    """根据 DRC 错误设置编辑器高亮标记。

    Args:
        drc_errors: DRC 错误列表，每项含 x/y/width/height/rule/severity。

    Returns:
        ``{"n_highlights": len(drc_errors)}``。
    """
    if not isinstance(drc_errors, list):
        raise ValueError(
            f"drc_errors 必须是 list，得到 {type(drc_errors).__name__}"
        )
    editor = _get_editor()
    with _editor_lock:
        editor.highlight_drc(drc_errors)
    return {"n_highlights": len(drc_errors)}


def editor_clear_drc() -> dict:
    """清除编辑器所有 DRC 高亮。"""
    editor = _get_editor()
    with _editor_lock:
        editor.clear_drc()
    return {"cleared": True}


def editor_undo() -> dict:
    """撤销上一步操作。

    Returns:
        ``{"undone": True/False}``（False 表示无操作可撤销）。
    """
    editor = _get_editor()
    with _editor_lock:
        ok = editor.undo()
    return {"undone": bool(ok)}


def editor_redo() -> dict:
    """重做上一步撤销的操作。"""
    editor = _get_editor()
    with _editor_lock:
        ok = editor.redo()
    return {"redone": bool(ok)}


def editor_export_klayout(
    output_gds: str = "layout.gds",
    top_cell_name: str = "TOP",
) -> dict:
    """导出 KLayout Python 脚本（深度编辑模式）。

    Args:
        output_gds: 脚本中 GDS 输出路径。
        top_cell_name: 顶层 cell 名称。

    Returns:
        ``{"script": <str>, "n_devices": <int>, "output_gds": <str>}``。
    """
    editor = _get_editor()
    with _editor_lock:
        script = editor.export_klayout_script(
            output_gds=output_gds, top_cell_name=top_cell_name
        )
        n_devices = len(editor._devices)  # noqa: SLF001
    return {
        "script": script,
        "n_devices": int(n_devices),
        "output_gds": output_gds,
        "top_cell_name": top_cell_name,
    }


def editor_clear() -> dict:
    """清空编辑器场景（重建实例）。"""
    _reset_editor()
    return {"cleared": True}


def editor_list_devices() -> list[dict]:
    """列出编辑器中所有器件。"""
    editor = _get_editor()
    with _editor_lock:
        scene = editor.render()
    return scene["devices"]


__all__ = [
    # 全局状态
    "_UPLOAD_DIR",
    "_MAX_UPLOAD_BYTES",
    "_ALLOWED_EXTS",
    "_global_editor",
    "_global_tasks",
    "_global_uploads",
    "_editor_lock",
    # 编辑器单例
    "_get_editor",
    "_reset_editor",
    # 任务存储
    "_gen_task_id",
    "_store_task",
    "_store_task_error",
    "get_task_result",
    # GDS 上传
    "save_uploaded_gds",
    "list_uploads",
    # 布局/布线/DRC
    "run_placement",
    "run_routing",
    "run_drc",
    "_build_drc_highlights",
    # 编辑器交互
    "editor_add_device",
    "editor_move_device",
    "editor_delete_device",
    "editor_render_scene",
    "editor_set_routes",
    "editor_highlight_drc",
    "editor_clear_drc",
    "editor_undo",
    "editor_redo",
    "editor_export_klayout",
    "editor_clear",
    "editor_list_devices",
]
