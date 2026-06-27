"""R20 路标：Synopsys OptoDesigner 版图驱动设计对齐模块。

对齐 Synopsys OptoDesigner 的版图驱动设计能力，实现 Design Intent 机制
（单层设计 → 多层掩膜自动生成）、PyCell API（Python 脚本驱动参数化版图）、
Any-angle flexConnector（任意角度弹性连接器）、层级化设计与 PDAflow 互操作。

## 学术依据

- Synopsys OptoDesigner 官方文档
  URL: https://www.synopsys.com/photonic-solutions/optocompiler/optodesigner.html
- Synopsys Photonic Solutions Newsletter 2023.12（PyCell + Any-angle flexConnector）
  URL: https://www.synopsys.com/photonic-solutions/e-news/2023-december.html
- PDAflow API 标准（光子设计自动化互操作标准）
  URL: http://pdaflow.org/
- Weste & Harris, "CMOS VLSI Design: A Circuits and Systems Perspective",
  4th ed., Addison-Wesley, 2010（层级化设计）
- Farin, "Curves and Surfaces for CAGD", 5th ed., 2002（贝塞尔曲线）

## 合规性

- project_rules.md 规则 14.1: 禁止 fall-back / 假数据 / mock
- project_rules.md 规则 18: 所有参数来自公开文献，标注来源 URL
- project_rules.md 规则 7.1: 文件 < 600 行
- R20 路标: docs/roundmap/R20.md

## 架构说明（facade 模式）

本文件为 facade 入口，实现已按功能拆分到子模块，外部 import 路径保持不变：
- ``optodesigner_design_intent`` — Design Intent 机制 + 工艺规则 + URL 常量
- ``optodesigner_pycell`` — PyCell + PyCellFactory 参数化版图
- ``optodesigner_flexconnector`` — Any-angle flexConnector 贝塞尔连接器
- ``optodesigner_hierarchy`` — 层级化设计（unlimited hierarchy levels）
- ``optodesigner_pdaflow`` — PDAflow 互操作（SPT 导出 + 字典转换）
"""

from __future__ import annotations

from polaris.pdk.optodesigner_design_intent import (  # noqa: F401
    DesignIntent,
    DesignIntentEngine,
    TechnologyRule,
)
from polaris.pdk.optodesigner_flexconnector import FlexConnector  # noqa: F401
from polaris.pdk.optodesigner_hierarchy import HierarchyDesign  # noqa: F401
from polaris.pdk.optodesigner_pdaflow import PDAflowInterop  # noqa: F401
from polaris.pdk.optodesigner_pycell import (  # noqa: F401
    PyCell,
    PyCellFactory,
)

__all__ = [
    "DesignIntent",
    "DesignIntentEngine",
    "FlexConnector",
    "HierarchyDesign",
    "PDAflowInterop",
    "PyCell",
    "PyCellFactory",
    "TechnologyRule",
]
