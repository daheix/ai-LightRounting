# PoLaRIS 模块开发指南

> 版本 v6.1 · 2026-07 · 如何扩展新模块与功能
> 数据来源：`modules/` 真实代码结构 + `pyproject.toml` + `modules/README.md`（R02 学术诚信）
> 前置：先读 [贡献指南](contributing_guide.md) 和 [API 参考手册](api_reference.md)

---

## 阅读说明

本指南面向**希望扩展 PoLaRIS 新功能的开发者**：添加新 PDK 器件、新物理求解器、新优化器、新布线策略、新流水线阶段、新 GUI 端点等。所有接口模式、模块清单、文件结构均**从真实代码提取**（R02 学术诚信），扩展示例代码标注「示例」字样，未与真实代码 1:1 对应的片段仅作演示用途。

**真实数据快照**（来源 `modules/README.md`，2026-07-03 扫描）：

- 33 子模块 / 289 源码文件 / 99,017 行 / 1,613 测试 / 3,031 文献 URL
- 全 33 子模块独立 import 通过；orchestrator 9 stage 全部成功（`n_success=9`）
- 全量 pytest 实测 1614 passed / 0 failed / 1 skipped

---

## 第 1 章：Monorepo 结构

### 1.1 33 子模块组织

PoLaRIS v5.0 采用细粒度 monorepo，33 个子模块按 **12 功能分类** 组织。每个子模块独立目录、独立 `pyproject.toml`、独立测试、独立 C ABI 头文件，可独立管理升级。来源：`modules/README.md`。

```
modules/
├── core/              # polaris-core 核心数据结构
├── orchestrator/      # polaris-orchestrator 9-stage EDA 编排
├── flow/              # polaris-flow 作业调度 / IPKISS / DesignIntent
├── pdk/               # polaris-pdk 4 平台 36 器件目录
├── pdk_advanced/      # polaris-pdk-advanced gdsfactory 互操作 / PCell
├── gds_tools/         # polaris-gds-tools 22 GDSII 工具 + 6 格式 IO
├── gdsio/             # polaris-gdsio GDSII import/export
├── place/             # polaris-place DREAMPlace + AlphaChip 布局
├── route/             # polaris-route 曲线波导布线
├── router_advanced/   # polaris-router-advanced 17 种高级布线算法
├── drc/               # polaris-drc 12 条 SiEPIC DRC 规则
├── lvs/               # polaris-lvs LVS 网表一致性比对
├── verify_advanced/   # polaris-verify-advanced 图同构 LVS / 层次化 DRC
├── fdtd/              # polaris-fdtd 3D FDTD（Yee + PML + JAX 可微）
├── fde/               # polaris-fde 2D 有限差分本征模
├── fdfd/              # polaris-fdfd 频域 Helmholtz
├── eme/               # polaris-eme 本征模展开（Redheffer）
├── bpm/               # polaris-bpm Crank-Nicolson 光束传播
├── circuit/           # polaris-circuit 频域/时域/SPICE/系统级
├── sparam/            # polaris-sparam S 参数模型 + Clements
├── inverse/           # polaris-inverse JAX 逆向设计
├── optimizer/         # polaris-optimizer 12 种优化器
├── nn/                # polaris-nn torch.nn 风格 + benchmark
├── trainer/           # polaris-trainer PPO + AlphaChip RL
├── multiphysics/      # polaris-multiphysics DDM/HEAT/VarFDTD/RCWA
├── lumerical/         # polaris-lumerical Lumerical/Tidy3D/MEEP 后端
├── parasitic/         # polaris-parasitic 寄生提取 + Verilog-A
├── pam4/              # polaris-pam4 PAM4 信号 + BER/眼图
├── yield/             # polaris-yield 蒙特卡洛 + Sobol 良率
├── quantum_advanced/  # polaris-quantum-advanced 玻色/QKD/层析/QEC
├── boson/             # polaris-boson 玻色采样
├── klm/               # polaris-klm KLM 量子 CNOT 门
├── gui/               # polaris-gui 版图编辑器 + Macro IDE
└── _c_abi/            # C ABI 公共层（polaris_types.h / polaris_error.h）
```

**按功能域分组**（来源 `modules/README.md` 与 `docs/contributing_guide.md` §2.3）：

| 功能域 | 模块（文件/行数/测试） |
|--------|----------------------|
| 核心与编排 | core(3/828/75) · orchestrator(2/396/25) · flow(24/7344/47) |
| PDK 与版图 IO | pdk(2/993/40) · pdk_advanced(7/3607/43) · gds_tools(33/15207/75) · gdsio(3/422/36) |
| 布局布线 | place(3/1317/45) · route(2/1146/72) · router_advanced(21/8356/107) |
| 验证 | drc(2/879/51) · lvs(2/423/42) · verify_advanced(17/5688/68) |
| 物理求解器 | fdtd(4/1121/53) · fde(2/589/53) · fdfd(2/540/36) · eme(2/570/52) · bpm(2/573/33) |
| 电路仿真 | circuit(10/2700/88) · sparam(4/817/40) |
| 逆向设计 | inverse(3/1157/56) · optimizer(10/3859/76) |
| AI/ML | nn(23/8094/48) · trainer(7/2639/33) |
| 多物理场 | multiphysics(44/13227/35) · lumerical(5/1091/31) · parasitic(11/2887/49) |
| 光通信 | pam4(2/347/30) · yield(8/3615/49) |
| 量子光子 | quantum_advanced(17/4811/42) · boson(5/577/32) · klm(2/194/21) |
| GUI | gui(5/3003/30) |

### 1.2 单个模块的文件结构

以 `polaris-place` 为例，真实文件清单（来源 Glob `modules/place/src/polaris_place/*.py`）：

```
modules/place/
├── src/polaris_place/
│   ├── __init__.py       # 公共 API 导出（place_circuit/compute_hpwl/render_ascii_layout）
│   ├── analytical.py     # 主入口（FFDH 调度 + AnalyticalConfig + Adam 优化器）
│   ├── metrics.py        # HPWL / 密度梯度 / Tarjan SCC / 拓扑深度
│   ├── legalize.py       # FFDH 合法化 + 1D 最近合法位置搜索
│   ├── align.py          # 端口对齐后处理
│   ├── align_matrix.py   # 对齐矩阵
│   ├── residual.py       # 残余违规成对双向修复
│   └── ppo_gnn.py        # AlphaChip Edge-GNN + PPO ActorCritic AI 布局
├── tests/
│   └── test_place.py     # 测试（45 项）
└── pyproject.toml        # 模块独立配置
```

**模块拆分原则**（来源 `modules/place/src/polaris_place/__init__.py` docstring）：单文件超过 800 行时按功能职责拆分。`analytical.py` 原 1480 行已拆分为 5 个文件（metrics/legalize/align/residual + 主入口），向后兼容通过 re-export 保持 `from polaris_place.analytical import X` 仍可用，新代码推荐直接从子模块导入（`from polaris_place.metrics import X`）。

### 1.3 单模块 IPO 三段式文档化

每个子模块 `src/polaris_<name>/__init__.py` 顶部 docstring 含 **Input → Process → Output** 三段式文档（来源 `modules/README.md`「拆分原则」）：

- **Input**：明确函数入参（类型/默认值/物理含义）
- **Process**：明确算法/公式/文献溯源（R02 学术诚信）
- **Output**：明确返回 dict 字段（JSON-serializable，业务可直接消费）

对应 `c_api/<name>.h` 顶部注释同样标注 IPO。失败即 raise（R03 禁止 fall-back）。

### 1.4 editable install 机制

**根项目安装**（来源 `pyproject.toml`）：

```bash
pip install -e ".[dev]"
```

- 包名 `polaris-pnr`，版本 `5.0.0`
- 构建后端 `setuptools.build_meta`（`setuptools>=68` + `wheel`）
- 包发现：`where = ["src", "3dtool"]`，`include = ["polaris*", "pycopy*"]`，`exclude = ["tests*"]`
- 入口点：`polaris = "polaris.pipeline:main"`
- 修改 `src/` 或 `modules/<name>/src/` 后立即生效（editable）

**单模块独立安装**（来源 `modules/README.md`「独立管理」）：

```bash
pip install -e modules/<name>/       # 独立安装某子模块
pytest modules/<name>/tests/         # 独立测试某子模块
```

33 子模块全部支持独立 `pip install -e modules/<name>/` + `python -c "import polaris_<name>"`（来源 `modules/README.md` 验证结果）。

### 1.5 Python 版本与运行时依赖

来源 `pyproject.toml`：

- **Python ≥ 3.9**（推荐 3.11，来源 `[tool.ruff] target-version = "py311"`）
- 核心依赖：`numpy · scipy · networkx · torch · gymnasium · matplotlib · pyyaml · klayout · simphony · sax · gdstk · shapely`
- 可选依赖：`gdsfactory>=8.0`（Python 3.14 不可用）/ `SiPANN`（依赖 tensorflow，仅 3.10–3.13）
- 开发依赖：`pytest · ruff · mypy`

---

## 第 2 章：添加新 PDK 器件

### 2.1 真实器件定义模式

PDK 器件采用**纯 dict 数据结构**（非 dataclass），来源 `modules/pdk/src/polaris_pdk/devices.py`。每个器件 dict 字段固定：

```python
# 真实字段结构（来源 devices.py DEVICES 列表）
{
    "platform": "SOI",                 # 平台名（SOI/SiN/InP/LNOI）
    "device_type": "strip_waveguide",  # 器件类型标识
    "name": "Strip Waveguide",         # 显示名
    "category": "passive",             # 分类（passive/active/modulator/...）
    "foundry": "SiEPIC",               # foundry 名
    "process_node": "220nm SOI",       # 工艺节点
    "params": {                        # 电光参数（含 pdk_reference 标注来源）
        "width_um": 0.5,
        "loss_db_cm": 2.0,
        "wavelength_nm": 1550,
        "pdk_reference": "SiEPIC_EBeam_PDK",
    },
    "source": make_source(             # 文献溯源（R02）
        "SiEPIC EBeam PDK strip waveguide",
        "SiEPIC", 2024,
        "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    ),
    "ports": [                         # 端口列表 [(name, x_um, y_um, direction), ...]
        ("in", 0.0, 0.0, "west"),
        ("out", 10.0, 0.0, "east"),
    ],
    "bbox_um": {                       # 包围盒（μm）
        "xmin": 0.0, "ymin": -0.25,
        "xmax": 10.0, "ymax": 0.25,
    },
}
```

`make_source(title, authors, year, url)` 是 `devices.py` 公开的来源标注构造器，返回 `{"title", "authors", "year", "url"}` dict（R02 学术诚信，每个器件可溯源）。

### 2.2 添加新器件步骤（示例）

**步骤 1**：在 `modules/pdk/src/polaris_pdk/devices.py` 的 `DEVICES` 列表中追加新器件 dict：

```python
# 示例：新增一个 SOI 平台的 ring modulator
{
    "platform": "SOI",
    "device_type": "ring_modulator",   # 新器件类型
    "name": "Ring Modulator",
    "category": "modulator",
    "foundry": "SiEPIC",
    "process_node": "220nm SOI",
    "params": {
        "radius_um": 10.0,
        "insertion_loss_db": 0.5,
        "modulation_bw_ghz": 25.0,
        "wavelength_nm": 1550,
        "pdk_reference": "SiEPIC_EBeam_PDK",
    },
    "source": make_source(
        "SiEPIC EBeam PDK ring modulator",
        "SiEPIC", 2024,
        "https://github.com/SiEPIC/SiEPIC_EBeam_PDK",
    ),
    "ports": [
        ("in", 0.0, 0.0, "west"),
        ("through", 20.0, 0.0, "east"),
        ("drop", 20.0, -20.0, "south"),
    ],
    "bbox_um": {"xmin": 0.0, "ymin": -20.0, "xmax": 20.0, "ymax": 0.0},
},
```

**步骤 2**：无需手动注册。`modules/pdk/src/polaris_pdk/filters.py` 中已自动构建检索索引：

```python
# 来源 filters.py（真实代码，自动索引）
_INDEX: dict[str, dict[str, Any]] = {
    f"{d['platform']}::{d['device_type']}": d for d in DEVICES
}
```

新器件加入 `DEVICES` 后，索引自动包含 `"SOI::ring_modulator"`，立即可被 `get_device("SOI", "ring_modulator")` 查询到。

**步骤 3**：如需新增平台，在 `filters.py` 的 `PLATFORM_META` 字典中追加平台元信息：

```python
# 示例：新增 Glass 平台
"Glass": {
    "foundry": "NewFoundry",
    "process_node": "Glass SiN",
    "pdk": "NewFoundry Glass PDK",
    "url": "https://example.com/newfoundry",
},
```

### 2.3 查询 API

来源 `modules/pdk/src/polaris_pdk/__init__.py` 与 `filters.py`：

| API | 签名 | 说明 |
|-----|------|------|
| `list_platforms()` | `-> list[dict]` | 返回 4 平台信息（platform/foundry/process_node/device_count/device_names） |
| `list_devices(platform)` | `-> list[dict]` | 返回指定平台所有器件（深拷贝） |
| `get_device(platform, device_type)` | `-> dict` | 按 `"platform::device_type"` 索引查询单器件（深拷贝） |

**R03 约束**：平台或器件未找到时 `raise RuntimeError`，禁止返回空 dict 或 None。查询返回深拷贝，避免调用方修改内部数据。

### 2.4 添加测试

来源现有测试模式（`modules/pdk/tests/`，40 项测试）：

```python
# modules/pdk/tests/test_ring_modulator.py（示例）
from polaris_pdk import get_device, list_devices


def test_ring_modulator_exists():
    dev = get_device("SOI", "ring_modulator")
    assert dev["device_type"] == "ring_modulator"
    assert dev["category"] == "modulator"


def test_ring_modulator_ports():
    dev = get_device("SOI", "ring_modulator")
    port_names = [p[0] for p in dev["ports"]]
    assert "in" in port_names
    assert "drop" in port_names
    assert len(dev["ports"]) == 3


def test_ring_modulator_source_traced():  # R02 学术诚信
    dev = get_device("SOI", "ring_modulator")
    assert "source" in dev
    assert dev["source"]["url"].startswith("https://")


def test_unknown_device_raises():  # R03 禁止 fall-back
    import pytest
    with pytest.raises(RuntimeError):
        get_device("SOI", "nonexistent_device")
```

### 2.5 文献溯源要求（R02）

PDK 模块 docstring 已含 ≥5 个文献 URL（来源 `catalog.py` docstring）：

- SiEPIC EBeam PDK: https://github.com/SiEPIC/SiEPIC_EBeam_PDK
- Ligentec ANR PDK: https://www.ligentec.com/
- Pattern Project / JEPPIX InP: https://www.jeppix.eu/
- HyperLight LNOI PDK: https://hyperlightphotonics.com/
- Soares et al., Appl. Sci. 2019, 9(8), 1588: https://doi.org/10.3390/app9081588
- Liu et al., Light: Advanced Manufacturing 2025, 6, 47: https://doi.org/10.37188/lam.2025.047

新增器件的 `params.pdk_reference` 与 `source.url` 必须指向真实可访问的 PDK 文档或文献。

---

## 第 3 章：添加新物理求解器

### 3.1 求解器接口规范

PoLaRIS 物理求解器遵循 **IPO 三段式 + JSON-serializable dict 返回**。以 `polaris-fdtd` 为真实范本（来源 `modules/fdtd/src/polaris_fdtd/__init__.py`）：

```python
# 真实 API 签名（来源 fdtd/__init__.py docstring）
def simulate_waveguide_fdtd(dx_um=0.05, n_steps=2000, wavelength_um=1.55) -> dict:
    """3D FDTD 全波仿真（Yee 1966 + Gedney 1996 PML）。

    Returns:
        dict: {transmission_db, T_fdtd, fdtd_duration_s, n_steps, dx_um, pml_enabled}
    """
```

**接口约定**（来源各求解器模块 docstring，R02/R03）：

1. **Input**：几何/材料/波长等物理参数，带默认值与物理含义标注
2. **Process**：算法 + 文献溯源（Yee 1966、Gedney 1996、Redheffer 等）
3. **Output**：返回 `dict`，所有字段 JSON-serializable，禁止返回内部对象
4. **错误处理**：仿真 NaN 即 `raise`，JAX 不可用即 `raise`（R03）
5. **GPU 战略**：纯 NumPy/SciPy/JAX(CPU)，强制 `JAX_PLATFORMS=cpu`（R04）

### 3.2 求解器类设计模式（示例）

底层内核采用类封装，来源 `polaris-fdtd` 真实类设计：

```python
# 真实类签名（来源 fdtd/__init__.py）
class YeeGrid3D:
    """3D Yee 网格（nx, ny, nz, dx, dy, dz, epsilon_r=None, mu_r=None）"""

class GedneyPML:
    """Gedney 1996 PML 吸收边界（grid, n_layers=8, sigma_ratio=1.0, m=3, eps_r_bg=None）"""

class DifferentiableFDTD:
    """JAX 可微 FDTD 内核（grid, pml=None, dt=None, eps_r_bg=None）"""
```

新求解器示例：

```python
# 示例：新增 RCWA 求解器（实际已有 solve_rcwa_1d 在 polaris-multiphysics）
class RCWASolver:
    """严格耦合波分析（RCWA）求解器。

    算法: Moharam & Gaylord 1981 RCWA，逐层傅里叶展开 + 传输矩阵。
    来源: https://doi.org/10.1364/JOSA.71.000811

    Args:
        n_harmonics: 傅里叶谐波数（默认 15）。
        wavelength_um: 波长 (μm)。
    """

    def __init__(self, n_harmonics: int = 15, wavelength_um: float = 1.55) -> None:
        if n_harmonics < 1:
            raise RuntimeError(  # R03 禁止 fall-back
                f"n_harmonics 必须为正: {n_harmonics}"
            )
        self.n_harmonics = n_harmonics
        self.wavelength_um = wavelength_um

    def solve(self, layer_stack: list[dict]) -> dict:
        """求解多层光栅的衍射效率。

        Args:
            layer_stack: 每层 {thickness_um, epsilon_r, is_grating, period_um}。

        Returns:
            dict: {transmission_eff, reflection_eff, diffraction_orders, ...}
        """
        ...
        return {"transmission_eff": ..., "reflection_eff": ..., ...}
```

### 3.3 新求解器模块的完整结构

```
modules/rcwa/                              # 示例新模块
├── src/polaris_rcwa/
│   ├── __init__.py     # 公共 API + IPO docstring + ≥5 文献 URL
│   ├── solver.py       # RCWASolver 核心实现
│   └── utils.py        # 傅里叶展开辅助函数
├── tests/
│   └── test_rcwa.py    # 单元测试
└── pyproject.toml      # 模块配置
```

`__init__.py` 必须包含（来源 `polaris-fdtd/__init__.py` 真实模式）：

```python
"""PoLaRIS RCWA 仿真子模块（polaris-rcwa）。

## Input / Process / Output 三段式（IPO）
- solve_rcwa:
  - I: layer_stack / n_harmonics=15 / wavelength_um=1.55
  - P: Moharam & Gaylord 1981 RCWA 逐层傅里叶展开 + 传输矩阵
  - O: dict{transmission_eff, reflection_eff, diffraction_orders}

## 设计原则
- R04 不参与 GPU: 纯 NumPy 实现
- R03 禁止 fall-back: 参数非法即 raise；NaN 即 raise
- R02 学术诚信: 所有物理常量/公式可溯源

## 来源（R02，≥5 文献 URL）
1. Moharam & Gaylord 1981 JOSA https://doi.org/10.1364/JOSA.71.000811
2. ...
"""
from polaris_rcwa.solver import RCWASolver, solve_rcwa

__version__ = "1.0.0"
__all__ = ["RCWASolver", "solve_rcwa", "__version__"]
```

### 3.4 现有求解器扩展点参考

来源 Grep `class.*(Solver|Backend)` 真实结果，可作为新求解器设计参考：

| 模块 | 求解器类 | 算法 |
|------|---------|------|
| `polaris-fdtd` | `YeeGrid3D` / `GedneyPML` / `DifferentiableFDTD` | Yee 1966 + PML + JAX |
| `polaris-multiphysics` | `VarFdtdSolver` / `DdmSolver` / `HeatSolver` / `FetdSolver` / `PoissonSolver` / `GummelSolver` | VarFDTD / DDM / 热 / FE |
| `polaris-circuit` | `MNASolver` | 改进节点分析（SPICE） |
| `polaris-lumerical` | `LumericalFDTDBackend` / `ModeSolver` / `Tidy3DBackend` / `MeepAdjointBackend` | 商业求解器后端 |

---

## 第 4 章：添加新优化器

### 4.1 真实优化器清单

`polaris-optimizer` 子模块提供 **12 种光子学优化器**（来源 `modules/optimizer/src/polaris_optimizer/__init__.py` docstring「12 种光子学优化器」），实际类（来源 Grep `class.*Optimizer`）：

| # | 类名 | 算法 | 文献 |
|---|------|------|------|
| 1 | `LBFGSOptimizer` | L-BFGS 两循环递归 + Wolfe 线搜索 | Liu & Nocedal 1989 https://doi.org/10.1007/BF01589116 |
| 2 | `ParticleSwarmOptimizer` | 粒子群（PSO） | Kennedy & Eberhart 1995 https://doi.org/10.1109/ICNN.1995.488968 |
| 3 | `CMAESOptimizer` | 协方差矩阵自适应进化策略 | Hansen & Ostermeier 2001 https://doi.org/10.1162/106365601750190398 |
| 4 | `GlobalOptimizer` | 全局优化统一封装 | — |
| 5 | `NSGA2Optimizer` | 快速非支配排序 + 拥挤距离 | Deb et al. 2002 https://doi.org/10.1109/4235.996017 |
| 6 | `NSGA3Optimizer` | 参考点法 + 小生境选择 | Deb & Jain 2014 https://doi.org/10.1109/TEVC.2013.2281535 |
| 7 | `TopologyOptimizer` | 拓扑优化（水平集） | Osher & Sethian 1988 https://doi.org/10.1016/S0021-9991(88)80002-2 |
| 8 | `TopologyAdjointOptimizer` | 密度伴随（JAX autograd） | Piggott 2017 https://www.nature.com/articles/nphoton.2017.102 |
| 9 | `ShapeAdjointOptimizer` | 形状伴随（参数化几何 + Adam） | Lalau-Keraly 2013 https://doi.org/10.1364/OE.21.0021693 |
| 10 | `RobustOptimizer` | 鲁棒优化（蒙特卡洛公差扰动） | Wang 2018 https://doi.org/10.1364/OE.26.023273 |
| 11 | `HJSolver` | Hamilton-Jacobi 水平集演化 | Osher & Sethian 1988 |
| 12 | `FeedbackAdapter` | 反馈适配（约束违规 → 布局布线建议） | Apollo 2025 https://arxiv.org/html/2504.18813v1 |

### 4.2 优化器类设计模式（真实范本）

来源 `modules/optimizer/src/polaris_optimizer/lbfgs.py`，`LBFGSOptimizer.optimize` 真实签名：

```python
class LBFGSOptimizer:
    """L-BFGS 优化器（对标 lumopt/scipy L-BFGS）。

    两循环递归近似逆 Hessian，线搜索满足 Wolfe 条件，最大化 FoM。
    """

    def __init__(self, config: LBFGSConfig | None = None) -> None:
        self.config = config or LBFGSConfig()
        self._s_history: deque = deque(maxlen=self.config.memory_size)
        self._y_history: deque = deque(maxlen=self.config.memory_size)
        self._rho_history: deque = deque(maxlen=self.config.memory_size)

    def optimize(
        self,
        initial_params: np.ndarray,
        fom_fn: Callable[[np.ndarray], float],
        grad_fn: Callable[[np.ndarray], np.ndarray],
    ) -> LBFGSResult:
        """最大化 FoM。

        Args:
            initial_params: 设计变量初值（1D float64）。
            fom_fn: 目标函数回调。
            grad_fn: 梯度回调（adjoint 方法提供）。

        Returns:
            LBFGSResult: 最优参数 + FoM 历史 + 收敛标志。
        """
        ...
```

**统一接口约定**（来源各优化器类）：

- `optimize()` 方法名统一
- 入参：`initial_params`（numpy 1D）、`fom_fn`（目标）、`grad_fn`（梯度，可选）
- 返回：`*Result` dataclass，含 `optimal_params` / `optimal_fom` / `fom_history` / `converged`
- 配置：`*Config` dataclass，带默认值

### 4.3 添加新优化器步骤（示例）

**步骤 1**：在 `modules/optimizer/src/polaris_optimizer/` 新建文件，例如 `bayesian.py`：

```python
# 示例：新增贝叶斯优化器
import numpy as np
from dataclasses import dataclass, field


@dataclass
class BayesianConfig:
    n_initial: int = 5
    n_iterations: int = 50
    acquisition: str = "ei"  # expected improvement


@dataclass
class BayesianResult:
    optimal_params: np.ndarray
    optimal_fom: float
    fom_history: list
    converged: bool


class BayesianOptimizer:
    """贝叶斯优化器（高斯过程 surrogate + 采集函数）。

    来源: Snoek et al. 2012 Practical Bayesian Optimization
      https://arxiv.org/abs/1206.2944
    """

    def __init__(self, config: BayesianConfig | None = None) -> None:
        self.config = config or BayesianConfig()

    def optimize(
        self,
        initial_params: np.ndarray,
        fom_fn,
        bounds,
    ) -> BayesianResult:
        ...
        return BayesianResult(...)
```

**步骤 2**：在 `__init__.py` 中导出（来源真实 `__all__` 模式）：

```python
from polaris_optimizer.bayesian import (
    BayesianConfig,
    BayesianOptimizer,
    BayesianResult,
)

# 追加到 __all__
__all__ = [
    ...
    "BayesianConfig",
    "BayesianResult",
    "BayesianOptimizer",
]
```

**注意**：PoLaRIS 优化器采用**直接导出 + 工厂函数**模式（如 `create_lbfgs_optimizer` / `create_pso_optimizer` / `create_cmaes_optimizer`），而非中央注册表。新优化器应遵循此模式，在 `__init__.py` 显式 re-export，并提供 `create_bayesian_optimizer()` 工厂函数。

**步骤 3**：补充测试到 `modules/optimizer/tests/`（现有 76 项测试）。

### 4.4 多目标优化扩展点

`NSGA2Optimizer` / `NSGA3Optimizer` 支持多目标，来源 `__init__.py` 真实导出：

- `Objective` / `ObjectiveType`：目标定义
- `Individual`：个体
- `ParetoResult`：帕累托前沿结果
- 辅助函数：`fast_non_dominated_sort` / `compute_crowding_distance` / `sbx_crossover` / `polynomial_mutation` / `tournament_selection` / `generate_reference_points`

新增多目标优化器可复用这些公共组件。

---

## 第 5 章：添加新布线策略

### 5.1 布线器接口规范

`polaris-route` 提供稳定的 `route_circuit` API，来源 `modules/route/src/polaris_route/__init__.py`：

```python
def route_circuit(circuit: dict, placements: dict, mode: str = "curvy") -> dict:
    """对已布局电路执行智能布线。

    Returns:
        dict: {
            paths: [{dev1, port1, dev2, port2, points, loss_db, n_bends, n_crossings}],
            total_loss_db: float,
            n_crossings: int,
            n_bends: int,
            router_type: str,
        }
    """
```

**真实支持的 mode**：来源 `_SUPPORTED_MODES = ("curvy",)`，目前仅 `"curvy"`。`polaris-router-advanced` 提供 17 种高级布线算法（来源 `modules/README.md`）。

### 5.2 CurvyRouter 真实范本

来源 `modules/route/src/polaris_route/curvy.py`（真实类）：

```python
class CurvyRouter:
    """曲线波导布线器。

    生成 S-bend 曲线波导（Euler 螺旋 / Bezier / Arc），
    支持损耗常数、几何工具。

    来源（R02）:
    - LiDAR ISPD'25 https://dl.acm.org/doi/pdf/10.1145/3698364.3705355
    - Klauss 2018 Euler spiral https://doi.org/10.1364/OE.26.029637
    """
```

`CurvyRouter.route(start, end)` 返回路径点列表 `[(x, y), ...]`，坐标为画布绝对坐标（μm）。

### 5.3 router_advanced 扩展点

`polaris-router-advanced` 提供 17 种高级布线器，来源 Grep `class.*Router` 真实结果：

| 布线器 | 算法 |
|--------|------|
| `GridRouter` | 网格布线基类 |
| `JPSRouter(GridRouter)` | Jump Point Search |
| `DiagonalGridRouter(GridRouter)` | 对角网格 |
| `CurvyAStarRouter` | 曲线 A* |
| `GlobalRouter` | 全局布线 |
| `HybridRouter` | 混合布线 |
| `MultiLayerRouter` | 多层布线 |
| `AllAngleRouter` | 全角度布线 |
| `OptoElectricalRouter` | 光电协同 |
| `GdsfactoryStyleRouter` | gdsfactory 风格 |
| `PhaseMatchedRouter` | 相位匹配 |
| `RFGSGRouter` | RF GSG |
| `BusRouter` | 总线布线 |
| `CommercialRouter` | 商业工具封装 |

**继承扩展模式**（真实）：新布线器可继承 `GridRouter` 基类（如 `JPSRouter(GridRouter)`），复用网格与约束逻辑。

### 5.4 添加新布线策略步骤（示例）

```python
# 示例：新增曼哈顿布线器
class ManhattanRouter:
    """曼哈顿直角布线器。

    生成 L 形 / Z 形直角路径，适用于密集直角布线场景。
    来源: VLSI 布线经典算法
    """

    def route(self, start: tuple, end: tuple) -> list[tuple]:
        """生成直角路径点列表。"""
        ...
        return [(x1, y1), (x2, y2), ...]
```

在 `route_circuit` 中扩展 `_SUPPORTED_MODES` 与 mode 分支，或作为 `polaris-router-advanced` 新增类。

### 5.5 损耗模型约束（R02）

布线损耗必须可溯源，来源 `modules/route/src/polaris_route/__init__.py` 真实参数：

- 传播损耗 `3.0 dB/cm`：Soref et al. 1993 IEEE Proc. 41(9)
- 单弯损耗 `0.05 dB`：SiEPIC EBeam PDK 通用路径上界
- 单次交叉损耗 `0.3 dB`：SiEPIC EBeam PDK crossing_te1550
- 器件插入损耗：从 `device.params.insertion_loss_db` 提取

新布线器的损耗模型必须引用真实文献，禁止编造损耗常数。

---

## 第 6 章：添加新流水线阶段

### 6.1 STAGE_EXECUTORS 真实结构

`polaris-flow` 提供 **12 个标准化阶段**（R392 工业光电子设计流程：先仿真后版图，GDS 导出为最后一步），来源 `modules/flow/src/polaris_flow/executors.py`（真实代码）：

```python
STAGE_EXECUTORS: dict[int, callable] = {
    1: stage1_pdk,            # PDK 器件目录加载
    2: stage2_circuit,        # 电路规格构建
    3: stage3_simulation,     # 原理图级电路仿真（版图前）
    4: stage4_inverse,        # AI 逆向设计（版图前）
    5: stage5_placement,      # 器件布局
    6: stage6_routing,        # 波导布线
    7: stage7_postlayout_sim, # 版图后仿真（含布线寄生）
    8: stage8_drc_lvs,        # DRC/LVS 约束检查
    9: stage9_yield,          # 蒙特卡洛良率分析（流片前签核）
    10: stage10_opto_electrical, # 光电协同仿真
    11: stage11_quantum,      # 量子光子验证
    12: stage12_gds,          # GDS 版图导出（流片交付最后一步）
}
```

**关键约定**（来源 `executors.py` docstring）：

1. 阶段函数签名统一为 `stageN_xxx(recipe, workspace, prev_outputs) -> dict`
2. 由 `JobScheduler` 按 `recipe.enabled_stages` 顺序调用
3. 阶段间通过 `prev_outputs` 字典传递数据，**不依赖全局状态或副作用**
4. 所有阶段输出必须可 JSON 序列化（dict/list/str/int/float/bool）
5. `CircuitSpec` 对象须序列化为 dict 再传递
6. 禁止 fall-back（R03）：错误时 raise，依赖输入缺失 raise `ValueError`

### 6.2 阶段实现拆分结构

来源 `executors.py` docstring「拆分结构」，12 阶段按职责分布到 7 个子模块：

| 子模块 | 阶段 | 职责 |
|--------|------|------|
| `stage_serializers` | — | CircuitSpec/DeviceSpec 序列化与依赖输入校验 |
| `stage_input` | 1-2 | PDK 器件目录加载 + 电路规格构建 |
| `stage_verification` | 3, 7-8 | 原理图仿真 + 版图后仿真 + DRC/LVS |
| `stage_advanced` | 4, 11 | AI 逆向设计 + 量子光子验证 |
| `stage_physical` | 5-6 | 器件布局 + 波导布线 |
| `stage_yield` | 9 | 蒙特卡洛良率分析 |
| `stage_output` | 10, 12 | 光电协同仿真 + GDS 版图导出 |

`executors.py` 本身是 **facade**，仅 re-export 实际实现，保持 `from polaris_flow.executors import X` 路径不变。

### 6.3 添加新阶段步骤（示例）

**步骤 1**：在对应职责子模块（如 `stage_output.py`）实现新阶段函数：

```python
# 示例：新增 stage13_thermal（热仿真阶段，位于 GDS 导出之后）
def stage13_thermal(recipe, workspace, prev_outputs: dict) -> dict:
    """阶段 13：热仿真。

    Args:
        recipe: 作业配方（Recipe dataclass）。
        workspace: 工作区路径。
        prev_outputs: 上游阶段输出（含 stage12_gds 的版图数据）。

    Returns:
        dict: {thermal_map, max_temp_c, hotspots}

    Raises:
        ValueError: 依赖输入缺失（R03 禁止 fall-back）。
    """
    gds_output = _require_input(prev_outputs, "stage12_gds")  # 真实依赖校验函数
    ...
    return {
        "thermal_map": [...],
        "max_temp_c": 85.0,
        "hotspots": [...],
    }
```

**步骤 2**：在 `executors.py` 注册（真实 `dict[int, callable]` 模式）：

```python
from polaris_flow.stage_output import stage13_thermal  # 追加导入

STAGE_EXECUTORS: dict[int, callable] = {
    1: stage1_pdk,
    ...
    12: stage12_gds,
    13: stage13_thermal,  # 新增
}
```

**步骤 3**：在 `__all__` 中导出 `stage13_thermal`。

**步骤 4**：在 `Recipe.enabled_stages` 中启用（来源 `modules/flow/src/polaris_flow/recipe.py`）：

```python
@dataclass
class Recipe:
    enabled_stages: list[int] = field(
        default_factory=lambda: list(range(1, 13))  # 默认 1-12
    )
```

使用时显式指定：

```python
recipe = Recipe(
    preset_id="mzi",
    enabled_stages=[1, 2, 3, 5, 6, 12, 13],  # 跳过部分阶段，启用新阶段
)
```

### 6.4 Recipe 配置

来源 `modules/flow/src/polaris_flow/recipe.py`，`Recipe` 是可序列化的流水线配置 dataclass：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `preset_id` | `str` | `"mzi"` | 电路预设 ID |
| `platform` | `str` | `"SOI"` | 工艺平台 |
| `placement_algo` | `str` | `"analytical"` | 布局算法 |
| `router_algo` | `str` | `"curvy"` | 布线算法 |
| `sim_config` | `SimConfig` | — | 仿真参数 |
| `enabled_stages` | `list[int]` | `[1..10]` | 启用阶段 |
| `canvas_w/h` | `float` | 1000/600 | 画布尺寸 |
| `custom_circuit` | `dict \| None` | `None` | 自定义电路 |

支持 JSON 与 YAML 双向序列化（YAML 采用简单缩进格式，不依赖 PyYAML）。

---

## 第 7 章：添加新 GUI 功能

### 7.1 Web Server 路由架构

`polaris-gui` 的 Web Server 采用 **HTTP 请求处理器 + 路由分发 + 业务逻辑分层** 模式，来源 `modules/gui/src/polaris_gui/routes.py`：

```python
class PolarisHTTPRequestHandler(D10RoutesMixin, BaseHTTPRequestHandler):
    """PoLaRIS HTTP 请求处理器。

    路由分发层，业务逻辑由 handlers.py + editor_handlers.py 提供。
    """
```

**分层职责**（来源 `routes.py` docstring）：

- `routes.py`：HTTP 协议层，GET/POST 路由分发
- `routes_d10.py`：D10 增强 API（`D10RoutesMixin`）
- `handlers.py`：业务逻辑（流水线运行、showcase、作业管理）
- `editor_handlers.py`：编辑器交互逻辑
- `web_server.py` / `web_server_helpers.py` / `web_server_presets.py`：服务器主体与辅助（`web_server_pipeline.py` 已于 R392 删除，功能归并 `handlers.py`）

### 7.2 现有 API 端点（真实清单）

来源 `routes.py` docstring，D10 GUI 增强 API：

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/upload_gds` | 上传 GDSII/OASIS/KLayout 脚本 |
| POST | `/api/run_placement` | 运行布局（polaris-place analytical） |
| POST | `/api/run_routing` | 运行布线（polaris-route curvy） |
| POST | `/api/run_drc` | 运行 DRC 检查（polaris-drc） |
| GET | `/api/results/{task_id}` | 获取任务结果 |
| GET | `/api/uploads` | 列出已上传文件 |
| POST | `/api/editor/device` | 添加器件到场景 |
| POST | `/api/editor/device/move` | 移动器件 |
| POST | `/api/editor/device/delete` | 删除器件 |
| GET | `/api/editor/scene` | 渲染场景图 |
| GET | `/api/editor/devices` | 列出场景器件 |
| POST | `/api/editor/routes` | 设置布线路径可视化 |
| POST | `/api/editor/drc` | 设置 DRC 高亮 |
| POST | `/api/editor/export_klayout` | 导出 KLayout Python 脚本 |

### 7.3 添加新 GUI 端点步骤（示例）

**步骤 1**：在 `handlers.py` 实现业务逻辑函数：

```python
# 示例：新增良率分析端点
def _run_yield_analysis(body: dict) -> dict:
    """调用 polaris-yield 执行良率分析。"""
    from polaris_yield import yield_analysis
    result = yield_analysis(body["circuit"], n_samples=body.get("n_samples", 1000))
    return {"success": True, "yield": result["yield_pct"]}
```

**步骤 2**：在 `routes.py` 或 `routes_d10.py` 注册路由分发：

```python
# 示例：在 PolarisHTTPRequestHandler 中添加路由分支
def _handle_post(self, path: str, body: dict) -> None:
    if path == "/api/run_yield":
        result = _run_yield_analysis(body)
        self._send_json(result)
    elif path == "/api/upload_gds":
        ...
```

**步骤 3**：补充测试。GUI 模块现有 30 项测试。

### 7.4 版图编辑器扩展

`LayoutEditor` 与 `MacroIDE` 是 GUI 核心组件（来源 `modules/README.md` GUI 模块），文件来源 Glob：

- `layout_editor.py`：版图编辑器主体
- `interactive.py` / `interactive_commands.py` / `interactive_macro.py`：交互命令与 Macro IDE
- `interactive_snap_airline.py`：吸附与连线
- `interactive_objects.py`：场景对象管理
- `widgets.py` / `dialogs.py`：UI 组件
- `editor_circuits.py` / `editor_handlers.py`：编辑器电路与处理器

---

## 第 8 章：模块开发规范

### 8.1 命名规范

来源 `docs/contributing_guide.md` §4.3 与 `modules/README.md`：

| 对象 | 规范 | 示例 |
|------|------|------|
| 模块目录 | `modules/<功能名>/` | `modules/rcwa/` |
| Python 包 | `polaris_<功能名>` | `polaris_rcwa` |
| 导入 | `from polaris_<功能名> import <API>` | `from polaris_rcwa import solve_rcwa` |
| 类 | PascalCase | `AnalyticalConfig` / `EulerSpiral` |
| 函数/方法 | snake_case | `solve_redheffer` / `run_drc` |
| 常量 | UPPER_SNAKE | `DENSITY_MIN` / `CFL_FACTOR` |
| 私有 | 前缀 `_` | `_parse_netlist` |

### 8.2 文件结构规范

```
modules/<功能名>/
├── src/polaris_<功能名>/
│   ├── __init__.py      # 公共 API + IPO docstring + ≥5 文献 URL
│   ├── core.py          # 核心实现（文件 ≤800 行，超限拆分）
│   └── ...
├── tests/
│   └── test_<功能名>.py
├── c_api/
│   └── <功能名>.h       # C ABI 头文件（IPO 注释）
└── pyproject.toml       # 模块独立配置
```

**R11 质量门禁**（来源 `AGENTS.md` §8、`modules/README.md`）：

| 指标 | 阈值 |
|------|------|
| 函数长度 | ≤ 80 行 |
| 文件长度 | ≤ 800 行（超限按功能拆分，如 place 的 analytical.py 拆 5 文件） |
| 圈复杂度 | ≤ 15 |
| 测试覆盖率 | ≥ 90% |

### 8.3 代码质量门禁

来源 `pyproject.toml` 与 `docs/contributing_guide.md` §4.2：

```bash
ruff check src/ modules/        # 风格检查（line-length=100, target py311）
mypy src/                       # 类型检查（python_version=3.11）
pytest -ra                      # 测试
pytest --cov=polaris_<name> --cov-report=term-missing  # 覆盖率 ≥90%
```

ruff 启用规则集：`E` / `F` / `W` / `I` / `UP` / `B`（来源 `[tool.ruff.lint] select`）。`__init__.py` 忽略 `F401`（re-export 模式，来源 `[tool.ruff.lint.per-file-ignores]`）。

### 8.4 学术诚信（R02）

来源 `docs/contributing_guide.md` §5 与 `AGENTS.md` §6：

- **每个模块 docstring 含 ≥ 5 个文献 URL**（来源 R02，所有现有模块已遵守）
- 引用须标注：作者、标题、年份、URL/DOI
- 所有参数/公式/算法必须真实可溯源，**禁止编造**
- 创新点标注 `*创新*` 并记录底层逻辑与支持理论
- 优先级：顶会论文 > 大厂官方博客 > 海外社区 > 国内内容（R01）

### 8.5 禁止 fall-back（R03）

来源 `docs/contributing_guide.md` §6 与 `AGENTS.md` §5：

```python
# 禁止：静默吞异常
except Exception:
    pass

# 禁止：返回 None / [] 掩盖错误
def solve():
    try:
        ...
    except Exception:
        return None   # ❌

# 正确：raise 明确异常，业务层处理
def solve():
    if not config_valid:
        raise ValueError("配置无效：缺少波导宽度参数")
```

**设计原则**：跑不通就是业务设计有问题，返回告警即可，由业务层处理。禁止用假数据"让程序跑通"。

### 8.6 GPU 战略（R04 不可撤销）

来源 `docs/contributing_guide.md` §8 与 `AGENTS.md` §9：

- 纯 **NumPy / SciPy / JAX(CPU)** 实现
- 禁止 CuPy / CUDA / ROCm / AppleMetal 等所有 GPU 后端
- 禁止 FP16 / BF16 半精度、多卡 GPU 分布式
- GPU 相关功能点标记 `🚫不参与`，不计入覆盖率
- 选择最合适的算法和数据结构，优先使用三方库，避免低效率低性能

---

## 第 9 章：测试新模块

### 9.1 测试配置

来源 `pyproject.toml` → `[tool.pytest.ini_options]`：

- 测试目录：`tests/`
- pythonpath：`src`、`3dtool`
- `addopts = "-ra"`
- 慢测试标记：`@pytest.mark.slow`，可用 `-m "not slow"` 跳过

运行方式：

```bash
pytest modules/<name>/tests/         # 单模块测试
pytest modules/<name>/tests/ -v      # 详细
pytest -m "not slow"                 # 跳过慢测试
pytest --cov=polaris_<name>          # 覆盖率
```

### 9.2 单元测试示例

```python
# modules/<功能名>/tests/test_<功能名>.py
import numpy as np
import pytest
from polaris_<name> import new_api


def test_new_api_basic():
    result = new_api(input_data)
    assert result is not None
    assert "expected_key" in result


def test_new_api_invalid_input():  # R03 禁止 fall-back
    with pytest.raises(RuntimeError):
        new_api(invalid_input)


@pytest.mark.slow
def test_new_api_full_simulation():
    """慢测试：完整仿真（可用 -m "not slow" 跳过）。"""
    result = new_api(large_input)
    assert result["converged"] is True
```

### 9.3 集成测试示例

针对流水线阶段的集成测试（来源 `executors.py` 阶段签名）：

```python
def test_new_stage_integration():
    from polaris_flow.executors import stage13_thermal
    from polaris_flow.recipe import Recipe

    recipe = Recipe(preset_id="mzi", enabled_stages=[1, 2, 3, 12, 13])
    prev_outputs = {"stage12_gds": {...}}  # 模拟上游输出
    result = stage13_thermal(recipe, "out/test", prev_outputs)
    assert result["max_temp_c"] > 0
    assert "thermal_map" in result


def test_new_stage_missing_dependency():  # R03
    import pytest
    with pytest.raises(ValueError):
        stage11_thermal(recipe, "out", {})  # 缺 stage7_gds
```

### 9.4 测试规范引用

详细测试规范参见 [测试指南](testing_guide.md)。质量门禁：覆盖率 ≥ 90%（来源 `AGENTS.md` §8）。

---

## 第 10 章：提交新模块

### 10.1 V8 极简工作流

来源 `.trae/rules/R11-工作流规范.md` 与 `AGENTS.md` §2：

- **只用 `main` 分支**，禁止 dev/feature/worktree
- 会话启动检查：`git branch --show-current`（必须在 main）
- **禁止 force push main**（R382 v2.0，2026-07-06）
- clone 后必须 fetch 所有远程分支：`git fetch origin 'refs/heads/*:refs/remotes/origin/*'`

### 10.2 提交规范

每个小任务完成后立即执行（来源 R11 §2）：

```bash
git add <精确文件名>   # 禁止 git add -A
git commit -m "<type>: <简述>"
git push origin main   # 禁止 --force
```

**commit message 类型**（来源 `docs/contributing_guide.md` §3.3）：

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat:` | 新功能 | `feat: 新增 RCWA 求解器子模块` |
| `fix:` | Bug 修复 | `fix: 修复 Euler 螺旋曲率半径下溢` |
| `docs:` | 纯文档变更 | `docs: 更新模块开发指南` |
| `refactor:` | 重构（无行为变更） | `refactor: 提取 DRC 规则公共基类` |
| `test:` | 测试相关 | `test: 补充 FDE 求解器回归测试` |
| `chore:` | 构建/工具链 | `chore: 升级 ruff target-version` |

> **强制**：commit message 类型必须与内容一致。禁止用 `docs:` 标注含代码变更的 commit。

### 10.3 任务派发前核查

来源 R11 §3、`AGENTS.md` §3，**必须依次执行**：

```bash
git log --all --oneline --follow -- <文件>  # 查 git 历史
grep <功能名> 操作记录.md                     # 查操作记录
ls <目标路径>                               # 查现有文件
```

| 核查结果 | 行动 |
|---------|------|
| git 有 commit + 操作记录有 | 跳过，禁止重复实现 |
| git 无 + 操作记录无 | 可以派发 |
| 目标文件存在 | 必须 Read 后再决定 |

### 10.4 提交前检查清单

来源 `docs/contributing_guide.md` §10，提交代码前逐项确认：

- [ ] 代码通过 `ruff check`（line-length=100，规则集 E/F/W/I/UP/B）
- [ ] 代码通过 `mypy`（python_version=3.11）
- [ ] 测试通过 `pytest -ra`
- [ ] 测试覆盖率 ≥ 90%
- [ ] 无 `TODO` / `FIXME` / `HACK` 残留（R05）
- [ ] 函数 ≤ 80 行 / 文件 ≤ 800 行 / 圈复杂度 ≤ 15
- [ ] docstring 含 ≥ 5 个文献 URL（R02）
- [ ] 创新点标注 `*创新*` 并记录底层逻辑（R02）
- [ ] 无 fall-back（无 `except: pass` / `return None` / `return []`）（R03）
- [ ] 无 GPU 代码（无 CuPy/CUDA/ROCm）（R04）
- [ ] 操作记录已追加到 `操作记录.md`（R07）
- [ ] commit message 类型与内容一致（R11）
- [ ] 精确 `git add <文件名>`（禁止 `git add -A`）（R11）
- [ ] `git push origin main`（禁止 `--force`）（R11）

### 10.5 操作记录

来源 R07 与 R11 §4，每个小任务完成后 **5 分钟内** 追加到 `操作记录.md`，每条记录必须包含：

- **轮次编号**
- **交付文件**（精确路径）
- **测试结果**（精确数字，禁止模糊描述）
- **创新点**（如有，标注 `*创新*` 及底层逻辑）
- **文献引用**（R02，≥ 5 条 URL）
- **规则依据**
- **无 fall-back 声明**

时间戳格式（来源 R12）：`### YYYY-MM-DD HH:MM 轮次编号`

### 10.6 监控脚本

来源 R11 §5、`AGENTS.md` §11：

| 脚本 | 轮询 | 功能 |
|------|------|------|
| `scripts/auto_commit.py V8` | 6 分钟 | 检测变更 → 提交 → push origin main |
| `scripts/keepalive.sh` | 5 分钟 | touch 文件防超时 |

会话启动第一件事（来源 `AGENTS.md` §1）：

```bash
nohup bash scripts/keepalive.sh > /dev/null 2>&1 &
git branch --show-current
ps aux | grep auto_commit
ps aux | grep keepalive
```

---

## 附录 A：Python ↔ C ABI 对照

PoLaRIS 提供 C ABI 公共层（来源 `modules/README.md`「C ABI 公共层」）：

- `modules/_c_abi/polaris_types.h`：统一类型（`polaris_circuit_t` / `polaris_device_spec_t` / `polaris_connection_t` / `polaris_tensor_t` / `polaris_placement_result_t` / `polaris_routing_result_t` / `polaris_result_t` / `polaris_error_t`）
- `modules/_c_abi/polaris_error.h`：统一错误处理（`POLARIS_OK`=0 / `POLARIS_ERR_INVALID` / `POLARIS_ERR_NOTFOUND` / ...）

**设计原则**（来源 `modules/README.md`）：

1. Python 函数 ↔ C 函数一一对应，函数名 `polaris_<module>_<verb>_<noun>`
2. 纯数据结构跨语言传递，无 Python 对象泄漏
3. 统一错误码，所有 C 函数返回 `polaris_error_t`
4. 显式生命周期，caller 用 `polaris_*_free()` 释放返回的结构

新模块若需 C ABI，需在 `c_api/<name>.h` 顶部注释标注 IPO 三段式，并保持与 Python API 一一对应。

---

## 附录 B：业务侧调用方式

来源 `modules/README.md`「业务侧使用方式」：

**方式 A：orchestrator 一键调用（推荐）**

```python
from polaris_orchestrator import run_eda_flow
from polaris_core import make_device, make_circuit

circuit = make_circuit('MZI', [...], [...], canvas_w=500, canvas_h=300)
result = run_eda_flow(circuit, 'out/my_design')
# result = {stages: [...], n_success: 9, n_failed: 0, total_duration: 26.04}
```

**方式 B：精细控制，直接调用子模块**

```python
from polaris_place import place_circuit
from polaris_route import route_circuit
placement = place_circuit(circuit, mode='analytical')
routing = route_circuit(circuit, placement['placements'])
```

---

## 规则来源索引

本指南所有规则均可溯源至以下文件：

| 规则 | 来源文件 | 核心内容 |
|------|---------|---------|
| R01 | `.trae/rules/R01-方案检索.md` | 动手前必检索权威资源 |
| R02 | `.trae/rules/R02-学术诚信.md` | 参数/公式可溯源，≥5 文献 URL，创新标注 `*创新*` |
| R03 | `.trae/rules/R03-禁止fall-back.md` | 失败即 raise，禁止静默兜底与假数据 |
| R04 | `.trae/rules/R04-不参与GPU.md` | 不参与 GPU 计算，纯 CPU 实现 |
| R05 | `.trae/rules/R05-Bug必须修复.md` | 发现即修，附回归测试，禁止 TODO 残留 |
| R07 | `.trae/rules/R07-操作记录.md` | 每任务追加操作记录 |
| R11 | `.trae/rules/R11-工作流规范.md` | V8 极简工作流（main 分支 / 精确 add / 禁止 force push） |
| R12 | `.trae/rules/R12-时间戳规范.md` | 时间戳格式 `YYYY-MM-DD HH:MM:SS CST` |
| 质量门禁 | `AGENTS.md` §8 | 函数≤80行 / 文件≤800行 / 圈复杂度≤15 / 覆盖率≥90% |
| 工程配置 | `pyproject.toml` | Python ≥3.9 / ruff / mypy / pytest 配置 |
| 模块清单 | `modules/README.md` | 33 子模块真实结构（v5.1） |

---

## 学术诚信声明（R02/R03）

- 所有接口模式从真实代码提取（`modules/pdk/`、`modules/flow/executors.py`、`modules/optimizer/`、`modules/route/`、`modules/fdtd/`、`modules/gui/routes.py`）
- 模块清单从 `modules/README.md` 真实提取（33 模块 / 289 文件 / 99,017 行 / 1,613 测试）
- 优化器清单从 Grep `class.*Optimizer` 真实提取（11 个 Optimizer 类 + HJSolver + FeedbackAdapter = 12 种）
- 布线器清单从 Grep `class.*Router` 真实提取
- STAGE_EXECUTORS 从 `executors.py` 真实提取（`dict[int, callable]`，12 阶段）
- 标注「示例」的代码片段为演示用途，未与真实代码 1:1 对应
- 禁止编造扩展点 API；扩展示例均基于真实模式改写
