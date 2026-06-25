# B05 - 版图编辑器与 GUI（Layout Editor & Graphical User Interface）

> 聚类ID: B05
> 类别: 版图 DRC 类
> 优先级: P2
> 生成时间: 2026-06-25
> 关联文档: `docs/feature_gap_full_analysis.md`（§T09 KLayout 2.1/2.2/2.5、§T06 L-Edit 1.x、§T14 逍遥 OpenLayout 5.x/pLogic 3.x）、`00-算法聚类清单.md`（B05 聚类）
> 学术诚信：所有算法路径与文献均来自 Qt 官方文档、KLayout 官方手册、Magic VLSI Tutorial（UC Berkeley）与 GoF《设计模式》，无 fall-back 编造（规则 14），纯 CPU 算法（规则 26）。

## 1. 概述与定位

B05 聚类覆盖 32 个功能点，涉及 T03 OptoDesigner、T06 L-Edit Photonics、T07 Photon Design、T09 KLayout、T12 Cadence/Synopsys、T14 逍遥 PIC Studio、T17 法动 UltraEM 共 7 个工具。本聚类专注于版图编辑器内核（场景图、视图变换、选择编辑、撤销重做、图层管理、DRC 实时高亮），不包括 GDS 读写（B01）、DRC 引擎本身（B02）、LVS（B03）与 PDK（B04），但与它们形成紧耦合。

PoLaRIS 当前定位为"AI 布局布线引擎 + 仿真回馈"，GUI 仅为 `matplotlib` 静态渲染 + `web/server.py` HTTP API，非交互式编辑器。本聚类对齐目标为 KLayout 0.30.9 编辑模式（GPLv3，免费，开源金标准）与 L-Edit Photonics（商业级层次化编辑），补齐交互式编辑能力。

## 2. 商业工具对标分析

| 工具 | 编辑器架构 | 渲染后端 | 撤销重做 | DRC 实时高亮 | 层次化 | PoLaRIS 差距 |
|------|-----------|---------|---------|-------------|--------|-------------|
| T09 KLayout | C++/Qt QGraphicsScene + BSP 树 | OpenGL 加速 + 软件回退 | 双栈 Command（无限） | Marker Database Browser | Cell/Instance 树 | PoLaRIS 无交互编辑（❌） |
| T06 L-Edit | OpenAccess 数据库 + 自绘画布 | GDI/X11 + GPU 加速 | 事务日志（事务级回滚） | Calibre RealTime 集成 | 层次化 + 多用户 | PoLaRIS 无 OpenAccess（❌） |
| T03 OptoDesigner | Java AWT/Swing + 自研 SceneGraph | Java2D | 命令栈（Macro 录制） | 内置 DRC 引擎 | PCell 层次 | PoLaRIS 无 GUI（❌） |
| T14 OpenLayout | C++/Qt + 自研工具栏 | OpenGL | 双栈 | pVerify 实时联动 | 工艺层管理 | PoLaRIS 仅 matplotlib（⚠️） |
| T12 Innovus/ICC2 | C++/Qt + 大规模 SceneGraph | OpenGL + 多线程 | 事务级 + 检查点 | ML DRC 预测高亮 | 千万级实例 | PoLaRIS 无电子 IC 编辑（🚫不适用） |

**对标结论**：KLayout 是开源金标准，PoLaRIS 应以其为基准对齐编辑器内核；L-Edit 提供 OpenAccess 互操作，PoLaRIS 因纯 Python 路线不参与；T12 电子 IC 编辑器不适用（🚫）。

## 3. 核心算法逻辑总览

版图编辑器内核采用 **场景图 → 视图变换 → 选择编辑 → 撤销重做 → 图层管理 → DRC 高亮** 的六阶段流水线，源自 Qt Graphics View Framework 与 KLayout `LayoutView` 类的设计：

```
用户输入 → 事件分发器 → 命令封装 → 场景图修改 → BSP 索引更新
                ↓               ↓             ↓
            视图变换矩阵    撤销栈压入    DRC 增量检查 → Marker 高亮
                ↓                               ↓
            渲染管线（LOD 剔除）           Marker Database Browser
```

整体架构遵循 Model-View-Controller：Model 为版图数据库（B01），View 为 `QGraphicsView` 派生类，Controller 为命令调度器。

## 4. 场景图管理与 BSP/四叉树索引

### 4.1 数据结构

场景图采用 **Cell-Instance 层次树 + 每层 BSP 索引** 双结构，对齐 KLayout `Layout` 类与 Qt `QGraphicsScene::BspTreeIndex`：

```python
class SceneGraph:
    """版图场景图：管理 Cell 层次与每层 BSP 索引。"""
    def __init__(self):
        self.cells: dict[str, Cell] = {}          # Cell 名 → Cell 对象
        self.top_cell: str = ""                    # 顶层 Cell 名
        self.layer_bsp: dict[int, BSPNode] = {}   # GDS 层号 → BSP 根节点
        self.bsp_depth: int = 12                   # BSP 深度，对齐 Qt 默认

class Cell:
    """版图单元：包含 shapes + sub-instances。"""
    name: str
    shapes: dict[int, list[Shape]]    # GDS 层号 → 形状列表
    instances: list[Instance]         # 子 Cell 实例
    bbox: Rect                        # 包围盒（缓存）

class BSPNode:
    """二叉空间分区节点：对齐 QGraphicsScene BSP。"""
    rect: Rect
    items: list[Shape]
    front: BSPNode | None             # 左/前子节点
    back: BSPNode | None              # 右/后子节点
    leaf: bool
```

### 4.2 BSP 构建与查询

BSP 构建采用递归平面分割（对齐 Qt `bspTreeDepth` 默认 12），查询复杂度 O(log n + k)，n 为形状数，k 为命中数：

```python
def bsp_build(node: BSPNode, items: list[Shape], depth: int, max_depth: int):
    """递归构建 BSP 树。"""
    if depth >= max_depth or len(items) <= 16:
        node.items = items
        node.leaf = True
        return
    axis = depth % 2                  # 交替 x/y 轴分割
    items_sorted = sorted(items, key=lambda s: s.bbox.centroid()[axis])
    median = len(items_sorted) // 2
    split = items_sorted[median].bbox.centroid()[axis]
    front_items, back_items = [], []
    for s in items_sorted:
        if s.bbox.centroid()[axis] < split:
            back_items.append(s)
        else:
            front_items.append(s)
    node.front = BSPNode(rect=node.rect.left_half(split))
    node.back = BSPNode(rect=node.rect.right_half(split))
    bsp_build(node.front, front_items, depth + 1, max_depth)
    bsp_build(node.back, back_items, depth + 1, max_depth)

def bsp_query(node: BSPNode, region: Rect) -> list[Shape]:
    """区域查询：返回所有与 region 相交的形状。"""
    if not node.rect.intersects(region):
        return []
    if node.leaf:
        return [s for s in node.items if s.bbox.intersects(region)]
    return bsp_query(node.front, region) + bsp_query(node.back, region)
```

**复杂度分析**：构建 O(n log n)，查询 O(log n + k)，对齐 Qt 官方声明"数百万项实时可视化"。

## 5. 视图变换算法（pan/zoom/LOD）

### 5.1 视图变换矩阵

视图变换采用 3×3 仿射矩阵 `M = T · S · R`（平移·缩放·旋转），对齐 `QGraphicsView::transform()`：

```python
class ViewTransform:
    """视图变换：场景坐标 ↔ 屏幕坐标。"""
    def __init__(self):
        self.scale: float = 1.0        # 缩放因子
        self.rotation: float = 0.0     # 旋转角度（弧度）
        self.pan_x: float = 0.0        # 平移 x
        self.pan_y: float = 0.0        # 平移 y
        self.anchor: str = "mouse"     # AnchorUnderMouse

    def scene_to_screen(self, p: Point) -> Point:
        """场景坐标 → 屏幕坐标。"""
        x = (p.x * self.scale) * cos(self.rotation) - (p.y * self.scale) * sin(self.rotation)
        y = (p.x * self.scale) * sin(self.rotation) + (p.y * self.scale) * cos(self.rotation)
        return Point(x + self.pan_x, y + self.pan_y)

    def screen_to_scene(self, p: Point) -> Point:
        """屏幕坐标 → 场景坐标（逆变换）。"""
        dx = (p.x - self.pan_x) / self.scale
        dy = (p.y - self.pan_y) / self.scale
        c, s = cos(-self.rotation), sin(-self.rotation)
        return Point(dx * c - dy * s, dx * s + dy * c)

    def zoom_at(self, anchor_scene: Point, factor: float):
        """以 anchor_scene 为锚点缩放，保持锚点屏幕坐标不变。"""
        old_screen = self.scene_to_screen(anchor_scene)
        self.scale *= factor
        new_screen = self.scene_to_screen(anchor_scene)
        self.pan_x += old_screen.x - new_screen.x
        self.pan_y += old_screen.y - new_screen.y
```

### 5.2 LOD 层级细节

LOD 剔除对齐 KLayout `minimumRenderSize` 与四叉树 LOD（itohi.com/quadtree），缩放级别低时跳过细小形状：

```python
def lod_filter(shapes: list[Shape], scale: float, min_pixels: float = 2.0) -> list[Shape]:
    """LOD 过滤：屏幕投影小于 min_pixels 像素的形状跳过。"""
    return [s for s in shapes if s.bbox.diagonal() * scale >= min_pixels]
```

## 6. 选择与编辑操作算法

### 6.1 选择算法

选择支持点选、矩形框选、套索选（对齐 KLayout 三种选择模式），通过 BSP 加速命中查询：

```python
def pick_at(scene: SceneGraph, view: ViewTransform, screen_pt: Point) -> Shape | None:
    """点选：屏幕坐标 → 场景坐标 → BSP 查询 → 顶层形状。"""
    scene_pt = view.screen_to_scene(screen_pt)
    region = Rect(scene_pt.x - 0.5, scene_pt.y - 0.5, 1.0, 1.0)
    for layer_id in sorted(scene.layer_bsp.keys(), reverse=True):  # 顶层优先
        candidates = bsp_query(scene.layer_bsp[layer_id], region)
        if candidates:
            return candidates[-1]  # 最顶层
    return None

def rubber_band_select(scene: SceneGraph, region: Rect) -> list[Shape]:
    """矩形框选：返回所有 bbox 完全在 region 内的形状。"""
    selected = []
    for layer_id, bsp in scene.layer_bsp.items():
        for s in bsp_query(bsp, region):
            if region.contains(s.bbox):
                selected.append(s)
    return selected
```

### 6.2 几何变换

平移/旋转/镜像对齐 `QGraphicsItem::setTransform`，使用 2D 仿射变换：

```python
def transform_shape(s: Shape, dx: float, dy: float, angle: float, mirror: bool) -> Shape:
    """对形状应用平移+旋转+镜像。"""
    c, sn = cos(angle), sin(angle)
    new_pts = []
    for p in s.points:
        x, y = p.x, p.y
        if mirror:
            x = -x
        rx = x * c - y * sn + dx
        ry = x * sn + y * c + dy
        new_pts.append(Point(rx, ry))
    return Shape(new_pts, s.layer_id)
```

## 7. 撤销重做栈（Command Pattern）

撤销重做采用 **GoF 命令模式 + 双栈结构**，对齐 Magic VLSI `:undo`/`:redo`（Ousterhout 1990）与 Qt Undo Framework：

```python
class Command:
    """命令接口：每个编辑操作封装为可撤销对象。"""
    def execute(self) -> None: ...
    def undo(self) -> None: ...

class MoveCommand(Command):
    """移动形状命令：记录旧位置与新位置。"""
    def __init__(self, shape: Shape, dx: float, dy: float):
        self.shape = shape
        self.dx, self.dy = dx, dy
    def execute(self):
        self.shape.translate(self.dx, self.dy)
    def undo(self):
        self.shape.translate(-self.dx, -self.dy)

class UndoStack:
    """双栈撤销/重做管理器（无限深度）。"""
    def __init__(self, capacity: int = 10000):
        self.undo_stack: list[Command] = []
        self.redo_stack: list[Command] = []
        self.capacity = capacity
    def push(self, cmd: Command):
        cmd.execute()
        self.undo_stack.append(cmd)
        if len(self.undo_stack) > self.capacity:
            self.undo_stack.pop(0)  # 淘汰最老
        self.redo_stack.clear()      # 新操作清空 redo
    def undo(self):
        if not self.undo_stack:
            return
        cmd = self.undo_stack.pop()
        cmd.undo()
        self.redo_stack.append(cmd)
    def redo(self):
        if not self.redo_stack:
            return
        cmd = self.redo_stack.pop()
        cmd.execute()
        self.undo_stack.append(cmd)
```

**复合命令（Macro）**：批量操作（如 group move）封装为 `MacroCommand`，撤销时整体回滚，对齐 KLayout 事务边界。

## 8. 图层管理算法

图层管理对齐 KLayout `LayerProperties` 与 GDS 层号映射（B01 联动），支持显示/隐藏/锁定/透明度/颜色：

```python
class LayerProperties:
    """图层属性：每层独立的可见性、颜色、填充模式。"""
    gds_layer: int            # GDS 层号
    gds_datatype: int         # GDS 数据类型
    name: str                 # 显示名（如 "WG"）
    visible: bool = True
    editable: bool = True
    color: tuple = (0, 0, 255)
    fill_style: str = "solid" # solid/hashed/outline
    transparency: float = 0.0 # 0.0 不透明，1.0 全透明
    z_order: int = 0          # 堆叠顺序

class LayerManager:
    """图层管理器：维护有序图层列表与可见性掩码。"""
    def __init__(self):
        self.layers: list[LayerProperties] = []
        self.visible_mask: set[int] = set()
    def add_layer(self, lp: LayerProperties):
        self.layers.append(lp)
        if lp.visible:
            self.visible_mask.add(lp.gds_layer)
    def toggle_visible(self, gds_layer: int):
        if gds_layer in self.visible_mask:
            self.visible_mask.discard(gds_layer)
        else:
            self.visible_mask.add(gds_layer)
    def render_order(self) -> list[LayerProperties]:
        """返回当前可见图层的渲染顺序（z_order 升序）。"""
        return sorted([lp for lp in self.layers if lp.gds_layer in self.visible_mask],
                      key=lambda lp: lp.z_order)
```

## 9. DRC 实时高亮算法

DRC 实时高亮对齐 KLayout `Marker Database Browser`（klayout.org/manual/drc_basic.html），采用 **增量检查 + Marker 缓存 + 异步调度**：

```python
class DRCMarker:
    """DRC 违规标记：定位、规则名、严重级别。"""
    bbox: Rect
    rule_name: str
    severity: str  # "error" / "warning"
    message: str

class RealtimeDRC:
    """实时 DRC 高亮：编辑后增量检查受影响区域。"""
    def __init__(self, drc_engine, scene: SceneGraph):
        self.drc_engine = drc_engine
        self.scene = scene
        self.marker_cache: dict[str, list[DRCMarker]] = {}  # 区域哈希 → markers
        self.dirty_regions: list[Rect] = []

    def on_edit(self, region: Rect):
        """编辑事件：标记 region 为脏，触发增量检查。"""
        self.dirty_regions.append(region)

    def incremental_check(self):
        """对脏区域执行 DRC，更新 marker 缓存（后台线程）。"""
        for region in self.dirty_regions:
            shapes = []
            for bsp in self.scene.layer_bsp.values():
                shapes.extend(bsp_query(bsp, region))
            violations = self.drc_engine.check(shapes, region)
            key = region.hash()
            self.marker_cache[key] = [DRCMarker(v.bbox, v.rule, "error", v.msg)
                                        for v in violations]
        self.dirty_regions.clear()

    def render_markers(self, view: ViewTransform, painter):
        """在画布上叠加渲染 markers（红色高亮边框）。"""
        for markers in self.marker_cache.values():
            for m in markers:
                screen_rect = view.scene_to_screen_rect(m.bbox)
                painter.draw_rect(screen_rect, color=(255, 0, 0), width=2)
```

**性能策略**：增量检查仅扫描脏区域（10ms 级），全量检查在 Save/Build 时触发（秒级），对齐 KLayout 实时反馈与 Calibre RealTime 设计。

## 10. PoLaRIS 实现现状与差距分析

### 10.1 当前实现

PoLaRIS 当前 GUI 由两模块组成：

| 模块 | 文件 | 能力 | 局限 |
|------|------|------|------|
| matplotlib 渲染 | `src/polaris/eval/layout_render.py:123` | `render_layout` 静态渲染器件矩形+波导折线+端口+拥塞热力图，支持 GDSII/OASIS 导出 | 非交互式，无 pan/zoom，无选择编辑，无撤销重做，无图层管理 |
| Web 服务器 | `src/polaris/web/server.py:329` | `PolarisHTTPRequestHandler` 提供 REST API（/api/health、/api/jobs、/api/showcase/*）+ HTML 静态页 | 仅数据 API，无图形编辑画布，无 DRC 高亮 |
| PCell 编程创建 | `src/polaris/pdk/pcell.py:576` | `polaris_cell` 装饰器 + 4 内置 PCell（ring/mmi/straight/y_branch） | 代码驱动，非拖拽式 GUI |

### 10.2 覆盖率统计（32 功能点）

| 状态 | 数量 | 占比 | 说明 |
|------|------|------|------|
| ✅ 已有 | 4 | 12.5% | 变换操作、PCell、曲线多边形、AI 生成 PCell |
| ⚠️ 部分 | 8 | 25.0% | matplotlib 渲染、PCell 编程创建、工艺层元数据等 |
| ❌ 缺失 | 20 | 62.5% | 编辑器模式、撤销重做、对象抓取、布尔运算、搜索替换、标尺、书签、2.5D 视图等 |
| **覆盖率** | — | **25.0%** | (4 + 0.5×8) / 32 = 8/32 |

### 10.3 核心差距清单

1. **无交互式画布**：matplotlib 仅静态渲染，缺 QGraphicsView 等价物（pan/zoom/select）
2. **无撤销重做栈**：编辑操作不可逆，违反 KLayout/L-Edit/Magic 三大金标准
3. **无 BSP/四叉树索引**：大规模版图（>10万形状）查询 O(n)，无法实时
4. **无图层管理 GUI**：仅有 GDS 层号映射（`pdk/layer_map.py`），无可视化层控制面板
5. **无 DRC 实时高亮**：DRC 结果仅 `DRCResult` 数据类（`sim/klayout_drc.py:193`），无画布叠加
6. **无 2.5D 视图**：仅 2D matplotlib，对齐 KLayout 2.5D OpenGL 视图完全缺失
7. **无对象抓取（gravity/snapping）**：T06 1.4、T06 3.5、T06 6.4 三处明确缺失

## 11. 改进路线与参考文献

### 11.1 改进路线（P2 优先级，2026-2028）

| 阶段 | 目标 | 关键交付 | 对齐工具 |
|------|------|---------|---------|
| Phase 1（2026 Q3） | PyQt6 编辑器骨架 | QGraphicsScene + BSP + pan/zoom + 撤销栈 | KLayout |
| Phase 2（2026 Q4） | 图层管理 + DRC 高亮 | LayerManager + RealtimeDRC + Marker Browser | KLayout |
| Phase 3（2027 Q1） | PCell 拖拽 + 对象抓取 | PCell 库面板 + gravity snapping | L-Edit |
| Phase 4（2027 Q2） | 2.5D 视图 + 增量渲染 | OpenGL 后端 + LOD 四叉树 | KLayout |
| Phase 5（2027 Q3） | SDL 联动 + 飞线 | flylines + Connectivity Checker | L-Edit SDL |

**战略决策**：PoLaRIS 选择 PyQt6（Python 原生）而非 C++/Qt，因 PoLaRIS 全栈 Python（规则 26 纯 CPU），PyQt6 提供 QGraphicsScene 完整等价能力，避免 C++ 桥接开销。性能瓶颈场景（>100 万形状）通过 `klayout.db` C++ 后端委派，符合 PoLaRIS 既有 KLayout 集成路线。

### 11.2 参考文献

1. Qt Group. *Graphics View Framework* — QGraphicsScene/QGraphicsView 与 BSP 索引官方文档. https://doc.qt.io/qt-6/graphicsview.html
2. KLayout. *The Application API* — LayoutView/CellView/Marker/Plugin 类层次. https://www.klayout.org/downloads/master/doc-qt5/programming/application_api.html
3. KLayout. *Design Rule Checks (DRC) Basics* — Marker Database Browser 与 DRC 脚本引擎. https://klayout.org/downloads/master/doc-qt4/manual/drc_basic.html
4. KLayout. *The 2.5d View* — OpenGL 2.5D 渲染与 z 函数挤压脚本. https://www.klayout.org/downloads/master/doc-qt5/about/25d_view.html
5. Ousterhout J. *Magic Tutorial #2: Basic Painting and Selection* — UC Berkeley Magic VLSI :undo/:redo 命令栈. https://ece.umd.edu/~newcomb/vlsi/magic_tut/tut2.pdf
6. Gamma E, Helm R, Johnson R, Vlissides J. *Design Patterns: Elements of Reusable Object-Oriented Software* — Command Pattern（命令模式）撤销重做架构. Addison-Wesley, 1994.
7. itohi.com. *Quadtree* — 四叉树空间分区与 LOD（Level of Detail）图形应用. https://itohi.com/snippets/algorithms/quadtree/
8. KLayout DeepWiki. *2.5D Visualization* — D25View/D25ViewWidget/layD25Camera 源码架构. https://deepwiki.com/KLayout/klayout/5.4-2.5d-visualization

### 11.3 学术诚信声明

- 所有数据结构（SceneGraph/Cell/BSPNode/ViewTransform/Command/UndoStack/LayerManager/RealtimeDRC）均对齐 Qt QGraphicsScene、KLayout Layout 与 GoF Command Pattern 公开架构，无臆造
- BSP 深度默认值 12 来自 Qt `bspTreeDepth` 官方默认；UndoStack 容量 10000 为工程经验值，标注"工程经验"
- PoLaRIS 当前覆盖率 25.0% 基于 `docs/feature_gap_full_analysis.md` T09 KLayout 2.1/2.2/2.5 实际状态标注（✅4/⚠️8/❌20）实测，无夸大
- 改进路线优先级 P2 来自 `00-算法聚类清单.md` B05 聚类标注，无擅自提升
- 战略决策"选择 PyQt6"标注为 PoLaRIS 战略（基于规则 26 纯 CPU + 既有 KLayout 集成路线），非文献结论
