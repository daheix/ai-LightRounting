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


def _mzi_circuit():
    """构建 MZI 干涉仪电路。"""
    from polaris.data.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="MZI",
        canvas_w=500,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out0", "wg1", "in"),
            ("mmi1", "out1", "wg2", "in"),
            ("wg1", "out", "mmi2", "in0"),
            ("wg2", "out", "mmi2", "in1"),
        ],
    )


def _ring_circuit():
    """构建微环谐振器电路。"""
    from polaris.data.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="Ring",
        canvas_w=400,
        canvas_h=300,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("wg1", "strip_waveguide", 200, 0.5),
            DeviceSpec("ring1", "ring_resonator", 30, 30),
            DeviceSpec("gc2", "grating_coupler", 10, 10),
        ],
        connections=[
            ("gc1", "out", "wg1", "in"),
            ("wg1", "out", "ring1", "bus_in"),
            ("ring1", "bus_out", "gc2", "in"),
        ],
    )


_PRESET_BUILDERS = {
    "mzi": _mzi_circuit,
    "ring": _ring_circuit,
}


def _build_circuit(preset_id: str):
    """根据预设 ID 构建电路规格。"""
    if preset_id in _PRESET_BUILDERS:
        return _PRESET_BUILDERS[preset_id]()
    if preset_id == "clements_4x4":
        from polaris.pipeline.integrated import _default_demo_circuit

        return _default_demo_circuit()
    raise ValueError(f"未知预设: {preset_id}")


def _extract_placements(result) -> list[dict]:
    """从 PipelineResult 提取器件布局列表。"""
    placements = []
    for name, pl in result.placements.items():
        placements.append({"name": name, "x": pl["x"], "y": pl["y"], "w": pl["w"], "h": pl["h"]})
    return placements


def _extract_paths(result) -> list[dict]:
    """从 PipelineResult 提取布线路径列表。"""
    paths = []
    for conn_key, pts in result.paths.items():
        if hasattr(pts, "points"):
            points, length_um, loss_db = pts.points, pts.length_um, pts.loss_db
        elif isinstance(pts, list):
            points, length_um, loss_db = pts, 0.0, 0.0
        else:
            points = pts.get("points", [])
            length_um = pts.get("length_um", 0)
            loss_db = pts.get("loss_db", 0)
        paths.append(
            {
                "connection": conn_key,
                "points": points,
                "length_um": length_um,
                "loss_db": loss_db,
            }
        )
    return paths


def _run_pipeline(preset_id: str, router_type: str = "default") -> dict:
    """运行布局布线流水线，返回结果 dict。"""
    from polaris.pipeline.integrated import IntegratedPipeline, PipelineConfig

    circuit = _build_circuit(preset_id)
    config = PipelineConfig(router_type=router_type)
    pipeline = IntegratedPipeline(config=config)
    result = pipeline.run(circuit)
    return {
        "preset": preset_id,
        "circuit_name": result.circuit_name,
        "n_devices": result.n_devices,
        "n_connections": result.n_connections,
        "n_paths": len(result.paths),
        "placements": _extract_placements(result),
        "paths": _extract_paths(result),
        "canvas_w": circuit.canvas_w,
        "canvas_h": circuit.canvas_h,
        "total_loss_db": result.total_loss_db,
        "n_crossings": result.n_crossings,
        "drc_passed": result.drc_passed,
        "sim_iterations": result.sim_iterations,
        "report_path": result.report_path,
        "gds_path": result.gds_path,
        "success": result.success,
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
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
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
