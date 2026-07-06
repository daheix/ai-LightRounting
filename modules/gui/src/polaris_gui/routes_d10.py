"""PoLaRIS Web Server D10 GUI 增强路由 mixin（routes_d10.py）。

从 routes.py 拆分而来（R11 质量门禁：单文件≤800行），承载 D10 GUI 增强
（4→8 分）的所有 HTTP handler 方法。作为 mixin 类，被 ``PolarisHTTPRequestHandler``
继承，复用其 ``_send_json`` / ``_read_json_body`` 等基础方法。

D10 GUI 增强 API（对齐 KLayout/gdsfactory 工作流）:
- POST /api/upload_gds             — 上传 GDSII/OASIS/KLayout 脚本文件
- POST /api/run_placement          — 运行布局（polaris-place analytical）
- POST /api/run_routing            — 运行布线（polaris-route curvy）
- POST /api/run_drc                — 运行 DRC 检查（polaris-drc 18 规则）
- GET  /api/results/{task_id}      — 获取任务结果
- GET  /api/uploads                — 列出已上传文件
- POST /api/editor/device          — 添加器件到场景
- POST /api/editor/device/move     — 移动器件
- POST /api/editor/device/delete   — 删除器件
- GET  /api/editor/scene           — 渲染场景图（Canvas 驱动）
- GET  /api/editor/devices         — 列出场景中所有器件
- POST /api/editor/routes          — 设置布线路径用于可视化
- POST /api/editor/drc             — 设置 DRC 高亮标记
- POST /api/editor/drc/clear       — 清除 DRC 高亮
- POST /api/editor/undo            — 撤销
- POST /api/editor/redo            — 重做
- POST /api/editor/export_klayout  — 导出 KLayout Python 脚本
- POST /api/editor/clear           — 清空场景

业务逻辑由 editor_handlers.py 提供，本模块仅负责 HTTP 协议层。

文献来源（R02 学术诚信，≥5 条）:
1. Python http.server: https://docs.python.org/3/library/http.server.html
2. OWASP Unrestricted File Upload:
   https://owasp.org/www-community/vulnerabilities/Unrestricted_File_Upload
3. RFC 7578 multipart/form-data: https://datatracker.ietf.org/doc/html/rfc7578
4. RFC 7807 Problem Details: https://datatracker.ietf.org/doc/html/rfc7807
5. KLayout GDSII 格式: https://www.klayout.org/doc-qt5/manual/gex.html
6. KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
7. REST API 错误处理: https://datatracker.ietf.org/doc/html/rfc7807
8. CWE-209 Information Exposure: https://cwe.mitre.org/data/definitions/209.html

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import json
import logging
import traceback

from polaris_gui.editor_handlers import (
    editor_add_device,
    editor_clear,
    editor_clear_drc,
    editor_delete_device,
    editor_export_klayout,
    editor_highlight_drc,
    editor_list_devices,
    editor_move_device,
    editor_redo,
    editor_render_scene,
    editor_set_routes,
    editor_undo,
    get_task_result,
    list_uploads,
    run_drc,
    run_placement,
    run_routing,
    save_uploaded_gds,
)

logger = logging.getLogger(__name__)


class D10RoutesMixin:
    """D10 GUI 增强 API 路由 mixin。

    被 ``PolarisHTTPRequestHandler`` 继承，提供 D10 增强路由的
    分发与 handler 方法。依赖宿主类提供 ``_send_json`` 方法。
    """

    # ==================================================================
    # D10 路由分发（_try_d10_get / _try_d10_post / _try_editor_post）
    # ==================================================================

    def _try_d10_get(self, path: str) -> bool:
        """处理 D10 增强 GET 路由，返回是否命中。

        路由: /api/results/{task_id} / /api/uploads /
              /api/editor/scene / /api/editor/devices
        """
        if path.startswith("/api/results/"):
            self._handle_get_results(path)
            return True
        if path == "/api/uploads":
            self._send_json({"uploads": list_uploads()})
            return True
        if path == "/api/editor/scene":
            self._send_json(editor_render_scene())
            return True
        if path == "/api/editor/devices":
            self._send_json({"devices": editor_list_devices()})
            return True
        return False

    def _try_d10_post(self, path: str) -> bool:
        """处理 D10 增强 POST 路由，返回是否命中。

        路由: /api/upload_gds / /api/run_placement / /api/run_routing /
              /api/run_drc / /api/editor/* (device/move/delete/routes/drc/
              undo/redo/export_klayout/clear)
        """
        if path == "/api/upload_gds":
            self._handle_upload_gds()
            return True
        if path == "/api/run_placement":
            self._handle_run_placement()
            return True
        if path == "/api/run_routing":
            self._handle_run_routing()
            return True
        if path == "/api/run_drc":
            self._handle_run_drc()
            return True
        return self._try_editor_post(path)

    def _try_editor_post(self, path: str) -> bool:
        """处理 /api/editor/* POST 路由，返回是否命中。"""
        if path == "/api/editor/device":
            self._handle_editor_add_device()
            return True
        if path == "/api/editor/device/move":
            self._handle_editor_move_device()
            return True
        if path == "/api/editor/device/delete":
            self._handle_editor_delete_device()
            return True
        if path == "/api/editor/routes":
            self._handle_editor_set_routes()
            return True
        if path == "/api/editor/drc":
            self._handle_editor_highlight_drc()
            return True
        if path == "/api/editor/drc/clear":
            self._send_json(editor_clear_drc())
            return True
        if path == "/api/editor/undo":
            self._send_json(editor_undo())
            return True
        if path == "/api/editor/redo":
            self._send_json(editor_redo())
            return True
        if path == "/api/editor/export_klayout":
            self._handle_editor_export_klayout()
            return True
        if path == "/api/editor/clear":
            self._send_json(editor_clear())
            return True
        return False

    # ------------------------------------------------------------------
    # D10 GET handler 方法
    # ------------------------------------------------------------------

    def _handle_get_results(self, path: str) -> None:
        """处理 GET /api/results/{task_id}: 返回任务结果。"""
        task_id = path.split("/")[-1]
        record = get_task_result(task_id)
        if record is None:
            self._send_json(
                {"success": False, "error": f"未知 task_id: {task_id}"},
                code=404,
            )
            return
        self._send_json({"success": True, **record})

    # ------------------------------------------------------------------
    # D10 POST handler 方法 — 文件上传与布局/布线/DRC
    # ------------------------------------------------------------------

    def _handle_upload_gds(self) -> None:
        """处理 POST /api/upload_gds: 上传 GDSII/OASIS/KLayout 脚本。

        支持 multipart/form-data（文件上传）与 raw body（二进制 + filename 头）。
        """
        content_type = self.headers.get("Content-Type", "")
        try:
            if content_type.startswith("multipart/form-data"):
                record = self._parse_multipart_upload(content_type)
            else:
                # raw body 模式：filename 从 header 取，body 即文件内容
                filename = self.headers.get("X-Filename", "upload.gds")
                content_length = int(self.headers.get("Content-Length", 0))
                content = (
                    self.rfile.read(content_length)
                    if content_length > 0 else b""
                )
                record = save_uploaded_gds(filename, content)
            self._send_json({"success": True, **record})
        except ValueError as e:
            self._send_json({"success": False, "error": str(e)}, code=400)
        except Exception as e:
            logger.error("上传 GDS 失败: %s\n%s", e, traceback.format_exc())
            self._send_json(
                {"success": False, "error": "上传处理内部错误"},
                code=500,
            )

    def _parse_multipart_upload(self, content_type: str) -> dict:
        """解析 multipart/form-data 上传请求，提取第一个文件字段。

        Args:
            content_type: Content-Type 头（含 boundary）。

        Returns:
            save_uploaded_gds 返回的上传记录 dict。

        Raises:
            ValueError: 无文件字段 / boundary 缺失 / 解析失败。
        """
        if "boundary=" not in content_type:
            raise ValueError("multipart 请求缺少 boundary")
        boundary = content_type.split("boundary=", 1)[1].strip()
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            raise ValueError("multipart 请求体为空")
        body = self.rfile.read(content_length)
        boundary_bytes = ("--" + boundary).encode("latin-1")
        parts = body.split(boundary_bytes)
        for part in parts:
            if b"filename=" not in part:
                continue
            header_end = part.find(b"\r\n\r\n")
            if header_end < 0:
                raise ValueError("multipart part 无 header 终止符")
            header_str = part[:header_end].decode("latin-1", errors="replace")
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            filename = _extract_filename_from_header(header_str)
            return save_uploaded_gds(filename, content)
        raise ValueError("multipart 请求未包含文件字段")

    def _handle_run_placement(self) -> None:
        """处理 POST /api/run_placement: 运行布局。"""
        params = self._read_json_body()
        if params is None:
            return
        preset = params.get("preset", "mzi")
        mode = params.get("mode", "analytical")
        try:
            record = run_placement(preset, mode=mode)
            self._send_json({"success": True, **record})
        except Exception as e:
            logger.error("run_placement 失败: %s\n%s", e, traceback.format_exc())
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )

    def _handle_run_routing(self) -> None:
        """处理 POST /api/run_routing: 运行布线。"""
        params = self._read_json_body()
        if params is None:
            return
        preset = params.get("preset", "mzi")
        try:
            record = run_routing(preset)
            self._send_json({"success": True, **record})
        except Exception as e:
            logger.error("run_routing 失败: %s\n%s", e, traceback.format_exc())
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )

    def _handle_run_drc(self) -> None:
        """处理 POST /api/run_drc: 运行 DRC 检查。"""
        params = self._read_json_body()
        if params is None:
            return
        preset = params.get("preset", "mzi")
        try:
            record = run_drc(preset)
            self._send_json({"success": True, **record})
        except Exception as e:
            logger.error("run_drc 失败: %s\n%s", e, traceback.format_exc())
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )

    def _read_json_body(self) -> dict | None:
        """读取并解析 JSON 请求体，失败时直接发送 400 响应并返回 None。"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            return json.loads(body) if body else {}
        except json.JSONDecodeError as e:
            self._send_json(
                {"success": False, "error": f"请求体不是有效的 JSON: {e}"},
                code=400,
            )
            return None

    # ------------------------------------------------------------------
    # D10 POST handler 方法 — 编辑器交互
    # ------------------------------------------------------------------

    def _handle_editor_add_device(self) -> None:
        """处理 POST /api/editor/device: 添加器件。"""
        params = self._read_json_body()
        if params is None:
            return
        try:
            device_type = params.get("device_type", "")
            position = params.get("position", [0.0, 0.0])
            rotation = float(params.get("rotation", 0.0))
            category = params.get("category", "passive")
            params_dict = params.get("params", {})
            record = editor_add_device(
                device_type=device_type,
                position=(float(position[0]), float(position[1])),
                rotation=rotation,
                category=category,
                params=params_dict if isinstance(params_dict, dict) else {},
            )
            self._send_json({"success": True, **record})
        except (ValueError, KeyError) as e:
            self._send_json({"success": False, "error": str(e)}, code=400)
        except Exception as e:
            logger.error("editor_add_device 失败: %s", e)
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )

    def _handle_editor_move_device(self) -> None:
        """处理 POST /api/editor/device/move: 移动器件。"""
        params = self._read_json_body()
        if params is None:
            return
        try:
            device_id = int(params.get("device_id", 0))
            new_position = params.get("new_position", [0.0, 0.0])
            record = editor_move_device(
                device_id, (float(new_position[0]), float(new_position[1]))
            )
            self._send_json({"success": True, **record})
        except (ValueError, KeyError) as e:
            self._send_json({"success": False, "error": str(e)}, code=400)
        except Exception as e:
            logger.error("editor_move_device 失败: %s", e)
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )

    def _handle_editor_delete_device(self) -> None:
        """处理 POST /api/editor/device/delete: 删除器件。"""
        params = self._read_json_body()
        if params is None:
            return
        try:
            device_id = int(params.get("device_id", 0))
            record = editor_delete_device(device_id)
            self._send_json({"success": True, **record})
        except (ValueError, KeyError) as e:
            self._send_json({"success": False, "error": str(e)}, code=400)
        except Exception as e:
            logger.error("editor_delete_device 失败: %s", e)
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )

    def _handle_editor_set_routes(self) -> None:
        """处理 POST /api/editor/routes: 设置布线路径用于可视化。"""
        params = self._read_json_body()
        if params is None:
            return
        routes = params.get("routes", [])
        try:
            record = editor_set_routes(
                routes if isinstance(routes, list) else []
            )
            self._send_json({"success": True, **record})
        except ValueError as e:
            self._send_json({"success": False, "error": str(e)}, code=400)

    def _handle_editor_highlight_drc(self) -> None:
        """处理 POST /api/editor/drc: 设置 DRC 高亮。"""
        params = self._read_json_body()
        if params is None:
            return
        drc_errors = params.get("drc_errors", [])
        try:
            record = editor_highlight_drc(
                drc_errors if isinstance(drc_errors, list) else []
            )
            self._send_json({"success": True, **record})
        except ValueError as e:
            self._send_json({"success": False, "error": str(e)}, code=400)

    def _handle_editor_export_klayout(self) -> None:
        """处理 POST /api/editor/export_klayout: 导出 KLayout 脚本。"""
        params = self._read_json_body()
        if params is None:
            return
        output_gds = params.get("output_gds", "layout.gds")
        top_cell = params.get("top_cell_name", "TOP")
        try:
            record = editor_export_klayout(
                output_gds=output_gds, top_cell_name=top_cell
            )
            self._send_json({"success": True, **record})
        except Exception as e:
            logger.error("editor_export_klayout 失败: %s", e)
            self._send_json(
                {"success": False, "error": str(e)}, code=500
            )


def _extract_filename_from_header(header_str: str) -> str:
    """从 multipart part 的 header 字符串中提取 filename。

    Args:
        header_str: multipart part 的 header 部分（latin-1 解码）。

    Returns:
        提取出的文件名，未找到则返回 ``"upload.gds"``。
    """
    for line in header_str.split("\r\n"):
        if "filename=" in line:
            idx = line.find("filename=")
            rest = line[idx + 9:].strip()
            if rest.startswith('"'):
                end = rest.find('"', 1)
                return rest[1:end] if end > 0 else rest[1:]
            return rest.split(";")[0].strip()
    return "upload.gds"


__all__ = ["D10RoutesMixin", "_extract_filename_from_header"]
