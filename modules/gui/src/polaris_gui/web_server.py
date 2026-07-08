"""PoLaRIS Web Server — HTTP API + 静态文件服务（阶段 F4）— Facade 层。

使用 Python 内置 http.server 实现 REST API + 静态前端服务，无需 Flask/FastAPI。
支持电路预设选择、一键布局布线、结果可视化、DRC 报告、GDS 导出、
端到端 Demo Showcase 全流程演示。

本文件为 facade 层，从拆分的子模块聚合（R11 质量门禁：文件≤800行）：
- handlers.py: 业务逻辑（全局状态/调度器/追踪器/预设/Showcase 后台执行）
- routes.py: PolarisHTTPRequestHandler（HTTP 路由分发与请求/响应处理）
- web_server.py（本文件）: WebServer 类 + run_server() + 重新导出

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

补充文献（R02 学术诚信补齐）:
- KLayout DRC 文档: https://www.klayout.org/doc-qt5/manual/drc_runsets.html
- KLayout LVS 文档: https://www.klayout.org/downloads/master/doc-qt5/manual/lvs_compare.html
- Python ThreadingHTTPServer: https://docs.python.org/3/library/http.server.html#http.server.ThreadingHTTPServer
- socketserver.ThreadingMixIn: https://docs.python.org/3/library/socketserver.html#socketserver.ThreadingMixIn

合规: R02 学术诚信 / R03 禁止 fall-back / R05 Bug 必修。
"""

from __future__ import annotations

import logging
import threading
from http.server import ThreadingHTTPServer

# 从拆分子模块重新导出，保持向后兼容
# （polaris_gui.__init__ lazy 导出 WebServer/run_server；
#   polaris_flow.stage_input 导入 _build_circuit）
from polaris_gui.handlers import (
    _PRESET_BUILDERS,
    _SHOWCASE_SUBDIRS,
    _STATIC_DIR,
    _build_circuit,
    _extract_paths,
    _extract_placements,
    _get_presets,
    _get_scheduler,
    _get_tracker,
    _global_lock,
    _global_scheduler,
    _global_tracker,
    _mzi_circuit,
    _ring_circuit,
    _run_pipeline,
    _run_showcase_background,
    _showcase_lock,
    _showcase_runs,
)
from polaris_gui.routes import PolarisHTTPRequestHandler

logger = logging.getLogger(__name__)


class WebServer:
    """PoLaRIS Web UI 服务器。

    Args:
        host: 监听地址（默认 0.0.0.0）。
        port: 监听端口（默认 8000）。
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self._server: ThreadingHTTPServer | None = None
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


__all__ = [
    # 服务器类与入口
    "WebServer",
    "run_server",
    "PolarisHTTPRequestHandler",
    # 重新导出业务函数（向后兼容）
    "_build_circuit",
    "_get_presets",
    "_get_scheduler",
    "_get_tracker",
    "_run_pipeline",
    "_run_showcase_background",
    "_mzi_circuit",
    "_ring_circuit",
    "_extract_placements",
    "_extract_paths",
    # 重新导出全局状态（向后兼容）
    "_STATIC_DIR",
    "_showcase_runs",
    "_showcase_lock",
    "_global_scheduler",
    "_global_tracker",
    "_global_lock",
    "_SHOWCASE_SUBDIRS",
    "_PRESET_BUILDERS",
]


if __name__ == "__main__":
    run_server()

