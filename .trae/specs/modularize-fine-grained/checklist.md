# Checklist

## 细粒度拆分（18 个子模块）
- [ ] modules/drc/ — DRC 设计规则检查（从 verify 拆出）
- [ ] modules/lvs/ — LVS 网表比对（从 verify 拆出）
- [ ] modules/sparam/ — 频域 S 参数（从 sim 拆出）
- [ ] modules/fdtd/ — 时域 FDTD（从 sim 拆出）
- [ ] modules/fde/ — 频域本征模（从 sim 拆出）
- [ ] modules/eme/ — 本征模展开（从 sim 拆出）
- [ ] modules/bpm/ — 光束传播法（从 sim 拆出）
- [ ] modules/fdfd/ — 频域有限差分（从 sim 拆出）
- [ ] modules/pam4/ — PAM4 信号仿真（从 sim 拆出）
- [ ] modules/boson/ — 玻色采样（从 quantum 拆出）
- [ ] modules/klm/ — KLM CNOT（从 quantum 拆出）
- [ ] modules/gdsio/ — GDSII 导入导出（从 pdk 拆出）
- [ ] 旧的 verify/sim/quantum 已删除

## input-process-output 文档
- [ ] 每个子模块 __init__.py 顶部三段式文档（Input/Process/Output）
- [ ] 每个子模块 c_api/<name>.h 顶部三段式文档
- [ ] 文档含输入参数类型/单位/来源
- [ ] 文档含处理算法/公式/文献
- [ ] 文档含输出结果类型/单位/物理意义

## 独立管理
- [ ] 每个子模块有独立 pyproject.toml
- [ ] 每个子模块有独立 tests/
- [ ] 每个子模块有独立 c_api/<name>.h
- [ ] 每个子模块可独立 import

## 编排层与业务示例
- [ ] orchestrator 调用18个子模块
- [ ] main.py 调用18个子模块
- [ ] main.c 包含18个头文件

## 端到端验证
- [ ] 18个子模块独立 import 通过
- [ ] orchestrator 一键调用成功
- [ ] modules/README.md 更新（18子模块+IPO）
- [ ] git add + commit + push
