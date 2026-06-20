# simulation/ — 仿真类工具

存放光子电路仿真相关的第三方工具说明。

**规则 5.2**：核心仿真工具（simphony/sax）为必装依赖。SiPANN 因依赖 tensorflow 无 Python 3.14 支持，在 Python 3.10-3.13 环境下必装。meep/femwell/meow 项目未使用，预留。

## 工具清单

### meep

- **用途**: FDTD 电磁仿真（器件参数验证）
- **状态**: ⏳ 预留（项目未使用器件级 FDTD）
- **来源**: https://meep.readthedocs.io/
- **安装**: `pip install meep`
- **项目使用**: 器件级 FDTD 仿真（项目未使用，预留）

### simphony

- **用途**: 光子电路 S 参数仿真
- **状态**: ✅ 已装 0.7.3（必装依赖）
- **来源**: https://simphonyphotonics.readthedocs.io/
- **安装**: `pip install simphony`
- **项目使用**: `src/polaris/sim/simulator.py` 的 `simphony_models()` 集成 SiEPIC 模型库

### sax

- **用途**: 光子电路频率域仿真
- **状态**: ✅ 已装 0.14.7（必装依赖）
- **来源**: https://flaport.github.io/sax/
- **安装**: `pip install sax`
- **项目使用**: `src/polaris/sim/cascade.py` 优先用 sax，回退到纯 numpy 复刻
- **依赖链**: jax + jaxlib + optax + pydantic + pandas + xarray + scikit-rf（约 200-400 MB）
- **复刻品**: `../pycopy/pyCopySAX/`（子网络增长算法，100% 纯 numpy 复刻）

### SiPANN

- **用途**: 硅光器件模型（耦合器、环谐振器）
- **状态**: ⚠️ Python 3.10-3.13 必装（依赖 tensorflow，无 Python 3.14 支持）
- **来源**: https://sipann.readthedocs.io/
- **安装**: `pip install SiPANN`
- **项目使用**: `src/polaris/sim/models.py` 复刻 SiPANN 的 S 参数模型
- **复刻品**: `../pycopy/pyCopySiPANN/`（10 个 S 参数模型，纯 Python 复刻）
- **兼容性说明**: SiPANN 依赖 tensorflow，tensorflow 无 Python 3.14 wheel。在 Python 3.10-3.13 环境下必装。

### femwell

- **用途**: FEM 模式求解器
- **状态**: ⏳ 预留（项目未使用）
- **来源**: https://helgegehring.github.io/femwell/
- **安装**: `pip install femwell`
- **项目使用**: FEM 模式求解器（项目未使用，预留）
- **复刻品**: `../pycopy/pyCopyFemwell/`（预留，有效折射率法）

### meow

- **用途**: 模式求解器
- **状态**: ⏳ 预留（项目未使用）
- **来源**: https://github.com/flaport/meow
- **安装**: `pip install meow`
- **项目使用**: 模式求解器（项目未使用，预留）
- **复刻品**: `../pycopy/pyCopyMeow/`（预留）
