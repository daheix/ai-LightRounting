"""PoLaRIS Web Server — HTTP API + 静态文件服务（阶段 F4）。

使用 Python 内置 http.server 实现 REST API + 静态前端服务，无需 Flask/FastAPI。
支持电路预设选择、一键布局布线、结果可视化、DRC 报告、GDS 导出、
端到端 Demo Showcase 全流程演示。

API 端点:
- GET  /api/health                          — 健康检查
- GET  /api/presets                         — 列出预设电路
- POST /api/run                             — 运行布局布线流水线
- POST /api/showcase/run                    — 启动端到端 Demo Showcase 全流程
- GET  /api/showcase/report/{run_id}        — 查询 Showcase 汇总报告
- GET  /api/showcase/stages/{run_id}/{stage_id} — 查询 Showcase 单阶段结果
- POST /api/jobs                            — 提交作业（Recipe JSON 作为 body）
- GET  /api/jobs                            — 列出所有作业（可选 ?status= 过滤）
- GET  /api/jobs/{job_id}                   — 查询作业详情
- GET  /api/jobs/{job_id}/status            — 查询作业状态与进度
- POST /api/jobs/{job_id}/cancel            — 取消作业
- GET  /api/jobs/{job_id}/stages/{stage_id} — 查询阶段输出
- GET  /api/jobs/{job_id}/report            — 查询作业汇总报告

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- REST 设计规范: https://docs.python.org/3/library/http.server.html


## 补充文献（R02 学术诚信补齐）
- KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS 文档: https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from polaris_flow.scheduler import JobScheduler
    from polaris_flow.tracker import JobTracker

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"

# Showcase 运行状态字典: {run_id: {"status": str, "output_dir": str, "error": str|None}}
# R05 Bug 修复 v4.0-WEB-LOCK（第1轮迭代发现）:
# 原 _showcase_runs 全局字典无锁，后台线程写 + HTTP 线程读存在竞态。
# 改为 threading.Lock 保护所有读写操作。
_showcase_runs: dict[str, dict] = {}
_showcase_lock = threading.Lock()

# 全局作业调度器与追踪器（对齐 Cadence ADE-XL 作业队列模型）
# R05 Bug 修复 v4.0-WEB-LOCK: 懒初始化加锁，防止 ThreadingHTTPServer 下创建多实例
_global_scheduler: JobScheduler | None = None
_global_tracker: JobTracker | None = None
_global_lock = threading.Lock()


def _get_scheduler() -> JobScheduler:
    """获取全局作业调度器（懒初始化，线程安全）。

    首次调用时创建 JobScheduler 实例，注入标准 10 阶段执行函数，
    后续调用复用同一实例。对齐 Cadence ADE-XL 的全局作业队列模型。

    R05 Bug 修复 v4.0-WEB-LOCK: 加 _global_lock 双重检查锁定，
    防止 ThreadingHTTPServer 下多线程并发创建多个 scheduler 实例。
    文献: Python threading.Lock https://docs.python.org/3/library/threading.html#lock-objects
    文献: Double-checked locking https://en.wikipedia.org/wiki/Double-checked_locking
    """
    global _global_scheduler
    if _global_scheduler is None:
        with _global_lock:
            # 双重检查锁定：进入锁后再检查一次，防止多线程同时通过第一次检查
            if _global_scheduler is None:
                from polaris_flow.executors import STAGE_EXECUTORS
                from polaris_flow.scheduler import JobScheduler

                _global_scheduler = JobScheduler(
                    max_workers=4, stage_executors=STAGE_EXECUTORS
                )
    return _global_scheduler


def _get_tracker() -> JobTracker:
    """获取全局作业追踪器（懒初始化，线程安全）。

    首次调用时创建 JobTracker 实例，扫描 out/jobs 目录，
    后续调用复用同一实例。

    R05 Bug 修复 v4.0-WEB-LOCK: 加 _global_lock 双重检查锁定。
    """
    global _global_tracker
    if _global_tracker is None:
        with _global_lock:
            if _global_tracker is None:
                from polaris_flow.tracker import JobTracker

                _global_tracker = JobTracker(base_output_dir="out/jobs")
    return _global_tracker


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
    """构建 MZI 干涉仪电路。

    端口名对齐 PDK 定义：
    - mmi_1x2: in, out1, out2（来源: polaris.pdk.soi.couplers._make_mmi_1x2_ports）
    - mmi_2x2: in1, in2, out1, out2（来源: polaris.pdk.soi.couplers._make_mmi_2x2_ports）
    """
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="MZI",
        canvas_w=1000,
        canvas_h=600,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            DeviceSpec("mmi1", "mmi_1x2", 20, 10),
            # 波导 length 参数 = width_um（光传播方向为较长维度）
            # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
            DeviceSpec("wg1", "strip_waveguide", 100, 0.5, params={"length": 100.0, "length_um": 100.0}),
            DeviceSpec("wg2", "strip_waveguide", 120, 0.5, params={"length": 120.0, "length_um": 120.0}),
            DeviceSpec("mmi2", "mmi_2x2", 20, 10),
        ],
        connections=[
            ("gc1", "out", "mmi1", "in"),
            ("mmi1", "out1", "wg1", "in"),
            ("mmi1", "out2", "wg2", "in"),
            ("wg1", "out", "mmi2", "in1"),
            ("wg2", "out", "mmi2", "in2"),
        ],
    )


def _ring_circuit():
    """构建微环谐振器电路。"""
    from polaris_core.specs import CircuitSpec, DeviceSpec

    return CircuitSpec(
        name="Ring",
        canvas_w=800,
        canvas_h=600,
        devices=[
            DeviceSpec("gc1", "grating_coupler", 10, 10),
            # 波导 length 参数 = width_um（光传播方向为较长维度）
            # 来源: SiEPIC EBeam PDK strip waveguide 几何约定
            DeviceSpec("wg1", "strip_waveguide", 200, 0.5, params={"length": 200.0, "length_um": 200.0}),
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
        raise ImportError(
            "_build_circuit('clements_4x4') 需要 polaris_orchestrator 子模块提供 "
            "_default_demo_circuit（v5.0 polaris_orchestrator 未迁移该函数，"
            "R03 禁止 fall-back）。请在 polaris_gui 内联构建 Clements 电路。"
        )
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


def _run_pipeline(preset_id: str, router_type: str = "curvy") -> dict:
    """运行布局布线流水线，返回结果 dict。

    默认使用 curvy router（euler 弯曲布线），自动满足弯曲半径约束。
    "default" 映射到 "curvy"，因为 A* 网格布线的直角弯半径 < min_bend_radius，
    会产生 DRC 违规。curvy router 用 euler 曲线替换直角弯，损耗更低。

    来源: LiDAR ISPD'25 curvy-aware routing
      https://dl.acm.org/doi/10.1145/3698364.3705355

    Raises:
        ImportError: polaris_orchestrator 未迁移 IntegratedPipeline（R03 禁止 fall-back）。
    """
    raise ImportError(
        "_run_pipeline 需要 polaris_orchestrator 子模块提供 "
        "IntegratedPipeline/PipelineConfig（v5.0 polaris_orchestrator 未迁移"
        "一体化流水线类，R03 禁止 fall-back）。"
        "请改用 polaris_flow 调度器执行布局布线流水线。"
    )


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
        showcase_dir = Path(__file__).parent.parent.parent.parent.parent / "examples" / "e2e_showcase"
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

        # R05 Bug 修复 v4.0-WEB-LOCK: _showcase_runs 写操作加锁
        with _showcase_lock:
            _showcase_runs[run_id]["status"] = "done"
        logger.info("Showcase 运行完成: run_id=%s", run_id)
    except Exception as e:
        logger.error(
            "Showcase 运行失败: run_id=%s, 错误: %s\n%s",
            run_id, e, traceback.format_exc(),
        )
        # R05 Bug 修复 v4.0-WEB-LOCK: _showcase_runs 写操作加锁
        with _showcase_lock:
            _showcase_runs[run_id]["status"] = "failed"
            _showcase_runs[run_id]["error"] = str(e)


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
        """HTTP GET 路由分发（重构后圈复杂度 ≤15）。

        路由优先级：简单精确匹配 > showcase > 作业管理 > 静态文件兜底。
        """
        parsed = urlparse(self.path)
        path = parsed.path
        # 优先级 1: 简单精确匹配
        if self._try_simple_get(path):
            return
        # 优先级 2: showcase 子路径
        if self._try_showcase_get(path):
            return
        # 优先级 3: 作业管理 API（对齐 Cadence ADE-XL 作业队列查询）
        if self._try_jobs_get(path, parsed):
            return
        # 默认: 静态文件
        self._serve_static_index(path)

    def _try_simple_get(self, path: str) -> bool:
        """处理简单精确匹配路由，返回是否命中。"""
        if path == "/api/health":
            self._send_json({"status": "ok", "service": "PoLaRIS Web UI"})
            return True
        if path == "/api/presets":
            self._send_json({"presets": _get_presets()})
            return True
        if path == "/showcase.html" or path == "/showcase":
            self._send_static(_STATIC_DIR / "showcase.html")
            return True
        return False

    def _try_showcase_get(self, path: str) -> bool:
        """处理 showcase 子路径，返回是否命中。"""
        if path.startswith("/api/showcase/report/"):
            run_id = path.split("/")[-1]
            self._handle_showcase_report(run_id)
            return True
        if path.startswith("/api/showcase/stages/"):
            self._handle_showcase_stages_path(path)
            return True
        return False

    def _handle_showcase_stages_path(self, path: str) -> None:
        """解析 /api/showcase/stages/{run_id}/{stage_id} 并分发。"""
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

    def _try_jobs_get(self, path: str, parsed) -> bool:
        """处理作业管理 API，返回是否命中。

        路由优先级：精确匹配 > 子路径（status/report/stages）> 通配 {job_id}。
        """
        if path == "/api/jobs":
            self._handle_jobs_list(parsed)
            return True
        if path.startswith("/api/jobs/"):
            self._route_jobs_subpath(path)
            return True
        return False

    def _handle_jobs_list(self, parsed) -> None:
        """列出所有作业，可选 ?status=running 过滤。"""
        status_filter = (
            parsed.query.replace("status=", "")
            if "status=" in parsed.query
            else None
        )
        jobs = _get_tracker().list_jobs(status=status_filter)
        self._send_json({"jobs": jobs})

    def _route_jobs_subpath(self, path: str) -> None:
        """作业子路径分发：status/report/stages/通配。"""
        if path.endswith("/status"):
            self._handle_jobs_status(path)
            return
        if path.endswith("/report"):
            self._handle_jobs_report(path)
            return
        if "/stages/" in path:
            self._handle_jobs_stages(path)
            return
        # 通配：查询作业详情（返回完整 job_dict）
        self._handle_jobs_detail(path)

    def _handle_jobs_status(self, path: str) -> None:
        """查询作业状态与进度。"""
        job_id = path.split("/")[3]
        job_meta = _get_tracker().get_job(job_id)
        if job_meta is None:
            self._send_json({"error": f"作业 {job_id} 不存在"}, code=404)
            return
        self._send_json({
            "job_id": job_id,
            "status": job_meta.get("status"),
            "progress": job_meta.get("progress"),
        })

    def _handle_jobs_report(self, path: str) -> None:
        """查询作业汇总报告（读取 reports/summary.json）。"""
        job_id = path.split("/")[3]
        report_path = Path("out/jobs") / job_id / "reports" / "summary.json"
        if not report_path.exists():
            self._send_json(
                {"error": f"作业 {job_id} 的汇总报告不存在"}, code=404
            )
            return
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            self._send_json(
                {"error": f"读取作业 {job_id} 汇总报告失败: {e}"},
                code=500,
            )
            return
        self._send_json(report)

    def _handle_jobs_stages(self, path: str) -> None:
        """查询阶段输出：/api/jobs/{job_id}/stages/{stage_id}。"""
        parts = path.split("/")
        job_id = parts[3]
        try:
            stage_id = int(parts[5])
        except (IndexError, ValueError):
            idx_str = parts[5] if len(parts) > 5 else "缺失"
            self._send_json(
                {"error": f"无效的阶段 ID: {idx_str}"},
                code=400,
            )
            return
        result = _get_tracker().get_stage_result(job_id, stage_id)
        if result is None:
            self._send_json(
                {"error": f"作业 {job_id} 阶段 {stage_id} 结果不存在"},
                code=404,
            )
            return
        self._send_json(result)

    def _handle_jobs_detail(self, path: str) -> None:
        """通配查询作业详情（返回完整 job_dict）。"""
        job_id = path.split("/")[3]
        job_meta = _get_tracker().get_job(job_id)
        if job_meta is None:
            self._send_json({"error": f"作业 {job_id} 不存在"}, code=404)
            return
        self._send_json(job_meta)

    def _serve_static_index(self, path: str) -> None:
        """默认静态文件服务，根路径映射到 index.html。"""
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
                # R05 Bug 修复 v4.0-WEB-SEC（第1轮迭代发现）:
                # 原代码返回 traceback 给客户端，泄露服务器文件路径、Python 版本、
                # 代码结构、依赖库版本，攻击者可据此构造针对性攻击。
                # 修复：traceback 仅写入服务器日志，客户端只收到通用错误消息。
                # 规则: R02 学术诚信 / R05 Bug 必修
                # 文献: OWASP Error Handling https://owasp.org/www-community/Improper_Error_Handling
                # 文献: CWE-209 Information Exposure Through Error https://cwe.mitre.org/data/definitions/209.html
                logger.error("Pipeline 运行失败: %s\n%s", e, traceback.format_exc())
                self._send_json(
                    {
                        "success": False,
                        "error": "内部错误，请联系支持（详见服务器日志）",
                        "error_type": type(e).__name__,
                    },
                    code=500,
                )
            return
        if path == "/api/showcase/run":
            self._handle_showcase_run()
            return

        # === 作业管理 API（对齐 Cadence ADE-XL 作业提交与取消）===
        # 路由优先级：精确匹配 /api/jobs > 子路径 /api/jobs/{job_id}/cancel
        if path == "/api/jobs":
            # 提交作业：接收 Recipe JSON，创建 Job + Workspace，提交到调度器
            content_length = int(self.headers.get("Content-Length", 0))
            body = (
                self.rfile.read(content_length)
                if content_length > 0
                else b"{}"
            )
            try:
                params = json.loads(body) if body else {}
                from polaris_flow.job import Job
                from polaris_flow.recipe import Recipe
                from polaris_flow.workspace import Workspace

                recipe = Recipe.from_dict(params)
                job_id = Job.generate_job_id()
                ws = Workspace(recipe.output_dir, job_id)
                job = Job(job_id=job_id, recipe=recipe, workspace=ws)
                scheduler = _get_scheduler()
                scheduler.submit(job)
                logger.info("作业已提交: job_id=%s", job_id)
                self._send_json({"job_id": job_id, "status": "queued"})
            except Exception as e:
                logger.error(
                    "提交作业失败: %s\n%s", e, traceback.format_exc()
                )
                self._send_json({"error": str(e)}, code=500)
            return
        if path.startswith("/api/jobs/") and path.endswith("/cancel"):
            # 取消作业：调用 scheduler.cancel(job_id)
            job_id = path.split("/")[3]
            scheduler = _get_scheduler()
            success = scheduler.cancel(job_id)
            if success:
                self._send_json({"job_id": job_id, "status": "cancelled"})
            else:
                self._send_json(
                    {"error": f"无法取消作业 {job_id}（不存在或已终态）"},
                    code=400,
                )
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
        # R05 Bug 修复 v4.0-WEB-LOCK: _showcase_runs 写操作加锁
        with _showcase_lock:
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
        # R05 Bug 修复 v4.0-WEB-LOCK: 读操作加锁，防止后台线程同时写
        with _showcase_lock:
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
        # R05 Bug 修复 v3.3-WEB-1: 增加 n_skipped 计数器
        # 原 summary 只含 n_done/n_failed/n_total，丢失无效行计数
        # 规则: R02 学术诚信 / R03 禁止静默吞异常（warning 已记录但需在 summary 体现）
        # 文献: JSON Lines 规范 http://jsonlines.org/
        # 文献: REST API 错误处理 https://datatracker.ietf.org/doc/html/rfc7807
        n_skipped = 0
        if jsonl_path.exists():
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            stages.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            n_skipped += 1
                            logger.warning(
                                "跳过无效 JSONL 行 (#%d): %s | error=%s",
                                n_skipped, line[:100], e,
                            )

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
                "n_skipped": n_skipped,
                "total_duration_s": round(total_duration, 4),
            },
        })

    def _handle_showcase_stage(self, run_id: str, stage_id: int) -> None:
        """处理 GET /api/showcase/stages/{run_id}/{stage_id}: 返回单阶段结果。"""
        # R05 Bug 修复 v4.0-WEB-LOCK: 读操作加锁
        with _showcase_lock:
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
        # R05 Bug 修复 v3.3-WEB-1: 原 except: continue 是静默 fall-back，改为 warning
        # 规则: R03 禁止静默吞异常 / R02 学术诚信
        # 文献: Python logging 最佳实践 https://docs.python.org/3/howto/logging.html
        if jsonl_path.exists():
            with jsonl_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        log = json.loads(line)
                    except json.JSONDecodeError as e:
                        logger.warning(
                            "showcase stage 查找：跳过无效 JSONL 行: %s | error=%s",
                            line[:100], e,
                        )
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
        # R05 Bug 修复 v4.0-WEB-THREAD（第1轮迭代发现）:
        # 原 HTTPServer 单线程，/api/run 同步运行流水线时所有其他请求阻塞，
        # 客户端 UI 冻结数十秒。改用 ThreadingHTTPServer 每请求一线程。
        # 配合 _global_lock + _showcase_lock 保证线程安全。
        # 规则: R05 Bug 必修
        # 文献: Python ThreadingHTTPServer https://docs.python.org/3/library/http.server.html#http.server.ThreadingHTTPServer
        # 文献: socketserver.ThreadingMixIn https://docs.python.org/3/library/socketserver.html#socketserver.ThreadingMixIn
        self._server = ThreadingHTTPServer(
            (self.host, self.port), PolarisHTTPRequestHandler
        )
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
