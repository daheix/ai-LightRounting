# simulation/ — 仿真类工具

存放光子电路仿真相关的第三方工具说明。

## 工具清单

### meep

- **用途**: FDTD 电磁仿真（器件参数验证）
- **状态**: ❌ 未安装
- **来源**: https://meep.readthedocs.io/
- **安装**: `pip install meep`
- **项目使用**: 器件级 FDTD 仿真（项目未使用，预留）

### simphony

- **用途**: 光子电路 S 参数仿真
- **状态**: ✅ 已装 0.6.0
- **来源**: https://simphonyphotonics.readthedocs.io/
- **安装**: `pip install simphony`
- **项目使用**: `src/polaris/sim/simulator.py` 的 `simphony_models()` 集成 SiEPIC 模型库

### sax

- **用途**: 光子电路频率域仿真
- **状态**: ✅ 已装 0.14.7
- **来源**: https://flaport.github.io/sax/
- **安装**: `pip install sax`
- **项目使用**: `src/polaris/sim/cascade.py` 优先用 sax，回退到纯 numpy 复刻
- **依赖链**: jax + jaxlib + optax + pydantic + pandas + xarray + scikit-rf（约 200-400 MB）
- **复刻品**: `../pycopy/pyCopySAX/`（子网络增长算法，100% 纯 numpy 复刻）

### SiPANN

- **用途**: 硅光器件模型（耦合器、环谐振器）
- **状态**: ❌ 未安装
- **来源**: https://sipann.readthedocs.io/
- **安装**: `pip install SiPANN`
- **项目使用**: `src/polaris/sim/models.py` 复刻 SiPANN 的 S 参数模型
- **复刻品**: `../pycopy/pyCopySiPANN/`（10 个 S 参数模型，纯 Python 复刻）

### femwell

- **用途**: FEM 模式求解器
- **状态**: ❌ 未安装
- **来源**: https://helgegehring.github.io/femwell/
- **安装**: `pip install femwell`
- **项目使用**: FEM 模式求解器（项目未使用，预留）
- **复刻品**: `../pycopy/pyCopyFemwell/`（预留，有效折射率法）

### meow

- **用途**: 模式求解器
- **状态**: ❌ 未安装
- **来源**: https://github.com/flaport/meow
- **安装**: `pip install meow`
- **项目使用**: 模式求解器（项目未使用，预留）
- **复刻品**: `../pycopy/pyCopyMeow/`（预留）
