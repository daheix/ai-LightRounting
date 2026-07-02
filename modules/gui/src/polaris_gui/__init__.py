"""PoLaRIS GUI/Web/教育平台子模块（polaris-gui）。

从 v4 旧包 ``polaris.gui``（2 文件）+ ``polaris.web``（server.py）+
``polaris.platform``（education.py）迁移而来，提供商业级版图编辑器、
交互式 Macro IDE、HTTP Web Server 与教育平台能力。

## IPO 三段式说明

### I（Inputs）
- ``EditorConfig``：版图编辑器配置（网格/DBU/快捷键）
- ``DeviceInstance``：器件实例（位置/旋转/镜像/类别）
- ``DRCHighlight``：DRC 错误高亮区域
- ``LayoutObject``：交互式曲线多边形对象（顶点列表 + 类型）
- Web 请求体：电路预设 ID / Recipe JSON / Showcase run_id
- 教育文档语料（用于 TF-IDF/PageRank/KnowledgeGraph）

### P（Process）
1. 版图编辑器（``LayoutEditor``）：
   - 器件拖拽/旋转/删除/镜像，NumPy 仿射变换
   - 撤销/重做栈（``CommandStack``），DRC 错误高亮
   - 视图仿射变换（pan/zoom/rotate）
   - Web 预览（``render()`` → JSON）+ KLayout 深度编辑双模式（*创新*）
2. 交互式编辑（``interactive``）：
   - 曲线多边形编辑（Catmull-Rom / De Casteljau 样条）
   - ``SnapEngine`` 网格吸附，``AirlineRouter`` 航线布线
   - ``MacroIDE`` + ``MacroDebugger`` 宏脚本调试
   - ``ViewerGuard`` 视图边界保护
3. Web Server（``WebServer``）：
   - REST API（/api/health /api/presets /api/run /api/jobs 等）
   - 静态文件服务（Canvas 前端）
   - Showcase 端到端 Demo 全流程（依赖 polaris-flow）
4. 教育平台（``education``）：
   - ``KnowledgeGraph`` 知识图谱构建（NumPy 邻接矩阵）
   - ``TFIDFRetriever`` TF-IDF 文档检索 + MMR 多样性重排
   - ``PageRank`` 文档重要性排序（幂迭代）
   - ``IRT3PL`` 三参数逻辑斯蒂教学评估

### O（Outputs）
- ``LayoutEditor`` 场景图（JSON 序列化）+ KLayout 脚本
- ``CommandStack`` 操作历史（undo/redo）
- Web HTTP 响应（JSON）/ 静态文件
- ``TFIDFRetriever`` 检索结果（doc_id + score）
- ``PageRank`` 排序向量 / ``IRT3PL`` 能力估计（θ）

## 稳定 API

### 版图编辑器（无外部依赖，纯 NumPy）
- ``LayoutEditor`` / ``EditorConfig`` / ``DeviceInstance`` / ``DRCHighlight``

### 交互式编辑（无外部依赖，纯 stdlib + NumPy）
- ``ObjectType`` / ``LayoutObject`` / ``evaluate_object``
- ``CommandStack`` / ``SnapEngine`` / ``SnapResult``
- ``AirlineRouter`` / ``AirlineSegment``
- ``MacroIDE`` / ``MacroDebugger`` / ``ViewerGuard``

### Web Server（依赖 polaris-flow，lazy 导出）
- ``WebServer`` / ``run_server``

### 教育平台（无外部依赖，纯 NumPy）
- ``KnowledgeGraph`` / ``KGNode``
- ``TFIDFRetriever``
- ``PageRank``
- ``IRT3PL``

## 设计原则

- R03 禁止 fall-back：失败即 raise，无 return None/[] 假数据
- R04 不参与 GPU：纯 NumPy/SciPy 实现
- R05 无 TODO/FIXME 残留
- R13 不保留 v4 兼容：内部 import 全部改为 ``polaris_gui.*``
- 跨子模块依赖（polaris_flow/polaris_core）采用 lazy import，
  运行时按需加载，缺失则 raise ImportError（符合 R03）

## 来源（R02 学术诚信，≥5 个文献 URL）

- KLayout 官方文档（编辑器/脚本/DRC API）:
  https://www.klayout.de/doc-qt5/manual/editor.html
- Siemens L-Edit Photonics（版图驱动 PIC 设计 / 拖拽 / 光学 pin 对齐）:
  https://eda.sw.siemens.com/en-US/ic/ic-custom/photonic/l-edit-photonics/
- GDSFactory 9.x（参数化单元 + KLayout 集成 + DRC/LVS 流程）:
  https://gdsfactory.github.io/gdsfactory/
- Krinke et al., "Layout Verification Using Open-Source Software",
  ISPD 2024, DOI:10.1145/3626184.3635289:
  https://dl.acm.org/doi/pdf/10.1145/3626184.3635289
- SiEPIC-Tools Wiki（PinRec/DEVREC 网表提取格式 + 端口标记规范）:
  https://github.com/SiEPIC/SiEPIC-Tools/wiki
- Foley & Van Dam, "Computer Graphics: Principles and Practice",
  3rd ed., Addison-Wesley 2013（齐次坐标仿射变换推导来源）
- Gamma et al., "Design Patterns", Addison-Wesley 1994（MVC 分离）
- Python http.server（Web Server 实现）:
  https://docs.python.org/3/library/http.server.html
- Manning, Raghavan, Schütze. Introduction to Information Retrieval.
  2008. Cambridge University Press（TF-IDF / MMR）:
  https://nlp.stanford.edu/IR-book/
- Page, Brin, Motwani, Winograd. The PageRank Citation Ranking.
  1998. Stanford（PageRank 幂迭代）:
  http://ilpubs.stanford.edu:8090/422/
- Brandes. A Faster Algorithm for Betweenness Centrality. 2001
  (KnowledgeGraph 中心性):
  https://www.sciencedirect.com/science/article/pii/S0306437901000707
- Carbonell & Goldstein. MMR Diversity-Based Reranking. SIGIR 1998:
  https://dl.acm.org/doi/10.1145/290941.291025
- Lord. Applications of Item Response Theory. 1980（IRT3PL）:
  Lawrence Erlbaum Associates
- Luceda Academy（教育平台对标）:
  https://academy.lucedaphotonics.com/
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

# === 版图编辑器（无外部依赖，仅 NumPy）===
from polaris_gui.layout_editor import (
    DRCHighlight,
    DeviceInstance,
    EditorConfig,
    LayoutEditor,
)

# === 交互式编辑（无外部依赖，纯 stdlib + NumPy）===
from polaris_gui.interactive import (
    AirlineRouter,
    AirlineSegment,
    CommandStack,
    LayoutObject,
    MacroDebugger,
    MacroIDE,
    ObjectType,
    SnapEngine,
    SnapResult,
    ViewerGuard,
    evaluate_object,
)

# === 教育平台（无外部依赖，纯 NumPy）===
from polaris_gui.education import (
    IRT3PL,
    KGNode,
    KnowledgeGraph,
    PageRank,
    TFIDFRetriever,
)

__version__ = "5.0.0"

# 依赖 polaris-flow / polaris-core 的模块通过 __getattr__ lazy 导出
# （polaris-flow 未安装时仅在显式访问 WebServer/run_server 时 raise ImportError，
#   不影响 LayoutEditor/interactive/education 等核心 API 使用）
_LAZY_EXPORTS: dict[str, str] = {
    # Web Server（依赖 polaris_flow.job/recipe/workspace/scheduler/tracker +
    #             polaris_core.specs + polaris.pipeline.integrated）
    "WebServer": "polaris_gui.web_server",
    "run_server": "polaris_gui.web_server",
}


def __getattr__(name: str) -> Any:
    """Lazy 导出依赖 polaris-flow 的 API（R03: 缺失则 raise ImportError）。"""
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'polaris_gui' has no attribute {name!r}")
    import importlib

    module = importlib.import_module(module_path)
    if not hasattr(module, name):
        raise AttributeError(
            f"module {module_path!r} has no attribute {name!r}"
        )
    return getattr(module, name)


__all__ = [
    # 版图编辑器
    "LayoutEditor",
    "EditorConfig",
    "DeviceInstance",
    "DRCHighlight",
    # 交互式编辑
    "ObjectType",
    "LayoutObject",
    "evaluate_object",
    "CommandStack",
    "SnapEngine",
    "SnapResult",
    "AirlineRouter",
    "AirlineSegment",
    "MacroIDE",
    "MacroDebugger",
    "ViewerGuard",
    # Web Server（lazy 导出，依赖 polaris-flow）
    "WebServer",
    "run_server",
    # 教育平台
    "KnowledgeGraph",
    "KGNode",
    "TFIDFRetriever",
    "PageRank",
    "IRT3PL",
    "__version__",
]
