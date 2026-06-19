"""PoLaRIS 命令行入口：``python -m polaris``。

来源:
- 端到端流水线: src/polaris/pipeline/__init__.py
"""

from __future__ import annotations

import sys

from polaris.pipeline import main

if __name__ == "__main__":
    sys.exit(main())
