"""pycopy — 自研复刻工具统一包（规则 4）。

本包是所有 pyCopyxx 复刻工具的统一入口。仅保留真正需要复刻的工具，
即原工具因上游兼容性问题无法在目标环境安装时才复刻。

子包:
- pyCopySiPANN: SiPANN 复刻（src/polaris/sim/models.py）
  原因: SiPANN 依赖 tensorflow，tensorflow 无 Python 3.14 wheel（上游兼容性问题）

已删除的复刻品（2026-06-21 清理，原因：原工具可直接 pip 安装且活跃维护）:
- pyCopyTorch: torch 活跃维护（2.12.0, 2026-05-13），直接用原工具
- pyCopySAX: sax 活跃维护（0.15.12, 2025-07-18），直接用原工具
- pyCopyKLayout: klayout 极度活跃（0.30.9, 2026-06-20），直接用原工具
- pyCopyMEEP/pyCopyFemwell/pyCopyMeow: 预留空包，项目未使用，删除
"""

__all__ = [
    "pyCopySiPANN",
]
