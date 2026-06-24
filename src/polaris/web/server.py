"""PoLaRIS Web Server — HTTP API + 静态文件服务（阶段 F4）。

使用 Python 内置 http.server 实现 REST API + 静态前端服务，无需 Flask/FastAPI。
<<<<<<< HEAD
支持电路预设选择、一键布局布线、结果可视化、DRC 报告、GDS 导出、
端到端 Demo Showcase 全流程演示。

API 端点:
- GET  /api/health                          — 健康检查
- GET  /api/presets                         — 列出预设电路
- POST /api/run                             — 运行布局布线流水线
- POST /api/showcase/run                    — 启动端到端 Demo Showcase 全流程
- GET  /api/showcase/report/{run_id}        — 查询 Showcase 汇总报告
- GET  /api/showcase/stages/{run_id}/{stage_id} — 查询 Showcase 单阶段结果
=======
支持电路预设选择、一键布局布线、结果可视化、DRC 报告、GDS 导出。

API 端点:
- GET  /api/presets        — 列出预设电路
- POST /api/run            — 运行布局布线流水线
- GET  /api/health         — 健康检查
>>>>>>> trae/solo-agent-pkVjID

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- REST 设计规范: https://docs.python.org/3/library/http.server.html
"""

from __future__ import annotations

import json
import logging
<<<<<<< HEAD
import sys
import threading
import traceback
from datetime import datetime
=======
import threading
import traceback
>>>>>>> trae/solo-agent-pkVjID
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

<<<<<<< HEAD
# Showcase 运行状态字典: {run_id: {"status": str, "output_dir": str, "error": str|None}}
_showcase_runs: dict[str, dict] = {}

=======
>>>>>>> trae/solo-agent-pkVjID

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


<<<<<<< HEAD
# Showcase 输出子目录列表
_SHOWCASE_SUBDIRS = ["logs", "gds", "verilog_a", "spice", "reports"]


def _run_showcase_background(run_id: str, output_dir: str) -> None:
    """在后台线程中运行端到端 Demo Showcase 全流程。

    顺序执行 9 个阶段，每阶段用 StageLogger 包裹，结构化日志写入
    output_dir/logs/showcase.jsonl。运行前清空 JSONL 文件，避免历史记录污染。

    Args:
        run_id: 运行 ID（时间戳格式 YYYYMMDD_HHMMSS）。
        output_dir: 输出目录路径。
    """
    try:
        # 添加 examples/e2e_showcase 到 sys.path，使 stages/ 与同级模块可被导入
        showcase_dir = Path(__file__).parent.parent.parent.parent / "examples" / "e2e_showcase"
        if str(showcase_dir) not in sys.path:
            sys.path.insert(0, str(showcase_dir))

        from logging_config import StageLogger, setup_logging  # noqa: E402
        from stages import (  # noqa: E402
            stage1_pdk_catalog,
            stage2_circuit_spec,
            stage3_ai_placement,
            stage4_routing,
            stage5_simulation,
            stage6_drc_lvs,
            stage7_gds_export,
            stage8_opto_electrical,
            stage9_quantum_photonics,
        )

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for subdir in _SHOWCASE_SUBDIRS:
            (out_dir / subdir).mkdir(parents=True, exist_ok=True)

        # 清空 JSONL 日志文件，避免历史记录污染本次运行结果
        jsonl_path = out_dir / "logs" / "showcase.jsonl"
        jsonl_path.write_text("", encoding="utf-8")

        setup_logging(out_dir)

        stages = [
            (1, "PDK 器件目录展示", stage1_pdk_catalog),
            (2, "电路规格定义", stage2_circuit_spec),
            (3, "AI 布局", stage3_ai_placement),
            (4, "智能布线", stage4_routing),
            (5, "仿真验证", stage5_simulation),
            (6, "DRC/LVS 验证", stage6_drc_lvs),
            (7, "GDS 导出", stage7_gds_export),
            (8, "光电协同", stage8_opto_electrical),
            (9, "量子光子验证", stage9_quantum_photonics),
        ]

        for stage_id, stage_name, stage_module in stages:
            with StageLogger(stage_id, stage_name, out_dir) as sl:
                # 记录输入参数（修复 P0: inputs 字段始终为空）
                sl.log_input("output_dir", str(out_dir))
                sl.log_input("stage_module", stage_module.__name__)
                result = stage_module.run(out_dir)
                if result:
                    for key, value in result.items():
                        sl.log_output(key, value)

        _showcase_runs[run_id]["status"] = "done"
        logger.info("Showcase 运行完成: run_id=%s", run_id)
    except Exception as e:
        logger.error(
            "Showcase 运行失败: run_id=%s, 错误: %s\n%s",
            run_id, e, traceback.format_exc(),
        )
        _showcase_runs[run_id]["status"] = "failed"
        _showcase_runs[run_id]["error"] = str(e)


=======
>>>>>>> trae/solo-agent-pkVjID
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
<<<<<<< HEAD
        if path.startswith("/api/showcase/report/"):
            run_id = path.split("/")[-1]
            self._handle_showcase_report(run_id)
            return
        if path.startswith("/api/showcase/stages/"):
            parts = path.split("/")
            # 路径格式: /api/showcase/stages/{run_id}/{stage_id}
            run_id = parts[-2]
            try:
                stage_id = int(parts[-1])
            except ValueError:
                self._send_json(
                    {"success": False, "error": f"无效的阶段 ID: {parts[-1]}"},
                    code=400,
                )
                return
            self._handle_showcase_stage(run_id, stage_id)
            return
        if path == "/showcase.html" or path == "/showcase":
            self._send_static(_STATIC_DIR / "showcase.html")
            return
=======
>>>>>>> trae/solo-agent-pkVjID

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
<<<<<<< HEAD
        if path == "/api/showcase/run":
            self._handle_showcase_run()
            return

        self.send_error(404, "Not found")

    def _handle_showcase_run(self) -> None:
        """处理 POST /api/showcase/run: 启动后台 Showcase 全流程。"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            params = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_json({"success": False, "error": "请求体不是有效的 JSON"}, code=400)
            return
        output_dir = params.get("output_dir", "out/e2e_showcase_web")

        run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        _showcase_runs[run_id] = {
            "status": "running",
            "output_dir": output_dir,
            "error": None,
        }

        thread = threading.Thread(
            target=_run_showcase_background,
            args=(run_id, output_dir),
            daemon=True,
        )
        thread.start()

        logger.info("启动 Showcase: run_id=%s, output_dir=%s", run_id, output_dir)
        self._send_json({
            "success": True,
            "run_id": run_id,
            "output_dir": output_dir,
            "message": f"Showcase 已启动，使用 GET /api/showcase/report/{run_id} 查询结果",
        })

    def _handle_showcase_report(self, run_id: str) -> None:
        """处理 GET /api/showcase/report/{run_id}: 返回汇总报告。"""
        run_info = _showcase_runs.get(run_id)
        if run_info is None:
            self._send_json(
                {"success": False, "error": f"未知 run_id: {run_id}"},
                code=404,
            )
            return
        output_dir = run_info.get("output_dir", "out/e2e_showcase_web")

        jsonl_path = Path(output_dir) / "logs" / "showcase.jsonl"
        stages: list[dict] = []
        if jsonl_path.exists():
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            stages.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning("跳过无效 JSONL 行: %s", line[:100])

        n_done = sum(1 for s in stages if s.get("status") == "done")
        n_failed = sum(1 for s in stages if s.get("status") == "failed")
        total_duration = sum(s.get("duration_s", 0) for s in stages)

        self._send_json({
            "success": True,
            "run_id": run_id,
            "status": run_info.get("status", "unknown"),
            "error": run_info.get("error"),
            "stages": stages,
            "summary": {
                "n_done": n_done,
                "n_failed": n_failed,
                "n_total": len(stages),
                "total_duration_s": round(total_duration, 4),
            },
        })

    def _handle_showcase_stage(self, run_id: str, stage_id: int) -> None:
        """处理 GET /api/showcase/stages/{run_id}/{stage_id}: 返回单阶段结果。"""
        run_info = _showcase_runs.get(run_id)
        if run_info is None:
            self._send_json(
                {"success": False, "error": f"未知 run_id: {run_id}"},
                code=404,
            )
            return
        output_dir = run_info.get("output_dir", "out/e2e_showcase_web")

        jsonl_path = Path(output_dir) / "logs" / "showcase.jsonl"
        stage_data: dict | None = None
        if jsonl_path.exists():
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if log.get("stage_id") == stage_id:
                        stage_data = log
                        break

        if stage_data is None:
            self._send_json(
                {
                    "success": False,
                    "error": f"阶段 {stage_id} 未找到（可能尚未运行或 run_id 无效）",
                },
                code=404,
            )
            return

        self._send_json({
            "success": True,
            "run_id": run_id,
            **stage_data,
        })

=======

        self.send_error(404, "Not found")

>>>>>>> trae/solo-agent-pkVjID

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


if __name__ == "__main__":
    run_server()
