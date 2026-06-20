"""PoLaRIS Web UI — 商业化前端（阶段 F4）。

提供基于 HTTP 的 Web 界面，支持电路选择、一键布局布线、可视化渲染、
DRC 报告查看与 GDS 导出。使用 Python 内置 http.server，无需额外依赖。

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- OpenPreview 部署: 项目规则 2.3.1 产品化
"""

from __future__ import annotations

from polaris.web.server import WebServer, run_server

__all__ = ["WebServer", "run_server"]
