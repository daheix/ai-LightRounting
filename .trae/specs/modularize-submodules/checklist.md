# Checklist

## 子模块划分（8 个独立子模块）
- [ ] modules/core/ — polaris-core 核心数据结构（CircuitSpec/DeviceSpec/Tensor）
- [ ] modules/pdk/ — polaris-pdk PDK 管理（4 平台 36 器件 + GDSII 导入导出）
- [ ] modules/place/ — polaris-place AI 布局（AlphaChip Edge-GNN + PPO + 解析布局）
- [ ] modules/route/ — polaris-route 智能布线（curvy + 全角度 + 对角线 + JPS）
- [ ] modules/sim/ — polaris-sim 仿真（FDTD/FDE/EME/BPM/频域 S 参数/PAM4）
- [ ] modules/verify/ — polaris-verify 验证（DRC/LVS/物理规则/制造约束）
- [ ] modules/inverse/ — polaris-inverse 逆向设计（JAX Adjoint + 拓扑优化）
- [ ] modules/quantum/ — polaris-quantum 量子光子（玻色采样/KLM/HOM/BB84）
- [ ] modules/orchestrator/ — 业务编排层（一键调用 8 子模块）

## 每个子模块独立管理
- [ ] 每个子模块有独立 pyproject.toml（可独立 pip install）
- [ ] 每个子模块有独立 src/polaris_<name>/ 目录
- [ ] 每个子模块有独立 tests/ 目录（可独立 pytest）
- [ ] 每个子模块有独立 c_api/<name>.h 头文件

## Python API 稳定性
- [ ] 每个子模块 __init__.py 暴露稳定 API（snake_case 函数名）
- [ ] API 参数用纯数据结构（dict/dataclass/ndarray），无内部对象泄漏
- [ ] 返回值用 JSON-serializable dict 或 numpy ndarray

## C ABI 接口（Python 函数转 C 函数，函数说明一致）
- [ ] modules/_c_abi/polaris_types.h — 统一张量/电路/错误码结构
- [ ] modules/_c_abi/polaris_error.h — 统一错误处理（polaris_error_t）
- [ ] 每个子模块 c_api/<name>.h — C 函数声明，与 Python API 一一对应
- [ ] C 函数命名遵循 polaris_<module>_<verb>_<noun>
- [ ] C 函数参数/返回/异常语义与 Python 完全一致
- [ ] C ABI 用纯数据结构（指针+结构体），无 Python 对象泄漏

## 业务编排层
- [ ] orchestrator 暴露 run_eda_flow(circuit, output_dir) 一键 API
- [ ] 编排顺序：PDK→布局→布线→仿真→验证→GDS→逆向设计→量子
- [ ] 业务侧只需依赖 orchestrator，不直接依赖子模块

## 业务侧真实调用示例
- [ ] examples/business_real_case/main.py — Python 版（100Gbps MZI 设计）
- [ ] examples/business_real_case/main.c — C 版（同样流程）
- [ ] examples/business_real_case/Makefile + README.md
- [ ] Python 版可运行，输出真实结果
- [ ] C 版可编译（至少头文件包含通过）

## API 说明文档
- [ ] modules/README.md — 8 子模块 API 速查表 + C ABI 对照表
- [ ] 每个子模块有 docstring（函数说明、参数、返回、异常）
- [ ] C ABI 头文件有 doxygen 风格注释

## 端到端验证
- [ ] python examples/business_real_case/main.py 8 子模块全部被调用
- [ ] 每个子模块可独立 import + 独立 pytest
- [ ] git add 精确文件 → commit → push origin main（R11）
- [ ] 操作记录.md 追加（R07）
