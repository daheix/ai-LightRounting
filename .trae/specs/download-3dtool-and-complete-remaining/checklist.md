# Checklist

## 阶段一：3dtool 仓库下载与融合
- [x] 磁盘空间 ≥4G 可用（释放 8.4G，从 60M → 4.9G）
- [x] daheix/3dtool 仓库完整克隆（用 token 认证，匿名返回 404，仓库为私有）
- [x] 3dtool-appimage 恢复成功（AppRun + python-runtime + python-site-packages + bin 精简解压）
- [x] AppRun python3 可调用（Python 3.14.4 验证通过）
- [x] 3dtool-appimage 融合到 workspace/3dtool/ 目录
- [x] 3dtool/wheels/install.sh 与 3dtool-appimage 共存正常（15 个 wheel + AppDir 精简版）
- [x] AppRun python3 可调用且版本为 3.14（验证通过）
- [x] 3dtool-appimage python site-packages 含 numpy/scipy/torch 等 10 核心包（klayout/sax 等专有依赖在 wheels/ 目录）

## 阶段二：P0 级 R03 违规修复
- [x] verilog_a.py 无合成脉冲信号 fall-back（删除 np.zeros 合成，改为 _parse_ngspice_rawfile 真实解析）
- [x] verilog_a.py Ngspice 输出解析正确或 raise 告警（5 个辅助函数，解析失败 raise RuntimeError）
- [x] calibration.py 无 except Exception: continue 静默吞异常（拆分 3 类具体异常）
- [x] gdsfactory_integration.py 无 except Exception: return False/[]/{} 静默兜底（3 处全部改 raise）
- [x] data_loader.py 无 except Exception: continue/warning 静默处理（区分 OSError 可恢复/ValueError 不可恢复）
- [x] 所有修改文件 py_compile 通过（10/10 通过）

## 阶段三：P0 级多物理耦合层补充
- [x] src/polaris/sim/multiphysics/__init__.py 创建（90 行，10 篇文献）
- [x] electro_optic.py 实现等离子体色散效应（Soref-Bennett 1987 公式）
- [x] electro_optic.py 连接 DDM 载流子 → 折射率变化（apply_electro_optic_coupling）
- [x] electro_optic.py 文献引用 7 篇（≥5 达标）
- [x] thermo_optic.py 实现热光效应（Cocorullo 1999，dn/dT=1.86e-4 K^-1）
- [x] thermo_optic.py 连接 HEAT 温度场 → 折射率变化（apply_thermo_optic_coupling）
- [x] thermo_optic.py 文献引用 7 篇（≥5 达标）
- [x] multiphysics 模块 py_compile 通过

## 阶段四：P1 级问题整改
- [x] alpha_chip.py 复用 AlphaChipEdgeGNN（不再自实现简化版 GNN）
- [x] alpha_chip.py 复用 PPOAgent（不再使用简化版 REINFORCE）
- [x] C05 频域扫描集成 jax.vmap 并行（_sweep_wavelength_jax + jax.pure_callback）
- [x] RewardNormalizer 类实现（Welford 算法运行均值方差归一化）
- [x] ExpertRewardShaper 集成 RewardNormalizer（enable_normalization 参数）
- [x] 所有修改文件 py_compile 通过

## 阶段五：提交与验证
- [x] ruff check 全部通过（修复 alpha_chip.py 2 个未使用导入后 All checks passed）
- [x] py_compile 全部修改文件通过（10/10 通过）
- [x] git add 精确文件 + commit + push origin main（cherry-pick 2 提交，推送 1992c39..f67107a）
- [x] 操作记录.md 更新本轮工作记录
