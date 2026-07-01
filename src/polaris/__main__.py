"""PoLaRIS 命令行入口：``python -m polaris``。

来源:
- 端到端流水线: src/polaris/pipeline/__init__.py

文献来源（≥5，规则 R02 学术诚信）：
1. Python Packaging Authority, "Entry Points & Console Scripts," Python Packaging
   User Guide (2024).
   https://packaging.python.org/en/latest/specifications/entry-points/
2. Smith K, "Click 8.1 Python CLI framework documentation" (2024).
   https://click.palletsprojects.com/en/8.1.x/
3. gdsfactory CLI 实现参考 (2024).
   https://gdsfactory.readthedocs.io/en/latest/
4. SiEPIC Tools / KLayout CLI 集成范式 (UBC, 2023).
   https://github.com/SiEPIC/SiEPIC-tools
5. Luceda IPKISS 命令行设计流程参考 (2024).
   https://academy.lucedaphotonics.com/
"""

from __future__ import annotations

import sys

from polaris.pipeline import main

if __name__ == "__main__":
    sys.exit(main())
