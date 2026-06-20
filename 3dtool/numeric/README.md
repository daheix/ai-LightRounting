# numeric/ — 数值计算类工具

存放数值计算与几何运算相关的第三方工具说明。

**规则 5.2**：所有工具均为必装依赖，无可选依赖。

## 工具清单

### numpy

- **用途**: 数值计算、矩阵运算
- **状态**: ✅ 已装 2.4.6（必装依赖）
- **来源**: https://numpy.org/
- **安装**: `pip install numpy`
- **项目使用**: 全项目核心依赖

### scipy

- **用途**: 优化求解、信号处理
- **状态**: ✅ 已装 1.17.1（必装依赖）
- **来源**: https://scipy.org/
- **安装**: `pip install scipy`
- **项目使用**: 优化求解

### shapely

- **用途**: 几何运算（多边形、缓冲区、相交检测）
- **状态**: ✅ 已装 2.1.2（必装依赖）
- **来源**: https://shapely.readthedocs.io/
- **安装**: `pip install shapely`
- **项目使用**: 几何运算，gdsfactory 依赖，constraint_checker 可选用

