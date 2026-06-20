"""PoLaRIS Web Server — HTTP API + 静态文件服务（阶段 F4）。

使用 Python 内置 http.server 实现 REST API + 静态前端服务，无需 Flask/FastAPI。
支持电路预设选择、一键布局布线、结果可视化、DRC 报告、GDS 导出。

API 端点:
- GET  /api/presets        — 列出预设电路
- POST /api/run            — 运行布局布线流水线
- GET  /api/health         — 健康检查

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- REST 设计规范: https://docs.python.org/3/library/http.server.html
"""

from __future__ import annotations

import json
import logging
import os
import threading
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


def _get_presets() -> list[dict]:
    """获取预设电路列表。"""
    return [
        {
            "id": "mzi",
            "name": "MZI 干涉仪",
            "description": "马赫-曾德尔干涉仪（2x2 MMI + 波导臂）",
            "devices": 5,
            "platform": "SOI",
        },
        {
            "id": "ring",
            "name": "微环谐振器",
            "description": "单微环 + 总线波导",
            "devices": 4,
            "platform": "SOI",
        },
        {
            "id": "clements_4x4",
            "name": "Clements 4x4 光矩阵",
            "description": "可编程光子线性计算单元（4x4）",
            "devices": 28,
            "platform": "SOI",
        },
    ]


def _build_circuit(preset_id: str):
    """根据预设 ID 构建电路规格。"""
    from polaris.data.circuit_spec import CircuitSpec, DeviceSpec

    if preset_id == "mzi":
        circuit = CircuitSpec(name="MZI", canvas_w=500, canvas_h=300, platform="SOI")
        circuit.add_device(DeviceSpec("mmi1", "mmi_1x2", 20, 10))
        circuit.add_device(DeviceSpec("wg1", "strip_waveguide", 100, 0.5))
        circuit.add_device(DeviceSpec("wg2", "strip_waveguide", 120, 0.5))
        circuit.add_device(DeviceSpec("mmi2", "mmi_2x2", 20, 10))
        circuit.add_device(DeviceSpec("gc1", "grating_coupler", 10, 10))
        circuit.add_connection("gc1", "out", "mmi1", "in")
        circuit.add_connection("mmi1", "out0", "wg1", "in")
        circuit.add_connection("mmi1", "out1", "wg2", "in")
        circuit.add_connection("wg1", "out", "mmi2", "in0")
        circuit.add_connection("wg2", "out", "mmi2", "in1")
        return circuit
    if preset_id == "ring":
        circuit = CircuitSpec(name="Ring", canvas_w=400, canvas_h=300, platform="SOI")
        circuit.add_device(DeviceSpec("gc1", "grating_coupler", 10, 10))
        circuit.add_device(DeviceSpec("wg1", "strip_waveguide", 200, 0.5))
        circuit.add_device(DeviceSpec("ring1", "ring_resonator", 30, 30))
        circuit.add_device(DeviceSpec("gc2", "grating_coupler", 10, 10))
        circuit.add_connection("gc1", "out", "wg1", "in")
        circuit.add_connection("wg1", "out", "ring1", "bus_in")
        circuit.add_connection("ring1", "bus_out", "gc2", "in")
        return circuit
    if preset_id == "clements_4x4":
        from polaris.data.benchmarks import build_clements

        return build_clements(n=4, platform="SOI")
    raise ValueError(f"未知预设: {preset_id}")


def _run_pipeline(preset_id: str, router_type: str = "default") -> dict:
    """运行布局布线流水线，返回结果 dict。"""
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    circuit = _build_circuit(preset_id)
    config = PipelineConfig(router_type=router_type)
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)

    placements = []
    for name, pl in result.get("placements", {}).items():
        placements.append(
            {"name": name, "x": pl["x"], "y": pl["y"], "w": pl["w"], "h": pl["h"]}
        )

    paths = []
    for conn_key, wp in result.get("paths", {}).items():
        paths.append(
            {
                "connection": conn_key,
                "points": wp.points if hasattr(wp, "points") else wp.get("points", []),
                "length_um": wp.length_um if hasattr(wp, "length_um") else wp.get("length_um", 0),
                "loss_db": wp.loss_db if hasattr(wp, "loss_db") else wp.get("loss_db", 0),
            }
        )

    return {
        "preset": preset_id,
        "n_devices": len(placements),
        "n_paths": len(paths),
        "placements": placements,
        "paths": paths,
        "canvas_w": circuit.canvas_w,
        "canvas_h": circuit.canvas_h,
        "total_wire_length": result.get("total_wire_length_um", 0),
        "routing_success_rate": result.get("routing_success_rate", 0),
        "drc_violations": result.get("drc_violations", 0),
    }


class PolarisHTTPRequestHandler(BaseHTTPRequestHandler):
    """PoLaRIS HTTP 请求处理器。"""

    def log_message(self, format: str, *args) -> None:
        logger.debug("HTTP %s - %s", self.address_string(), format % args)

    def _send_json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, filepath: Path) -> None:
        if not filepath.exists() or not filepath.is_file():
            self.send_error(404, "File not found")
            return
        ext = filepath.suffix.lower()
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".png": "image/png",
            ".svg": "image/svg+xml",
        }
        content_type = content_types.get(ext, "application/octet-stream")
        body = filepath.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/health":
            self._send_json({"status": "ok", "service": "PoLaRIS Web UI"})
            return
        if path == "/api/presets":
            self._send_json({"presets": _get_presets()})
            return

        if path == "/" or path == "":
            path = "/index.html"
        static_path = _STATIC_DIR / path.lstrip("/")
        self._send_static(static_path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/run":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                params = json.loads(body) if body else {}
                preset_id = params.get("preset", "mzi")
                router_type = params.get("router_type", "default")
                result = _run_pipeline(preset_id, router_type)
                self._send_json({"success": True, "result": result})
            except Exception as e:
                logger.error("Pipeline 运行失败: %s\n%s", e, traceback.format_exc())
                self._send_json(
                    {"success": False, "error": str(e), "traceback": traceback.format_exc()},
                    code=500,
                )
            return

        self.send_error(404, "Not found")


class WebServer:
    """PoLaRIS Web UI 服务器。

    Args:
        host: 监听地址（默认 0.0.0.0）。
        port: 监听端口（默认 8000）。
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self, blocking: bool = True) -> None:
        """启动服务器。

        Args:
            blocking: True 为阻塞运行，False 为后台线程运行。
        """
        self._server = HTTPServer((self.host, self.port), PolarisHTTPRequestHandler)
        logger.info("PoLaRIS Web UI 启动: http://%s:%s", self.host, self.port)
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(
                target=self._server.serve_forever, daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        """停止服务器。"""
        if self._server:
            self._server.shutdown()
            self._server = None
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """启动 PoLaRIS Web UI 服务器（阻塞）。"""
    server = WebServer(host=host, port=port)
    server.start(blocking=True)
