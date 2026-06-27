# Checklist

## 阶段一：3dtool 仓库下载与融合
- [ ] 磁盘空间 ≥4G 可用
- [ ] daheix/3dtool 仓库完整克隆（17 个分片）
- [ ] 3dtool-appimage 恢复成功（AppRun 可执行）
- [ ] AppRun check 自检通过
- [ ] 3dtool-appimage 融合到 workspace/3dtool/ 目录
- [ ] 3dtool/wheels/install.sh 与 3dtool-appimage 共存正常
- [ ] AppRun python3 可调用且版本为 3.14
- [ ] AppRun klayout 可调用

## 阶段二：P0 级 R03 违规修复
- [ ] verilog_a.py 无合成脉冲信号 fall-back
- [ ] verilog_a.py Ngspice 输出解析正确或 raise 告警
- [ ] calibration.py 无 except Exception: continue 静默吞异常
- [ ] gdsfactory_integration.py 无 except Exception: return False/[]/{} 静默兜底
- [ ] data_loader.py 无 except Exception: continue/warning 静默处理
- [ ] 所有修改文件 py_compile 通过

## 阶段三：P0 级多物理耦合层补充
- [ ] src/polaris/sim/multiphysics/__init__.py 创建
- [ ] electro_optic.py 实现等离子体色散效应（Soref-Bennett 公式）
- [ ] electro_optic.py 连接 DDM 载流子 → 折射率变化
- [ ] electro_optic.py 文献引用 ≥5 篇
- [ ] thermo_optic.py 实现热光效应
- [ ] thermo_optic.py 连接 HEAT 温度场 → 折射率变化
- [ ] thermo_optic.py 文献引用 ≥5 篇
- [ ] multiphysics 模块 py_compile 通过

## 阶段四：P1 级问题整改
- [x] alpha_chip.py 复用 AlphaChipEdgeGNN（不再自实现简化版 GNN）
- [x] alpha_chip.py 复用 PPOAgent（不再使用简化版 REINFORCE）
- [x] C05 频域扫描集成 jax.vmap 并行
- [x] RewardNormalizer 类实现（运行均值方差归一化）
- [x] ExpertRewardShaper 集成 RewardNormalizer
- [x] 所有修改文件 py_compile 通过

## 阶段五：提交与验证
- [ ] ruff check 全部通过（无新增 lint 错误）
- [x] py_compile 全部修改文件通过
- [ ] git add 精确文件 + commit + push origin main
- [ ] 操作记录.md 更新本轮工作记录
