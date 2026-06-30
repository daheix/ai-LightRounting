"""PoLaRIS Web UI — 商业化前端（阶段 F4）。

提供基于 HTTP 的 Web 界面，支持电路选择、一键布局布线、可视化渲染、
DRC 报告查看与 GDS 导出。使用 Python 内置 http.server，无需额外依赖。

来源:
- Python http.server: https://docs.python.org/3/library/http.server.html
- OpenPreview 部署: 项目规则 2.3.1 产品化

参考文献：
[1] Python Software Foundation. Python http.server module[EB/OL]. 2024. https://docs.python.org/3/library/http.server.html
[2] Mozilla Developer Network. WebGL API[EB/OL]. 2024. https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API
[3] Plotly Technologies Inc. Plotly Python graphing library[CP/OL]. 2024. https://plotly.com/python/getting-started/
[4] Flexcompute. Tidy3D web-based simulation platform[EB/OL]. 2024. https://docs.flexcompute.com/projects/tidy3d/en/stable/
[5] The OpenROAD Project. OpenROAD cloud: Web-based EDA[EB/OL]. 2024. https://theopenroadproject.org/
[6] gdsfactory. gdsfactory web viewer[EB/OL]. 2024. https://gdsfactory.github.io/gdsfactory/
"""

from __future__ import annotations

from polaris.web.server import WebServer, run_server

__all__ = ["WebServer", "run_server"]
